import streamlit as st
import pandas as pd
from urllib.parse import quote

# =========================
# CONFIG BÁSICA
# =========================
st.set_page_config(page_title="Margen Neto", layout="wide")

# =========================
# LOGIN SIMPLE (PASSWORD)
# =========================
def check_password():
    PASSWORD = "Serur2026*"   # <-- CAMBIA AQUÍ LA CLAVE

    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False

    if st.session_state.auth_ok:
        return True

    st.title("Acceso al Dashboard")
    pw = st.text_input("Contraseña", type="password")

    if st.button("Entrar"):
        if pw == PASSWORD:
            st.session_state.auth_ok = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta")

    return False

if not check_password():
    st.stop()

# =========================
# CONFIG DE DATOS
# =========================
SHEET_ID = "1UpYQT6ErO3Xj3xdZ36IYJPRR9uDRQw-eYui9B_Y-JwU"
SHEET_NAME = "Hoja1"

SHEET_ID_COMPRAS = "17X31u6slmVg--HSiL0AahdRSObvtVM0Q_KDd72EH-Ro"
SHEET_NAME_COMPRAS = "Hoja1"

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

def ensure_col(df_, col, default=""):
    if col not in df_.columns:
        df_[col] = default
    return df_

# =========================
# LOADERS
# =========================
@st.cache_data(ttl=60)
def load_ventas():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={quote(SHEET_NAME)}"
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip().str.lower()

    df = ensure_col(df, "especie", "")
    df = ensure_col(df, "articulo", "")

    df["fecha"] = pd.to_datetime(df.get("fecha"), errors="coerce", dayfirst=True)
    df["cantidad"] = to_num(df.get("cantidad"))
    df["importe"] = to_num(df.get("importe"))
    df["cos_rep"] = to_num(df.get("cos_rep"))

    df["venta_sin_iva"] = df["cantidad"] * df["importe"]
    df["costo"] = df["cantidad"] * df["cos_rep"]
    df["utilidad_neta"] = (df["venta_sin_iva"] - df["costo"]) * 0.93

    return money_round(df, ["venta_sin_iva", "costo", "utilidad_neta"], 2)

@st.cache_data(ttl=60)
def load_compras():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID_COMPRAS}/gviz/tq?tqx=out:csv&sheet={quote(SHEET_NAME_COMPRAS)}"
    c = pd.read_csv(url)
    c.columns = c.columns.str.strip().str.lower()

    c["fecha"] = pd.to_datetime(c.get("fecha"), errors="coerce", dayfirst=True)
    c["cantidad"] = to_num(c.get("cantidad"))
    c["importe"] = to_num(c.get("importe"))
    c["compras"] = c["cantidad"] * c["importe"]

    return money_round(c, ["compras"], 2)

df = load_ventas()
dfc = load_compras()

# =========================
# HEADER + KPIs
# =========================
st.caption("Basado en información programa NEXT")
st.title("Utilidad y Margen NETO")

venta = df["venta_sin_iva"].sum()
costo = df["costo"].sum()
util = df["utilidad_neta"].sum()
margen = util / venta if venta else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Venta sin IVA", f"${venta:,.2f}")
k2.metric("Costo", f"${costo:,.2f}")
k3.metric("Utilidad neta (-7%)", f"${util:,.2f}")
k4.metric("Margen neto %", f"{margen*100:,.2f}%")

st.divider()

# =========================
# EXPLORADOR POR ESPECIE (ORDENADO POR UTILIDAD)
# =========================
st.subheader("Explorador por ESPECIE (clic para ver detalle)")

esp = (
    df.groupby("especie", as_index=False)
    .agg(
        utilidad=("utilidad_neta", "sum"),
        venta=("venta_sin_iva", "sum"),
    )
)
esp["margen_pct"] = esp["utilidad"] / esp["venta"]
esp = esp.sort_values("utilidad", ascending=False).reset_index(drop=True)

cols = st.columns(5)
for i, r in esp.iterrows():
    with cols[i % 5]:
        st.button(
            f"{r['especie']}\n\nMargen: {r['margen_pct']*100:,.2f}%\nUtilidad: ${r['utilidad']:,.0f}",
            use_container_width=True,
            key=f"esp_{i}"
        )

st.divider()
st.caption("Dashboard protegido con contraseña")
