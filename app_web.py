import streamlit as st
import psycopg2
from psycopg2 import extras
import pandas as pd
import io
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="SOR MARIA - Gestión Integral", layout="wide")

def conectar():
    try:
        return psycopg2.connect(st.secrets["postgres_url"])
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# --- INICIALIZACIÓN ---
def init_db():
    conn = conectar()
    if conn:
        with conn.cursor() as c:
            # Tabla Alumnos (incluye fechas de instancias f1-f10)
            c.execute('''CREATE TABLE IF NOT EXISTS alumnos (
                id SERIAL PRIMARY KEY, nombre TEXT, curso TEXT, division TEXT, 
                materias_adeudadas TEXT, tercera_materia TEXT, profesor TEXT,
                n1 TEXT, e1 TEXT, f1 DATE, n2 TEXT, e2 TEXT, f2 DATE,
                n3 TEXT, e3 TEXT, f3 DATE, n4 TEXT, e4 TEXT, f4 DATE,
                n5 TEXT, e5 TEXT, f5 DATE, n6 TEXT, e6 TEXT, f6 DATE,
                n7 TEXT, e7 TEXT, f7 DATE, n8 TEXT, e8 TEXT, f8 DATE,
                n9 TEXT, e9 TEXT, f9 DATE, n10 TEXT, e10 TEXT, f10 DATE,
                estado TEXT DEFAULT 'PENDIENTE')''')
            # Tabla Seguimientos (Encuentros detallados)
            c.execute('''CREATE TABLE IF NOT EXISTS seguimientos (
                id SERIAL PRIMARY KEY, alumno_id INTEGER, 
                fecha_encuentro DATE, objetivo TEXT, observaciones TEXT)''')
            conn.commit()
        conn.close()

init_db()

# --- NAVEGACIÓN ---
menu = st.sidebar.radio("MENÚ", ["Seguimiento de Notas", "Gestión de Encuentros", "Cargar Alumno", "Backup & Datos"])

# --- 1. SEGUIMIENTO DE NOTAS (INSTANCIAS CON FECHA REAL) ---
if menu == "Seguimiento de Notas":
    st.subheader("📝 Instancias de Evaluación")
    conn = conectar()
    df = pd.read_sql("SELECT id, nombre, curso, tercera_materia, estado FROM alumnos", conn)
    
    col_sel, _ = st.columns([2, 2])
    idx = col_sel.selectbox("Seleccione Alumno", df['id'].tolist(), format_func=lambda x: df[df['id']==x]['nombre'].values[0])
    
    if idx:
        with conn.cursor() as c:
            c.execute("SELECT * FROM alumnos WHERE id=%s", (idx,))
            d = c.fetchone()
        
        with st.form("form_notas"):
            st.write(f"### Editando: {d[1]}")
            nuevos_datos = []
            for i in range(10):
                c1, c2, c3 = st.columns([2, 4, 1])
                # Mapeo: Nota: 8+(i*3), Estado: 9+(i*3), Fecha: 10+(i*3)
                f_ini = d[10 + i*3] if d[10 + i*3] else datetime.now()
                f_val = c1.date_input(f"Fecha {i+1}", value=f_ini, key=f"f{i}")
                n_val = c2.text_input(f"Nota/Obs {i+1}", value=d[8 + i*3] if d[8 + i*3] else "", key=f"n{i}")
                a_val = c3.checkbox("OK", value=(d[9 + i*3] == "S"), key=f"e{i}")
                nuevos_datos.extend([n_val, "S" if a_val else "N", f_val])
            
            if st.form_submit_button("Guardar Cambios"):
                with conn.cursor() as c:
                    q = """UPDATE alumnos SET n1=%s, e1=%s, f1=%s, n2=%s, e2=%s, f2=%s, n3=%s, e3=%s, f3=%s, 
                           n4=%s, e4=%s, f4=%s, n5=%s, e5=%s, f5=%s, n6=%s, e6=%s, f6=%s, n7=%s, e7=%s, f7=%s, 
                           n8=%s, e8=%s, f8=%s, n9=%s, e9=%s, f9=%s, n10=%s, e10=%s, f10=%s WHERE id=%s"""
                    c.execute(q, (*nuevos_datos, idx))
                    conn.commit()
                st.success("Notas actualizadas.")
    conn.close()

