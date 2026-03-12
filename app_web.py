import streamlit as st
import grpc
import time
import batalla_pb2
import batalla_pb2_grpc

# 1. Configuración inicial de la página y el estado de la sesión
st.set_page_config(page_title="Batalla Naval gRPC", layout="wide")

# Inicializamos las variables que no queremos que se borren al recargar la página
if 'stub' not in st.session_state:
    # Para pruebas locales usamos localhost. Luego lo cambiaremos por la URL de Railway.
    canal = grpc.insecure_channel('localhost:10000') 
    st.session_state.stub = batalla_pb2_grpc.MotorMultijugadorStub(canal)

if 'mi_id' not in st.session_state:
    st.session_state.mi_id = 0
if 'fase' not in st.session_state:
    st.session_state.fase = "LOBBY"
if 'max_jugadores' not in st.session_state:
    st.session_state.max_jugadores = 0
if 'mis_coordenadas' not in st.session_state:
    st.session_state.mis_coordenadas = []

# 2. Funciones de interacción con gRPC
def registrar_jugador(esperados):
    peticion = batalla_pb2.PeticionRegistro(total_esperados=esperados)
    respuesta = st.session_state.stub.RegistrarJugador(peticion)
    st.session_state.mi_id = respuesta.id_jugador
    st.session_state.max_jugadores = esperados
    st.session_state.fase = "ESPERANDO_LOBBY"
    st.rerun() # Forzamos a que Streamlit recargue la pantalla

def colocar_barco(x, y):
    if len(st.session_state.mis_coordenadas) < 10:
        if (x, y) not in st.session_state.mis_coordenadas:
            peticion = batalla_pb2.PeticionCoordenada(id_jugador=st.session_state.mi_id, x=x, y=y)
            st.session_state.stub.ColocarBarco(peticion)
            st.session_state.mis_coordenadas.append((x, y))
            
            if len(st.session_state.mis_coordenadas) == 10:
                # Si ya colocamos 10, declaramos listo
                st.session_state.stub.DeclararListo(batalla_pb2.PeticionJugador(id_jugador=st.session_state.mi_id))
                st.session_state.fase = "ESPERANDO_LISTOS"
            
            st.rerun()

# 3. Interfaz Visual (Renderizado condicional según la fase)
st.title("Batalla Naval Royale 🚢")

if st.session_state.fase == "LOBBY":
    st.subheader("Configuración de la Partida")
    esperados = st.number_input("¿Cuántos jugadores?", min_value=2, max_value=4, value=2)
    if st.button("Unirse a la partida"):
        registrar_jugador(esperados)

elif st.session_state.fase == "ESPERANDO_LOBBY":
    conectados = st.session_state.stub.ObtenerCantidadConectados(batalla_pb2.Vacio()).valor
    st.info(f"Eres el jugador {st.session_state.mi_id}. Esperando jugadores... ({conectados}/{st.session_state.max_jugadores})")
    
    if st.button("Actualizar estado"):
        if conectados == st.session_state.max_jugadores:
            st.session_state.fase = "POSICIONAMIENTO"
        st.rerun()

elif st.session_state.fase == "POSICIONAMIENTO":
    st.subheader(f"Jugador {st.session_state.mi_id} | Coloca tus barcos")
    st.write(f"Barcos colocados: {len(st.session_state.mis_coordenadas)} / 10")
    
    # Dibujamos una cuadrícula usando columnas de Streamlit
    tamano = st.session_state.max_jugadores * 3
    for x in range(tamano):
        cols = st.columns(tamano)
        for y in range(tamano):
            with cols[y]:
                if (x, y) in st.session_state.mis_coordenadas:
                    st.button("🚢", key=f"def_{x}_{y}", disabled=True)
                else:
                    if st.button("🌊", key=f"def_{x}_{y}"):
                        colocar_barco(x, y)

elif st.session_state.fase == "ESPERANDO_LISTOS":
    todos_listos = st.session_state.stub.TodosListos(batalla_pb2.Vacio()).valor
    if todos_listos:
        st.session_state.fase = "COMBATE"
        st.rerun()
    else:
        st.warning("Esperando a que los demás jugadores terminen de acomodar sus barcos...")
        if st.button("Actualizar estado"):
            st.rerun()

elif st.session_state.fase == "COMBATE":
    st.subheader("¡Fase de Combate!")
    # Aquí irá la lógica para mostrar el radar de ataque y pedir el turno
    st.write("En construcción...")
