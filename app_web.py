import streamlit as st
import psycopg2
from psycopg2 import extras
import pandas as pd
import io
from datetime import datetime, date
from fpdf import FPDF

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="SOR MARIA - Gestión Integral", layout="wide")

def conectar():
    try:
        # Usamos st.secrets para conectar a Neon local o en la nube
        return psycopg2.connect(st.secrets["postgres_url"])
    except Exception as e:
        st.error(f"Error crítico de conexión: {e}")
        return None

def clean_text(t):
    """Limpia caracteres para evitar errores en la generación de PDF"""
    if t is None: return ""
    return str(t).encode('latin-1', 'replace').decode('latin-1')

# --- CLASE PARA PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'INSTITUTO SOR MARIA DE PAZ Y FIGUEROA', 0, 1, 'C')
        self.ln(5)

# --- INICIALIZACIÓN DE TABLAS ---
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
menu = st.sidebar.radio("MENÚ PRINCIPAL", ["Seguimiento de Notas", "Gestión de Encuentros", "Ficha y Reportes", "Cargar Alumno", "Modificar Alumno", "Backup & Datos"])

# --- 1. SEGUIMIENTO DE NOTAS ---
if menu == "Seguimiento de Notas":
    st.subheader("📝 Instancias de Evaluación")
    conn = conectar()
    if conn:
        # Traemos alumnos con un diccionario para no errar en índices
        df = pd.read_sql("SELECT id, nombre, curso FROM alumnos ORDER BY nombre", conn)
        
        if not df.empty:
            sel_id = st.selectbox("Seleccione Alumno", df['id'].tolist(), 
                                  format_func=lambda x: f"{df[df['id']==x]['nombre'].values[0]} ({df[df['id']==x]['curso'].values[0]})")
            
            # Traemos el registro completo como diccionario
            with conn.cursor(cursor_factory=extras.DictCursor) as c:
                c.execute("SELECT * FROM alumnos WHERE id=%s", (sel_id,))
                d = c.fetchone()
            
            if d:
                with st.form("form_notas"):
                    st.markdown(f"### Estudiante: **{d['nombre']}**")
                    nuevos_datos = []
                    for i in range(1, 11):
                        c1, c2, c3 = st.columns([1.5, 3, 1])
                        # Acceso por nombre de columna para evitar errores de índice
                        f_db = d[f'f{i}']
                        f_ini = f_db if isinstance(f_db, (date, datetime)) else date.today()
                        
                        f_val = c1.date_input(f"Fecha {i}", value=f_ini, key=f"f{i}")
                        n_val = c2.text_input(f"Nota {i}", value=d[f'n{i}'] if d[f'n{i}'] else "", key=f"n{i}")
                        a_val = c3.checkbox("APROBADO", value=(d[f'e{i}'] == "S"), key=f"e{i}")
                        
                        nuevos_datos.extend([n_val, "S" if a_val else "N", f_val])
                    
                    if st.form_submit_button("💾 Guardar Cambios"):
                        with conn.cursor() as c_upd:
                            q = "UPDATE alumnos SET " + ", ".join([f"n{i}=%s, e{i}=%s, f{i}=%s" for i in range(1, 11)]) + " WHERE id=%s"
                            c_upd.execute(q, (*nuevos_datos, sel_id))
                            conn.commit()
                        st.success("¡Datos actualizados!")
                        st.rerun()
        else:
            st.warning("No hay alumnos cargados. Por favor, ve a 'Cargar Alumno'.")
        conn.close()

# --- 2. GESTIÓN DE ENCUENTROS ---
elif menu == "Gestión de Encuentros":
    st.subheader("🤝 Seguimiento de Encuentros")
    conn = conectar()
    if conn:
        df_a = pd.read_sql("SELECT id, nombre FROM alumnos ORDER BY nombre", conn)
        if not df_a.empty:
            with st.form("nuevo_enc"):
                a_id = st.selectbox("Alumno", df_a['id'].tolist(), format_func=lambda x: df_a[df_a['id']==x]['nombre'].values[0])
                f_e = st.date_input("Fecha", value=date.today())
                obj = st.text_input("Objetivo")
                obs = st.text_area("Observaciones", max_chars=2000)
                if st.form_submit_button("Registrar Encuentro"):
                    with conn.cursor() as c:
                        c.execute("INSERT INTO seguimientos (alumno_id, fecha_encuentro, objetivo, observaciones) VALUES (%s,%s,%s,%s)", (a_id, f_e, obj, obs))
                        conn.commit()
                    st.success("Encuentro registrado.")
        else:
            st.warning("Debe cargar alumnos primero.")
        conn.close()

