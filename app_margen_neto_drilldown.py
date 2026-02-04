import streamlit as st
import pandas as pd
from urllib.parse import quote

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
# CONFIG (DESPUÉS DEL LOGIN)
# =========================
st.set_page_config(page_title="Margen Neto", layout="wide")

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

# =========================
# LOADERS
# =========================
@st.cache_data(ttl=120)
def load_ventas():
    sheet = quote(SHEET_NAME)
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet}"
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip().str.lower()

    df = ensure_col(df, "especie", "")
    df = ensure_col(df, "categoria", "")
    df = ensure_col(df, "articulo", "")

    df["fecha"] = pd.to_datetime(df.get("fecha"), errors="coerce", dayfirst=True)
    df["cantidad"] = to_num(df.get("cantidad"))
    df["importe"] = to_num(df.get("importe"))
    df["cos_rep"] = to_num(df.get("cos_rep"))

    df["venta_sin_iva"] = df["cantidad"] * df["importe"]
    df["costo"] = df["cantidad"] * df["cos_rep"]
    df["utilidad_neta"] = (df["venta_sin_iva"] - df["costo"]) * 0.93  # -7%

    df = money_round(df, ["venta_sin_iva", "costo", "utilidad_neta"], 2)
    return df

@st.cache_data(ttl=120)
def load_compras():
    sheet = quote(SHEET_NAME_COMPRAS)
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID_COMPRAS}/gviz/tq?tqx=out:csv&sheet={sheet}"
    c = pd.read_csv(url)
    c.columns = c.columns.str.strip().str.lower()

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
# HEADER + FILTRO FECHAS
# =========================
st.caption("Basado en información programa NEXT")
st.title("Utilidad y Margen NETO")

df_fechas = df.dropna(subset=["fecha"])
min_d = df_fechas["fecha"].min().date()
max_d = df_fechas["fecha"].max().date()

c1, c2, _ = st.columns([2, 2, 6])
d_ini = c1.date_input("Desde", min_d, min_d, max_d)
d_fin = c2.date_input("Hasta", max_d, min_d, max_d)

df_f = df[(df["fecha"].dt.date >= d_ini) & (df["fecha"].dt.date <= d_fin)].copy()
dfc_f = dfc[(dfc["fecha"].dt.date >= d_ini) & (dfc["fecha"].dt.date <= d_fin)].copy()

# =========================
# FILTROS (SIDEBAR)
# =========================
with st.sidebar:
    st.subheader("Filtros")
    especies = safe_unique(df_f, "especie")
    especie_sel = st.selectbox("Especie", ["(Todas)"] + especies)

    categorias = safe_unique(df_f, "categoria")
    categoria_sel = st.selectbox("Categoría", ["(Todas)"] + categorias)

if especie_sel != "(Todas)":
    df_f = df_f[df_f["especie"] == especie_sel]
    dfc_f = dfc_f[dfc_f["especie"] == especie_sel]

if categoria_sel != "(Todas)":
    df_f = df_f[df_f["categoria"] == categoria_sel]
    dfc_f = dfc_f[dfc_f["categoria"] == categoria_sel]

st.divider()

# =========================
# KPIs
# =========================
venta = float(df_f["venta_sin_iva"].sum())
costo = float(df_f["costo"].sum())
util = float(df_f["utilidad_neta"].sum())
pzas = int(round(df_f["cantidad"].sum()))
margen = util / venta if venta else 0
compras = float(dfc_f["compras"].sum()) if "compras" in dfc_f.columns else 0.0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Venta sin IVA", f"${venta:,.2f}")
k2.metric("Costo", f"${costo:,.2f}")
k3.metric("Utilidad neta (-7%)", f"${util:,.2f}")
k4.metric("Margen neto %", f"{margen*100:,.2f}%")
k5.metric("Piezas", f"{pzas:,}")

b1, b2, b3, b4, b5 = st.columns(5)
b2.metric("Compras", f"${compras:,.2f}")

st.divider()

# =========================
# EXPLORADOR POR ESPECIE + 80/20 (PARETO)
# (CLICK EN TODA LA TARJETA SIN RECARGAR)
# =========================
if "especie_click" not in st.session_state:
    st.session_state.especie_click = None

