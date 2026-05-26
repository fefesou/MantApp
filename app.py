import streamlit as st
import pandas as pd
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Dict, Tuple, Optional, List
import re
import unicodedata

from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont
import plotly.express as px
import qrcode


# =========================================================
# CONFIGURACION GENERAL
# =========================================================
st.set_page_config(page_title="Gestión de Equipos Hospitium", page_icon="🏥", layout="wide")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
IMG_DIR = BASE_DIR / "imagenes_equipos"
# IMPORTANTE: el usuario ya usa la carpeta qr_equipos para guardar FOTOS/IMÁGENES de los equipos.
# Por eso los QR generados se guardan en una carpeta distinta para no sobrescribir esas imágenes.
EQUIPO_IMG_DIR = BASE_DIR / "qr_equipos"
QR_DIR = BASE_DIR / "qrs_generados"
PDF_DIR = BASE_DIR / "bitacoras"
EVID_DIR = BASE_DIR / "evidencias"
GUIAS_DIR = BASE_DIR / "guias_equipos"

FILE_EXCEL = DATA_DIR / "INVENTARIO.xlsx"
LOGO_FILE = BASE_DIR / "logo_escuela.png"
FOLIO_FILE = DATA_DIR / "folio_actual.txt"

for carpeta in [DATA_DIR, IMG_DIR, EQUIPO_IMG_DIR, QR_DIR, PDF_DIR, EVID_DIR, GUIAS_DIR]:
    carpeta.mkdir(exist_ok=True)

try:
    APP_URL = st.secrets["APP_URL"]
except Exception:
    APP_URL = "https://mantapp.streamlit.app/"


def normalizar_app_url(url: str) -> str:
    url = str(url).strip()
    if not url:
        return "https://mantapp.streamlit.app/"
    if not url.endswith("/"):
        url += "/"
    return url


APP_URL = normalizar_app_url(APP_URL)

try:
    BAJA_PIN = str(st.secrets.get("BAJA_PIN", "")).strip()
except Exception:
    BAJA_PIN = ""


# =========================================================
# COLUMNAS DE BASE DE DATOS
# =========================================================
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

REPORT_COLUMNS = [
    "Folio reporte", "Control", "Fecha", "Reporta", "Área", "Prioridad",
    "Tipo de reporte", "Descripción", "Estado del reporte", "Evidencia"
]

BAJA_COLUMNS = [
    "Folio baja", "Control", "Fecha solicitud", "Solicitante", "Motivo de baja",
    "Condición del equipo", "Reparación posible", "Observaciones", "Estatus", "Evidencia"
]


# =========================================================
# EQUIPOS DEFINITIVOS PARA QR
# =========================================================
EQUIPOS_QR = {
    "QX-003": {
        "nombre": "Incubadora OHMEDA Medical GIRAFFE Omnibed",
        "marca": "OHMEDA Medical",
        "modelo": "GIRAFFE Omnibed",
        "area_sugerida": "No especificada",
        "archivo_qr": "QR_QX-003_Incubadora_Ohmeda_Giraffe_Omnibed.png",
        "imagen_archivo_actual": "QR_INC-001_Incubadora_Ohmeda.png",
        "imagen_sugerida": "QX-003.png",
        "guia": "GUÍA INCUBADORA OHMEDA MEDICAL GIRAFFE OMNIBED.doc",
    },
    "CM-010": {
        "nombre": "Sistema de grabación Stryker SDC Ultra",
        "marca": "Stryker",
        "modelo": "SDC Ultra",
        "area_sugerida": "No especificada",
        "archivo_qr": "QR_CM-010_Stryker_SDC_Ultra.png",
        "imagen_archivo_actual": "QR_STR-001_Stryker_SDC_Ultra.png",
        "imagen_sugerida": "CM-010.png",
        "guia": "GUÍA SISTEMA DE GRABACIÓN STRYKER SDC ULTRA.doc",
    },
    "LB-001": {
        "nombre": "Analizador de orina Siemens CLINITEK Status",
        "marca": "Siemens",
        "modelo": "CLINITEK Status",
        "area_sugerida": "No especificada",
        "archivo_qr": "QR_LB-001_Siemens_Clinitek_Status.png",
        "imagen_archivo_actual": "QR_URI-001_Clinitek_Status.png",
        "imagen_sugerida": "LB-001.png",
        "guia": "GUÍA ANALIZADOR DE ORINA SIEMENS CLINITEK Status.doc",
    },
    "UR-009": {
        "nombre": "Calentador de sábanas COVIDIEN WarmTouch",
        "marca": "COVIDIEN",
        "modelo": "WarmTouch",
        "area_sugerida": "No especificada",
        "archivo_qr": "QR_UR-009_Covidien_WarmTouch.png",
        "imagen_archivo_actual": "QR_CAL-001_Calentador_Covidien.png",
        "imagen_sugerida": "UR-009.png",
        "guia": "GUÍA CALENTADOR DE SÁBANAS COVIDIEN WARMTOUCH.doc",
    },
    "UN-002": {
        "nombre": "Cuna de calor radiante Hill-Rom WBR82-1",
        "marca": "Hill-Rom",
        "modelo": "WBR82-1",
        "area_sugerida": "No especificada",
        "archivo_qr": "QR_UN-002_Cuna_HillRom_WBR82-1.png",
        "imagen_archivo_actual": "QR_CUN-001_Cuna_HillRom.png",
        "imagen_sugerida": "UN-002.png",
        "guia": "GUÍA CUNA DE CALOR RADIANTE HILL-ROM WBR82-1.doc",
    },
}