# --- 3. FICHA Y REPORTES (CORRECCIÓN DEFINITIVA) ---
elif menu == "Ficha y Reportes":
    st.subheader("📊 Fichas Individuales y Reportes Generales")
    conn = conectar()
    
    if conn:
        tab1, tab2 = st.tabs(["📄 Ficha de Alumno (Individual)", "📋 Reporte General de Cursada"])

        # Función auxiliar para limpiar texto
        def clean_text(t):
            return str(t).encode('latin-1', 'replace').decode('latin-1')

        with tab1:
            st.write("#### Generar Ficha Pedagógica Individual")
            df_a = pd.read_sql("SELECT id, nombre, curso FROM alumnos ORDER BY nombre", conn)
            
            if not df_a.empty:
                # Usamos el nombre para el formato, pero el ID para la búsqueda
                sel_id = st.selectbox(
                    "Seleccione el Alumno para el PDF", 
                    df_a['id'].tolist(), 
                    format_func=lambda x: f"{df_a[df_a['id']==x]['nombre'].values[0]} ({df_a[df_a['id']==x]['curso'].values[0]})"
                )
                
                # Generamos el PDF
                if st.button("🖨️ Preparar Ficha PDF"):
                    try:
                        with conn.cursor(cursor_factory=extras.DictCursor) as c:
                            c.execute("SELECT * FROM alumnos WHERE id=%s", (sel_id,))
                            a = c.fetchone()
                            # Ajustamos la consulta de seguimientos (asegúrate que la tabla existe)
                            c.execute("SELECT fecha_encuentro, objetivo, observaciones FROM seguimientos WHERE alumno_id=%s ORDER BY fecha_encuentro", (sel_id,))
                            encuentros = c.fetchall()

                        pdf = FPDF() # Asegúrate que la clase es FPDF o la que hayas definido
                        pdf.add_page()
                        
                        # Encabezado con color
                        pdf.set_fill_color(240, 240, 240)
                        pdf.set_font('Arial', 'B', 12)
                        pdf.cell(0, 10, f"FICHA DE SEGUIMIENTO: {clean_text(a['nombre']).upper()}", 1, 1, 'C', fill=True)
                        pdf.ln(5)
                        
                        # Datos básicos
                        pdf.set_font('Arial', 'B', 10)
                        pdf.cell(30, 8, "Curso:", 0); pdf.set_font('Arial', '', 10); pdf.cell(60, 8, clean_text(a['curso']), 0)
                        pdf.set_font('Arial', 'B', 10); pdf.cell(30, 8, "Division:", 0); pdf.set_font('Arial', '', 10); pdf.cell(0, 8, clean_text(a.get('division', '-')), 0, 1)
                        
                        pdf.ln(5)
                        pdf.set_font('Arial', 'B', 11)
                        pdf.cell(0, 10, "INFORMACION ACADEMICA", 0, 1, 'L')
                        pdf.set_font('Arial', '', 10)
                        pdf.multi_cell(0, 8, f"Materias Adeudadas: {clean_text(a.get('materias_adeudadas', 'Ninguna'))}")
                        pdf.cell(0, 8, f"Tercera Materia: {clean_text(a.get('tercera_materia', 'N/A'))}", ln=True)
                        pdf.cell(0, 8, f"Estado General: {clean_text(a.get('estado_general', 'Pendiente'))}", ln=True)

                        # Detalle de Encuentros (Si existen)
                        if encuentros:
                            pdf.ln(10)
                            pdf.set_font('Arial', 'B', 11)
                            pdf.cell(0, 10, "DETALLE DE ENCUENTROS", 0, 1, 'L')
                            for enc in encuentros:
                                pdf.set_font('Arial', 'B', 9)
                                fecha_str = enc[0].strftime('%d/%m/%Y') if enc[0] else "S/F"
                                pdf.cell(0, 8, f"Fecha: {fecha_str} - Obj: {clean_text(enc[1])}", "T", 1)
                                pdf.set_font('Arial', '', 9)
                                pdf.multi_cell(0, 6, f"Observaciones: {clean_text(enc[2])}", 0)
                                pdf.ln(2)

                        # Output y Botón de descarga
                        pdf_raw = pdf.output(dest='S')
                        if isinstance(pdf_raw, str):
                            pdf_raw = pdf_raw.encode('latin-1', 'replace')

                        st.download_button(
                            label=f"📥 Descargar PDF de {a['nombre']}",
                            data=pdf_raw,
                            file_name=f"Ficha_{a['nombre'].replace(' ', '_')}.pdf",
                            mime="application/pdf"
                        )
                        st.success("PDF generado. Haz clic arriba para descargar.")

                    except Exception as e:
                        st.error(f"Error generando PDF: {e}")
            else:
                st.warning("No hay alumnos cargados.")

                with tab2:
                    st.write("#### Reporte General")
                    c1, c2, c3 = st.columns(3)
                    f_cur = c1.text_input("Filtrar Curso", key="rep_cur")
                    f_div = c2.text_input("Filtrar División", key="rep_div")
                    # Ajustamos las opciones del selectbox para que coincidan con tus datos
                    f_est = c3.selectbox("Estado", ["TODOS", "Pendiente", "Aprobada", "No Aprobada", "En Curso"], key="rep_est")

                    # USAMOS SELECT * PARA EVITAR EL ERROR DE COLUMNA INEXISTENTE AL CARGAR
                    query = "SELECT * FROM alumnos WHERE 1=1"
                    params = []
                    
                    if f_cur: 
                        query += " AND curso ILIKE %s"
                        params.append(f"%{f_cur}%")
                    if f_div: 
                        query += " AND division ILIKE %s"
                        params.append(f"%{f_div}%")
                    
                    # Ejecutamos la consulta de forma segura
                    try:
                        df_reporte = pd.read_sql(query, conn, params=params)
                        
                        # Filtramos el estado en el DataFrame de Pandas para evitar errores de SQL
                        if f_est != "TODOS":
                            # Ajusta 'estado_general' si en tu DB se llama 'estado'
                            col_estado = 'estado_general' if 'estado_general' in df_reporte.columns else 'estado'
                            if col_estado in df_reporte.columns:
                                df_reporte = df_reporte[df_reporte[col_estado] == f_est]

                        # Mostramos solo las columnas que existan para que la tabla sea limpia
                        columnas_visibles = [c for c in ['nombre', 'curso', 'division', 'tercera_materia', 'estado_general'] if c in df_reporte.columns]
                        st.dataframe(df_reporte[columnas_visibles], use_container_width=True)

                        if not df_reporte.empty:
                            if st.button("📊 Preparar Reporte General PDF"):
                                # ... (aquí va el resto del código del PDF que te pasé antes)
                                st.info("Generando archivo...")
                    
                    except Exception as e:
                        st.error(f"Error al cargar el reporte: {e}")
                        st.info("Revisa si los nombres de las columnas en Supabase coinciden con el código.")

        conn.close()