st.subheader("Explorador por ESPECIE (Pareto 80/20 por UTILIDAD)")

esp = (
    df_f.groupby("especie", as_index=False)
    .agg(
        utilidad=("utilidad_neta", "sum"),
        venta=("venta_sin_iva", "sum"),
        piezas=("cantidad", "sum"),
    )
)

esp["margen_pct"] = (esp["utilidad"] / esp["venta"]).fillna(0)
esp = money_round(esp, ["venta", "utilidad"], 2)
esp = int_round(esp, ["piezas"])

# Orden por utilidad
esp = esp.sort_values("utilidad", ascending=False).reset_index(drop=True)

# ---- PARETO 80/20 por UTILIDAD ----
total_util = float(esp["utilidad"].sum())
if total_util > 0:
    esp["utilidad_acum"] = esp["utilidad"].cumsum()
    esp["pct_acum"] = (esp["utilidad_acum"] / total_util).fillna(0)

    # Marca TOP80 incluyendo la especie que "cruza" el 80%
    esp["top_80"] = esp["pct_acum"] <= 0.80
    first_over = esp.index[esp["pct_acum"] > 0.80]
    if len(first_over) > 0:
        esp.loc[first_over[0], "top_80"] = True
else:
    esp["utilidad_acum"] = 0
    esp["pct_acum"] = 0
    esp["top_80"] = False

top80_count = int(esp["top_80"].sum())
top80_util = float(esp.loc[esp["top_80"], "utilidad"].sum()) if total_util > 0 else 0.0
top80_pct = (top80_util / total_util) if total_util > 0 else 0.0

cpareto1, cpareto2, cpareto3 = st.columns([2, 2, 6])
cpareto1.metric("Especies TOP", f"{top80_count}")
cpareto2.metric("Utilidad cubierta", f"{top80_pct*100:,.2f}%")
cpareto3.caption("Las tarjetas en VERDE son las especies que acumulan ~80% de la utilidad neta (-7%).")

# CSS para que un st.button se vea como tarjeta + color TOP80
st.markdown(
    """
    <style>
      /* base card */
      div.stButton > button {
        width: 100%;
        border-radius: 14px;
        padding: 18px 14px;
        border: 1px solid rgba(255,255,255,0.12);
        background: rgba(255,255,255,0.04);
        color: white;
        text-align: center;
        white-space: pre-line;
        line-height: 1.25;
      }
      div.stButton > button:hover {
        border-color: rgba(255,255,255,0.22);
        transform: translateY(-1px);
      }

      /* top80 wrapper makes that button green */
      .top80wrap div.stButton > button{
        background: rgba(46, 204, 113, 0.18) !important;
        border: 1px solid rgba(46,204,113,0.55) !important;
      }
      .top80wrap div.stButton > button:hover{
        border: 1px solid rgba(46,204,113,0.75) !important;
      }
    </style>
    """,
    unsafe_allow_html=True
)

# Grid 5 columnas (tarjetas)
cols = st.columns(5)
for i, row in esp.iterrows():
    with cols[i % 5]:
        label = (
            f"{row['especie']}\n\n"
            f"Margen: {row['margen_pct']*100:,.2f}%   "
            f"Utilidad: {fmt_money0(row['utilidad'])}"
        )

        if bool(row["top_80"]):
            st.markdown('<div class="top80wrap">', unsafe_allow_html=True)
            if st.button(label, key=f"esp_{i}", use_container_width=True):
                st.session_state.especie_click = row["especie"]
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            if st.button(label, key=f"esp_{i}", use_container_width=True):
                st.session_state.especie_click = row["especie"]

c_clear, _ = st.columns([2, 8])
if c_clear.button("Limpiar selección", use_container_width=True):
    st.session_state.especie_click = None

# =========================
# DETALLE POR ESPECIE (PRODUCTOS) - SIN RECARGA
# =========================
esp_sel = st.session_state.especie_click

if esp_sel and (("especie" not in df_f.columns) or (esp_sel not in df_f["especie"].astype(str).unique())):
    st.session_state.especie_click = None
    esp_sel = None

