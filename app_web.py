import streamlit as st
import grpc
import time
import batalla_pb2
import batalla_pb2_grpc

# --- 1. CONFIGURACIÓN DE CONEXIÓN A RAILWAY ---
# Pega aquí exactamente el enlace de TCP Proxy que te dio Railway
# Ejemplo: 'roundhouse.proxy.rlwy.net:45821'
URL_RAILWAY = 'crossover.proxy.rlwy.net:49586' 

@st.cache_resource
def obtener_stub():
    # Usamos insecure_channel porque el túnel TCP ya es directo y no usa SSL
    canal = grpc.insecure_channel(URL_RAILWAY)
    return batalla_pb2_grpc.MotorMultijugadorStub(canal)

stub = obtener_stub()

# --- 2. VARIABLES DE SESIÓN ---
# Evita que se borre nuestra info cuando Streamlit recarga la página
if 'fase' not in st.session_state: st.session_state.fase = "LOBBY"
if 'mi_id' not in st.session_state: st.session_state.mi_id = 0
if 'max_jugadores' not in st.session_state: st.session_state.max_jugadores = 0
if 'barcos_colocados' not in st.session_state: st.session_state.barcos_colocados = []

# --- 3. INTERFAZ GRÁFICA ---
st.set_page_config(page_title="Batalla Naval Royale", layout="centered")
st.title("🚢 Batalla Naval Royale (gRPC)")

# FASE 1: LOBBY
if st.session_state.fase == "LOBBY":
    st.subheader("Unirse a la partida")
    # Checamos si el servidor ya tiene un máximo de jugadores
    max_server = stub.ObtenerMaxJugadores(batalla_pb2.Vacio()).valor
    
    if max_server == 0:
        esperados = st.number_input("Eres el primero. ¿Cuántos jugadores serán?", min_value=2, max_value=4, value=2)
    else:
        esperados = max_server
        st.info(f"La partida está configurada para {esperados} jugadores.")
        
    if st.button("Conectar al Servidor"):
        peticion = batalla_pb2.PeticionRegistro(total_esperados=esperados)
        respuesta = stub.RegistrarJugador(peticion)
        st.session_state.mi_id = respuesta.id_jugador
        st.session_state.max_jugadores = esperados
        st.session_state.fase = "ESPERANDO_JUGADORES"
        st.rerun()

# FASE 2: ESPERANDO JUGADORES
elif st.session_state.fase == "ESPERANDO_JUGADORES":
    conectados = stub.ObtenerCantidadConectados(batalla_pb2.Vacio()).valor
    st.info(f"Jugador {st.session_state.mi_id}. Esperando a los demás... ({conectados}/{st.session_state.max_jugadores})")
    
    if conectados >= st.session_state.max_jugadores:
        st.success("¡Todos conectados! Iniciando posicionamiento...")
        time.sleep(2)
        st.session_state.fase = "POSICIONAMIENTO"
        st.rerun()
    else:
        # Recarga automática mientras esperamos
        time.sleep(2)
        st.rerun()

# FASE 3: POSICIONAMIENTO
elif st.session_state.fase == "POSICIONAMIENTO":
    st.subheader(f"Jugador {st.session_state.mi_id} | Coloca tus 10 barcos")
    faltan = 10 - len(st.session_state.barcos_colocados)
    st.write(f"Barcos restantes: **{faltan}**")
    
    tamano = st.session_state.max_jugadores * 3
    
    # Dibujamos el tablero con botones
    for x in range(tamano):
        cols = st.columns(tamano)
        for y in range(tamano):
            with cols[y]:
                if (x, y) in st.session_state.barcos_colocados:
                    st.button("🚢", key=f"btn_{x}_{y}", disabled=True)
                else:
                    if st.button("🌊", key=f"btn_{x}_{y}"):
                        peticion = batalla_pb2.PeticionCoordenada(id_jugador=st.session_state.mi_id, x=x, y=y)
                        stub.ColocarBarco(peticion)
                        st.session_state.barcos_colocados.append((x, y))
                        
                        if len(st.session_state.barcos_colocados) == 10:
                            stub.DeclararListo(batalla_pb2.PeticionJugador(id_jugador=st.session_state.mi_id))
                            st.session_state.fase = "ESPERANDO_LISTOS"
                        st.rerun()

# FASE 4: ESPERANDO QUE TODOS ESTÉN LISTOS
elif st.session_state.fase == "ESPERANDO_LISTOS":
    if stub.TodosListos(batalla_pb2.Vacio()).valor:
        st.session_state.fase = "COMBATE"
        st.rerun()
    else:
        st.warning("Tus barcos están listos. Esperando a que los enemigos terminen de acomodar su flota...")
        # Recarga automática mientras esperamos
        time.sleep(2)
        st.rerun()

