import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sqlite3
import pandas as pd
import sys

# --- CONFIGURACIÓN DE COLORES Y ESTILO ---
BG_COLOR = "white"
TXT_COLOR = "black"

def conectar_db():
    # Se conecta a la base en la misma carpeta
    return sqlite3.connect('gestion_alumnos.db')

class HerramientaMigracion:
    def __init__(self, root):
        self.root = root
        self.root.title("ADMIN: Herramienta de Carga Masiva - SOR MARIA")
        self.root.geometry("600x550")
        self.root.configure(bg=BG_COLOR)

        # Encabezado
        tk.Label(root, text="HERRAMIENTA DE MIGRACIÓN DE DATOS", 
                 font=("Arial", 16, "bold"), bg=BG_COLOR, fg=TXT_COLOR).pack(pady=20)
        
        instrucciones = (
            "ORDEN REQUERIDO EN EXCEL:\n"
            "1. CURSO | 2. DIVISIÓN | 3. NOMBRE | 4. MATERIAS ADEUDADAS\n"
            "(El script salta la primera fila de encabezados)"
        )
        tk.Label(root, text=instrucciones, bg="#fcf3cf", fg=TXT_COLOR, 
                 font=("Arial", 10, "italic"), pady=10, padx=10, relief="solid").pack(pady=10)

        # Botón de Acción
        self.btn_file = tk.Button(root, text="SELECCIONAR ARCHIVO Y CARGAR", 
                                 command=self.ejecutar_importacion, 
                                 bg="#3498db", fg=TXT_COLOR, font=("Arial", 11, "bold"), height=2)
        self.btn_file.pack(pady=20)

        # Consola de Monitoreo
        tk.Label(root, text="Log de Ingesta:", bg=BG_COLOR, fg=TXT_COLOR, font=("Arial", 9, "bold")).pack(anchor="w", padx=20)
        self.txt_log = tk.Text(root, height=15, width=70, bg="#f0f0f0", fg=TXT_COLOR, font=("Courier", 10))
        self.txt_log.pack(pady=5, padx=20)
        
        # Barra de progreso
        self.pb = ttk.Progressbar(root, orient='horizontal', mode='determinate', length=550)
        self.pb.pack(pady=20)

    def log(self, mensaje):
        self.txt_log.insert(tk.END, mensaje + "\n")
        self.txt_log.see(tk.END)
        self.root.update_idletasks()

    def ejecutar_importacion(self):
        archivo = filedialog.askopenfilename(
            title="Seleccionar archivo de datos",
            filetypes=[("Excel", "*.xlsx *.xls"), ("CSV", "*.csv")]
        )
        
        if not archivo:
            return

        self.txt_log.delete(1.0, tk.END)
        self.log(f"--- Iniciando proceso desde: {archivo.split('/')[-1]} ---")

        try:
            # Leer archivo
            if archivo.endswith('.csv'):
                df = pd.read_csv(archivo, header=None)
            else:
                df = pd.read_excel(archivo, header=None)

            total = len(df) - 1
            self.pb["maximum"] = total
            self.pb["value"] = 0

            conn = conectar_db()
            cursor = conn.cursor()
            
            # Asegurar que la tabla exista (por si corres esto en una carpeta vacía)
            cursor.execute('''CREATE TABLE IF NOT EXISTS alumnos (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                nombre TEXT, curso TEXT, division TEXT, materias_adeudadas TEXT, 
                tercera_materia TEXT, modalidad TEXT, 
                n1 TEXT, e1 TEXT, n2 TEXT, e2 TEXT, n3 TEXT, e3 TEXT, n4 TEXT, e4 TEXT, 
                n5 TEXT, e5 TEXT, n6 TEXT, e6 TEXT, n7 TEXT, e7 TEXT, n8 TEXT, e8 TEXT, 
                n9 TEXT, e9 TEXT, n10 TEXT, e10 TEXT, 
                estado TEXT DEFAULT 'PENDIENTE')''')

            conteo = 0
            for index, fila in df.iloc[1:].iterrows():
                # ASIGNACIÓN POR ORDEN PEDIDO
                cur = str(fila[0]) if pd.notna(fila[0]) else ""
                div = str(fila[1]) if pd.notna(fila[1]) else ""
                nom = str(fila[2]) if pd.notna(fila[2]) else ""
                mat = str(fila[3]) if pd.notna(fila[3]) else ""

                if not nom.strip():
                    continue

                cursor.execute("""
                    INSERT INTO alumnos (nombre, curso, division, materias_adeudadas, estado) 
                    VALUES (?, ?, ?, ?, 'PENDIENTE')
                """, (nom, cur, div, mat))
                
                conteo += 1
                self.pb["value"] = conteo
                self.log(f"OK > Ingresado: {nom} ({cur} {div})")

            conn.commit()
            conn.close()
            
            self.log(f"\n--- PROCESO FINALIZADO ---")
            self.log(f"Total alumnos cargados: {conteo}")
            messagebox.showinfo("Éxito", f"Se cargaron {conteo} alumnos.")

        except Exception as e:
            self.log(f"ERROR CRÍTICO: {str(e)}")
            messagebox.showerror("Error", f"Ocurrió un error: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = HerramientaMigracion(root)
    root.mainloop()