GUIA_RESUMIDA = {
    "QX-003": {
        "descripcion": "Equipo neonatal que combina funciones de incubadora cerrada y calentador radiante, permitiendo soporte térmico controlado y transición entre modos sin transferir al neonato.",
        "componentes": [
            "Capelo elevable con elemento de calentamiento radiante integrado.",
            "Puertas de acceso frontales y laterales.",
            "Plataforma de cama con ajuste de altura y posición.",
            "Panel de control electrónico.",
            "Sensores de temperatura de aire y sondas cutáneas.",
            "Sistema de humidificación y alarmas visuales/audibles.",
        ],
        "uso": "Verificar alimentación eléctrica, alarmas, sensores, limpieza, accesorios y correcto funcionamiento antes del uso clínico.",
    },
    "CM-010": {
        "descripcion": "Sistema médico para captura, almacenamiento y manejo de imágenes o videos obtenidos durante procedimientos quirúrgicos.",
        "componentes": [
            "Pantalla táctil LCD.",
            "Unidad de lectura CD/DVD.",
            "Puerto USB.",
            "Botón de encendido/apagado.",
            "Conexiones de video, audio, red y alimentación eléctrica.",
        ],
        "uso": "Verificar conexión de video, almacenamiento, alimentación, periféricos y disponibilidad para documentación clínica.",
    },
    "LB-001": {
        "descripcion": "Analizador de orina para lectura de tiras reactivas y apoyo en pruebas básicas de laboratorio clínico.",
        "componentes": [
            "Módulo lector.",
            "Pantalla y controles de operación.",
            "Bandeja o soporte de tira reactiva.",
            "Sistema de impresión o salida de resultados, si aplica.",
            "Fuente de alimentación.",
        ],
        "uso": "Verificar limpieza, calibración/control, fuente de energía, consumibles y correcta lectura antes de procesar muestras.",
    },
    "UR-009": {
        "descripcion": "Calentador de sábanas para mantener textiles hospitalarios a temperatura controlada antes de su uso clínico.",
        "componentes": [
            "Cámara o gabinete de calentamiento.",
            "Panel de control de temperatura.",
            "Sistema de calefacción interno.",
            "Puerta de acceso.",
            "Cable y entrada de alimentación eléctrica.",
        ],
        "uso": "Verificar temperatura programada, limpieza, integridad del cable, ventilación y ausencia de sobrecalentamiento.",
    },
    "UN-002": {
        "descripcion": "Equipo de soporte térmico neonatal mediante radiación infrarroja, útil para estabilización térmica y procedimientos con acceso abierto al recién nacido.",
        "componentes": [
            "Colchón.",
            "Módulo superior con calefacción radiante.",
            "Sensor de temperatura cutánea.",
            "Panel de control digital con alarmas audiovisuales.",
            "Soporte para accesorios.",
            "Base móvil con ruedas y freno.",
        ],
        "uso": "Verificar sensor cutáneo, módulo radiante, alarmas, frenos, limpieza y estabilidad antes de uso clínico.",
    },
}


# =========================================================
# UTILIDADES GENERALES
# =========================================================
def normalizar_ascii(texto: str) -> str:
    texto = str(texto)
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^A-Za-z0-9_.-]+", "_", texto)
    texto = re.sub(r"_+", "_", texto).strip("_")
    return texto


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


def obtener_parametro(nombre: str) -> str:
    try:
        valor = st.query_params.get(nombre, "")
    except Exception:
        try:
            params = st.experimental_get_query_params()
            valor = params.get(nombre, [""])
        except Exception:
            valor = ""

    if isinstance(valor, list):
        valor = valor[0] if valor else ""
    return str(valor).strip()


def construir_url_equipo(control_id: str) -> str:
    return f"{APP_URL}?equipo={str(control_id).strip()}"


def buscar_archivo_en_proyecto(nombre_archivo: str) -> Optional[Path]:
    candidatos = [
        BASE_DIR / nombre_archivo,
        GUIAS_DIR / nombre_archivo,
        DATA_DIR / nombre_archivo,
    ]
    for ruta in candidatos:
        if ruta.exists():
            return ruta
    return None


def obtener_siguiente_folio(df: pd.DataFrame, columna: str, prefijo: str) -> str:
    if df.empty or columna not in df.columns:
        return f"{prefijo}-0001"

    max_num = 0
    for valor in df[columna].dropna().astype(str).tolist():
        match = re.search(r"(\d+)$", valor.strip())
        if match:
            max_num = max(max_num, int(match.group(1)))
    return f"{prefijo}-{max_num + 1:04d}"


def guardar_subida_archivo(uploaded_file, destino: Path) -> str:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return str(destino)


def guardar_evidencia(uploaded_file, prefijo: str, folio: str) -> str:
    if uploaded_file is None:
        return ""
    suffix = Path(uploaded_file.name).suffix.lower() or ".png"
    nombre = f"{normalizar_ascii(prefijo)}_{normalizar_ascii(folio)}_{date.today().isoformat()}{suffix}"
    return guardar_subida_archivo(uploaded_file, EVID_DIR / nombre)


def buscar_imagen_equipo(control_id: str, datos_equipo: Optional[pd.Series] = None) -> Optional[Path]:
    if datos_equipo is not None:
        imagen_registrada = str(datos_equipo.get("Imagen", "")).strip()
        if imagen_registrada:
            ruta = Path(imagen_registrada)
            if ruta.exists():
                return ruta

    control_id = str(control_id).strip().upper()

    # 1) Tus imágenes actuales están en qr_equipos/ con nombres que comienzan con QR_,
    # pero son FOTOS del equipo, no códigos QR. Esta búsqueda evita sobrescribirlas.
    if control_id in EQUIPOS_QR:
        nombre_img_actual = EQUIPOS_QR[control_id].get("imagen_archivo_actual", "")
        if nombre_img_actual:
            ruta_actual = EQUIPO_IMG_DIR / nombre_img_actual
            if ruta_actual.exists():
                return ruta_actual

    # 2) También se soporta la carpeta tradicional imagenes_equipos/CONTROL.png.
    extensiones = [".png", ".jpg", ".jpeg", ".webp"]
    for ext in extensiones:
        ruta = IMG_DIR / f"{control_id}{ext}"
        if ruta.exists():
            return ruta

    if control_id in EQUIPOS_QR:
        sugerida = IMG_DIR / EQUIPOS_QR[control_id]["imagen_sugerida"]
        if sugerida.exists():
            return sugerida

    return None