# --- 2. NUEVA FUNCIONALIDAD: GESTIÓN DEL SEGUIMIENTO (ENCUENTROS) ---
elif menu == "Gestión de Encuentros":
    st.subheader("🤝 GESTION DEL SEGUIMIENTO")
    conn = conectar()
    alumnos_df = pd.read_sql("SELECT id, nombre, curso, division FROM alumnos ORDER BY nombre", conn)
    
    tab1, tab2 = st.tabs(["Cargar Encuentro", "Ver Historial / Generar Acta"])
    
    with tab1:
        with st.form("nuevo_encuentro"):
            alumno_id = st.selectbox("Seleccionar Alumno", alumnos_df['id'].tolist(), 
                                    format_func=lambda x: f"{alumnos_df[alumnos_df['id']==x]['nombre'].values[0]} ({alumnos_df[alumnos_df['id']==x]['curso'].values[0]})")
            fecha_e = st.date_input("Fecha del encuentro", value=datetime.now())
            objetivo = st.text_input("Objetivo del encuentro")
            obs = st.text_area("Detalle del encuentro (máx 2000 car.)", max_chars=2000, height=200)
            
            if st.form_submit_button("Registrar Encuentro"):
                with conn.cursor() as c:
                    c.execute("INSERT INTO seguimientos (alumno_id, fecha_encuentro, objetivo, observaciones) VALUES (%s,%s,%s,%s)",
                              (alumno_id, fecha_e, objetivo, obs))
                    conn.commit()
                st.success("Encuentro registrado correctamente.")

    with tab2:
        sel_id = st.selectbox("Ver encuentros de:", alumnos_df['id'].tolist(), 
                             format_func=lambda x: alumnos_df[alumnos_df['id']==x]['nombre'].values[0], key="view_hist")
        
        # Obtener datos del alumno para el encabezado
        alumno_data = alumnos_df[alumnos_df['id'] == sel_id].iloc[0]
        encuentros = pd.read_sql(f"SELECT fecha_encuentro, objetivo, observaciones FROM seguimientos WHERE alumno_id={sel_id} ORDER BY fecha_encuentro DESC", conn)
        
        if not encuentros.empty:
            st.write("---")
            # --- GENERACIÓN DE DOCUMENTO ---
            acta_text = f"ACTA DE SEGUIMIENTO - ALUMNO: {alumno_data['nombre'].upper()}\n"
            acta_text += f"CURSO: {alumno_data['curso']} - DIVISIÓN: {alumno_data['division']}\n"
            acta_text += "="*50 + "\n\n"
            
            for _, row in encuentros.iterrows():
                st.info(f"📅 **Fecha:** {row['fecha_encuentro']} | **Objetivo:** {row['objetivo']}")
                st.write(row['observaciones'])
                st.write("---")
                
                acta_text += f"FECHA: {row['fecha_encuentro']}\nOBJETIVO: {row['objetivo']}\n"
                acta_text += f"OBSERVACIONES: {row['observaciones']}\n"
                acta_text += "-"*50 + "\n"

            st.download_button("📥 Descargar Acta (TXT)", acta_text, file_name=f"Acta_{alumno_data['nombre']}.txt")
        else:
            st.warning("No hay encuentros registrados para este alumno.")
    conn.close()

# --- 3. BACKUP & EXCEL ---
elif menu == "Backup & Datos":
    st.subheader("💾 Backup y Restauración")
    conn = conectar()
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("#### Generar Respaldo")
        if st.button("Preparar Excel"):
            df_total = pd.read_sql("SELECT * FROM alumnos", conn)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_total.to_excel(writer, index=False)
            st.download_button("Descargar Backup", output.getvalue(), "backup_colegio.xlsx")
            
    with col2:
        st.write("#### Importar Excel")
        file = st.file_uploader("Subir .xlsx", type=["xlsx"])
        if file and st.button("Confirmar Carga Masiva"):
            df_in = pd.read_excel(file).fillna("")
            with conn.cursor() as c:
                c.execute("TRUNCATE TABLE alumnos RESTART IDENTITY CASCADE")
                query = f"INSERT INTO alumnos ({','.join(df_in.columns)}) VALUES %s"
                extras.execute_values(c, query, [tuple(x) for x in df_in.values])
                conn.commit()
            st.success("Importación exitosa.")
    conn.close()

elif menu == "Cargar Alumno":
    # ... (Sección de carga individual simplificada que ya tenías) ...
    st.subheader("➕ Alta de Estudiante")
    with st.form("alta"):
        n = st.text_input("Nombre")
        c = st.text_input("Curso")
        if st.form_submit_button("Guardar"):
            conn = conectar()
            with conn.cursor() as c_ins:
                c_ins.execute("INSERT INTO alumnos (nombre, curso) VALUES (%s,%s)", (n, c))
                conn.commit()
            st.success("Alumno guardado.")