# --- 4. CARGAR ALUMNO ---
elif menu == "Cargar Alumno":
    st.subheader("➕ Alta de Alumno")
    with st.form("alta"):
        # Datos básicos
        col1, col2, col3 = st.columns(3)
        with col1:
            nom = st.text_input("Nombre y Apellido")
        with col2:
            cur = st.text_input("Curso")
        with col3:
            div = st.text_input("División")
        
        # Datos de materias (Lo que faltaba)
        st.markdown("---")
        st.write("📚 **Información Académica**")
        mat_adeuda = st.text_area("Materias que adeudaba (Ciclos anteriores)")
        tercera_mat = st.text_input("Tercera Materia elegida")
        
        estado_gen = st.selectbox("Estado General de la Materia", 
                                 ["Pendiente", "Aprobada", "No Aprobada", "En Curso"])

        if st.form_submit_button("Guardar"):
            if nom and cur:
                conn = conectar()
                if conn:
                    try:
                        with conn.cursor() as c:
                            # Actualizamos el INSERT con las nuevas columnas
                            sql = """
                                INSERT INTO alumnos 
                                (nombre, curso, division, materias_adeudadas, tercera_materia, estado_general) 
                                VALUES (%s, %s, %s, %s, %s, %s)
                            """
                            valores = (nom, cur, div, mat_adeuda, tercera_mat, estado_gen)
                            c.execute(sql, valores)
                            conn.commit()
                        st.success(f"✅ {nom} registrado con éxito.")
                    except Exception as e:
                        st.error(f"Error al insertar: {e}")
                    finally:
                        conn.close()
            else:
                st.error("Nombre y Curso son obligatorios.")


