import streamlit as st
import psycopg2
from psycopg2 import extras
import pandas as pd
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SOR MARIA - Gestión 3ra Materia", layout="wide")

# --- CONEXIÓN A NEON / POSTGRES ---
def conectar():
    try:
        # Busca la URL en .streamlit/secrets.toml bajo la clave "postgres_url"
        conn = psycopg2.connect(st.secrets["postgres_url"])
        return conn
    except Exception as e:
        st.error(f"❌ Error de conexión a la base de datos: {e}")
        return None

# --- INICIALIZACIÓN DE TABLAS (POSTGRES) ---
def init_db():
    conn = conectar()
    if conn:
        with conn.cursor() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS alumnos (
                id SERIAL PRIMARY KEY, 
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
st.title("🏫 Sistema de Seguimiento - SOR MARIA (Edición Postgres)")

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
                if conn:
                    with conn.cursor() as c:
                        c.execute("INSERT INTO alumnos (nombre, curso, division, materias_adeudadas) VALUES (%s,%s,%s,%s)",
                                    (nombre, curso, div, adeuda))
                        conn.commit()
                    conn.close()
                    st.success(f"Alumno {nombre} registrado con éxito.")
            else:
                st.error("El nombre es obligatorio.")

elif menu == "Seguimiento y Filtros":
    st.subheader("🔍 Control de Instancias")
    
    col_f1, col_f2, col_f3 = st.columns(3)
    f_curso = col_f1.text_input("Filtrar por Curso")
    f_mat = col_f2.text_input("Filtrar por Materia")
    f_est = col_f3.selectbox("Estado", ["TODOS", "PENDIENTE", "APROBADO", "REPROBADO"])

    conn = conectar()
    if conn:
        query = "SELECT id, curso, division, nombre, tercera_materia, profesor, estado FROM alumnos WHERE 1=1"
        params = []
        if f_curso:
            query += " AND curso ILIKE %s"; params.append(f"%{f_curso}%")
        if f_mat:
            query += " AND tercera_materia ILIKE %s"; params.append(f"%{f_mat}%")
        if f_est != "TODOS":
            query += " AND estado = %s"; params.append(f_est)
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        st.dataframe(df, use_container_width=True, hide_index=True)

        alumno_id = st.selectbox("Seleccione ID de Alumno para Gestionar Notas", df['id'].tolist() if not df.empty else [])
        
        if alumno_id:
            st.divider()
            conn = conectar()
            with conn.cursor() as c:
                c.execute("SELECT * FROM alumnos WHERE id=%s", (alumno_id,))
                d = c.fetchone()
            
            with st.expander(f"Editar Datos de {d[1]}", expanded=True):
                col_e1, col_e2 = st.columns(2)
                new_nom = col_e1.text_input("Nombre", value=d[1])
                new_mat = col_e2.text_input("3ra Materia", value=d[5] if d[5] else "")
                new_prof = col_e1.text_input("Profesor", value=d[6] if d[6] else "")
                new_est = col_e2.selectbox("Estado Final", ["PENDIENTE", "APROBADO", "REPROBADO"], 
                                          index=["PENDIENTE", "APROBADO", "REPROBADO"].index(d[28]))
                
                st.write("#### Notas e Instancias")
                nuevas_notas = []
                # Generar 10 pares de campos (Nota y Aprobó)
                for i in range(10):
                    c_n, c_a = st.columns([3, 1])
                    val_n = d[8 + i*2] if d[8 + i*2] else ""
                    val_a = (d[9 + i*2] == "S")
                    nota = c_n.text_input(f"Instancia {i+1}", value=val_n, key=f"n{i}")
                    aprob = c_a.checkbox("Aprobó", value=val_a, key=f"e{i}")
                    nuevas_notas.extend([nota, "S" if aprob else "N"])

                if st.button("Grabar Todos los Cambios"):
                    with conn.cursor() as c:
                        q_update = '''UPDATE alumnos SET nombre=%s, tercera_materia=%s, profesor=%s, 
                                      n1=%s, e1=%s, n2=%s, e2=%s, n3=%s, e3=%s, n4=%s, e4=%s, n5=%s, e5=%s, 
                                      n6=%s, e6=%s, n7=%s, e7=%s, n8=%s, e8=%s, n9=%s, e9=%s, n10=%s, e10=%s, 
                                      estado=%s WHERE id=%s'''
                        c.execute(q_update, (new_nom, new_mat, new_prof, *nuevas_notas, new_est, alumno_id))
                        conn.commit()
                    conn.close()
                    st.success("Cambios guardados en Postgres.")
                    st.rerun()

elif menu == "Importar Excel":
    st.subheader("📥 Carga Masiva a Postgres")
    subida = st.file_uploader("Subir archivo Excel", type=["xlsx"])
    if subida:
        df_excel = pd.read_excel(subida)
        st.write("Previsualización:")
        st.dataframe(df_excel.head())
        
        if st.button("Confirmar Ingesta"):
            conn = conectar()
            if conn:
                try:
                    with conn.cursor() as c:
                        # Limpieza de columnas para asegurar que coincidan con la DB
                        df_excel = df_excel.fillna("")
                        data = [tuple(x) for x in df_excel.values]
                        
                        # Ajusta las columnas según tu Excel
                        query = "INSERT INTO alumnos (nombre, curso, division, materias_adeudadas) VALUES %s"
                        extras.execute_values(c, query, data)
                        conn.commit()
                    conn.close()
                    st.success("Importación finalizada con éxito.")
                except Exception as e:
                    st.error(f"Error al importar: {e}")