# =========================================================
# CARGA Y GUARDADO DE EXCEL
# =========================================================
@st.cache_data(ttl=5)
def cargar_datos() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if FILE_EXCEL.exists():
        try:
            xls = pd.ExcelFile(FILE_EXCEL, engine="openpyxl")
            sheet_names = xls.sheet_names

            df_inv = pd.read_excel(FILE_EXCEL, sheet_name="INVENTARIO", engine="openpyxl") if "INVENTARIO" in sheet_names else pd.DataFrame(columns=INV_COLUMNS)
            df_mant = pd.read_excel(FILE_EXCEL, sheet_name="MANTENIMIENTO", engine="openpyxl") if "MANTENIMIENTO" in sheet_names else pd.DataFrame(columns=MANT_COLUMNS)
            df_reportes = pd.read_excel(FILE_EXCEL, sheet_name="REPORTES", engine="openpyxl") if "REPORTES" in sheet_names else pd.DataFrame(columns=REPORT_COLUMNS)
            df_bajas = pd.read_excel(FILE_EXCEL, sheet_name="BAJAS", engine="openpyxl") if "BAJAS" in sheet_names else pd.DataFrame(columns=BAJA_COLUMNS)

            df_inv = asegurar_columnas(df_inv, INV_COLUMNS)
            df_mant = asegurar_columnas(df_mant, MANT_COLUMNS)
            df_reportes = asegurar_columnas(df_reportes, REPORT_COLUMNS)
            df_bajas = asegurar_columnas(df_bajas, BAJA_COLUMNS)

            df_inv = normalizar_fecha_columna(df_inv, "Fecha de adquisición")
            df_mant = normalizar_fecha_columna(df_mant, "Fecha")
            df_reportes = normalizar_fecha_columna(df_reportes, "Fecha")
            df_bajas = normalizar_fecha_columna(df_bajas, "Fecha solicitud")

            return df_inv, df_mant, df_reportes, df_bajas

        except Exception as e:
            st.error(f"Error al leer el Excel: {e}")

    return (
        pd.DataFrame(columns=INV_COLUMNS),
        pd.DataFrame(columns=MANT_COLUMNS),
        pd.DataFrame(columns=REPORT_COLUMNS),
        pd.DataFrame(columns=BAJA_COLUMNS),
    )


def guardar_datos(
    df_inv: pd.DataFrame,
    df_mant: pd.DataFrame,
    df_reportes: Optional[pd.DataFrame] = None,
    df_bajas: Optional[pd.DataFrame] = None,
) -> None:
    if df_reportes is None or df_bajas is None:
        _, _, actuales_reportes, actuales_bajas = cargar_datos()
        if df_reportes is None:
            df_reportes = actuales_reportes
        if df_bajas is None:
            df_bajas = actuales_bajas

    df_inv = asegurar_columnas(df_inv, INV_COLUMNS)
    df_mant = asegurar_columnas(df_mant, MANT_COLUMNS)
    df_reportes = asegurar_columnas(df_reportes, REPORT_COLUMNS)
    df_bajas = asegurar_columnas(df_bajas, BAJA_COLUMNS)

    with pd.ExcelWriter(FILE_EXCEL, engine="openpyxl") as writer:
        df_inv.to_excel(writer, sheet_name="INVENTARIO", index=False)
        df_mant.to_excel(writer, sheet_name="MANTENIMIENTO", index=False)
        df_reportes.to_excel(writer, sheet_name="REPORTES", index=False)
        df_bajas.to_excel(writer, sheet_name="BAJAS", index=False)

    st.cache_data.clear()


def sincronizar_equipos_base(df_inv: pd.DataFrame) -> pd.DataFrame:
    df = asegurar_columnas(df_inv, INV_COLUMNS).copy()
    controles_existentes = set(df["Control"].astype(str).str.strip().tolist())

    nuevos = []
    for control, info in EQUIPOS_QR.items():
        if control not in controles_existentes:
            nuevos.append({
                "Control": control,
                "Área": info["area_sugerida"],
                "Nombre": info["nombre"],
                "Marca": info["marca"],
                "Modelo": info["modelo"],
                "Serie": "",
                "Ubicación": "",
                "Estado del equipo": "Operativo",
                "Fecha de adquisición": "",
                "Garantía vigente": "No especificada",
                "Criticidad clínica": "Media",
                "Batería de respaldo": "No especificada",
                "Dependencia eléctrica": "Si",
                "Accesorios": "",
                "Imagen": str(EQUIPO_IMG_DIR / info["imagen_archivo_actual"]),
            })
        else:
            idx = df[df["Control"].astype(str).str.strip() == control].index[0]
            for campo, valor in {
                "Nombre": info["nombre"],
                "Marca": info["marca"],
                "Modelo": info["modelo"],
            }.items():
                if not str(df.at[idx, campo]).strip():
                    df.at[idx, campo] = valor

    if nuevos:
        df = pd.concat([df, pd.DataFrame(nuevos)], ignore_index=True)

    return asegurar_columnas(df, INV_COLUMNS)


