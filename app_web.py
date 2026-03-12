import streamlit as st
import grpc
import time
import batalla_pb2
import batalla_pb2_grpc

# --- 1. CONFIGURACIÓN DE CONEXIÓN A RAILWAY ---
# Usamos el puerto 443 y credenciales SSL porque Railway es seguro por defecto
URL_RAILWAY = 'batallanaval-grpc-production.up.railway.app:443'

@st.cache_resource
def obtener_stub():
    credenciales = grpc.ssl_channel_credentials()
    canal = grpc.secure_channel(URL_RAILWAY, credenciales)
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
        if st.button("Actualizar 🔄"):
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
        st.warning("Tus barcos están listos. Esperando a los enemigos...")
        if st.button("Actualizar Estado 🔄"):
            st.rerun()

# FASE 5: COMBATE (Esqueleto básico)
elif st.session_state.fase == "COMBATE":
    ganador = stub.ObtenerGanador(batalla_pb2.Vacio()).valor
    if ganador > 0:
        st.success(f"¡EL JUGADOR {ganador} HA GANADO LA PARTIDA!")
        marcador = stub.ObtenerMarcador(batalla_pb2.Vacio()).texto
        st.code(marcador)
    else:
        turno = stub.DeQuienEsElTurno(batalla_pb2.Vacio()).valor
        if turno == st.session_state.mi_id:
            st.error(f"¡ES TU TURNO JUGADOR {st.session_state.mi_id}! Ataca.")
            # Aquí iría el tablero de ataque
        else:
            st.info(f"Turno del Jugador {turno}. Espera tu turno...")
            
        if st.button("Refrescar Tablero 🔄"):
            st.rerun()
