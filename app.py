import streamlit as st
import pandas as pd
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Dict, Tuple

from fpdf import FPDF
from PIL import Image
import plotly.express as px
import qrcode


# =========================================================
# CONFIGURACION GENERAL
# =========================================================
st.set_page_config(page_title="Gestión de Equipos Hospitium", page_icon="🏥", layout="wide")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
IMG_DIR = BASE_DIR / "imagenes_equipos"
PDF_DIR = BASE_DIR / "bitacoras"

FILE_EXCEL = DATA_DIR / "INVENTARIO.xlsx"
LOGO_FILE = BASE_DIR / "logo_escuela.png"
FOLIO_FILE = DATA_DIR / "folio_actual.txt"

DATA_DIR.mkdir(exist_ok=True)
IMG_DIR.mkdir(exist_ok=True)
PDF_DIR.mkdir(exist_ok=True)

try:
    APP_URL = st.secrets["APP_URL"]
except Exception:
    APP_URL = "https://bioingenapp.streamlit.app/"


INV_COLUMNS = [
    "Control", "Área", "Nombre", "Marca", "Modelo", "Serie", "Ubicación",
    "Estado del equipo", "Fecha de adquisición", "Garantía vigente",
    "Criticidad clínica", "Batería de respaldo", "Dependencia eléctrica",
    "Accesorios", "Imagen"
]

MANT_COLUMNS = [
    "Control", "Fecha", "Tipo de mantenimiento", "Descripción del problema",
    "Actividad realizada", "Responsable", "Estado", "Proximo mantenimiento",
    "Evidencia"
]


# =========================================================
# UTILIDADES
# =========================================================
def normalizar_fecha_columna(df: pd.DataFrame, col: str) -> pd.DataFrame:
    df = df.copy()
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    return df


def asegurar_columnas(df: pd.DataFrame, expected_columns: list) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    for col in expected_columns:
        if col not in df.columns:
            df[col] = ""
    return df[expected_columns]


def obtener_folio() -> int:
    if not FOLIO_FILE.exists():
        FOLIO_FILE.write_text("1000", encoding="utf-8")
    contenido = FOLIO_FILE.read_text(encoding="utf-8").strip()
    try:
        return int(contenido)
    except ValueError:
        FOLIO_FILE.write_text("1000", encoding="utf-8")
        return 1000


def incrementar_folio() -> None:
    siguiente = obtener_folio() + 1
    FOLIO_FILE.write_text(str(siguiente), encoding="utf-8")


@st.cache_data(ttl=5)
def cargar_datos() -> Tuple[pd.DataFrame, pd.DataFrame]:
    if FILE_EXCEL.exists():
        try:
            xls = pd.ExcelFile(FILE_EXCEL, engine="openpyxl")
            sheet_names = xls.sheet_names

            if "INVENTARIO" in sheet_names:
                df_inv = pd.read_excel(FILE_EXCEL, sheet_name="INVENTARIO", engine="openpyxl")
            else:
                df_inv = pd.DataFrame(columns=INV_COLUMNS)

            if "MANTENIMIENTO" in sheet_names:
                df_mant = pd.read_excel(FILE_EXCEL, sheet_name="MANTENIMIENTO", engine="openpyxl")
            else:
                df_mant = pd.DataFrame(columns=MANT_COLUMNS)

            df_inv = asegurar_columnas(df_inv, INV_COLUMNS)
            df_mant = asegurar_columnas(df_mant, MANT_COLUMNS)

            df_inv = normalizar_fecha_columna(df_inv, "Fecha de adquisición")
            df_mant = normalizar_fecha_columna(df_mant, "Fecha")

            return df_inv, df_mant

        except Exception as e:
            st.error(f"Error al leer el Excel: {e}")

    df_inv = pd.DataFrame(columns=INV_COLUMNS)
    df_mant = pd.DataFrame(columns=MANT_COLUMNS)
    return df_inv, df_mant


def guardar_datos(df_inv: pd.DataFrame, df_mant: pd.DataFrame) -> None:
    df_inv = asegurar_columnas(df_inv, INV_COLUMNS)
    df_mant = asegurar_columnas(df_mant, MANT_COLUMNS)

    with pd.ExcelWriter(FILE_EXCEL, engine="openpyxl") as writer:
        df_inv.to_excel(writer, sheet_name="INVENTARIO", index=False)
        df_mant.to_excel(writer, sheet_name="MANTENIMIENTO", index=False)

    st.cache_data.clear()