# FASE 5: COMBATE
elif st.session_state.fase == "COMBATE":
    st.subheader("⚔️ FASE DE COMBATE ⚔️")
    
    # 1. Checamos si ya hay un ganador
    ganador = stub.ObtenerGanador(batalla_pb2.Vacio()).valor
    if ganador > 0:
        st.success(f"¡EL JUGADOR {ganador} HA GANADO LA PARTIDA!")
        marcador = stub.ObtenerMarcador(batalla_pb2.Vacio()).texto
        st.text(marcador)
        if st.button("Volver a jugar / Reiniciar"):
            st.session_state.clear()
            st.rerun()
    else:
        # 2. Vemos de quién es el turno
        turno = stub.DeQuienEsElTurno(batalla_pb2.Vacio()).valor
        if turno == st.session_state.mi_id:
            st.warning(f"¡ES TU TURNO JUGADOR {st.session_state.mi_id}! Selecciona una coordenada en el Radar.")
        else:
            st.info(f"Turno del Jugador {turno}. Espera a que termine su movimiento...")

        # 3. Traemos el tablero del servidor
        respuesta_tablero = stub.ObtenerEstadoTablero(batalla_pb2.Vacio())
        tamano = st.session_state.max_jugadores * 3
        
        # 4. Dibujamos dos columnas (Defensa Izquierda, Ataque Derecha)
        col_defensa, espacio, col_ataque = st.columns([1, 0.2, 1])
        
        with col_defensa:
            st.markdown("**Tu Flota (Defensa)**")
            for x in range(tamano):
                cols_def = st.columns(tamano)
                for y in range(tamano):
                    valor = respuesta_tablero.filas[x].valores[y]
                    with cols_def[y]:
                        if (x, y) in st.session_state.barcos_colocados:
                            if valor > 0 and str(st.session_state.mi_id) in str(valor):
                                st.button("💥", key=f"def_{x}_{y}", disabled=True) # Nos dieron
                            else:
                                st.button("🚢", key=f"def_{x}_{y}", disabled=True) # Intacto
                        else:
                            if valor == -1:
                                st.button("💧", key=f"def_{x}_{y}", disabled=True) # Fallo enemigo aquí
                            else:
                                st.button("🌊", key=f"def_{x}_{y}", disabled=True) # Agua

        with col_ataque:
            st.markdown("**Radar (Ataque)**")
            for x in range(tamano):
                cols_atk = st.columns(tamano)
                for y in range(tamano):
                    valor = respuesta_tablero.filas[x].valores[y]
                    with cols_atk[y]:
                        
                        # 1. Elegimos qué ícono mostrar según el historial de la casilla
                        if valor == -1:
                            icono = "💧" # Alguien falló aquí antes
                        elif valor > 0:
                            icono = "💥" # Alguien acertó aquí antes
                        else:
                            icono = "🌊" # Agua sin explorar

                        # 2. Si es TU turno, TODOS los botones están activos para que dispares donde quieras
                        if turno == st.session_state.mi_id:
                            if st.button(icono, key=f"atk_{x}_{y}"):
                                peticion = batalla_pb2.PeticionCoordenada(id_jugador=st.session_state.mi_id, x=x, y=y)
                                res_disparo = stub.Disparar(peticion).valor
                                
                                if res_disparo == 8:
                                    st.error("Movimiento inválido.")
                                st.rerun()
                        
                        # 3. Si NO es tu turno, los bloqueamos solo para que no des clics por accidente
                        else:
                            st.button(icono, key=f"atk_{x}_{y}", disabled=True)
            st.markdown("**Radar (Ataque)**")
            for x in range(tamano):
                cols_atk = st.columns(tamano)
                for y in range(tamano):
                    valor = respuesta_tablero.filas[x].valores[y]
                    with cols_atk[y]:
                        # Si ya se disparó ahí, mostramos el resultado
                        if valor == -1:
                            st.button("💧", key=f"atk_{x}_{y}", disabled=True) # Fallo
                        elif valor > 0:
                            st.button("💥", key=f"atk_{x}_{y}", disabled=True) # Acierto
                        else:
                            # Si es agua, habilitamos el botón SOLO si es nuestro turno
                            if turno == st.session_state.mi_id:
                                if st.button("🎯", key=f"atk_{x}_{y}"):
                                    peticion = batalla_pb2.PeticionCoordenada(id_jugador=st.session_state.mi_id, x=x, y=y)
                                    res_disparo = stub.Disparar(peticion).valor
                                    if res_disparo == 8:
                                        st.error("Movimiento inválido.")
                                    st.rerun() # Recargamos para ver el disparo
                            else:
                                st.button("🌊", key=f"atk_{x}_{y}", disabled=True)
        
        st.write("---")
        # --- RECARGA AUTOMÁTICA INTELIGENTE ---
        # Solo recargamos automáticamente si NO es tu turno. 
        # Si es tu turno, la pantalla se queda quieta para dejarte apuntar.
        if turno != st.session_state.mi_id:
            with st.spinner("Esperando el movimiento del enemigo..."):
                time.sleep(2)
                st.rerun()
