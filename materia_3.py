import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import pandas as pd
import sys

# --- CONEXIÓN Y MANTENIMIENTO DE DB ---
def conectar():
    return sqlite3.connect('gestion_alumnos.db')

def init_db():
    conn = conectar()
    c = conn.cursor()
    # Estructura base
    c.execute('''CREATE TABLE IF NOT EXISTS alumnos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        nombre TEXT, curso TEXT, division TEXT, materias_adeudadas TEXT, 
        tercera_materia TEXT, modalidad TEXT, 
        n1 TEXT, e1 TEXT, n2 TEXT, e2 TEXT, n3 TEXT, e3 TEXT, n4 TEXT, e4 TEXT, 
        n5 TEXT, e5 TEXT, n6 TEXT, e6 TEXT, n7 TEXT, e7 TEXT, n8 TEXT, e8 TEXT, 
        n9 TEXT, e9 TEXT, n10 TEXT, e10 TEXT, 
        estado TEXT DEFAULT 'PENDIENTE')''')
    
    # LÓGICA DE AUTO-PARCHE: Agrega la columna profesor si no existe
    try:
        c.execute("ALTER TABLE alumnos ADD COLUMN profesor TEXT")
    except sqlite3.OperationalError:
        pass # La columna ya existe
        
    conn.commit()
    conn.close()

