import grpc
from concurrent import futures
import time
import batalla_pb2
import batalla_pb2_grpc
import os

class MotorMultijugadorServicer(batalla_pb2_grpc.MotorMultijugadorServicer):
    def __init__(self):
        self.jugadores_conectados = 0
        self.max_jugadores = 0
        self.jugadores_listos = 0
        self.turno_actual = 1
        self.disparos_hechos_este_turno = 0
        
        self.matriz_disparos = []
        self.flotas = {} 
        self.vidas = {}
        self.puntajes = {}
        self.jugadores_vivos = 0

    def RegistrarJugador(self, request, context):
        if self.max_jugadores == 0:
            self.max_jugadores = request.total_esperados
            # ¡Redujimos el mapa a * 3!
            tamano_cuadricula = self.max_jugadores * 3 
            self.matriz_disparos = [[0 for _ in range(tamano_cuadricula)] for _ in range(tamano_cuadricula)]
        
        self.jugadores_conectados += 1
        id_jugador = self.jugadores_conectados
        
        self.flotas[id_jugador] = []
        self.vidas[id_jugador] = 10  # ¡Subimos a 10 barcos!
        self.puntajes[id_jugador] = 0
        self.jugadores_vivos += 1
        
        return batalla_pb2.RespuestaRegistro(id_jugador=id_jugador)

    def ObtenerCantidadConectados(self, request, context): 
        return batalla_pb2.RespuestaEntero(valor=self.jugadores_conectados)

    def ObtenerMaxJugadores(self, request, context): 
        return batalla_pb2.RespuestaEntero(valor=self.max_jugadores)
    
    def ColocarBarco(self, request, context):
        x = request.x
        y = request.y
        idJugador = request.id_jugador
        
        if (x, y) not in self.flotas[idJugador]:
            self.flotas[idJugador].append((x, y))
        return batalla_pb2.Vacio()

    def DeclararListo(self, request, context):
        self.jugadores_listos += 1
        return batalla_pb2.Vacio()

    def TodosListos(self, request, context):
        listos = self.jugadores_listos == self.max_jugadores and self.max_jugadores > 0
        return batalla_pb2.RespuestaBooleano(valor=listos)

    def DeQuienEsElTurno(self, request, context):
        return batalla_pb2.RespuestaEntero(valor=self.turno_actual)

    def avanzar_turno(self):
        self.turno_actual += 1
        if self.turno_actual > self.max_jugadores: self.turno_actual = 1
        while self.vidas[self.turno_actual] <= 0 and self.jugadores_vivos > 1:
            self.turno_actual += 1
            if self.turno_actual > self.max_jugadores: self.turno_actual = 1

    def Disparar(self, request, context):
        idJugador = request.id_jugador
        x = request.x
        y = request.y

        if idJugador != self.turno_actual or self.jugadores_vivos <= 1:
            return batalla_pb2.RespuestaEntero(valor=8) 

        # ¡Ya no bloqueamos la casilla! Todos pueden disparar donde sea.
        impacto = False
        ids_impactados = ""

        # Revisamos todas las flotas para ver a quién le damos
        for enemigo_id, barcos in self.flotas.items():
            if enemigo_id != idJugador and (x, y) in barcos:
                barcos.remove((x, y)) 
                self.vidas[enemigo_id] -= 1
                self.puntajes[idJugador] += 1
                
                impacto = True
                ids_impactados += str(enemigo_id) 
                
                if self.vidas[enemigo_id] == 0:
                    self.jugadores_vivos -= 1

        # Lógica del radar público gRPC
        if impacto:
            valor_anterior = self.matriz_disparos[x][y]
            if valor_anterior > 0:
                nuevo_valor = str(valor_anterior) + ids_impactados
                self.matriz_disparos[x][y] = int(nuevo_valor)
                resultado = int(nuevo_valor)
            else:
                self.matriz_disparos[x][y] = int(ids_impactados)
                resultado = int(ids_impactados)
        else:
            if self.matriz_disparos[x][y] == 0:
                self.matriz_disparos[x][y] = -1 
            resultado = 0

        self.disparos_hechos_este_turno += 1
        if self.disparos_hechos_este_turno >= (self.max_jugadores - 1):
            self.disparos_hechos_este_turno = 0
            self.avanzar_turno()

        return batalla_pb2.RespuestaEntero(valor=resultado)

    def ObtenerEstadoTablero(self, request, context): 
        filas_proto = []
        for fila_python in self.matriz_disparos:
            filas_proto.append(batalla_pb2.Fila(valores=fila_python))
        return batalla_pb2.RespuestaTablero(filas=filas_proto)

    def ObtenerGanador(self, request, context):
        ganador = 0
        if self.jugadores_vivos <= 1 and self.max_jugadores > 0 and self.jugadores_listos == self.max_jugadores:
            for id_jugador, v in self.vidas.items():
                if v > 0: ganador = id_jugador
        return batalla_pb2.RespuestaEntero(valor=ganador)

    def ObtenerMarcador(self, request, context):
        texto = "=== MARCADOR FINAL ===\n\n"
        for i in range(1, self.max_jugadores + 1):
            estado = "VIVO" if self.vidas[i] > 0 else "ELIMINADO"
            texto += f"Jugador {i} ({estado}): {self.puntajes[i]} destruidos\n"
        return batalla_pb2.RespuestaMarcador(texto=texto)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    batalla_pb2_grpc.add_MotorMultijugadorServicer_to_server(MotorMultijugadorServicer(), server)

    puerto = os.environ.get("PORT", "10000") 
    server.add_insecure_port(f'[::]:{puerto}')

    server.start()
    print("Servidor gRPC listo y a la escucha en el puerto 10000. Los barcos ahora son secretos.")
    server.wait_for_termination()

if __name__ == '__main__':
    serve() 