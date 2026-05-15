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


# --- 1. SEGUIMIENTO DE NOTAS (ACTUALIZADO) ---
if menu == "Seguimiento de Notas":
    st.subheader("📝 Instancias de Evaluación")
    conn = conectar()
    if conn:
        df = pd.read_sql("SELECT id, nombre, curso FROM alumnos ORDER BY nombre", conn)

        if not df.empty:
            if "reset_buscador" not in st.session_state:
                st.session_state.reset_buscador = 0

            sel_id = st.selectbox(
                "Seleccione Alumno",
                df["id"].tolist(),
                format_func=lambda x: f"{df[df['id']==x]['nombre'].values[0]} ({df[df['id']==x]['curso'].values[0]})",
                key=f"selector_{st.session_state.reset_buscador}",
            )

            with conn.cursor(cursor_factory=extras.DictCursor) as c:
                c.execute("SELECT * FROM alumnos WHERE id=%s", (sel_id,))
                d = c.fetchone()

            if d:
                st.markdown(f"### Estudiante: **{d['nombre']}**")
                
                ctx1, ctx2, ctx3 = st.columns(3)
                ctx1.metric("Curso", f"{d['curso']} {d.get('division', '')}")
                ctx2.metric("Tercera Materia", d.get('tercera_materia', 'No asignada'))
                # Normalizado a 'estado' según tu base de datos
                ctx3.metric("Estado Actual", d.get('estado', 'Pendience'))
                
                st.divider()

                # ── Encabezado (Basado en Captura de pantalla 2026-05-14) ────────
                h0, h1, h2, h3, h4, h5 = st.columns([0.4, 0.7, 1.8, 3.2, 1.3, 0.6])
                headers = ["**#**","**Cargar**","**Fecha**","**Observaciones**","**Aprobado**","**Limpiar**"]
                for col, txt in zip([h0, h1, h2, h3, h4, h5], headers):
                    col.markdown(txt)

                # ── Filas de datos ─────────────────
                for i in range(1, 11):
                    c0, c1, c2, c3, c4, c5 = st.columns([0.4, 0.7, 1.8, 3.2, 1.3, 0.6])
                    c0.markdown(f"<div style='padding-top:8px'><b>{i}</b></div>", unsafe_allow_html=True)

                    v_act = d[f"f{i}"] is not None
                    v_f   = d[f"f{i}"] if d[f"f{i}"] else date.today()
                    v_n   = d[f"n{i}"] if d[f"n{i}"] else ""
                    
                    # Lógica de carga de valor previo de Aprobado
                    v_e_db = d[f"e{i}"] if d[f"e{i}"] else "No"
                    opciones_aprobado = ["No", "Tema", "Materia"]
                    idx_aprobado = opciones_aprobado.index(v_e_db) if v_e_db in opciones_aprobado else 0

                    act = c1.checkbox(" ", value=v_act, key=f"act_{i}_{sel_id}", label_visibility="collapsed")

                    if act:
                        c2.date_input(f"F{i}", value=v_f, key=f"f_{i}_{sel_id}", label_visibility="collapsed", format="DD/MM/YYYY")
                    else:
                        c2.markdown("<div style='color:#aaa;padding-top:8px;font-size:0.9em;'>dd/mm/aaaa</div>", unsafe_allow_html=True)

                    c3.text_input(f"N{i}", value=v_n, key=f"n_{i}_{sel_id}", label_visibility="collapsed", placeholder="Notas...")
                    
                    # Selector de Aprobación (Mejora solicitada)
                    c4.selectbox(" ", opciones_aprobado, index=idx_aprobado, key=f"e_{i}_{sel_id}", label_visibility="collapsed")

                    if c5.button("🗑️", key=f"limp_{i}_{sel_id}"):
                        for k in [f"act_{i}_{sel_id}", f"f_{i}_{sel_id}", f"n_{i}_{sel_id}", f"e_{i}_{sel_id}"]:
                            if k in st.session_state: del st.session_state[k]
                        st.rerun()

                st.divider()

                # ── Botón Guardar con Actualización de Estado ──────────────────
                if st.button("💾 Guardar Cambios y Finalizar", use_container_width=True, type="primary"):
                    try:
                        valores = []
                        materia_aprobada_ahora = False
                        
                        for i in range(1, 11):
                            is_act = st.session_state[f"act_{i}_{sel_id}"]
                            f_val  = st.session_state.get(f"f_{i}_{sel_id}") if is_act else None
                            n_val  = st.session_state[f"n_{i}_{sel_id}"]
                            e_val  = st.session_state[f"e_{i}_{sel_id}"]
                            
                            if e_val == "Materia":
                                materia_aprobada_ahora = True
                                
                            valores.extend([n_val, e_val, f_val])

                        with conn.cursor() as c_upd:
                            # 1. Guardar las notas de las instancias
                            q = "UPDATE alumnos SET " + ", ".join([f"n{i}=%s, e{i}=%s, f{i}=%s" for i in range(1, 11)]) + " WHERE id=%s"
                            c_upd.execute(q, (*valores, sel_id))
                            
                            # 2. Si se marcó 'Materia', actualizamos el estado general
                            if materia_aprobada_ahora:
                                c_upd.execute("UPDATE alumnos SET estado = 'Aprobada' WHERE id = %s", (sel_id,))
                            
                            conn.commit()

                        st.success(f"✅ ¡Datos guardados! {'¡Felicitaciones, materia aprobada!' if materia_aprobada_ahora else ''}")
                        
                        st.session_state.reset_buscador += 1
                        st.rerun()

                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

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

        def clean_text(t):
            return str(t).encode('latin-1', 'replace').decode('latin-1')

        # --- TAB 1: FICHA INDIVIDUAL ---
        with tab1:
            st.write("#### Generar Ficha Pedagógica Individual")
            df_a = pd.read_sql("SELECT id, nombre, curso FROM alumnos ORDER BY nombre", conn)
            
            if not df_a.empty:
                sel_id = st.selectbox(
                    "Seleccione el Alumno para el PDF", 
                    df_a['id'].tolist(), 
                    format_func=lambda x: f"{df_a[df_a['id']==x]['nombre'].values[0]} ({df_a[df_a['id']==x]['curso'].values[0]})"
                )
                
                if st.button("🖨️ Preparar Ficha PDF"):
                    try:
                        with conn.cursor(cursor_factory=extras.DictCursor) as c:
                            c.execute("SELECT * FROM alumnos WHERE id=%s", (sel_id,))
                            a = c.fetchone()
                            # Ajuste dinámico de columna estado para el PDF
                            col_est_ficha = 'estado' if 'estado' in a.keys() else 'estado_general'
                            
                            c.execute("SELECT fecha_encuentro, objetivo, observaciones FROM seguimientos WHERE alumno_id=%s ORDER BY fecha_encuentro", (sel_id,))
                            encuentros = c.fetchall()

                        pdf = FPDF()
                        pdf.add_page()
                        pdf.set_fill_color(240, 240, 240)
                        pdf.set_font('Arial', 'B', 12)
                        pdf.cell(0, 10, f"FICHA DE SEGUIMIENTO: {clean_text(a['nombre']).upper()}", 1, 1, 'C', fill=True)
                        pdf.ln(5)
                        
                        pdf.set_font('Arial', 'B', 10)
                        pdf.cell(30, 8, "Curso:", 0); pdf.set_font('Arial', '', 10); pdf.cell(60, 8, clean_text(a['curso']), 0)
                        pdf.set_font('Arial', 'B', 10); pdf.cell(30, 8, "Division:", 0); pdf.set_font('Arial', '', 10); pdf.cell(0, 8, clean_text(a.get('division', '-')), 0, 1)
                        
                        pdf.ln(5)
                        pdf.set_font('Arial', 'B', 11)
                        pdf.cell(0, 10, "INFORMACION ACADEMICA", 0, 1, 'L')
                        pdf.set_font('Arial', '', 10)
                        pdf.multi_cell(0, 8, f"Materias Adeudadas: {clean_text(a.get('materias_adeudadas', 'Ninguna'))}")
                        pdf.cell(0, 8, f"Tercera Materia: {clean_text(a.get('tercera_materia', 'N/A'))}", ln=True)
                        pdf.cell(0, 8, f"Estado General: {clean_text(a.get(col_est_ficha, 'Pendiente'))}", ln=True)

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

                        pdf_raw = pdf.output(dest='S')
                        if isinstance(pdf_raw, str): pdf_raw = pdf_raw.encode('latin-1', 'replace')

                        st.download_button(
                            label=f"📥 Descargar PDF de {a['nombre']}",
                            data=pdf_raw,
                            file_name=f"Ficha_{a['nombre'].replace(' ', '_')}.pdf",
                            mime="application/pdf"
                        )
                        st.success("PDF generado.")
                    except Exception as e:
                        st.error(f"Error generando PDF: {e}")
            else:
                st.warning("No hay alumnos cargados.")

        # --- TAB 2: REPORTE GENERAL (SOLUCIÓN GENERACIÓN PDF) ---
        with tab2:
            st.write("#### Reporte General de Cursada")
            c1, c2, c3 = st.columns(3)
            f_cur = c1.text_input("Filtrar Curso", key="rep_cur")
            f_div = c2.text_input("Filtrar División", key="rep_div")
            f_est = c3.selectbox("Estado", ["TODOS", "Pendiente", "Aprobada", "No Aprobada", "En Curso"], key="rep_est")

            query = "SELECT * FROM alumnos WHERE 1=1"
            params = []
            
            if f_cur: 
                query += " AND curso ILIKE %s"; params.append(f"%{f_cur}%")
            if f_div: 
                query += " AND division ILIKE %s"; params.append(f"%{f_div}%")
            
            try:
                df_reporte = pd.read_sql(query, conn, params=params)
                col_estado = 'estado' if 'estado' in df_reporte.columns else 'estado_general'
                
                if f_est != "TODOS" and col_estado in df_reporte.columns:
                    df_reporte = df_reporte[df_reporte[col_estado] == f_est]

                cols_vis = ['nombre', 'curso', 'division', 'tercera_materia', col_estado]
                columnas_finales = [c for c in cols_vis if c in df_reporte.columns]
                
                if not df_reporte.empty:
                    st.dataframe(df_reporte[columnas_finales], use_container_width=True)
                    
                    # --- BOTÓN CON LÓGICA DE PDF ---
                    if st.button("📊 Generar Reporte General PDF"):
                        try:
                            pdf = FPDF()
                            pdf.add_page()
                            pdf.set_font('Arial', 'B', 14)
                            pdf.cell(0, 10, clean_text("REPORTE GENERAL DE CURSADA"), 1, 1, 'C')
                            pdf.ln(5)
                            
                            # Encabezados de tabla en el PDF
                            pdf.set_font('Arial', 'B', 10)
                            pdf.set_fill_color(200, 200, 200)
                            pdf.cell(60, 8, "Nombre", 1, 0, 'C', True)
                            pdf.cell(30, 8, "Curso", 1, 0, 'C', True)
                            pdf.cell(20, 8, "Div", 1, 0, 'C', True)
                            pdf.cell(40, 8, "Materia", 1, 0, 'C', True)
                            pdf.cell(40, 8, "Estado", 1, 1, 'C', True)
                            
                            # Datos
                            pdf.set_font('Arial', '', 9)
                            for _, fila in df_reporte.iterrows():
                                pdf.cell(60, 7, clean_text(fila['nombre'][:30]), 1)
                                pdf.cell(30, 7, clean_text(fila['curso']), 1)
                                pdf.cell(20, 7, clean_text(fila.get('division', '-')), 1)
                                pdf.cell(40, 7, clean_text(fila.get('tercera_materia', '-')[:20]), 1)
                                pdf.cell(40, 7, clean_text(fila.get(col_estado, 'Pendiente')), 1, 1)
                            
                            # Generar archivo en memoria
                            pdf_raw = pdf.output(dest='S')
                            if isinstance(pdf_raw, str):
                                pdf_raw = pdf_raw.encode('latin-1', 'replace')
                                
                            st.download_button(
                                label="📥 DESCARGAR REPORTE PDF",
                                data=pdf_raw,
                                file_name=f"Reporte_General_{date.today()}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                            st.success("✅ Reporte listo para descargar.")
                            
                        except Exception as pdf_err:
                            st.error(f"Error al construir el PDF: {pdf_err}")
                else:
                    st.info("No hay alumnos que coincidan con los filtros.")
            
            except Exception as e:
                st.error(f"Error al cargar el reporte: {e}")
# --- 4. CARGAR ALUMNOS ---
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
        
        # Datos de materias
        st.markdown("---")
        st.write("📚 **Información Académica**")
        mat_adeuda = st.text_area("Materias que adeudaba (Ciclos anteriores)")
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            tercera_mat = st.text_input("Tercera Materia elegida")
            profesor = st.text_input("Profesor de la materia")
        with col_m2:
            modalidad = st.selectbox("Modalidad de examen", ["Materia Completa", "Por Temas", "Trabajo Práctico"])
            # Variable interna normalizada
            estado_val = st.selectbox("Estado", ["Pendiente", "Aprobada", "No Aprobada", "En Curso"])

        if st.form_submit_button("Guardar"):
            if nom and cur:
                conn = conectar()
                if conn:
                    try:
                        with conn.cursor() as c:
                            # SQL NORMALIZADO: Se cambió 'estado_general' por 'estado'
                            sql = """
                                INSERT INTO alumnos 
                                (nombre, curso, division, materias_adeudadas, tercera_materia, profesor, modalidad, estado) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """
                            valores = (nom, cur, div, mat_adeuda, tercera_mat, profesor, modalidad, estado_val)
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
                    sql_select = "SELECT * FROM alumnos WHERE nombre ILIKE %s"
                    c.execute(sql_select, (f"%{nombre_buscar}%",))
                    
                    columnas = [desc[0] for desc in c.description]
                    resultados = c.fetchall()
                
                if resultados:
                    lista_alumnos = [dict(zip(columnas, r)) for r in resultados]
                    opciones = {f"{a['nombre']} (Curso: {a.get('curso', '')})": i for i, a in enumerate(lista_alumnos)}
                    seleccion = st.selectbox("Seleccioná el alumno exacto:", list(opciones.keys()))
                    
                    al_sel = lista_alumnos[opciones[seleccion]]
                    id_alumno = al_sel['id']

                    with st.form("form_edicion"):
                        st.info(f"Editando a: {al_sel['nombre']}")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            nuevo_nom = st.text_input("Nombre y Apellido", value=al_sel.get('nombre', ''))
                        with col2:
                            nuevo_cur = st.text_input("Curso", value=al_sel.get('curso', ''))
                        with col3:
                            nuevo_div = st.text_input("División", value=al_sel.get('division', ''))

                        st.markdown("---")
                        nuevas_adeudadas = st.text_area("Materias que adeudaba", value=al_sel.get('materias_adeudadas', ''))
                        
                        col_e1, col_e2 = st.columns(2)
                        with col_e1:
                            nueva_tercera = st.text_input("Tercera Materia", value=al_sel.get('tercera_materia', ''))
                            nuevo_profesor = st.text_input("Profesor", value=al_sel.get('profesor', ''))
                        with col_e2:
                            # Modalidad
                            mods = ["Materia Completa", "Por Temas", "Trabajo Práctico"]
                            mod_db = al_sel.get('modalidad', 'Materia Completa')
                            idx_mod = mods.index(mod_db) if mod_db in mods else 0
                            nueva_modalidad = st.selectbox("Modalidad", mods, index=idx_mod)
                            
                            # Estado - CORREGIDO A 'estado' que es el nombre real en tu DB
                            estados = ["Pendiente", "Aprobada", "No Aprobada", "En Curso"]
                            # Buscamos 'estado' en el diccionario del alumno
                            est_db = al_sel.get('estado', 'Pendiente')
                            idx_est = estados.index(est_db) if est_db in estados else 0
                            nuevo_estado = st.selectbox("Estado", estados, index=idx_est)

                        if st.form_submit_button("Guardar Cambios"):
                            with conn.cursor() as c_up:
                                # SQL LIMPIO: Usamos 'estado' directamente
                                sql_update = """
                                    UPDATE alumnos 
                                    SET nombre=%s, curso=%s, division=%s, 
                                        materias_adeudadas=%s, tercera_materia=%s, 
                                        profesor=%s, modalidad=%s, estado=%s
                                    WHERE id=%s
                                """
                                c_up.execute(sql_update, (
                                    nuevo_nom, nuevo_cur, nuevo_div, 
                                    nuevas_adeudadas, nueva_tercera, 
                                    nuevo_profesor, nueva_modalidad, nuevo_estado, 
                                    id_alumno
                                ))
                                conn.commit()
                                st.success("✅ Datos actualizados correctamente.")
                                st.rerun()
                else:
                    st.warning("No se encontraron alumnos.")
            except Exception as e:
                # El error de Postgres saldrá aquí si algo más falla
                st.error(f"Error técnico con la base de datos: {e}")
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