# =========================================================
# QR
# =========================================================
def generar_qr_buffer(url: str) -> bytes:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def generar_qr_personalizado_buffer(control_id: str) -> bytes:
    control_id = str(control_id).strip()
    info = EQUIPOS_QR.get(control_id, {})
    nombre = info.get("nombre", control_id)
    url = construir_url_equipo(control_id)

    qr_img = Image.open(BytesIO(generar_qr_buffer(url))).convert("RGB")
    ancho = qr_img.width
    alto_extra = 135
    canvas = Image.new("RGB", (ancho, qr_img.height + alto_extra), "white")
    canvas.paste(qr_img, (0, 0))

    draw = ImageDraw.Draw(canvas)
    try:
        font_titulo = ImageFont.truetype("arial.ttf", 28)
        font_texto = ImageFont.truetype("arial.ttf", 18)
        font_url = ImageFont.truetype("arial.ttf", 14)
    except Exception:
        font_titulo = ImageFont.load_default()
        font_texto = ImageFont.load_default()
        font_url = ImageFont.load_default()

    y = qr_img.height + 10
    lineas = [control_id, nombre, "MantApp Hospitium"]
    for i, linea in enumerate(lineas):
        fuente = font_titulo if i == 0 else font_texto
        linea_segura = unicodedata.normalize("NFKD", linea).encode("ascii", "ignore").decode("ascii")
        bbox = draw.textbbox((0, 0), linea_segura, font=fuente)
        x = max((ancho - (bbox[2] - bbox[0])) // 2, 5)
        draw.text((x, y), linea_segura, fill="black", font=fuente)
        y += 34 if i == 0 else 25

    url_corta = url.replace("https://", "")
    bbox = draw.textbbox((0, 0), url_corta, font=font_url)
    x = max((ancho - (bbox[2] - bbox[0])) // 2, 5)
    draw.text((x, y), url_corta, fill="black", font=font_url)

    buffer = BytesIO()
    canvas.save(buffer, format="PNG")
    return buffer.getvalue()


def guardar_qr_equipo(control_id: str) -> List[Path]:
    control_id = str(control_id).strip().upper()
    if control_id not in EQUIPOS_QR:
        raise ValueError(f"Control no configurado para QR: {control_id}")

    qr_bytes = generar_qr_personalizado_buffer(control_id)
    info = EQUIPOS_QR[control_id]

    # Los QR generados se guardan en qrs_generados/ para NO sobrescribir las imágenes
    # actuales de los equipos que están en qr_equipos/.
    rutas = [QR_DIR / info["archivo_qr"]]

    for ruta in rutas:
        ruta.write_bytes(qr_bytes)

    return rutas


def render_qr_sidebar() -> None:
    st.sidebar.markdown("---")
    st.sidebar.subheader("QR de la app")

    qr_bytes = generar_qr_buffer(APP_URL)

    st.sidebar.image(qr_bytes, caption="Escanea para abrir la app", use_container_width=True)
    st.sidebar.download_button(
        label="📥 Descargar QR general",
        data=qr_bytes,
        file_name="qr_hospitium_app.png",
        mime="image/png",
    )
    st.sidebar.caption(APP_URL)


# =========================================================
# PDF HOSPITIUM
# =========================================================
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

    servicios = ["INSTALACIÓN Y ARRANQUE", "PREVENTIVO", "MANTENIMIENTO CORRECTIVO", "OTRO"]
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


# =========================================================
# FORMULARIOS FUNCIONALES
# =========================================================
def render_form_reporte_equipo(
    control_id: str,
    df_inv: pd.DataFrame,
    df_mant: pd.DataFrame,
    df_reportes: pd.DataFrame,
    df_bajas: pd.DataFrame,
) -> None:
    equipo = df_inv[df_inv["Control"].astype(str).str.strip() == control_id]
    area_default = ""
    if not equipo.empty:
        area_default = str(equipo.iloc[0].get("Área", ""))

    st.write("Registra una falla, daño, alarma o solicitud de revisión para este equipo.")

    with st.form(f"form_reporte_{control_id}"):
        c1, c2 = st.columns(2)
        reporta = c1.text_input("Nombre de quien reporta:").strip()
        area = c2.text_input("Área:", value=area_default).strip()

        c3, c4 = st.columns(2)
        prioridad = c3.selectbox("Prioridad:", ["Baja", "Media", "Alta", "Crítica"])
        tipo_reporte = c4.selectbox(
            "Tipo de reporte:",
            ["Falla", "Daño físico", "Accesorio faltante", "Alarma", "Revisión solicitada", "Otro"],
        )

        descripcion = st.text_area("Descripción del problema:", height=120)
        evidencia = st.file_uploader("Evidencia fotográfica opcional:", type=["jpg", "png", "jpeg"], key=f"ev_rep_{control_id}")
        submit = st.form_submit_button("Guardar reporte")

    if submit:
        if not reporta or not descripcion.strip():
            st.error("Captura al menos quién reporta y la descripción del problema.")
            return

        folio = obtener_siguiente_folio(df_reportes, "Folio reporte", "REP")
        evidencia_path = guardar_evidencia(evidencia, "reporte", folio)

        nuevo = {
            "Folio reporte": folio,
            "Control": control_id,
            "Fecha": date.today(),
            "Reporta": reporta,
            "Área": area,
            "Prioridad": prioridad,
            "Tipo de reporte": tipo_reporte,
            "Descripción": descripcion.strip(),
            "Estado del reporte": "Abierto",
            "Evidencia": evidencia_path,
        }

        df_reportes_actualizado = pd.concat([df_reportes, pd.DataFrame([nuevo])], ignore_index=True)
        guardar_datos(df_inv, df_mant, df_reportes_actualizado, df_bajas)
        st.success(f"Reporte {folio} guardado correctamente.")


def render_form_baja_equipo(
    control_id: str,
    df_inv: pd.DataFrame,
    df_mant: pd.DataFrame,
    df_reportes: pd.DataFrame,
    df_bajas: pd.DataFrame,
) -> None:
    st.write("Genera una solicitud de baja. No cambia el estado del equipo hasta que sea autorizada.")

    if not BAJA_PIN:
        st.warning("No hay BAJA_PIN configurado en Streamlit Secrets. La solicitud se permitirá sin PIN administrativo.")

    with st.form(f"form_baja_{control_id}"):
        solicitante = st.text_input("Solicitante:").strip()
        motivo = st.selectbox(
            "Motivo de baja:",
            [
                "Obsolescencia",
                "Daño irreparable",
                "Costo de reparación elevado",
                "Equipo reemplazado",
                "Equipo incompleto",
                "Otro",
            ],
        )
        condicion = st.text_area("Condición actual del equipo:", height=100)
        reparacion = st.selectbox("¿La reparación parece posible?", ["No evaluado", "Sí", "No"])
        observaciones = st.text_area("Observaciones adicionales:", height=100)
        evidencia = st.file_uploader("Evidencia fotográfica opcional:", type=["jpg", "png", "jpeg"], key=f"ev_baja_{control_id}")
        pin = st.text_input("PIN administrativo para baja:", type="password") if BAJA_PIN else ""
        submit = st.form_submit_button("Crear solicitud de baja")

    if submit:
        if BAJA_PIN and pin != BAJA_PIN:
            st.error("PIN administrativo incorrecto. No se creó la solicitud de baja.")
            return
        if not solicitante or not condicion.strip():
            st.error("Captura al menos el solicitante y la condición actual del equipo.")
            return

        folio = obtener_siguiente_folio(df_bajas, "Folio baja", "BAJA")
        evidencia_path = guardar_evidencia(evidencia, "baja", folio)

        nuevo = {
            "Folio baja": folio,
            "Control": control_id,
            "Fecha solicitud": date.today(),
            "Solicitante": solicitante,
            "Motivo de baja": motivo,
            "Condición del equipo": condicion.strip(),
            "Reparación posible": reparacion,
            "Observaciones": observaciones.strip(),
            "Estatus": "Pendiente de autorización",
            "Evidencia": evidencia_path,
        }

        df_bajas_actualizado = pd.concat([df_bajas, pd.DataFrame([nuevo])], ignore_index=True)
        guardar_datos(df_inv, df_mant, df_reportes, df_bajas_actualizado)
        st.success(f"Solicitud de baja {folio} guardada correctamente.")


def render_bitacora(
    df_inv: pd.DataFrame,
    df_mant: pd.DataFrame,
    df_reportes: pd.DataFrame,
    df_bajas: pd.DataFrame,
    control_preseleccionado: Optional[str] = None,
    modo_compacto: bool = False,
) -> None:
    titulo = "🛠️ Bitácora de Servicio - Hospitium" if not modo_compacto else "Generar bitácora para este equipo"
    st.title(titulo) if not modo_compacto else st.subheader(titulo)

    if df_inv.empty:
        st.error("Primero debes registrar equipos en el inventario.")
        return

    opciones = (df_inv["Control"].astype(str) + " - " + df_inv["Nombre"].astype(str)).tolist()
    index_preseleccionado = 0
    if control_preseleccionado:
        for i, opcion in enumerate(opciones):
            if opcion.startswith(str(control_preseleccionado).strip() + " - "):
                index_preseleccionado = i
                break

    folio_actual = obtener_folio()
    st.info(f"Folio ODS automático a generar: {folio_actual}")

    with st.form(f"form_bitacora_{control_preseleccionado or 'general'}"):
        c1, c2 = st.columns(2)
        contrato = c1.text_input("Contrato:", value="019GYP019N1874-008-00")
        hospital = c2.text_input("Hospital / Unidad:")
        direccion = st.text_input("Dirección:")

        equipo_selec = st.selectbox(
            "Seleccionar Equipo del Inventario:",
            opciones,
            index=index_preseleccionado,
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
        estado_final = col_m1.selectbox("Estado final del equipo:", ["Operativo", "Fuera de servicio", "En reparación", "Baja"])
        prox_mant = col_m2.text_input("Próximo mantenimiento (ej. 2027-01-10 o 'No especificado')")

        evidencia = st.file_uploader(
            "Adjuntar fotografía de evidencia (Opcional)",
            type=["jpg", "png", "jpeg"],
            key=f"ev_bit_{control_preseleccionado or 'general'}",
        )

        submit = st.form_submit_button("Generar PDF y Guardar en Excel")

    if submit:
        if not actividad.strip():
            st.error("La actividad realizada es obligatoria.")
            return

        id_eq = equipo_selec.split(" - ")[0]
        datos_eq = df_inv[df_inv["Control"].astype(str) == id_eq].iloc[0]

        evidencia_path = guardar_evidencia(evidencia, "bitacora", str(folio_actual))

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

        df_mant_actualizado = pd.concat([df_mant, pd.DataFrame([nuevo_mantenimiento])], ignore_index=True)

        df_inv_actualizado = df_inv.copy()
        idx = df_inv_actualizado[df_inv_actualizado["Control"].astype(str) == id_eq].index
        if len(idx) > 0:
            df_inv_actualizado.at[idx[0], "Estado del equipo"] = estado_final

        guardar_datos(df_inv_actualizado, df_mant_actualizado, df_reportes, df_bajas)

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


# =========================================================
# PANTALLAS
# =========================================================
def render_ficha_equipo(
    control_id: str,
    df_inv: pd.DataFrame,
    df_mant: pd.DataFrame,
    df_reportes: pd.DataFrame,
    df_bajas: pd.DataFrame,
) -> None:
    control_id = str(control_id).strip().upper()

    st.markdown(
        "<div style='color: #4CAF50; font-size: 12px; font-weight: bold;'>👩‍💻 Desarrollado por: Fernanda Soriano</div>",
        unsafe_allow_html=True,
    )
    st.title("Ficha técnica del equipo")
    st.caption(f"Control: {control_id}")

    if df_inv.empty or "Control" not in df_inv.columns:
        st.error("No se encontró inventario cargado.")
        return

    equipo = df_inv[df_inv["Control"].astype(str).str.strip().str.upper() == control_id]

    if equipo.empty:
        st.error(f"No se encontró ningún equipo con control {control_id}.")
        st.info("Verifica que el equipo exista en la hoja INVENTARIO del Excel. También puedes usar el botón de sincronización del módulo de QR.")
        if control_id in EQUIPOS_QR:
            st.write("Equipo configurado para QR:")
            st.json(EQUIPOS_QR[control_id])
        return

    datos = equipo.iloc[0]
    info_qr = EQUIPOS_QR.get(control_id, {})

    col_img, col_info = st.columns([1, 2])

    with col_img:
        ruta_img = buscar_imagen_equipo(control_id, datos)
        if ruta_img is not None and ruta_img.exists():
            try:
                st.image(str(ruta_img), caption=str(datos.get("Nombre", "")), use_container_width=True)
            except Exception:
                st.error("No fue posible mostrar la imagen guardada.")
        else:
            st.warning("Este equipo aún no tiene imagen cargada.")
            st.caption("Verifica que la imagen exista en qr_equipos/ con el nombre configurado o en imagenes_equipos/CONTROL.png.")

        qr_bytes = generar_qr_personalizado_buffer(control_id) if control_id in EQUIPOS_QR else generar_qr_buffer(construir_url_equipo(control_id))
        st.image(qr_bytes, caption="QR individual del equipo", use_container_width=True)
        st.download_button(
            "📥 Descargar QR individual",
            data=qr_bytes,
            file_name=info_qr.get("archivo_qr", f"QR_{control_id}.png"),
            mime="image/png",
            key=f"download_qr_ficha_{control_id}",
        )

    with col_info:
        st.subheader(str(datos.get("Nombre", info_qr.get("nombre", "Equipo sin nombre"))))
        c1, c2, c3 = st.columns(3)
        c1.metric("Estado", str(datos.get("Estado del equipo", "No especificado")))
        c2.metric("Criticidad", str(datos.get("Criticidad clínica", "No especificada")))
        c3.metric("Control", control_id)

        st.write(f"**Marca:** {datos.get('Marca', 'No especificada')}")
        st.write(f"**Modelo:** {datos.get('Modelo', 'No especificado')}")
        st.write(f"**Serie:** {datos.get('Serie', 'No especificada')}")
        st.write(f"**Área:** {datos.get('Área', 'No especificada')}")
        st.write(f"**Ubicación:** {datos.get('Ubicación', 'No especificada')}")
        st.write(f"**Garantía vigente:** {datos.get('Garantía vigente', 'No especificada')}")
        st.write(f"**Batería de respaldo:** {datos.get('Batería de respaldo', 'No especificada')}")
        st.write(f"**Dependencia eléctrica:** {datos.get('Dependencia eléctrica', 'No especificada')}")
        st.code(construir_url_equipo(control_id), language="text")

    st.markdown("---")

    tab_ficha, tab_historial, tab_reporte, tab_bitacora, tab_baja = st.tabs([
        "📋 Ficha técnica",
        "📚 Historial",
        "🛠️ Levantar reporte",
        "📄 Generar bitácora",
        "⚠️ Solicitar baja",
    ])

    with tab_ficha:
        st.subheader("Guía técnica resumida")
        resumen = GUIA_RESUMIDA.get(control_id)
        if resumen:
            st.write(f"**Descripción general:** {resumen['descripcion']}")
            st.write("**Componentes principales:**")
            for componente in resumen["componentes"]:
                st.markdown(f"- {componente}")
            st.write(f"**Consideraciones de uso:** {resumen['uso']}")
        else:
            st.info("No hay guía resumida configurada para este equipo.")

        st.subheader("Accesorios registrados")
        accesorios = str(datos.get("Accesorios", "")).strip()
        st.write(accesorios if accesorios else "No se registraron accesorios.")

        guia_nombre = info_qr.get("guia", "")
        guia_path = buscar_archivo_en_proyecto(guia_nombre) if guia_nombre else None
        if guia_path:
            with open(guia_path, "rb") as f:
                st.download_button(
                    "📥 Descargar guía técnica completa",
                    data=f.read(),
                    file_name=guia_path.name,
                    mime="application/msword",
                    key=f"download_guia_{control_id}",
                )
        else:
            st.caption("Guía completa no encontrada en la carpeta del proyecto. Colócala en la raíz del proyecto o en guias_equipos/.")

    with tab_historial:
        st.subheader("Historial de mantenimiento")
        historial = df_mant[df_mant["Control"].astype(str).str.strip().str.upper() == control_id].copy()
        if historial.empty:
            st.info("Este equipo aún no tiene historial de mantenimiento.")
        else:
            historial["Fecha"] = pd.to_datetime(historial["Fecha"], errors="coerce")
            historial = historial.sort_values("Fecha", ascending=False)
            st.dataframe(historial, use_container_width=True)

        st.subheader("Reportes asociados")
        reportes_eq = df_reportes[df_reportes["Control"].astype(str).str.strip().str.upper() == control_id].copy()
        if reportes_eq.empty:
            st.info("Este equipo no tiene reportes registrados.")
        else:
            st.dataframe(reportes_eq, use_container_width=True)

        st.subheader("Solicitudes de baja asociadas")
        bajas_eq = df_bajas[df_bajas["Control"].astype(str).str.strip().str.upper() == control_id].copy()
        if bajas_eq.empty:
            st.info("Este equipo no tiene solicitudes de baja registradas.")
        else:
            st.dataframe(bajas_eq, use_container_width=True)

    with tab_reporte:
        render_form_reporte_equipo(control_id, df_inv, df_mant, df_reportes, df_bajas)

    with tab_bitacora:
        render_bitacora(df_inv, df_mant, df_reportes, df_bajas, control_preseleccionado=control_id, modo_compacto=True)

    with tab_baja:
        render_form_baja_equipo(control_id, df_inv, df_mant, df_reportes, df_bajas)


def render_dashboard(df_inv: pd.DataFrame, df_mant: pd.DataFrame, df_reportes: pd.DataFrame, df_bajas: pd.DataFrame) -> None:
    st.markdown(
        "<div style='color: #4CAF50; font-size: 12px; font-weight: bold;'>👩‍💻 Desarrollado por: Fernanda Soriano</div>",
        unsafe_allow_html=True,
    )
    st.title("Panel de Control de Equipos")

    if df_inv.empty:
        st.warning("No se encontró información en el inventario.")
        if st.button("Crear inventario base con los 5 equipos QR"):
            df_sync = sincronizar_equipos_base(df_inv)
            guardar_datos(df_sync, df_mant, df_reportes, df_bajas)
            st.success("Inventario base creado. Recarga la página.")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de Equipos", len(df_inv))
    col2.metric("Áreas Cubiertas", df_inv["Área"].nunique() if "Área" in df_inv.columns else 0)

    df_mant_temp = df_mant.copy()
    df_mant_temp["Fecha"] = pd.to_datetime(df_mant_temp["Fecha"], errors="coerce")
    hace_30_dias = pd.Timestamp.today() - pd.Timedelta(days=30)

    mant_recientes = df_mant_temp[
        (df_mant_temp["Fecha"] >= hace_30_dias)
        & (df_mant_temp["Tipo de mantenimiento"].astype(str).str.contains("Preventivo", case=False, na=False))
    ].shape[0]

    col3.metric("Preventivos últimos 30 días", mant_recientes)
    col4.metric("Reportes abiertos", df_reportes[df_reportes["Estado del reporte"].astype(str).str.lower() == "abierto"].shape[0] if not df_reportes.empty else 0)

    st.markdown("---")
    c_graf1, c_graf2 = st.columns(2)

    with c_graf1:
        st.subheader("Distribución por Área")
        conteo_areas = df_inv.groupby("Área").size().reset_index(name="Cantidad")
        if not conteo_areas.empty:
            fig_pie = px.pie(conteo_areas, names="Área", values="Cantidad", hole=0.3)
            st.plotly_chart(fig_pie, use_container_width=True)
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
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Aún no se han registrado mantenimientos.")

    st.markdown("---")
    st.subheader("Buscador de Equipos y Fotografías")

    opciones_equipos = df_inv["Control"].astype(str) + " - " + df_inv["Nombre"].astype(str)
    equipo_buscado = st.selectbox("Selecciona un equipo:", opciones_equipos)

    if equipo_buscado:
        id_selec = equipo_buscado.split(" - ")[0]
        idx_equipo = df_inv[df_inv["Control"].astype(str) == id_selec].index[0]
        datos_equipo = df_inv.loc[idx_equipo]

        c_img1, c_img2 = st.columns([1, 2])

        with c_img1:
            ruta_img = buscar_imagen_equipo(id_selec, datos_equipo)
            if ruta_img:
                try:
                    st.image(str(ruta_img), use_container_width=True)
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
                guardar_datos(df_inv, df_mant, df_reportes, df_bajas)
                st.success("Foto actualizada correctamente. Recarga la página si no aparece de inmediato.")

        with c_img2:
            st.write(f"**Control ID:** {datos_equipo['Control']}")
            st.write(f"**Nombre / Marca:** {datos_equipo['Nombre']} - {datos_equipo['Marca']}")
            st.write(f"**Modelo / Serie:** {datos_equipo['Modelo']} / {datos_equipo['Serie']}")
            st.write(f"**Área / Ubicación:** {datos_equipo['Área']} - {datos_equipo['Ubicación']}")
            st.write(f"**Estado Actual:** {datos_equipo['Estado del equipo']}")
            st.link_button("Abrir ficha QR", construir_url_equipo(id_selec))

    st.markdown("---")
    st.subheader("Base de Datos Interactiva")
    tab_inv, tab_mant, tab_rep, tab_baja = st.tabs([
        "📦 Inventario",
        "🛠️ Mantenimientos",
        "📋 Reportes",
        "⚠️ Bajas",
    ])

    with tab_inv:
        if st.button("Sincronizar/agregar los 5 equipos QR base"):
            df_sync = sincronizar_equipos_base(df_inv)
            guardar_datos(df_sync, df_mant, df_reportes, df_bajas)
            st.success("Equipos QR sincronizados. Recarga la página.")

        df_editado_inv = st.data_editor(df_inv, use_container_width=True, num_rows="dynamic", key="editor_inv")
        if st.button("💾 Guardar Cambios en Inventario"):
            guardar_datos(df_editado_inv, df_mant, df_reportes, df_bajas)
            st.success("Inventario actualizado correctamente.")

    with tab_mant:
        df_editado_mant = st.data_editor(df_mant, use_container_width=True, num_rows="dynamic", key="editor_mant")
        if st.button("💾 Guardar Cambios en Mantenimientos"):
            guardar_datos(df_inv, df_editado_mant, df_reportes, df_bajas)
            st.success("Mantenimientos actualizados correctamente.")

    with tab_rep:
        df_editado_rep = st.data_editor(df_reportes, use_container_width=True, num_rows="dynamic", key="editor_reportes")
        if st.button("💾 Guardar Cambios en Reportes"):
            guardar_datos(df_inv, df_mant, df_editado_rep, df_bajas)
            st.success("Reportes actualizados correctamente.")

    with tab_baja:
        df_editado_baja = st.data_editor(df_bajas, use_container_width=True, num_rows="dynamic", key="editor_bajas")
        if st.button("💾 Guardar Cambios en Bajas"):
            guardar_datos(df_inv, df_mant, df_reportes, df_editado_baja)
            st.success("Solicitudes de baja actualizadas correctamente.")

    if FILE_EXCEL.exists():
        with open(str(FILE_EXCEL), "rb") as f:
            st.download_button(
                "📥 Descargar Excel Completo",
                data=f.read(),
                file_name="INVENTARIO_ACTUALIZADO.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


def render_nuevo_equipo(df_inv: pd.DataFrame, df_mant: pd.DataFrame, df_reportes: pd.DataFrame, df_bajas: pd.DataFrame) -> None:
    st.title("Ingresar Nuevo Equipo")
    st.write("Completa los datos para registrar un equipo nuevo directamente en tu archivo Excel.")

    with st.form("form_nuevo_equipo"):
        nuevo_inv_id = st.text_input("ID de Control (ej. QX-006):").strip().upper()

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
        n_estado = col7.selectbox("Estado del equipo:", ["Operativo", "Fuera de servicio", "En reparación", "Baja"])
        n_garantia = col8.selectbox("Garantía vigente:", ["Si", "No", "No especificada"])
        n_criticidad = col9.selectbox("Criticidad clínica:", ["Alta", "Media", "Baja"])

        col10, col11 = st.columns(2)
        n_bateria = col10.selectbox("Batería de respaldo:", ["Si", "No", "No especificada"])
        n_dependencia = col11.selectbox("Dependencia eléctrica:", ["Si", "No", "No especificada"])

        n_fecha_adq = st.date_input("Fecha de adquisición:")
        n_accesorios = st.text_area("Accesorios incluidos:")
        n_foto = st.file_uploader("Foto del Equipo (Opcional)", type=["jpg", "png", "jpeg"])
        submit_nuevo = st.form_submit_button("Guardar Equipo en el Excel")

    if submit_nuevo:
        if not nuevo_inv_id or not n_nombre:
            st.error("Debes capturar al menos el ID de control y el nombre del equipo.")
        elif nuevo_inv_id in df_inv["Control"].astype(str).str.upper().tolist():
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
            guardar_datos(df_inv_actualizado, df_mant, df_reportes, df_bajas)
            st.success(f"Equipo {n_nombre} registrado correctamente.")


def render_qrs_por_equipo(df_inv: pd.DataFrame, df_mant: pd.DataFrame, df_reportes: pd.DataFrame, df_bajas: pd.DataFrame) -> None:
    st.title("🏷️ QRs por Equipo")
    st.write("Genera QRs individuales. Cada QR abre directamente la ficha técnica del equipo por su control real.")

    st.info("Las imágenes actuales de los equipos se leen desde qr_equipos/. Los QR nuevos se generan en qrs_generados/ para no sobrescribir esas imágenes.")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Regenerar y guardar todos los QR"):
            rutas_generadas = []
            for control in EQUIPOS_QR:
                rutas_generadas.extend(guardar_qr_equipo(control))
            st.success("QRs generados correctamente en la carpeta qrs_generados.")
            for ruta in rutas_generadas:
                st.code(str(ruta), language="text")

    with c2:
        if st.button("Crear/sincronizar inventario base de estos 5 equipos"):
            df_sync = sincronizar_equipos_base(df_inv)
            guardar_datos(df_sync, df_mant, df_reportes, df_bajas)
            st.success("Inventario base sincronizado. Recarga la página.")

    st.markdown("---")

    for control, info in EQUIPOS_QR.items():
        with st.container(border=True):
            col_a, col_b = st.columns([1, 2])
            url = construir_url_equipo(control)
            qr_bytes = generar_qr_personalizado_buffer(control)

            with col_a:
                st.image(qr_bytes, use_container_width=True)

            with col_b:
                st.subheader(f"{control} — {info['nombre']}")
                st.write(f"**URL del QR:** {url}")
                st.write(f"**Archivo corregido recomendado:** `{info['archivo_qr']}`")
                st.write(f"**Imagen del equipo usada:** `qr_equipos/{info['imagen_archivo_actual']}`")
                st.download_button(
                    "📥 Descargar QR",
                    data=qr_bytes,
                    file_name=info["archivo_qr"],
                    mime="image/png",
                    key=f"qr_download_{control}",
                )
                st.link_button("Abrir ficha", url)


def render_reportes(df_inv: pd.DataFrame, df_mant: pd.DataFrame, df_reportes: pd.DataFrame, df_bajas: pd.DataFrame) -> None:
    st.title("📋 Reportes de Equipos")

    if df_reportes.empty:
        st.info("Aún no hay reportes registrados.")
    else:
        estados = ["Todos"] + sorted(df_reportes["Estado del reporte"].dropna().astype(str).unique().tolist())
        estado_sel = st.selectbox("Filtrar por estado:", estados)
        df_view = df_reportes.copy()
        if estado_sel != "Todos":
            df_view = df_view[df_view["Estado del reporte"].astype(str) == estado_sel]
        st.dataframe(df_view, use_container_width=True)

    st.markdown("---")
    st.subheader("Editar reportes")
    df_editado = st.data_editor(df_reportes, use_container_width=True, num_rows="dynamic", key="editor_reportes_panel")
    if st.button("💾 Guardar cambios de reportes"):
        guardar_datos(df_inv, df_mant, df_editado, df_bajas)
        st.success("Reportes guardados correctamente.")


def render_bajas(df_inv: pd.DataFrame, df_mant: pd.DataFrame, df_reportes: pd.DataFrame, df_bajas: pd.DataFrame) -> None:
    st.title("⚠️ Solicitudes de Baja")

    if df_bajas.empty:
        st.info("Aún no hay solicitudes de baja registradas.")
    else:
        estados = ["Todos"] + sorted(df_bajas["Estatus"].dropna().astype(str).unique().tolist())
        estado_sel = st.selectbox("Filtrar por estatus:", estados)
        df_view = df_bajas.copy()
        if estado_sel != "Todos":
            df_view = df_view[df_view["Estatus"].astype(str) == estado_sel]
        st.dataframe(df_view, use_container_width=True)

    st.markdown("---")
    st.subheader("Editar solicitudes de baja")
    st.caption("Estatus sugeridos: Pendiente de autorización, Autorizada, Rechazada, Ejecutada.")
    df_editado = st.data_editor(df_bajas, use_container_width=True, num_rows="dynamic", key="editor_bajas_panel")

    aplicar_baja = st.checkbox("Si una solicitud está en estatus 'Ejecutada', cambiar el estado del equipo a 'Baja'.")

    if st.button("💾 Guardar cambios de bajas"):
        df_inv_actualizado = df_inv.copy()
        if aplicar_baja and not df_editado.empty:
            ejecutadas = df_editado[df_editado["Estatus"].astype(str).str.strip().str.lower() == "ejecutada"]
            for _, fila in ejecutadas.iterrows():
                control = str(fila["Control"]).strip()
                idx = df_inv_actualizado[df_inv_actualizado["Control"].astype(str).str.strip() == control].index
                if len(idx) > 0:
                    df_inv_actualizado.at[idx[0], "Estado del equipo"] = "Baja"

        guardar_datos(df_inv_actualizado, df_mant, df_reportes, df_editado)
        st.success("Solicitudes de baja guardadas correctamente.")


# =========================================================
# EJECUCION PRINCIPAL
# =========================================================
df_inv, df_mant, df_reportes, df_bajas = cargar_datos()

# Acceso directo desde QR: https://mantapp.streamlit.app/?equipo=QX-003
equipo_qr = obtener_parametro("equipo")
if equipo_qr:
    render_ficha_equipo(equipo_qr, df_inv, df_mant, df_reportes, df_bajas)
    st.stop()


# =========================================================
# SIDEBAR
# =========================================================
if LOGO_FILE.exists():
    st.sidebar.image(str(LOGO_FILE), use_container_width=True)
else:
    st.sidebar.markdown("## 🏥 Hospitium")

st.sidebar.title("Hospitium App")
opcion = st.sidebar.radio(
    "Navegación",
    [
        "📊 Dashboard y Base de Datos",
        "➕ Nuevo Equipo",
        "🛠️ Generar Bitácora",
        "🏷️ QRs por Equipo",
        "📋 Reportes",
        "⚠️ Solicitudes de Baja",
    ],
)

render_qr_sidebar()


if opcion == "📊 Dashboard y Base de Datos":
    render_dashboard(df_inv, df_mant, df_reportes, df_bajas)

elif opcion == "➕ Nuevo Equipo":
    render_nuevo_equipo(df_inv, df_mant, df_reportes, df_bajas)

elif opcion == "🛠️ Generar Bitácora":
    render_bitacora(df_inv, df_mant, df_reportes, df_bajas)

elif opcion == "🏷️ QRs por Equipo":
    render_qrs_por_equipo(df_inv, df_mant, df_reportes, df_bajas)

elif opcion == "📋 Reportes":
    render_reportes(df_inv, df_mant, df_reportes, df_bajas)

elif opcion == "⚠️ Solicitudes de Baja":
    render_bajas(df_inv, df_mant, df_reportes, df_bajas)
