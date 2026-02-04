import streamlit as st
import pandas as pd
from urllib.parse import quote

# =========================
# CONFIG (DEBE IR PRIMERO)
# =========================
st.set_page_config(page_title="Panel Director", layout="wide")

# =========================
# LOGIN SIMPLE (PASSWORD)
# =========================
def check_password():
    PASSWORD = "Serur2026*"  # <-- CAMBIA AQUÍ LA CLAVE

    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False

    if st.session_state.auth_ok:
        return True

    st.title("Acceso al Panel")
    st.caption("Ingresa la contraseña para continuar")

    pw = st.text_input("Contraseña", type="password")
    if st.button("Entrar", use_container_width=True):
        if pw == PASSWORD:
            st.session_state.auth_ok = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta")

    return False

if not check_password():
    st.stop()

# =========================
# CONFIG DATOS
# =========================
SHEET_ID = "1UpYQT6ErO3Xj3xdZ36IYJPRR9uDRQw-eYui9B_Y-JwU"
SHEET_NAME = "Hoja1"          # VENTAS

SHEET_ID_COMPRAS = "17X31u6slmVg--HSiL0AahdRSObvtVM0Q_KDd72EH-Ro"
SHEET_NAME_COMPRAS = "Hoja1"  # COMPRAS

# =========================
# HELPERS
# =========================
def to_num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0)

def money_round(df_, cols, nd=2):
    for c in cols:
        if c in df_.columns:
            df_[c] = pd.to_numeric(df_[c], errors="coerce").fillna(0).round(nd)
    return df_

def int_round(df_, cols):
    for c in cols:
        if c in df_.columns:
            df_[c] = pd.to_numeric(df_[c], errors="coerce").fillna(0).round(0).astype(int)
    return df_

def ensure_col(df_, col, default=""):
    if col not in df_.columns:
        df_[col] = default
    return df_

def safe_unique(df_, col):
    if col not in df_.columns:
        return []
    return sorted([x for x in df_[col].dropna().unique().tolist() if str(x).strip() != ""])

def fmt_money0(x):
    return f"${float(x):,.0f}"

def clean_text_series(s: pd.Series) -> pd.Series:
    return s.astype(str).fillna("").str.strip()

def nunique_clean(s: pd.Series) -> int:
    x = clean_text_series(s)
    x = x.replace("", pd.NA).dropna()
    return int(x.nunique())

# =========================
# LOADERS
# =========================
@st.cache_data(ttl=120)
def load_ventas():
    sheet = quote(SHEET_NAME)
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet}"
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip().str.lower()

    # columnas esperadas / opcionales
    df = ensure_col(df, "fecha", None)
    df = ensure_col(df, "especie", "")
    df = ensure_col(df, "categoria", "")
    df = ensure_col(df, "articulo", "")
    df = ensure_col(df, "vendedor", "")
    df = ensure_col(df, "cliente", "")  # <- confirmado

    df["fecha"] = pd.to_datetime(df.get("fecha"), errors="coerce", dayfirst=True)
    df["cantidad"] = to_num(df.get("cantidad"))
    df["importe"] = to_num(df.get("importe"))
    df["cos_rep"] = to_num(df.get("cos_rep"))

    df["venta_sin_iva"] = df["cantidad"] * df["importe"]
    df["costo"] = df["cantidad"] * df["cos_rep"]
    df["utilidad_neta"] = (df["venta_sin_iva"] - df["costo"]) * 0.93  # -7%

    # redondeo SOLO visual
    df = money_round(df, ["venta_sin_iva", "costo", "utilidad_neta"], 2)
    return df

@st.cache_data(ttl=120)
def load_compras():
    sheet = quote(SHEET_NAME_COMPRAS)
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID_COMPRAS}/gviz/tq?tqx=out:csv&sheet={sheet}"
    c = pd.read_csv(url)
    c.columns = c.columns.str.strip().str.lower()

    c = ensure_col(c, "fecha", None)
    c = ensure_col(c, "especie", "")
    c = ensure_col(c, "categoria", "")
    c = ensure_col(c, "articulo", "")
    c = ensure_col(c, "proveedor", "")

    c["fecha"] = pd.to_datetime(c.get("fecha"), errors="coerce", dayfirst=True)
    c["cantidad"] = to_num(c.get("cantidad"))
    c["importe"] = to_num(c.get("importe"))

    c["compras"] = c["cantidad"] * c["importe"]
    c = money_round(c, ["compras"], 2)
    return c

df = load_ventas()
dfc = load_compras()

# =========================
# NAVEGACIÓN (MENÚ / VISTAS)
# =========================
if "view" not in st.session_state:
    st.session_state.view = "menu"

def go(view_name: str):
    st.session_state.view = view_name
    st.rerun()

