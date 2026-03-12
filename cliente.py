import sys
import tkinter as tk
from tkinter import simpledialog, messagebox
import grpc
import batalla_pb2
import batalla_pb2_grpc

BG_MAIN = "#2C3E50"      
COLOR_AGUA = "#34495E"   
COLOR_FALLO = "#95A5A6"  
COLOR_ACIERTO = "#E74C3C" 
COLOR_MIO = "#2ECC71"    
COLOR_TEXTO = "#ECF0F1"  

class ClienteBatallaNaval:
    def __init__(self, master, stub): 
        self.master = master
        self.servidor = stub
        self.master.title("Batalla Naval Royale - Interfaz Dual (gRPC)")
        self.master.geometry("1000x550")
        self.master.config(bg=BG_MAIN)
        
        self.mi_id = 0
        self.max_jugadores = 0
        self.fase = "LOBBY" 
        self.barcos_a_colocar = 10 # ¡10 Barcos!
        self.barcos_colocados = 0
        self.mis_coordenadas = [] 
        
        self.botones_defensa = {}
        self.botones_ataque = {}  
        
        self.lbl_estado = tk.Label(master, text="Conectando...", font=("Verdana", 14, "bold"), bg=BG_MAIN, fg=COLOR_TEXTO)
        self.lbl_estado.pack(pady=10)
        
        self.frame_contenedor = tk.Frame(master, bg=BG_MAIN)
        self.frame_contenedor.pack(expand=True, fill="both", padx=10, pady=5)
        
        self.frame_izq = tk.Frame(self.frame_contenedor, bg=BG_MAIN)
        self.frame_izq.pack(side=tk.LEFT, expand=True, fill="both", padx=10)
        tk.Label(self.frame_izq, text="TU FLOTA (Posición y Defensa)", bg=BG_MAIN, fg=COLOR_TEXTO).pack()
        self.grid_defensa = tk.Frame(self.frame_izq, bg=BG_MAIN)
        self.grid_defensa.pack(expand=True, fill="both")
        
        self.frame_der = tk.Frame(self.frame_contenedor, bg=BG_MAIN)
        self.frame_der.pack(side=tk.RIGHT, expand=True, fill="both", padx=10)
        tk.Label(self.frame_der, text="RADAR DE ATAQUE (Dispara aquí)", bg=BG_MAIN, fg=COLOR_TEXTO).pack()
        self.grid_ataque = tk.Frame(self.frame_der, bg=BG_MAIN)
        self.grid_ataque.pack(expand=True, fill="both")

        self.iniciar_conexion()

    def iniciar_conexion(self):
        max_servidor = self.servidor.ObtenerMaxJugadores(batalla_pb2.Vacio()).valor
        esperados = max_servidor
        
        if max_servidor == 0:
            esperados = simpledialog.askinteger("Partida", "¿Cuántos jugadores?", minvalue=2, maxvalue=4)
            if not esperados: self.master.quit(); return
                
        peticion_reg = batalla_pb2.PeticionRegistro(total_esperados=esperados)
        self.mi_id = self.servidor.RegistrarJugador(peticion_reg).id_jugador
        self.max_jugadores = esperados
        self.actualizar_estado_periodicamente()

    def actualizar_estado_periodicamente(self):
        ganador = self.servidor.ObtenerGanador(batalla_pb2.Vacio()).valor
        if ganador > 0:
            marcador = self.servidor.ObtenerMarcador(batalla_pb2.Vacio()).texto
            messagebox.showinfo("Fin", f"¡EL JUGADOR {ganador} HA GANADO!\n\n{marcador}")
            self.master.quit(); return

        if self.fase == "LOBBY":
            conectados = self.servidor.ObtenerCantidadConectados(batalla_pb2.Vacio()).valor
            if conectados == self.max_jugadores:
                self.fase = "POSICIONAMIENTO"
                self.lbl_estado.config(text=f"JUGADOR {self.mi_id} | Oculta tus {self.barcos_a_colocar} barcos en el panel Izquierdo")
                self.dibujar_tableros()
            else:
                self.lbl_estado.config(text=f"Jugador {self.mi_id} | Esperando... ({conectados}/{self.max_jugadores})")
                
        elif self.fase == "ESPERANDO_LISTOS":
            if self.servidor.TodosListos(batalla_pb2.Vacio()).valor: 
                self.fase = "COMBATE"
                
        elif self.fase == "COMBATE":
            respuesta_tablero = self.servidor.ObtenerEstadoTablero(batalla_pb2.Vacio())
            tamano = self.max_jugadores * 3 # ¡Ajustado a * 3!
            
            for x in range(tamano):
                for y in range(tamano):
                    valor = respuesta_tablero.filas[x].valores[y]
                    btn_def = self.botones_defensa[(x,y)]
                    btn_atk = self.botones_ataque[(x,y)]
                    
                    if (x,y) in self.mis_coordenadas:
                        if valor > 0 and str(self.mi_id) in str(valor): 
                            btn_def.config(bg=COLOR_ACIERTO, text="X") 
                        else: 
                            btn_def.config(bg=COLOR_MIO, text="B") 
                    else:
                        if valor == -1: btn_def.config(bg=COLOR_FALLO, text="O") 

                    if valor == -1:
                        btn_atk.config(bg=COLOR_FALLO, text="O") 
                    elif valor > 0:
                        btn_atk.config(bg=COLOR_ACIERTO, text=f"J{valor}") 

            turno = self.servidor.DeQuienEsElTurno(batalla_pb2.Vacio()).valor
            if turno == self.mi_id: self.lbl_estado.config(text=f"¡TU TURNO JUGADOR {self.mi_id}! Dispara en el panel Derecho", fg="#F1C40F")
            else: self.lbl_estado.config(text=f"Turno del Jugador {turno}...", fg=COLOR_TEXTO)

        self.master.after(1000, self.actualizar_estado_periodicamente)

    def dibujar_tableros(self):
        tamano = self.max_jugadores * 3 # ¡Ajustado a * 3!
        for fila in range(tamano):
            self.grid_defensa.grid_rowconfigure(fila, weight=1); self.grid_defensa.grid_columnconfigure(fila, weight=1)
            self.grid_ataque.grid_rowconfigure(fila, weight=1); self.grid_ataque.grid_columnconfigure(fila, weight=1)
            
            for col in range(tamano):
                btn_d = tk.Button(self.grid_defensa, text="", bg=COLOR_AGUA, font=("Arial", 9, "bold"))
                btn_d.config(command=lambda x=fila, y=col: self.clic_posicionar(x, y))
                btn_d.grid(row=fila, column=col, sticky="nsew", padx=1, pady=1)
                self.botones_defensa[(fila, col)] = btn_d 
                
                btn_a = tk.Button(self.grid_ataque, text="", bg=COLOR_AGUA, font=("Arial", 9, "bold"))
                btn_a.config(command=lambda x=fila, y=col: self.clic_atacar(x, y))
                btn_a.grid(row=fila, column=col, sticky="nsew", padx=1, pady=1)
                self.botones_ataque[(fila, col)] = btn_a 

    def clic_posicionar(self, x, y):
        if self.fase == "POSICIONAMIENTO":
            if (x, y) not in self.mis_coordenadas: 
                peticion = batalla_pb2.PeticionCoordenada(id_jugador=self.mi_id, x=x, y=y)
                self.servidor.ColocarBarco(peticion)
                self.mis_coordenadas.append((x,y)) 
                
                btn = self.botones_defensa[(x, y)]
                btn.config(bg=COLOR_MIO, text="B")
                
                self.barcos_colocados += 1
                if self.barcos_colocados == self.barcos_a_colocar:
                    self.fase = "ESPERANDO_LISTOS"
                    self.lbl_estado.config(text="Flota lista. Esperando enemigos...")
                    self.servidor.DeclararListo(batalla_pb2.PeticionJugador(id_jugador=self.mi_id))

    def clic_atacar(self, x, y):
        if self.fase == "COMBATE":
            turno_actual = self.servidor.DeQuienEsElTurno(batalla_pb2.Vacio()).valor
            if turno_actual == self.mi_id:
                peticion = batalla_pb2.PeticionCoordenada(id_jugador=self.mi_id, x=x, y=y)
                resultado = self.servidor.Disparar(peticion).valor
                
                if resultado == 8:
                    messagebox.showwarning("Aviso", "Movimiento inválido o ya atacaste ahí.")
                elif resultado > 0:
                    messagebox.showinfo("¡BOOM!", f"¡Fuego efectivo! Has impactado a la flota: {resultado}")

if __name__ == '__main__':
    # ¡Ya puse tu IP local aquí!
    canal = grpc.insecure_channel('10.149.25.127:10000')
    stub = batalla_pb2_grpc.MotorMultijugadorStub(canal)
    
    ventana_principal = tk.Tk()
    app = ClienteBatallaNaval(ventana_principal, stub)
    ventana_principal.mainloop()