class SistemaSorMaria:
    def __init__(self, root):
        self.root = root
        self.root.title("SISTEMA SOR MARIA - Gestión de 3ra Materia y Docentes")
        self.root.geometry("1250x750")
        init_db()

        # Estilo para Mac y Windows
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", foreground="black", background="white", fieldbackground="white", rowheight=30)
        style.configure("Treeview.Heading", foreground="black", font=('Arial', 10, 'bold'))

        # Menú Lateral
        self.menu = tk.Frame(root, width=180, bg="#ecf0f1", highlightthickness=1, highlightbackground="black")
        self.menu.pack(side="left", fill="y")
        
        tk.Label(self.menu, text="SOR MARIA", fg="black", bg="#ecf0f1", font=("Arial", 16, "bold")).pack(pady=30)
        
        tk.Button(self.menu, text="Cargar Alumno", command=self.vista_carga, fg="black", height=2).pack(pady=5, padx=10, fill="x")
        tk.Button(self.menu, text="Seguimiento", command=self.vista_consulta, fg="black", height=2).pack(pady=5, padx=10, fill="x")
        
        tk.Button(self.menu, text="SALIR", bg="#e74c3c", fg="black", command=self.root.destroy, height=2).pack(side="bottom", pady=20, padx=10, fill="x")

        # Panel Principal
        self.contenedor = tk.Frame(root, bg="white")
        self.contenedor.pack(side="right", expand=True, fill="both")
        self.vista_consulta()

    def vista_carga(self):
        for w in self.contenedor.winfo_children(): w.destroy()
        f = tk.Frame(self.contenedor, bg="white")
        f.place(relx=0.5, rely=0.4, anchor="center")
        self.entries = {}
        for txt, clave in [("Nombre:", "nom"), ("Curso:", "cur"), ("Div:", "div"), ("Adeuda:", "ade")]:
            tk.Label(f, text=txt, bg="white", fg="black", font=("Arial", 10, "bold")).pack(anchor="w")
            e = tk.Entry(f, width=40, bg="#f0f0f0", fg="black", insertbackground="black")
            e.pack(pady=5); self.entries[clave] = e
        tk.Button(f, text="GUARDAR ALUMNO", bg="#2ecc71", fg="black", command=self.guardar, height=2).pack(pady=20)

    def guardar(self):
        n = self.entries["nom"].get()
        if not n: return messagebox.showwarning("!", "Nombre requerido")
        conn = conectar(); c = conn.cursor()
        c.execute("INSERT INTO alumnos (nombre, curso, division, materias_adeudadas) VALUES (?,?,?,?)",
                 (n, self.entries["cur"].get(), self.entries["div"].get(), self.entries["ade"].get()))
        conn.commit(); conn.close()
        messagebox.showinfo("OK", "Registrado"); self.vista_carga()

    def vista_consulta(self):
        for w in self.contenedor.winfo_children(): w.destroy()
        f_filtros = tk.Frame(self.contenedor, bg="#f8f9f9")
        f_filtros.pack(fill="x", padx=10, pady=10)
        
        tk.Label(f_filtros, text="Filtro Curso:", bg="#f8f9f9", fg="black").pack(side="left", padx=5)
        self.f_cur = tk.Entry(f_filtros, width=10, fg="black"); self.f_cur.pack(side="left", padx=5)
        
        tk.Button(f_filtros, text="FILTRAR", command=self.actualizar_tabla, fg="black").pack(side="left", padx=10)
        tk.Button(f_filtros, text="EXPORTAR EXCEL", bg="#27ae60", fg="black", command=self.exportar).pack(side="right", padx=10)

        # Tabla con columna Profesor agregada visualmente
        self.tabla = ttk.Treeview(self.contenedor, columns=("C", "D", "N", "M", "P", "E"), show='headings')
        for col, head in [("C","Curso"),("D","Div"),("N","Nombre"),("M","3ra Mat"),("P","Profesor"),("E","Estado")]:
            self.tabla.heading(col, text=head)
            self.tabla.column(col, width=100)
        self.tabla.pack(expand=True, fill="both", padx=10)

        f_btns = tk.Frame(self.contenedor, bg="white")
        f_btns.pack(pady=10)
        tk.Button(f_btns, text="EDITAR / GESTIONAR", bg="#3498db", fg="black", height=2, command=self.gestionar).pack(side="left", padx=10)
        tk.Button(f_btns, text="ELIMINAR", bg="#e74c3c", fg="black", height=2, command=self.eliminar).pack(side="left", padx=10)
        self.actualizar_tabla()

    def actualizar_tabla(self):
        for i in self.tabla.get_children(): self.tabla.delete(i)
        conn = conectar(); c = conn.cursor()
        # Seleccionamos también la columna profesor
        q = "SELECT id, curso, division, nombre, tercera_materia, profesor, estado FROM alumnos WHERE curso LIKE ?"
        c.execute(q, (f"%{self.f_cur.get()}%",))
        for r in c.fetchall():
            self.tabla.insert("", "end", iid=r[0], values=(r[1], r[2], r[3], r[4] if r[4] else "---", r[5] if r[5] else "---", r[6]))
        conn.close()

    def gestionar(self):
        sel = self.tabla.selection()
        if not sel: return
        uid = sel[0]
        conn = conectar(); c = conn.cursor()
        c.execute("SELECT * FROM alumnos WHERE id=?", (uid,)); d = c.fetchone(); conn.close()

        v = tk.Toplevel(self.root); v.title("Edición y Seguimiento"); v.geometry("550x700")
        canvas = tk.Canvas(v, bg="white"); scroll = tk.Scrollbar(v, orient="vertical", command=canvas.yview)
        f_scroll = tk.Frame(canvas, bg="white")
        f_scroll.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=f_scroll, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set); canvas.pack(side="left", fill="both", expand=True); scroll.pack(side="right", fill="y")

        # --- SECCIÓN: DATOS GENERALES ---
        tk.Label(f_scroll, text="DATOS DEL ALUMNO Y MATERIA", font=("Arial", 11, "bold"), bg="white", fg="black").pack(pady=10)
        f_e = tk.Frame(f_scroll, bg="white")
        f_e.pack()
        
        lbl_s = {"bg": "white", "fg": "black"}
        tk.Label(f_e, text="Nombre:", **lbl_s).grid(row=0, column=0, sticky="e")
        en_nom = tk.Entry(f_e, width=35, fg="black"); en_nom.grid(row=0, column=1); en_nom.insert(0, d[1])
        
        tk.Label(f_e, text="Curso:", **lbl_s).grid(row=1, column=0, sticky="e")
        en_cur = tk.Entry(f_e, width=35, fg="black"); en_cur.grid(row=1, column=1); en_cur.insert(0, d[2])
        
        tk.Label(f_e, text="División:", **lbl_s).grid(row=2, column=0, sticky="e")
        en_div = tk.Entry(f_e, width=35, fg="black"); en_div.grid(row=2, column=1); en_div.insert(0, d[3])

        tk.Label(f_e, text="3ra Materia:", **lbl_s).grid(row=3, column=0, sticky="e")
        e3 = tk.Entry(f_e, width=35, fg="black"); e3.grid(row=3, column=1); e3.insert(0, d[5] if d[5] else "")

        # --- NUEVO CAMPO: PROFESOR ---
        tk.Label(f_e, text="Profesor:", **lbl_s).grid(row=4, column=0, sticky="e")
        en_prof = tk.Entry(f_e, width=35, fg="black"); en_prof.grid(row=4, column=1)
        # Buscamos el profesor en el índice 28 (siempre que se haya hecho el parche)
        val_prof = d[28] if len(d) > 28 and d[28] else ""
        en_prof.insert(0, val_prof)

        tk.Label(f_scroll, text="ESTADO DE SEGUIMIENTO", font=("Arial", 11, "bold"), bg="white", fg="black").pack(pady=10)
        combo_est = ttk.Combobox(f_scroll, values=["PENDIENTE", "APROBADO", "REPROBADO"], state="readonly", width=30)
        combo_est.set(d[27]); combo_est.pack()

        # --- SECCIÓN: 10 INSTANCIAS ---
        tk.Label(f_scroll, text="SEGUIMIENTO DE INSTANCIAS", font=("Arial", 11, "bold"), bg="white", fg="black").pack(pady=10)
        self.inst_data = []
        f_g = tk.Frame(f_scroll, bg="white")
        f_g.pack()
        for i in range(10):
            tk.Label(f_g, text=f"#{i+1}:", **lbl_s).grid(row=i, column=0)
            en = tk.Entry(f_g, width=8, fg="black"); en.grid(row=i, column=1)
            val_n = d[7+i*2] if len(d) > 7+i*2 and d[7+i*2] else ""
            en.insert(0, val_n)
            val_e = d[8+i*2] if len(d) > 8+i*2 and d[8+i*2] else "N"
            var = tk.StringVar(value=val_e)
            chk = tk.Checkbutton(f_g, variable=var, onvalue="S", offvalue="N", bg="white")
            chk.grid(row=i, column=2); self.inst_data.append((en, var))

        def guardar():
            vals = []
            for en, var in self.inst_data:
                vals.extend([en.get(), var.get()])
            
            conn = conectar(); c = conn.cursor()
            # Query actualizada con el campo profesor
            query = '''UPDATE alumnos SET nombre=?, curso=?, division=?, tercera_materia=?, profesor=?, 
                       n1=?, e1=?, n2=?, e2=?, n3=?, e3=?, n4=?, e4=?, n5=?, e5=?, 
                       n6=?, e6=?, n7=?, e7=?, n8=?, e8=?, n9=?, e9=?, n10=?, e10=?, 
                       estado=? WHERE id=?'''
            c.execute(query, (en_nom.get(), en_cur.get(), en_div.get(), e3.get(), en_prof.get(), *vals, combo_est.get(), uid))
            conn.commit(); conn.close()
            v.destroy(); self.actualizar_tabla()

        tk.Button(f_scroll, text="GRABAR CAMBIOS", bg="#2ecc71", fg="black", font=("Arial", 10, "bold"), command=guardar, height=2, width=30).pack(pady=25)

    def eliminar(self):
        sel = self.tabla.selection()
        if not sel: return
        if messagebox.askyesno("!", "¿Eliminar registro?"):
            conn = conectar(); c = conn.cursor()
            c.execute("DELETE FROM alumnos WHERE id=?", (sel[0],))
            conn.commit(); conn.close(); self.actualizar_tabla()

    def exportar(self):
        dest = filedialog.asksaveasfilename(defaultextension=".xlsx")
        if dest:
            conn = conectar(); df = pd.read_sql_query("SELECT * FROM alumnos", conn); conn.close()
            df.to_excel(dest, index=False); messagebox.showinfo("OK", "Reporte Exportado")

if __name__ == "__main__":
    root = tk.Tk(); app = SistemaSorMaria(root); root.mainloop()
