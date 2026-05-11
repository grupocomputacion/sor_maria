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

# --- 3. FICHA Y REPORTES (CORRECCIÓN DEFINITIVA BYTES/PDF) ---
elif menu == "Ficha y Reportes":
    st.subheader("📊 Fichas Individuales y Reportes Generales")
    conn = conectar()
    
    if conn:
        tab1, tab2 = st.tabs(["📄 Ficha de Alumno (Individual)", "📋 Reporte General de Cursada"])

        with tab1:
            st.write("#### Generar Ficha Pedagógica Individual")
            df_a = pd.read_sql("SELECT id, nombre, curso FROM alumnos ORDER BY nombre", conn)
            if not df_a.empty:
                sel_id = st.selectbox("Seleccione el Alumno para el PDF", df_a['id'].tolist(), 
                                      format_func=lambda x: f"{df_a[df_a['id']==x]['nombre'].values[0]} ({df_a[df_a['id']==x]['curso'].values[0]})")
                
                if st.button("🖨️ Generar Ficha PDF"):
                    try:
                        with conn.cursor(cursor_factory=extras.DictCursor) as c:
                            c.execute("SELECT * FROM alumnos WHERE id=%s", (sel_id,))
                            a = c.fetchone()
                            c.execute("SELECT fecha_encuentro, objetivo, observaciones FROM seguimientos WHERE alumno_id=%s ORDER BY fecha_encuentro", (sel_id,))
                            encuentros = c.fetchall()

                        pdf = PDF()
                        pdf.add_page()
                        
                        # Limpieza de caracteres para evitar errores de encoding en el PDF
                        def clean_text(t):
                            return str(t).encode('latin-1', 'replace').decode('latin-1')

                        pdf.set_fill_color(240, 240, 240)
                        pdf.set_font('Arial', 'B', 12)
                        pdf.cell(0, 10, f"FICHA DE SEGUIMIENTO: {clean_text(a['nombre']).upper()}", 1, 1, 'C', fill=True)
                        pdf.ln(5)
                        
                        pdf.set_font('Arial', 'B', 10)
                        pdf.cell(30, 8, "Curso:", 0); pdf.set_font('Arial', '', 10); pdf.cell(60, 8, clean_text(a['curso']), 0)
                        pdf.set_font('Arial', 'B', 10); pdf.cell(30, 8, "Division:", 0); pdf.set_font('Arial', '', 10); pdf.cell(0, 8, clean_text(a['division']), 0, 1)
                        
                        pdf.ln(5)
                        pdf.set_font('Arial', 'B', 11)
                        pdf.cell(0, 10, "INSTANCIAS EVALUATIVAS", 0, 1, 'L')
                        pdf.set_font('Arial', 'B', 9)
                        pdf.cell(30, 8, "Fecha", 1); pdf.cell(120, 8, "Nota / Observacion", 1); pdf.cell(40, 8, "Estado", 1, 1)
                        
                        pdf.set_font('Arial', '', 9)
                        for i in range(1, 11):
                            if a[f'n{i}']:
                                f_val = a[f'f{i}'].strftime("%d/%m/%Y") if a[f'f{i}'] else "-"
                                est_val = "APROBADO" if a[f'e{i}'] == "S" else "PENDIENTE"
                                pdf.cell(30, 8, f_val, 1)
                                pdf.cell(120, 8, clean_text(a[f'n{i}'])[:70], 1)
                                pdf.cell(40, 8, est_val, 1, 1)

                        if encuentros:
                            pdf.ln(10)
                            pdf.set_font('Arial', 'B', 11)
                            pdf.cell(0, 10, "DETALLE DE ENCUENTROS", 0, 1, 'L')
                            for enc in encuentros:
                                pdf.set_font('Arial', 'B', 9)
                                pdf.cell(0, 8, f"Fecha: {enc[0].strftime('%d/%m/%Y')} - Obj: {clean_text(enc[1])}", "T", 1)
                                pdf.set_font('Arial', '', 9)
                                pdf.multi_cell(0, 6, f"Detalle: {clean_text(enc[2])}", 0)
                                pdf.ln(2)

                            # --- FIX SEGURO ---
                            pdf_raw = pdf.output(dest='S')
                            # Si pdf_raw es string, lo encodamos. Si ya es bytes, lo dejamos pasar.
                            if isinstance(pdf_raw, str):
                                pdf_raw = pdf_raw.encode('latin-1')

                            st.download_button(
                                label=f"📥 Bajar PDF {a['nombre']}", 
                                data=pdf_raw, 
                                file_name=f"Ficha_{a['nombre']}.pdf", 
                                mime="application/pdf"
                            )                       

                    except Exception as e:
                        st.error(f"Error generando PDF: {e}")
            else:
                st.warning("No hay alumnos cargados.")

        with tab2:
            st.write("#### Filtros de Reporte General")
            c1, c2, c3, c4 = st.columns(4)
            f_cur = c1.text_input("Curso", key="rep_cur")
            f_div = c2.text_input("División", key="rep_div")
            f_mat = c3.text_input("Materia", key="rep_mat")
            f_est = c4.selectbox("Estado", ["TODOS", "APROBADO", "PENDIENTE"], key="rep_est")

            query = "SELECT nombre, curso, division, tercera_materia, profesor, estado FROM alumnos WHERE 1=1"
            params = []
            if f_cur: query += " AND curso ILIKE %s"; params.append(f"%{f_cur}%")
            if f_div: query += " AND division ILIKE %s"; params.append(f"%{f_div}%")
            if f_mat: query += " AND tercera_materia ILIKE %s"; params.append(f"%{f_mat}%")
            
            df_reporte = pd.read_sql(query, conn, params=params)
            if f_est != "TODOS":
                df_reporte = df_reporte[df_reporte['estado'] == f_est]

            st.dataframe(df_reporte, use_container_width=True)

            if not df_reporte.empty:
                if st.button("📊 Generar Reporte General PDF"):
                    try:
                        pdf_rep = PDF()
                        pdf_rep.add_page()
                        pdf_rep.set_font('Arial', 'B', 14)
                        pdf_rep.cell(0, 10, "REPORTE GENERAL - ESTADO DE ALUMNOS", 0, 1, 'C')
                        pdf_rep.ln(5)
                        
                        pdf_rep.set_font('Arial', 'B', 9)
                        pdf_rep.set_fill_color(200, 220, 255)
                        pdf_rep.cell(60, 10, "Alumno", 1, 0, 'C', True)
                        pdf_rep.cell(30, 10, "Curso/Div", 1, 0, 'C', True)
                        pdf_rep.cell(60, 10, "Materia", 1, 0, 'C', True)
                        pdf_rep.cell(30, 10, "Estado", 1, 1, 'C', True)

                        pdf_rep.set_font('Arial', '', 8)
                        for _, r in df_reporte.iterrows():
                            pdf_rep.cell(60, 8, clean_text(r['nombre'])[:30], 1)
                            pdf_rep.cell(30, 8, f"{r['curso']} {r['division']}", 1, 0, 'C')
                            pdf_rep.cell(60, 8, clean_text(r['tercera_materia'])[:30], 1)
                            pdf_rep.cell(30, 8, str(r['estado']), 1, 1, 'C')

                        # --- FIX SEGURO ---
                        pdf_rep_raw = pdf_rep.output(dest='S')
                        if isinstance(pdf_rep_raw, str):
                            pdf_rep_raw = pdf_rep_raw.encode('latin-1')

                        st.download_button(
                            label="📥 Bajar Reporte", 
                            data=pdf_rep_raw, 
                            file_name="Reporte.pdf", 
                            mime="application/pdf"
                        )
                    except Exception as e:
                        st.error(f"Error generando Reporte: {e}")
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
    st.subheader("📝 Modificar Datos Completos de Alumno")
    
    # Buscador para elegir al alumno
    nombre_buscar = st.text_input("Buscar alumno por nombre para editar")
    
    if nombre_buscar:
        conn = conectar()
        with conn.cursor() as c:
            # --- CAMBIO 1: QUERY DE SELECCIÓN CON JOINS ---
            # Traemos datos del alumno + datos de su tercera materia (si tiene)
            sql_select = """
                SELECT 
                    a.id, a.nombre, a.curso, a.materias_adeuda,
                    i.id_materia, i.id_profesor, i.estado_materia
                FROM alumnos a
                LEFT JOIN inscripciones_tercera i ON a.id = i.id_alumno
                WHERE a.nombre ILIKE %s
            """
            c.execute(sql_select, (f"%{nombre_buscar}%",))
            resultados = c.fetchall()
        
        if resultados:
            # Diccionario para el selectbox
            opciones = {f"{r[1]} ({r[2]})": r[0] for r in resultados}
            seleccion = st.selectbox("Seleccioná el alumno exacto:", list(opciones.keys()))
            id_alumno = opciones[seleccion]

            # Traemos los datos actuales del alumno elegido del fetchall
            alumno_actual = next(r for r in resultados if r[0] == id_alumno)

            # Índices de alumno_actual según la query:
            # 0: id, 1: nombre, 2: curso, 3: materias_adeuda, 
            # 4: id_materia, 5: id_profesor, 6: estado_materia

            # --- OBTENER LISTAS PARA SELECTBOXES (Materias y Profesores) ---
            # Esto es necesario para que el usuario elija de una lista, no escriba
            with conn.cursor() as c:
                c.execute("SELECT id, nombre_materia FROM materias")
                lista_materias = c.fetchall() # [(1, 'Matemáticas'), (2, 'Historia')]
                
                c.execute("SELECT id, nombre_profesor FROM profesores")
                lista_profesores = c.fetchall() # [(1, 'Dr. Gómez'), (2, 'Lic. Pérez')]

            # Creamos diccionarios para mapear nombre<->id en Streamlit
            dict_materias = {m[1]: m[0] for m in lista_materias}
            dict_profesores = {p[1]: p[0] for p in lista_profesores}

            # --- 2. Formulario de edición ---
            with st.form("form_edicion_completa"):
                st.info(f"Editando a: {alumno_actual[1]} (ID: {id_alumno})")
                
                # --- CAMBIO 2: CAMPOS DE LA INTERFAZ ---
                
                # A. Materias que adeuda (asumiendo campo de texto largo)
                # Usamos value="" si es None
                adeuda_actual = alumno_actual[3] if alumno_actual[3] else ""
                nuevas_adeudadas = st.text_area("Materias que adeuda (separadas por coma)", value=adeuda_actual)
                
                st.write("---")
                st.write("**Datos de la Tercera Materia**")

                # B. Tercera Materia (Selectbox)
                # Calculamos el índice actual
                materia_id_actual = alumno_actual[4]
                # Obtenemos el nombre actual si existe el ID
                materia_nombre_actual = next((nombre for nombre, id in dict_materias.items() if id == materia_id_actual), None)
                
                # Selectbox de materias
                materias_keys = list(dict_materias.keys())
                # Si el alumno tiene materia, buscamos su índice. Si no, default a 0 o agregamos opción 'Ninguna'
                index_materia = materias_keys.index(materia_nombre_actual) if materia_nombre_actual in materias_keys else 0
                materia_seleccionada = st.selectbox("Tercera Materia", materias_keys, index=index_materia)

                # C. Profesor involucrado (Selectbox)
                profe_id_actual = alumno_actual[5]
                profe_nombre_actual = next((nombre for nombre, id in dict_profesores.items() if id == profe_id_actual), None)
                
                profesores_keys = list(dict_profesores.keys())
                index_profe = profesores_keys.index(profe_nombre_actual) if profe_nombre_actual in profesores_keys else 0
                profesor_seleccionado = st.selectbox("Profesor involucrado", profesores_keys, index=index_profe)

                # D. Estado de la tercera materia (Selectbox)
                estados_posibles = ["Pendiente", "En Curso", "Aprobada", "No Aprobada"]
                estado_actual = alumno_actual[6] if alumno_actual[6] else "Pendiente"
                
                index_estado = estados_posibles.index(estado_actual) if estado_actual in estados_posibles else 0
                nuevo_estado_materia = st.selectbox("Estado de la tercera materia", estados_posibles, index=index_estado)

                # BOTÓN DE ACTUALIZAR
                if st.form_submit_button("Guardar Cambios Completos"):
                    # Obtenemos los IDs reales seleccionados
                    id_materia_nueva = dict_materias[materia_seleccionada]
                    id_profesor_nuevo = dict_profesores[profesor_seleccionado]

                    with conn.cursor() as c:
                        try:
                            # --- CAMBIO 3: QUERIES DE ACTUALIZACIÓN ---
                            
                            # 1. Actualizar tabla alumnos (materias adeudadas)
                            sql_adeuda = "UPDATE alumnos SET materias_adeuda = %s WHERE id = %s"
                            c.execute(sql_adeuda, (nuevas_adeudadas, id_alumno))
                            
                            # 2. Actualizar tabla inscripciones_tercera 
                            # (Usamos ON CONFLICT por si el alumno no tenía inscripción previa)
                            # Esto asume que id_alumno es UNIQUE o PRIMARY KEY en inscripciones_tercera
                            sql_tercera = """
                                INSERT INTO inscripciones_tercera (id_alumno, id_materia, id_profesor, estado_materia)
                                VALUES (%s, %s, %s, %s)
                                ON CONFLICT (id_alumno) 
                                DO UPDATE SET 
                                    id_materia = EXCLUDED.id_materia,
                                    id_profesor = EXCLUDED.id_profesor,
                                    estado_materia = EXCLUDED.estado_materia
                            """
                            c.execute(sql_tercera, (id_alumno, id_materia_nueva, id_profesor_nuevo, nuevo_estado_materia))
                            
                            conn.commit()
                            st.success("✅ Datos del alumno y tercera materia actualizados correctamente.")
                        except Exception as e:
                            conn.rollback()
                            st.error(f"❌ Error al actualizar: {e}")

        else:
            st.warning("No se encontraron alumnos con ese nombre.")
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