# --- 5. MODIFICAR ALUMNO ---
elif menu == "Modificar Alumno":
    st.subheader("📝 Modificar Datos de Alumno")
    
    nombre_buscar = st.text_input("Buscar alumno por nombre para editar")
    
    if nombre_buscar:
        conn = conectar()
        if conn:
            try:
                with conn.cursor() as c:
                    # Traemos todas las columnas para evitar el error de "columna no encontrada" 
                    # si hay diferencias de nombres entre el código y la DB
                    sql_select = "SELECT * FROM alumnos WHERE nombre ILIKE %s"
                    c.execute(sql_select, (f"%{nombre_buscar}%",))
                    
                    # Obtenemos los nombres de las columnas reales de la DB
                    columnas = [desc[0] for desc in c.description]
                    resultados = c.fetchall()
                
                if resultados:
                    # Creamos una lista de diccionarios para manejar los datos por nombre de columna
                    lista_alumnos = [dict(zip(columnas, r)) for r in resultados]
                    
                    opciones = {f"{a['nombre']} (Curso: {a.get('curso', '')})": i for i, a in enumerate(lista_alumnos)}
                    seleccion = st.selectbox("Seleccioná el alumno exacto:", list(opciones.keys()))
                    
                    # Alumno seleccionado (diccionario)
                    al_sel = lista_alumnos[opciones[seleccion]]
                    id_alumno = al_sel['id']

                    with st.form("form_edicion"):
                        st.info(f"Editando a: {al_sel['nombre']}")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            # Usamos .get() para que si la columna se llama distinto en la DB no explote
                            nuevo_nom = st.text_input("Nombre y Apellido", value=al_sel.get('nombre', ''))
                        with col2:
                            nuevo_cur = st.text_input("Curso", value=al_sel.get('curso', ''))
                        with col3:
                            nuevo_div = st.text_input("División", value=al_sel.get('division', ''))

                        st.markdown("---")
                        # BUSCAMOS LOS NOMBRES QUE USASTE EN EL INSERT DE LA FUNCIÓN 4
                        adeudadas_val = al_sel.get('materias_adeudadas', '') 
                        nuevas_adeudadas = st.text_area("Materias que adeudaba", value=adeudadas_val)
                        
                        tercera_val = al_sel.get('tercera_materia', '')
                        nueva_tercera = st.text_input("Tercera Materia elegida", value=tercera_val)
                        
                        # Manejo del Estado General
                        estados = ["Pendiente", "Aprobada", "No Aprobada", "En Curso"]
                        estado_db = al_sel.get('estado_general', 'Pendiente')
                        idx_estado = estados.index(estado_db) if estado_db in estados else 0
                        nuevo_estado = st.selectbox("Estado General", estados, index=idx_estado)

                        if st.form_submit_button("Guardar Cambios"):
                            with conn.cursor() as c_up:
                                # Sincronizamos el UPDATE con los mismos nombres del INSERT de la Func 4
                                sql_update = """
                                    UPDATE alumnos 
                                    SET nombre=%s, curso=%s, division=%s, 
                                        materias_adeudadas=%s, tercera_materia=%s, estado_general=%s
                                    WHERE id=%s
                                """
                                c_up.execute(sql_update, (
                                    nuevo_nom, nuevo_cur, nuevo_div, 
                                    nuevas_adeudadas, nueva_tercera, nuevo_estado, 
                                    id_alumno
                                ))
                                conn.commit()
                                st.success("✅ Datos actualizados correctamente.")
                                st.rerun()
                else:
                    st.warning("No se encontraron alumnos.")
            
            except Exception as e:
                st.error(f"Hubo un error con la base de datos: {e}")
            finally:
                conn.close()

# --- 6. BACKUP ---
elif menu == "Backup & Datos":
    st.subheader("💾 Gestión de Datos")
    conn = conectar()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Generar Backup"):
            df_back = pd.read_sql("SELECT * FROM alumnos", conn)
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as w:
                df_back.to_excel(w, index=False)
            st.download_button("📥 Descargar Excel", buf.getvalue(), "backup_alumnos.xlsx")
    with col2:
        file = st.file_uploader("Subir Excel para restaurar", type=["xlsx"])
        if file and st.button("Confirmar Restauración"):
            df_in = pd.read_excel(file).fillna("")
            with conn.cursor() as c:
                c.execute("TRUNCATE TABLE alumnos RESTART IDENTITY CASCADE")
                cols = ",".join(df_in.columns)
                extras.execute_values(c, f"INSERT INTO alumnos ({cols}) VALUES %s", [tuple(x) for x in df_in.values])
                conn.commit()
            st.success("Restauración completa.")
    conn.close()