if esp_sel:
    st.divider()
    st.subheader(f"Detalle de especie: {esp_sel}")

    dfx = df_f[df_f["especie"].astype(str) == str(esp_sel)].copy()

    prod = (
        dfx.groupby("articulo", as_index=False)
        .agg(
            piezas=("cantidad", "sum"),
            venta_sin_iva=("venta_sin_iva", "sum"),
            costo=("costo", "sum"),
            utilidad_neta=("utilidad_neta", "sum"),
        )
    )
    prod["margen_pct"] = (prod["utilidad_neta"] / prod["venta_sin_iva"]).fillna(0)

    prod = money_round(prod, ["venta_sin_iva", "costo", "utilidad_neta"], 2)
    prod = int_round(prod, ["piezas"])

    top_pzas = prod.sort_values("piezas", ascending=False).head(1)
    top_venta = prod.sort_values("venta_sin_iva", ascending=False).head(1)
    top_util = prod.sort_values("utilidad_neta", ascending=False).head(1)
    top_margen = prod.sort_values("margen_pct", ascending=False).head(1)

    cA, cB, cC, cD = st.columns(4)
    cA.metric("Más vendido (pzas)", str(top_pzas.iloc[0]["articulo"]), f'{int(top_pzas.iloc[0]["piezas"]):,} pzas')
    cB.metric("Mayor venta", str(top_venta.iloc[0]["articulo"]), f'${float(top_venta.iloc[0]["venta_sin_iva"]):,.2f}')
    cC.metric("Mayor utilidad", str(top_util.iloc[0]["articulo"]), f'${float(top_util.iloc[0]["utilidad_neta"]):,.2f}')
    cD.metric("Mejor margen %", str(top_margen.iloc[0]["articulo"]), f'{float(top_margen.iloc[0]["margen_pct"])*100:,.2f}%')

    st.divider()
    t1, t2, t3, t4 = st.tabs(["Top 20 por Utilidad", "Top 20 por Venta", "Top 20 por Piezas", "Tabla completa"])

    def show_table(data, h=560):
        st.data_editor(
            data,
            hide_index=True,
            disabled=True,
            height=h,
            column_config={
                "piezas": st.column_config.NumberColumn("Piezas", format="%,.0f"),
                "venta_sin_iva": st.column_config.NumberColumn("Venta sin IVA", format="$%,.2f"),
                "costo": st.column_config.NumberColumn("Costo", format="$%,.2f"),
                "utilidad_neta": st.column_config.NumberColumn("Utilidad neta", format="$%,.2f"),
                "margen_pct": st.column_config.NumberColumn("Margen %", format="%.2f%%"),
            }
        )

    with t1:
        show_table(prod.sort_values("utilidad_neta", ascending=False).head(20))
    with t2:
        show_table(prod.sort_values("venta_sin_iva", ascending=False).head(20))
    with t3:
        show_table(prod.sort_values("piezas", ascending=False).head(20))
    with t4:
        show_table(prod.sort_values("utilidad_neta", ascending=False), h=650)

# =========================
# MARGEN POR PROVEEDOR
# =========================
st.divider()
st.subheader("Margen por proveedor")

if "proveedor" not in dfc_f.columns or dfc_f["proveedor"].astype(str).str.strip().eq("").all():
    st.info("Para ver esta sección, tu hoja de COMPRAS debe traer una columna llamada 'proveedor'.")
else:
    prov = (
        dfc_f.groupby("proveedor", as_index=False)
        .agg(
            compras=("compras", "sum"),
            cantidad=("cantidad", "sum")
        )
    )
    prov = money_round(prov, ["compras"], 2)
    prov = int_round(prov, ["cantidad"])
    prov = prov.sort_values("compras", ascending=False).reset_index(drop=True)

    st.data_editor(
        prov,
        hide_index=True,
        disabled=True,
        height=420,
        column_config={
            "compras": st.column_config.NumberColumn("Compras", format="$%,.2f"),
            "cantidad": st.column_config.NumberColumn("Piezas compradas", format="%,.0f"),
        }
    )

# =========================
# REFRESH
# =========================
st.button("Actualizar ahora", on_click=st.cache_data.clear)
st.caption("Dashboard protegido con contraseña")
