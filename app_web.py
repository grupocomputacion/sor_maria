import streamlit as st
import psycopg2
from psycopg2 import extras
import pandas as pd
import io
from datetime import datetime, date

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
            c.execute('''CREATE TABLE IF NOT EXISTS alumnos (
                id SERIAL PRIMARY KEY, nombre TEXT, curso TEXT, division TEXT, 
                materias_adeudadas TEXT, tercera_materia TEXT, profesor TEXT,
                n1 TEXT, e1 TEXT, f1 DATE, n2 TEXT, e2 TEXT, f2 DATE,
                n3 TEXT, e3 TEXT, f3 DATE, n4 TEXT, e4 TEXT, f4 DATE,
                n5 TEXT, e5 TEXT, f5 DATE, n6 TEXT, e6 TEXT, f6 DATE,
                n7 TEXT, e7 TEXT, f7 DATE, n8 TEXT, e8 TEXT, f8 DATE,
                n9 TEXT, e9 TEXT, f9 DATE, n10 TEXT, e10 TEXT, f10 DATE,
                estado TEXT DEFAULT 'PENDIENTE')''')
            c.execute('''CREATE TABLE IF NOT EXISTS seguimientos (
                id SERIAL PRIMARY KEY, alumno_id INTEGER, 
                fecha_encuentro DATE, objetivo TEXT, observaciones TEXT)''')
            conn.commit()
        conn.close()

init_db()

# --- NAVEGACIÓN ---
menu = st.sidebar.radio("MENÚ", ["Seguimiento de Notas", "Gestión de Encuentros", "Cargar Alumno", "Backup & Datos"])


# --- 1. SEGUIMIENTO DE NOTAS (BLINDADO Y ESTÉTICO) ---
if menu == "Seguimiento de Notas":
    st.subheader("📝 Instancias de Evaluación")
    conn = conectar()
    df = pd.read_sql("SELECT id, nombre, curso, tercera_materia, estado FROM alumnos ORDER BY nombre", conn)
    
    if not df.empty:
        col_sel, _ = st.columns([2, 2])
        idx = col_sel.selectbox("Seleccione Alumno", df['id'].tolist(), 
                                format_func=lambda x: f"{df[df['id']==x]['nombre'].values[0]} ({df[df['id']==x]['curso'].values[0]})")
        
        if idx:
            with conn.cursor() as c:
                c.execute("SELECT * FROM alumnos WHERE id=%s", (idx,))
                d = c.fetchone()
            
            # Usamos un formulario para agrupar todo
            with st.form("form_notas_final"):
                st.markdown(f"### 🧑‍🎓 Estudiante: **{d[1]}**")
                
                nuevos_datos = []
                
                # Renderizamos las 10 instancias
                for i in range(10):
                    with st.container():
                        c_fec, c_not, c_apr = st.columns([1.5, 3, 1])
                        
                        # --- CAPA DE SEGURIDAD PARA FECHAS ---
                        # Buscamos la fecha en la posición 29 + i (f1 es la col 29 en Postgres)
                        try:
                            f_raw = d[29 + i]
                            # Si es un objeto date/datetime lo usamos, sino ponemos hoy
                            f_val_init = f_raw if isinstance(f_raw, (date, datetime)) else date.today()
                        except:
                            f_val_init = date.today()

                        # Widgets
                        f_val = c_fec.date_input(f"📅 Fecha {i+1}", value=f_val_init, key=f"f{i}")
                        n_val = c_not.text_input(f"🖋️ Nota {i+1}", value=d[8 + i*3] if d[8 + i*3] else "", key=f"n{i}")
                        a_val = c_apr.checkbox("✅ APROBADO", value=(d[9 + i*3] == "S"), key=f"e{i}")
                        
                        # Guardamos para el UPDATE (Nota, Aprobado, Fecha)
                        nuevos_datos.extend([n_val, "S" if a_val else "N", f_val])
                
                st.markdown("---")
                # El botón DEBE estar dentro del 'with st.form'
                btn_guardar = st.form_submit_button("💾 GUARDAR TODA LA FICHA")
                
                if btn_guardar:
                    with conn.cursor() as c_upd:
                        q = """UPDATE alumnos SET 
                               n1=%s, e1=%s, f1=%s, n2=%s, e2=%s, f2=%s, n3=%s, e3=%s, f3=%s, 
                               n4=%s, e4=%s, f4=%s, n5=%s, e5=%s, f5=%s, n6=%s, e6=%s, f6=%s, 
                               n7=%s, e7=%s, f7=%s, n8=%s, e8=%s, f8=%s, n9=%s, e9=%s, f9=%s, 
                               n10=%s, e10=%s, f10=%s WHERE id=%s"""
                        c_upd.execute(q, (*nuevos_datos, idx))
                        conn.commit()
                    st.success(f"✨ ¡Ficha de {d[1]} guardada!")
                    st.balloons()
                    st.rerun()
    else:
        st.info("No hay alumnos cargados.")
    conn.close()
    