def guardar_subida_archivo(uploaded_file, destino: Path) -> str:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return str(destino)


def generar_qr_buffer(url: str) -> bytes:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()

def mapear_tipo_servicio(tipo_servicio: str) -> str:
    tipo = str(tipo_servicio).strip().lower()
    equivalencias = {
        "preventivo": "PREVENTIVO",
        "correctivo": "MANTENIMIENTO CORRECTIVO",
        "instalación": "INSTALACIÓN Y ARRANQUE",
        "instalacion": "INSTALACIÓN Y ARRANQUE",
        "otro": "OTRO",
    }
    return equivalencias.get(tipo, "OTRO")


def generar_pdf_hospitium(datos: Dict) -> str:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    tiene_logo = LOGO_FILE.exists()
    if tiene_logo:
        pdf.image(str(LOGO_FILE), 10, 8, 25)
        pdf.set_xy(40, 10)

    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 8, "HOSPITIUM SOLUTIONS", new_x="LMARGIN", new_y="NEXT", align="L")

    if tiene_logo:
        pdf.set_x(40)

    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "BITÁCORA DE SERVICIO", new_x="LMARGIN", new_y="NEXT", align="L")
    pdf.ln(8)

    pdf.set_font("helvetica", "B", 9)
    pdf.cell(100, 6, f"CONTRATO: {datos['contrato']}", border=1)
    pdf.cell(90, 6, f"FECHA: {datos['fecha']}", border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.cell(100, 6, f"HOSPITAL: {datos['hospital']}", border=1)
    pdf.cell(90, 6, f"FOLIO ODS: {datos['folio']}", border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.cell(190, 6, f"DIRECCIÓN: {datos['direccion']}", border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_fill_color(220, 220, 220)
    pdf.cell(190, 6, "CARACTERÍSTICAS DEL EQUIPO", border=1, new_x="LMARGIN", new_y="NEXT", align="C", fill=True)
    pdf.cell(95, 6, f"EQUIPO: {datos['equipo_nombre']}", border=1)
    pdf.cell(95, 6, f"MARCA: {datos['marca']}", border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.cell(63, 6, f"MODELO: {datos['modelo']}", border=1)
    pdf.cell(63, 6, f"SERIE: {datos['serie']}", border=1)
    pdf.cell(64, 6, f"CONTROL: {datos['inventario']}", border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.cell(190, 6, "SERVICIO REALIZADO", border=1, new_x="LMARGIN", new_y="NEXT", align="C", fill=True)

    servicios = [
        "INSTALACIÓN Y ARRANQUE",
        "PREVENTIVO",
        "MANTENIMIENTO CORRECTIVO",
        "OTRO"
    ]
    tipo_mapeado = mapear_tipo_servicio(datos["tipo_servicio"])

    for i, serv in enumerate(servicios):
        check = "[ X ]" if tipo_mapeado == serv else "[   ]"
        if i % 2 == 0:
            pdf.cell(95, 6, f"{check} {serv}", border=1)
        else:
            pdf.cell(95, 6, f"{check} {serv}", border=1, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)

    pdf.set_font("helvetica", "B", 9)
    pdf.cell(190, 6, "FALLA REPORTADA", border=1, new_x="LMARGIN", new_y="NEXT", align="C", fill=True)
    pdf.set_font("helvetica", "", 9)
    pdf.multi_cell(190, 6, datos["falla"] if str(datos["falla"]).strip() else "N/A", border=1)
    pdf.ln(4)

    pdf.set_font("helvetica", "B", 9)
    pdf.cell(190, 6, "REFACCIONES INSTALADAS", border=1, new_x="LMARGIN", new_y="NEXT", align="C", fill=True)
    pdf.cell(30, 6, "CÓDIGO", border=1, align="C")
    pdf.cell(65, 6, "DESCRIPCIÓN", border=1, align="C")
    pdf.cell(30, 6, "CÓDIGO", border=1, align="C")
    pdf.cell(65, 6, "DESCRIPCIÓN", border=1, new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.set_font("helvetica", "", 8)
    pdf.cell(30, 6, str(datos["ref1_cod"]), border=1)
    pdf.cell(65, 6, str(datos["ref1_desc"]), border=1)
    pdf.cell(30, 6, str(datos["ref2_cod"]), border=1)
    pdf.cell(65, 6, str(datos["ref2_desc"]), border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("helvetica", "B", 9)
    pdf.cell(190, 6, "ACTIVIDAD REALIZADA", border=1, new_x="LMARGIN", new_y="NEXT", align="C", fill=True)
    pdf.set_font("helvetica", "", 9)
    pdf.multi_cell(190, 5, str(datos["actividad"]), border=1)
    pdf.ln(15)

    pdf.cell(63, 10, "_________________________", align="C")
    pdf.cell(63, 10, "_________________________", align="C")
    pdf.cell(64, 10, "_________________________", new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.set_font("helvetica", "B", 8)
    pdf.cell(63, 5, "NOMBRE Y FIRMA DEL TÉCNICO", align="C")
    pdf.cell(63, 5, "SELLO DE CLAVE PRESUPUESTAL", align="C")
    pdf.cell(64, 5, "SELLO DE UNIDAD MÉDICA", new_x="LMARGIN", new_y="NEXT", align="C")

    archivo_pdf = PDF_DIR / f"Bitacora_{datos['folio']}.pdf"
    pdf.output(str(archivo_pdf))
    return str(archivo_pdf)


def render_qr_sidebar() -> None:
    st.sidebar.markdown("---")
    st.sidebar.subheader("QR de la app")

    qr_bytes = generar_qr_buffer(APP_URL)

    st.sidebar.image(
        qr_bytes,
        caption="Escanea para abrir la app",
        width='stretch',
    )

    st.sidebar.download_button(
        label="📥 Descargar QR",
        data=qr_bytes,
        file_name="qr_hospitium_app.png",
        mime="image/png",
    )

    st.sidebar.caption(APP_URL)

# =========================================================
# CARGA INICIAL
# =========================================================
df_inv, df_mant = cargar_datos()


# =========================================================
# SIDEBAR
# =========================================================
if LOGO_FILE.exists():
    st.sidebar.image(str(LOGO_FILE), width='stretch')
else:
    st.sidebar.markdown("## 🏥 Hospitium")

st.sidebar.title("Hospitium App")
opcion = st.sidebar.radio(
    "Navegación",
    [
        "📊 Dashboard y Base de Datos",
        "➕ Nuevo Equipo",
        "🛠️ Generar Bitácora",
    ],
)

render_qr_sidebar()


# =========================================================
# DASHBOARD
# =========================================================
if opcion == "📊 Dashboard y Base de Datos":
    st.markdown(
        "<div style='color: #4CAF50; font-size: 12px; font-weight: bold;'>👩‍💻 Desarrollado por: Fernanda Soriano</div>",
        unsafe_allow_html=True
    )
    st.title("Panel de Control de Equipos")

    if df_inv.empty:
        st.warning("No se encontró información en el inventario.")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Equipos", len(df_inv))
        col2.metric("Áreas Cubiertas", df_inv["Área"].nunique() if "Área" in df_inv.columns else 0)

        df_mant_temp = df_mant.copy()
        df_mant_temp["Fecha"] = pd.to_datetime(df_mant_temp["Fecha"], errors="coerce")
        hace_30_dias = pd.Timestamp.today() - pd.Timedelta(days=30)

        mant_recientes = df_mant_temp[
            (df_mant_temp["Fecha"] >= hace_30_dias)
            & (df_mant_temp["Tipo de mantenimiento"].astype(str).str.contains("Preventivo", case=False, na=False))
        ].shape[0]

        col3.metric("Preventivos (Últimos 30 días)", mant_recientes)

        st.markdown("---")
        c_graf1, c_graf2 = st.columns(2)

        with c_graf1:
            st.subheader("Distribución por Área")
            if not df_inv.empty and "Área" in df_inv.columns:
                conteo_areas = df_inv.groupby("Área").size().reset_index(name="Cantidad")
                if not conteo_areas.empty:
                    fig_pie = px.pie(conteo_areas, names="Área", values="Cantidad", hole=0.3)
                    st.plotly_chart(fig_pie, width='stretch')
                else:
                    st.info("No hay datos suficientes para la gráfica por área.")

        with c_graf2:
            st.subheader("Mantenimientos por Fecha")
            df_graf_mant = df_mant_temp.dropna(subset=["Fecha"]).copy()

            if not df_graf_mant.empty:
                df_graf_mant["Fecha"] = df_graf_mant["Fecha"].dt.date
                conteo_fechas = df_graf_mant.groupby("Fecha").size().reset_index(name="Cantidad").sort_values("Fecha")
                conteo_fechas["Fecha_str"] = conteo_fechas["Fecha"].astype(str)

                fig_bar = px.bar(
                    conteo_fechas,
                    x="Fecha_str",
                    y="Cantidad",
                    text="Cantidad",
                    labels={"Fecha_str": "Día del Mantenimiento"},
                )
                fig_bar.update_xaxes(type="category")
                st.plotly_chart(fig_bar,width='stretch')
            else:
                st.info("Aún no se han registrado mantenimientos.")

        st.markdown("---")
        st.subheader("Buscador de Equipos y Fotografías")
        st.write("Selecciona un equipo para ver sus detalles y actualizar su imagen.")

        opciones_equipos = df_inv["Control"].astype(str) + " - " + df_inv["Nombre"].astype(str)
        equipo_buscado = st.selectbox("Selecciona un equipo:", opciones_equipos)

        if equipo_buscado:
            id_selec = equipo_buscado.split(" - ")[0]
            idx_equipo = df_inv[df_inv["Control"].astype(str) == id_selec].index[0]
            datos_equipo = df_inv.loc[idx_equipo]

            c_img1, c_img2 = st.columns([1, 2])

            with c_img1:
                imagen_actual = str(datos_equipo.get("Imagen", "")).strip()
                if imagen_actual and Path(imagen_actual).exists():
                    try:
                        st.image(Image.open(str(imagen_actual)),width='stretch')
                    except Exception:
                        st.error("No fue posible mostrar la imagen guardada.")
                else:
                    st.info("Sin foto del equipo.")

                nueva_img = st.file_uploader(
                    "Subir/Actualizar Fotografía",
                    type=["jpg", "png", "jpeg"],
                    key=f"foto_{id_selec}",
                )

                if nueva_img is not None:
                    suffix = Path(nueva_img.name).suffix.lower() or ".png"
                    ruta_img = IMG_DIR / f"{id_selec}{suffix}"
                    df_inv.at[idx_equipo, "Imagen"] = guardar_subida_archivo(nueva_img, ruta_img)
                    guardar_datos(df_inv, df_mant)
                    st.success("Foto actualizada correctamente. Recarga la página si no aparece de inmediato.")

            with c_img2:
                st.write(f"**Control ID:** {datos_equipo['Control']}")
                st.write(f"**Nombre / Marca:** {datos_equipo['Nombre']} - {datos_equipo['Marca']}")
                st.write(f"**Modelo / Serie:** {datos_equipo['Modelo']} / {datos_equipo['Serie']}")
                st.write(f"**Área / Ubicación:** {datos_equipo['Área']} - {datos_equipo['Ubicación']}")
                st.write(f"**Estado Actual:** {datos_equipo['Estado del equipo']}")

        st.markdown("---")
        st.subheader("Base de Datos Interactiva")
        tab_inv, tab_mant = st.tabs(["📦 Inventario de Equipos", "🛠️ Historial de Mantenimientos"])

        with tab_inv:
            df_editado_inv = st.data_editor(df_inv, width='stretch', num_rows="dynamic", key="editor_inv")
            c_btn1, c_btn2 = st.columns(2)

            with c_btn1:
                if st.button("💾 Guardar Cambios en Inventario"):
                    guardar_datos(df_editado_inv, df_mant)
                    st.success("Inventario actualizado correctamente.")

            with c_btn2:
                if FILE_EXCEL.exists():
                    with open(str(FILE_EXCEL), "rb") as f:
                        st.download_button(
                            "📥 Descargar Excel Completo",
                            data=f.read(),
                            file_name="INVENTARIO_ACTUALIZADO.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )

        with tab_mant:
            df_editado_mant = st.data_editor(df_mant, width='stretch', num_rows="dynamic", key="editor_mant")
            c_btn3, c_btn4 = st.columns(2)

            with c_btn3:
                if st.button("💾 Guardar Cambios en Mantenimientos"):
                    guardar_datos(df_inv, df_editado_mant)
                    st.success("Mantenimientos actualizados correctamente.")

            with c_btn4:
                if FILE_EXCEL.exists():
                    with open(str(FILE_EXCEL), "rb") as f:
                        st.download_button(
                            "📥 Descargar Excel Completo",
                            data=f.read(),
                            file_name="INVENTARIO_ACTUALIZADO.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="btn_desc_mant",
                        )


# =========================================================
# NUEVO EQUIPO
# =========================================================
elif opcion == "➕ Nuevo Equipo":
    st.title("Ingresar Nuevo Equipo")
    st.write("Completa los datos para registrar un equipo nuevo directamente en tu archivo Excel.")

    with st.form("form_nuevo_equipo"):
        nuevo_inv_id = st.text_input("ID de Control (ej. QX-006):").strip()

        col1, col2 = st.columns(2)
        n_nombre = col1.text_input("Nombre del Equipo:").strip()
        n_marca = col2.text_input("Marca:").strip()

        col3, col4 = st.columns(2)
        n_modelo = col3.text_input("Modelo:").strip()
        n_serie = col4.text_input("Número de Serie:").strip()

        col5, col6 = st.columns(2)
        n_area = col5.text_input("Área (ej. Quirófano, UCIN):").strip()
        n_ubicacion = col6.text_input("Ubicación específica (ej. Sala 1):").strip()

        col7, col8, col9 = st.columns(3)
        n_estado = col7.selectbox("Estado del equipo:", ["Operativo", "Fuera de servicio", "En reparación"])
        n_garantia = col8.selectbox("Garantía vigente:", ["Si", "No"])
        n_criticidad = col9.selectbox("Criticidad clínica:", ["Alta", "Media", "Baja"])

        col10, col11 = st.columns(2)
        n_bateria = col10.selectbox("Batería de respaldo:", ["Si", "No"])
        n_dependencia = col11.selectbox("Dependencia eléctrica:", ["Si", "No"])

        n_fecha_adq = st.date_input("Fecha de adquisición:")
        n_accesorios = st.text_area("Accesorios incluidos:")
        n_foto = st.file_uploader("Foto del Equipo (Opcional)", type=["jpg", "png", "jpeg"])
        submit_nuevo = st.form_submit_button("Guardar Equipo en el Excel")

    if submit_nuevo:
        if not nuevo_inv_id or not n_nombre:
            st.error("Debes capturar al menos el ID de control y el nombre del equipo.")
        elif nuevo_inv_id in df_inv["Control"].astype(str).tolist():
            st.error("Ya existe un equipo con ese ID de control.")
        else:
            ruta_guardada = ""
            if n_foto is not None:
                suffix = Path(n_foto.name).suffix.lower() or ".png"
                ruta_guardada = guardar_subida_archivo(n_foto, IMG_DIR / f"{nuevo_inv_id}{suffix}")

            nuevo_registro = {
                "Control": nuevo_inv_id,
                "Área": n_area,
                "Nombre": n_nombre,
                "Marca": n_marca,
                "Modelo": n_modelo,
                "Serie": n_serie,
                "Ubicación": n_ubicacion,
                "Estado del equipo": n_estado,
                "Fecha de adquisición": n_fecha_adq,
                "Garantía vigente": n_garantia,
                "Criticidad clínica": n_criticidad,
                "Batería de respaldo": n_bateria,
                "Dependencia eléctrica": n_dependencia,
                "Accesorios": n_accesorios,
                "Imagen": ruta_guardada,
            }

            df_inv_actualizado = pd.concat([df_inv, pd.DataFrame([nuevo_registro])], ignore_index=True)
            guardar_datos(df_inv_actualizado, df_mant)
            st.success(f"Equipo {n_nombre} registrado correctamente.")


# =========================================================
# BITACORA
# =========================================================
elif opcion == "🛠️ Generar Bitácora":
    st.title("🛠️ Bitácora de Servicio - Hospitium")

    if df_inv.empty:
        st.error("Primero debes registrar equipos en el inventario.")
    else:
        folio_actual = obtener_folio()
        st.info(f"Folio ODS automático a generar: {folio_actual}")

        with st.form("form_bitacora"):
            c1, c2 = st.columns(2)
            contrato = c1.text_input("Contrato:", value="019GYP019N1874-008-00")
            hospital = c2.text_input("Hospital / Unidad:")
            direccion = st.text_input("Dirección:")

            equipo_selec = st.selectbox(
                "Seleccionar Equipo del Inventario:",
                df_inv["Control"].astype(str) + " - " + df_inv["Nombre"].astype(str),
            )

            tipo_servicio = st.radio(
                "Servicio Realizado:",
                ["Preventivo", "Correctivo", "Instalación", "Otro"],
                horizontal=True,
            )

            falla = st.text_input("Descripción del problema:")
            st.write("Refacciones Instaladas:")

            r1, r2, r3, r4 = st.columns(4)
            ref1_cod = r1.text_input("Código Ref 1")
            ref1_desc = r2.text_input("Descripción Ref 1")
            ref2_cod = r3.text_input("Código Ref 2")
            ref2_desc = r4.text_input("Descripción Ref 2")

            actividad = st.text_area("Actividad Realizada:", height=100)

            col_m1, col_m2 = st.columns(2)
            estado_final = col_m1.selectbox("Estado final del equipo:", ["Operativo", "Fuera de servicio"])
            prox_mant = col_m2.text_input("Próximo mantenimiento (ej. 2027-01-10 o 'No especificado')")

            evidencia = st.file_uploader(
                "Adjuntar fotografía de evidencia (Opcional)",
                type=["jpg", "png", "jpeg"]
            )

            submit = st.form_submit_button("Generar PDF y Guardar en Excel")

        if evidencia is not None:
            st.image(evidencia, caption="Vista previa de la evidencia a guardar", width=300)

        if submit:
            if not actividad.strip():
                st.error("La actividad realizada es obligatoria.")
            else:
                id_eq = equipo_selec.split(" - ")[0]
                datos_eq = df_inv[df_inv["Control"].astype(str) == id_eq].iloc[0]

                evidencia_path = ""
                if evidencia is not None:
                    suffix = Path(evidencia.name).suffix.lower() or ".png"
                    evidencia_path = guardar_subida_archivo(
                        evidencia,
                        IMG_DIR / f"Evidencia_{folio_actual}{suffix}"
                    )

                nuevo_mantenimiento = {
                    "Control": id_eq,
                    "Fecha": date.today(),
                    "Tipo de mantenimiento": tipo_servicio,
                    "Descripción del problema": falla if falla.strip() else "N/A",
                    "Actividad realizada": actividad,
                    "Responsable": "IB. Fernanda Soriano",
                    "Estado": estado_final,
                    "Proximo mantenimiento": prox_mant if prox_mant.strip() else "No especificado",
                    "Evidencia": evidencia_path,
                }

                df_mant_actualizado = pd.concat(
                    [df_mant, pd.DataFrame([nuevo_mantenimiento])],
                    ignore_index=True
                )
                guardar_datos(df_inv, df_mant_actualizado)

                datos_pdf = {
                    "folio": str(folio_actual),
                    "fecha": date.today().strftime("%d/%m/%Y"),
                    "contrato": contrato,
                    "hospital": hospital,
                    "direccion": direccion,
                    "equipo_nombre": str(datos_eq["Nombre"]),
                    "marca": str(datos_eq["Marca"]),
                    "modelo": str(datos_eq["Modelo"]),
                    "serie": str(datos_eq["Serie"]),
                    "inventario": str(datos_eq["Control"]),
                    "tipo_servicio": tipo_servicio,
                    "falla": falla,
                    "actividad": actividad,
                    "ref1_cod": ref1_cod,
                    "ref1_desc": ref1_desc,
                    "ref2_cod": ref2_cod,
                    "ref2_desc": ref2_desc,
                }

                ruta_pdf = generar_pdf_hospitium(datos_pdf)
                incrementar_folio()

                st.success(f"Bitácora PDF generada con el folio {folio_actual} y guardada en el Excel.")

                with open(str(ruta_pdf), "rb") as file:
                    st.download_button(
                        "📥 Descargar Bitácora PDF",
                        data=file.read(),
                        file_name=f"Bitacora_{folio_actual}.pdf",
                        mime="application/pdf",
                    )
