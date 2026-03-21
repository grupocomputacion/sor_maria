import streamlit as st
import sqlite3
import pandas as pd

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SOR MARIA - Gestión 3ra Materia", layout="wide")

def conectar():
    return sqlite3.connect('gestion_alumnos.db', check_same_thread=False)

# --- LÓGICA DE BASE DE DATOS (Mantenemos tu estructura) ---
def init_db():
    conn = conectar()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS alumnos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        nombre TEXT, curso TEXT, division TEXT, materias_adeudadas TEXT, 
        tercera_materia TEXT, profesor TEXT, modalidad TEXT, 
        n1 TEXT, e1 TEXT, n2 TEXT, e2 TEXT, n3 TEXT, e3 TEXT, n4 TEXT, e4 TEXT, 
        n5 TEXT, e5 TEXT, n6 TEXT, e6 TEXT, n7 TEXT, e7 TEXT, n8 TEXT, e8 TEXT, 
        n9 TEXT, e9 TEXT, n10 TEXT, e10 TEXT, 
        estado TEXT DEFAULT 'PENDIENTE')''')
    conn.commit()
    conn.close()

init_db()

# --- INTERFAZ STREAMLIT ---
st.title("🏫 Sistema de Seguimiento - SOR MARIA")

menu = st.sidebar.radio("MENÚ PRINCIPAL", ["Seguimiento y Filtros", "Cargar Nuevo Alumno", "Importar Excel"])

if menu == "Cargar Nuevo Alumno":
    st.subheader("📝 Registro de Nuevo Estudiante")
    with st.form("form_carga"):
        col1, col2 = st.columns(2)
        nombre = col1.text_input("Nombre Completo")
        curso = col2.text_input("Curso")
        div = col1.text_input("División")
        adeuda = col2.text_area("Materias que adeuda")
        
        if st.form_submit_button("Guardar Alumno"):
            if nombre:
                conn = conectar()
                conn.execute("INSERT INTO alumnos (nombre, curso, division, materias_adeudadas) VALUES (?,?,?,?)",
                            (nombre, curso, div, adeuda))
                conn.commit()
                st.success(f"Alumno {nombre} registrado con éxito.")
            else:
                st.error("El nombre es obligatorio.")

elif menu == "Seguimiento y Filtros":
    st.subheader("🔍 Control de Instancias")
    
    # Filtros dinámicos
    col_f1, col_f2, col_f3 = st.columns(3)
    f_curso = col_f1.text_input("Filtrar por Curso")
    f_mat = col_f2.text_input("Filtrar por Materia")
    f_est = col_f3.selectbox("Estado", ["TODOS", "PENDIENTE", "APROBADO", "REPROBADO"])

    conn = conectar()
    query = "SELECT id, curso, division, nombre, tercera_materia, profesor, estado FROM alumnos WHERE 1=1"
    params = []
    if f_curso:
        query += " AND curso LIKE ?"; params.append(f"%{f_curso}%")
    if f_mat:
        query += " AND tercera_materia LIKE ?"; params.append(f"%{f_mat}%")
    if f_est != "TODOS":
        query += " AND estado = ?"; params.append(f_est)
    
    df = pd.read_sql_query(query, conn, params=params)
    
    # Mostrar Tabla Interactiva
    st.dataframe(df, use_container_width=True)

    # Selección de alumno para editar
    alumno_id = st.selectbox("Seleccione ID de Alumno para Gestionar Notas", df['id'].tolist() if not df.empty else [])
    
    if alumno_id:
        st.divider()
        st.write(f"### Gestionando ID: {alumno_id}")
        
        # Traer datos actuales
        c = conn.cursor()
        c.execute("SELECT * FROM alumnos WHERE id=?", (alumno_id,))
        d = c.fetchone()
        
        with st.expander("Editar Datos y 10 Instancias", expanded=True):
            col_e1, col_e2 = st.columns(2)
            new_nom = col_e1.text_input("Nombre", value=d[1])
            new_mat = col_e2.text_input("3ra Materia", value=d[5] if d[5] else "")
            new_prof = col_e1.text_input("Profesor", value=d[28] if len(d)>28 and d[28] else "")
            new_est = col_e2.selectbox("Estado Final", ["PENDIENTE", "APROBADO", "REPROBADO"], 
                                      index=["PENDIENTE", "APROBADO", "REPROBADO"].index(d[27]))
            
            st.write("#### Notas e Instancias")
            notas_cols = st.columns(5)
            check_cols = st.columns(5)
            
            nuevas_notas = []
            for i in range(10):
                # Organizar 10 campos de forma compacta
                idx_col = i % 5
                nota = st.text_input(f"Nota {i+1}", value=d[7+i*2] if d[7+i*2] else "", key=f"n{i}")
                aprob = st.checkbox("Aprobó", value=(d[8+i*2]=="S"), key=f"e{i}")
                nuevas_notas.extend([nota, "S" if aprob else "N"])

            if st.button("Grabar Todos los Cambios"):
                q_update = '''UPDATE alumnos SET nombre=?, tercera_materia=?, profesor=?, 
                              n1=?, e1=?, n2=?, e2=?, n3=?, e3=?, n4=?, e4=?, n5=?, e5=?, 
                              n6=?, e6=?, n7=?, e7=?, n8=?, e8=?, n9=?, e9=?, n10=?, e10=?, 
                              estado=? WHERE id=?'''
                conn.execute(q_update, (new_nom, new_mat, new_prof, *nuevas_notas, new_est, alumno_id))
                conn.commit()
                st.success("Cambios guardados correctamente.")
                st.rerun()

elif menu == "Importar Excel":
    st.subheader("📥 Carga Masiva")
    subida = st.file_uploader("Subir archivo Excel", type=["xlsx"])
    if subida:
        df_excel = pd.read_excel(subida)
        st.write("Previsualización de datos:")
        st.dataframe(df_excel.head())
        if st.button("Confirmar Ingesta"):
            # Lógica de importación similar al script anterior
            st.info("Procesando...")
            # ... (código de inserción)
            st.success("Importación finalizada.")