# --- 2. GESTIÓN DEL SEGUIMIENTO (ENCUENTROS) ---
elif menu == "Gestión de Encuentros":
    st.subheader("🤝 Gestión de Encuentros Detallados")
    conn = conectar()
    alumnos_df = pd.read_sql("SELECT id, nombre, curso, division FROM alumnos ORDER BY nombre", conn)
    
    tab1, tab2 = st.tabs(["Cargar Encuentro", "Ver Historial y Acta"])
    
    with tab1:
        with st.form("nuevo_encuentro"):
            alumno_id = st.selectbox("Alumno", alumnos_df['id'].tolist(), 
                                    format_func=lambda x: f"{alumnos_df[alumnos_df['id']==x]['nombre'].values[0]}")
            fecha_e = st.date_input("Fecha", value=date.today())
            objetivo = st.text_input("Objetivo")
            obs = st.text_area("Observaciones (máx 2000 car.)", max_chars=2000)
            if st.form_submit_button("Registrar"):
                with conn.cursor() as c:
                    c.execute("INSERT INTO seguimientos (alumno_id, fecha_encuentro, objetivo, observaciones) VALUES (%s,%s,%s,%s)",
                              (alumno_id, fecha_e, objetivo, obs))
                    conn.commit()
                st.success("Encuentro registrado.")

    with tab2:
        sel_id = st.selectbox("Seleccionar Alumno para Acta", alumnos_df['id'].tolist(), 
                             format_func=lambda x: alumnos_df[alumnos_df['id']==x]['nombre'].values[0])
        
        encuentros = pd.read_sql(f"SELECT fecha_encuentro, objetivo, observaciones FROM seguimientos WHERE alumno_id={sel_id} ORDER BY fecha_encuentro DESC", conn)
        
        if not encuentros.empty:
            alumno_info = alumnos_df[alumnos_df['id'] == sel_id].iloc[0]
            acta = f"ACTA DE SEGUIMIENTO: {alumno_info['nombre'].upper()}\nCURSO: {alumno_info['curso']}\n{'='*40}\n\n"
            
            for _, row in encuentros.iterrows():
                st.markdown(f"**Fecha:** {row['fecha_encuentro']} | **Objetivo:** {row['objetivo']}")
                st.write(row['observaciones'])
                st.markdown("---")
                acta += f"FECHA: {row['fecha_encuentro']}\nOBJETIVO: {row['objetivo']}\nOBS: {row['observaciones']}\n{'-'*40}\n"

            st.download_button("📥 Descargar Acta .txt", acta, file_name=f"Acta_{alumno_info['nombre']}.txt")
    conn.close()

# --- 3. BACKUP & DATOS (RESTABLECIDO) ---
elif menu == "Backup & Datos":
    st.subheader("💾 Backup y Restauración")
    conn = conectar()
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("Genera un Excel con todos los datos de la base.")
        if st.button("Generar Backup"):
            df_total = pd.read_sql("SELECT * FROM alumnos", conn)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_total.to_excel(writer, index=False)
            st.download_button("Descargar Excel", output.getvalue(), "backup_sistema.xlsx")
            
    with col2:
        st.write("#### Restaurar desde Excel")
        file = st.file_uploader("Subir .xlsx para importar", type=["xlsx"], key="restaurador")
        if file and st.button("Confirmar Sobreescritura"):
            try:
                df_in = pd.read_excel(file).fillna("")
                conn = conectar()
                with conn.cursor() as c:
                    # AQUÍ ESTABA EL ERROR: Aseguramos que la sentencia sea completa
                    c.execute("TRUNCATE TABLE alumnos RESTART IDENTITY CASCADE")
                    
                    # Preparamos las columnas y los placeholders dinámicos
                    cols = ",".join(df_in.columns)
                    placeholders = ",".join(["%s"] * len(df_in.columns))
                    query = f"INSERT INTO alumnos ({cols}) VALUES ({placeholders})"
                    
                    # Carga masiva
                    extras.execute_values(c, f"INSERT INTO alumnos ({cols}) VALUES %s", [tuple(x) for x in df_in.values])
                    conn.commit()
                st.success("✅ Base de datos restaurada con éxito.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error en la restauración: {str(e)}")
            finally:
                if conn: conn.close()