# =========================
# ESTILOS TARJETAS (BOTONES)
# =========================
st.markdown(
    """
    <style>
      .cardwrap button{
        width:100% !important;
        border-radius:18px !important;
        padding:18px 16px !important;
        border:1px solid rgba(255,255,255,0.14) !important;
        background: rgba(255,255,255,0.04) !important;
        color: white !important;
        white-space: pre-line !important;
        text-align: left !important;
        line-height: 1.15 !important;
      }
      .cardwrap button:hover{
        border-color: rgba(255,255,255,0.24) !important;
        transform: translateY(-1px) !important;
      }
      .menuwrap button{
        text-align:center !important;
        font-size: 18px !important;
        padding:24px 18px !important;
      }
      .muted {
        color: rgba(255,255,255,0.65);
        font-size: 12px;
      }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# VISTA: MENÚ
# =========================
if st.session_state.view == "menu":
    st.title("Panel Director")
    st.caption("Selecciona un módulo")

    c1, c2, c3 = st.columns([2, 2, 6])

    with c1:
        st.markdown('<div class="cardwrap menuwrap">', unsafe_allow_html=True)
        if st.button("VENTAS", use_container_width=True):
            go("ventas")
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="cardwrap menuwrap">', unsafe_allow_html=True)
        if st.button("VENTAS POR PROVEEDOR", use_container_width=True):
            go("ventas_proveedor")
        st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    st.button("Actualizar ahora", on_click=st.cache_data.clear)
    st.caption("Dashboard protegido con contraseña")
    st.stop()

# =========================
# VISTA: VENTAS
# =========================
if st.session_state.view == "ventas":
    topbar1, topbar2, _ = st.columns([2, 2, 8])
    if topbar1.button("⬅️ Regresar al menú", use_container_width=True):
        go("menu")
    if topbar2.button("Actualizar ahora", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.caption("Basado en información programa NEXT")
    st.title("VENTAS")

    # Fechas
    df_fechas = df.dropna(subset=["fecha"])
    if df_fechas.empty:
        st.error("No hay fechas válidas en VENTAS (columna 'fecha').")
        st.stop()

    min_d = df_fechas["fecha"].min().date()
    max_d = df_fechas["fecha"].max().date()

    f1, f2, _ = st.columns([2, 2, 6])
    d_ini = f1.date_input("Desde", min_d, min_d, max_d)
    d_fin = f2.date_input("Hasta", max_d, min_d, max_d)

    df_f = df[(df["fecha"].dt.date >= d_ini) & (df["fecha"].dt.date <= d_fin)].copy()

    # Sidebar filtros (opcionales)
    with st.sidebar:
        st.subheader("Filtros")
        especies = safe_unique(df_f, "especie")
        especie_sel = st.selectbox("Especie", ["(Todas)"] + especies)

        categorias = safe_unique(df_f, "categoria")
        categoria_sel = st.selectbox("Categoría", ["(Todas)"] + categorias)

    if especie_sel != "(Todas)":
        df_f = df_f[df_f["especie"] == especie_sel]
    if categoria_sel != "(Todas)":
        df_f = df_f[df_f["categoria"] == categoria_sel]

    st.divider()

    # KPIs
    venta = float(df_f["venta_sin_iva"].sum())
    costo = float(df_f["costo"].sum())
    util = float(df_f["utilidad_neta"].sum())
    pzas = int(round(df_f["cantidad"].sum()))
    margen = util / venta if venta else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Venta sin IVA", f"${venta:,.2f}")
    k2.metric("Costo", f"${costo:,.2f}")
    k3.metric("Utilidad neta (-7%)", f"${util:,.2f}")
    k4.metric("Margen neto %", f"{margen*100:,.2f}%")
    k5.metric("Piezas", f"{pzas:,}")

    st.divider()
    st.subheader("Vendedores (ordenados por venta)")

    df_f["vendedor"] = clean_text_series(df_f["vendedor"])
    df_f["cliente"] = clean_text_series(df_f["cliente"])

    dffv = df_f[df_f["vendedor"] != ""].copy()
    if dffv.empty:
        st.info("No veo datos en la columna 'vendedor' (o viene vacía).")
        st.stop()

    vend = (
        dffv.groupby("vendedor", as_index=False)
        .agg(
            clientes=("cliente", nunique_clean),
            venta=("venta_sin_iva", "sum"),
            utilidad=("utilidad_neta", "sum"),
            piezas=("cantidad", "sum"),
        )
    )

    vend = vend.sort_values("venta", ascending=False).reset_index(drop=True)
    vend = money_round(vend, ["venta", "utilidad"], 2)
    vend = int_round(vend, ["piezas", "clientes"])

    cols = st.columns(5)
    for i, row in vend.iterrows():
        with cols[i % 5]:
            label = (
                f"{row['vendedor']}\n\n"
                f"Clientes: {int(row['clientes']):,}\n"
                f"Venta: {fmt_money0(row['venta'])}\n"
                f"Utilidad: {fmt_money0(row['utilidad'])}"
            )
            st.markdown('<div class="cardwrap">', unsafe_allow_html=True)
            st.button(label, key=f"vend_{i}", use_container_width=True, disabled=True)
            st.markdown("</div>", unsafe_allow_html=True)

    st.stop()

# =========================
# VISTA: VENTAS POR PROVEEDOR (SIGUIENTE PASO)
# =========================
if st.session_state.view == "ventas_proveedor":
    topbar1, topbar2, _ = st.columns([2, 2, 8])
    if topbar1.button("⬅️ Regresar al menú", use_container_width=True):
        go("menu")
    if topbar2.button("Actualizar ahora", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.title("VENTAS POR PROVEEDOR")
    st.info("Siguiente paso: cruzar VENTAS vs COMPRAS por proveedor (vendido, comprado y utilidad).")
    st.stop()
