import streamlit as st
import pandas as pd
from urllib.parse import quote
import html

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

# NEGOCIADO (TAB FALTANTE)
SHEET_ID_NEGOCIADO = SHEET_ID
SHEET_NAME_NEGOCIADO = "FALTANTE"

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

def safe_unique(df_, col):
    if col not in df_.columns:
        return []
    return sorted([x for x in df_[col].dropna().unique().tolist() if str(x).strip() != ""])

def fmt_money0(x):
    return f"${float(x):,.0f}"

def clean_cols(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = df.columns.astype(str).str.strip().str.lower()
    return df

def clean_text_series(s: pd.Series) -> pd.Series:
    return s.astype(str).fillna("").str.strip()

def nunique_clean(s: pd.Series) -> int:
    x = clean_text_series(s).replace("", pd.NA).dropna()
    return int(x.nunique())

def gsheet_csv(sheet_id: str, sheet_name: str) -> str:
    sheet = quote(sheet_name)
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet}"

def first_nonempty(series: pd.Series) -> str:
    x = series.dropna().astype(str).str.strip()
    x = x[x != ""]
    return x.iloc[0] if len(x) else ""

def pick_code_col(df_: pd.DataFrame, candidates: list[str]) -> str:
    """Devuelve el primer nombre de columna existente con datos."""
    for c in candidates:
        if c in df_.columns:
            s = clean_text_series(df_[c])
            if not s.eq("").all():
                return c
    # si existen pero vacías, regresa la primera existente
    for c in candidates:
        if c in df_.columns:
            return c
    return ""

# =========================
# LOADERS
# =========================
@st.cache_data(ttl=120)
def load_ventas():
    url = gsheet_csv(SHEET_ID, SHEET_NAME)
    df = pd.read_csv(url)
    df = clean_cols(df)

    df = ensure_col(df, "fecha", None)
    df = ensure_col(df, "especie", "")
    df = ensure_col(df, "categoria", "")
    df = ensure_col(df, "articulo", "")
    df = ensure_col(df, "vendedor", "")
    df = ensure_col(df, "cliente", "")

    # en tu captura el código viene como "clave"
    df = ensure_col(df, "clave", "")
    df = ensure_col(df, "cve_art", "")  # por si algún día lo agregas

    df["fecha"] = pd.to_datetime(df.get("fecha"), errors="coerce", dayfirst=True)

    df["cantidad"] = to_num(df.get("cantidad"))
    df["importe"] = to_num(df.get("importe"))
    df["cos_rep"] = to_num(df.get("cos_rep"))

    df["venta_sin_iva"] = df["cantidad"] * df["importe"]
    df["costo"] = df["cantidad"] * df["cos_rep"]
    df["utilidad_neta"] = (df["venta_sin_iva"] - df["costo"]) * 0.93  # -7%

    # normalizaciones texto
    for col in ["especie", "categoria", "articulo", "vendedor", "cliente", "clave", "cve_art"]:
        df[col] = clean_text_series(df[col])

    df = money_round(df, ["venta_sin_iva", "costo", "utilidad_neta"], 2)
    return df

@st.cache_data(ttl=120)
def load_compras():
    url = gsheet_csv(SHEET_ID_COMPRAS, SHEET_NAME_COMPRAS)
    c = pd.read_csv(url)
    c = clean_cols(c)

    c = ensure_col(c, "fecha", None)
    c = ensure_col(c, "especie", "")
    c = ensure_col(c, "categoria", "")
    c = ensure_col(c, "articulo", "")
    c = ensure_col(c, "proveedor", "")

    # código: preferimos cve_art, pero aceptamos clave
    c = ensure_col(c, "cve_art", "")
    c = ensure_col(c, "clave", "")

    c["fecha"] = pd.to_datetime(c.get("fecha"), errors="coerce", dayfirst=True)
    c["cantidad"] = to_num(c.get("cantidad"))
    c["importe"] = to_num(c.get("importe"))

    c["compras"] = c["cantidad"] * c["importe"]

    for col in ["especie", "categoria", "articulo", "proveedor", "cve_art", "clave"]:
        c[col] = clean_text_series(c[col])

    c = money_round(c, ["compras"], 2)
    return c

@st.cache_data(ttl=120)
def load_negociado():
    url = gsheet_csv(SHEET_ID_NEGOCIADO, SHEET_NAME_NEGOCIADO)
    n = pd.read_csv(url)
    n = clean_cols(n)

    # en tu captura: cve_art y (expression)
    n = ensure_col(n, "cve_art", "")
    n = ensure_col(n, "clave", "")
    n = ensure_col(n, "(expression)", 0)

    n["cve_art"] = clean_text_series(n["cve_art"])
    n["clave"] = clean_text_series(n["clave"])
    n["negociado"] = to_num(n["(expression)"])

    return n[["cve_art", "clave", "negociado"]].copy()

df = load_ventas()
dfc = load_compras()
dfn = load_negociado()

# =========================
# NAVEGACIÓN
# =========================
if "view" not in st.session_state:
    st.session_state.view = "menu"

def go(view_name: str):
    st.session_state.view = view_name
    st.rerun()

# =========================
# ESTILOS
# =========================
st.markdown(
    """
    <style>
      .menuwrap button{
        width:100% !important;
        border-radius:18px !important;
        padding:22px 18px !important;
        border:1px solid rgba(255,255,255,0.14) !important;
        background: rgba(255,255,255,0.05) !important;
        color: white !important;
        font-size:18px !important;
      }
      .menuwrap button:hover{
        border-color: rgba(255,255,255,0.24) !important;
        transform: translateY(-1px) !important;
      }

      .hcard{
        border-radius: 18px;
        padding: 14px 14px;
        border: 1px solid rgba(255,255,255,0.14);
        background: rgba(255,255,255,0.04);
        min-height: 110px;
      }
      .hcard.top80{
        background: rgba(46,204,113,0.22);
        border: 1px solid rgba(46,204,113,0.90);
      }
      .hcard-title{
        font-weight: 800;
        font-size: 15px;
        margin-bottom: 6px;
      }
      .hcard-line{
        font-size: 13px;
        opacity: 0.92;
        line-height: 1.25;
      }
      .muted{
        color: rgba(255,255,255,0.65);
        font-size: 12px;
      }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# MENU
# =========================
if st.session_state.view == "menu":
    st.title("Panel Director")
    st.caption("Selecciona un módulo")

    c1, c2, c3 = st.columns([2, 2, 6])

    with c1:
        st.markdown('<div class="menuwrap">', unsafe_allow_html=True)
        if st.button("VENTAS"):
            go("ventas")
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="menuwrap">', unsafe_allow_html=True)
        if st.button("VENTAS POR PROVEEDOR"):
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

    df_fechas = df.dropna(subset=["fecha"])
    if df_fechas.empty:
        st.error("No hay fechas válidas en VENTAS (columna 'fecha').")
        st.stop()

    min_d = df_fechas["fecha"].min().date()
    max_d = df_fechas["fecha"].max().date()

    f1, f2, _ = st.columns([2, 2, 6])
    d_ini = f1.date_input("Desde", min_d, min_d, max_d, key="v_d_ini")
    d_fin = f2.date_input("Hasta", max_d, min_d, max_d, key="v_d_fin")

    df_f = df[(df["fecha"].dt.date >= d_ini) & (df["fecha"].dt.date <= d_fin)].copy()

    with st.sidebar:
        st.subheader("Filtros (ventas)")
        especies = safe_unique(df_f, "especie")
        especie_sel = st.selectbox("Especie", ["(Todas)"] + especies, key="v_esp")
        categorias = safe_unique(df_f, "categoria")
        categoria_sel = st.selectbox("Categoría", ["(Todas)"] + categorias, key="v_cat")

    if especie_sel != "(Todas)":
        df_f = df_f[df_f["especie"] == especie_sel]
    if categoria_sel != "(Todas)":
        df_f = df_f[df_f["categoria"] == categoria_sel]

    st.divider()

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
        )
    ).sort_values("venta", ascending=False).reset_index(drop=True)

    cols = st.columns(5)
    for i, row in vend.iterrows():
        with cols[i % 5]:
            nombre = html.escape(str(row["vendedor"]))
            card = f"""
              <div class="hcard">
                <div class="hcard-title">{nombre}</div>
                <div class="hcard-line">Clientes: {int(row['clientes']):,}</div>
                <div class="hcard-line">Venta: {fmt_money0(row['venta'])}</div>
                <div class="hcard-line">Utilidad: {fmt_money0(row['utilidad'])}</div>
              </div>
            """
            st.markdown(card, unsafe_allow_html=True)

    st.stop()

# =========================
# VISTA: VENTAS POR PROVEEDOR (ESPECIE + VENDIDO/UTILIDAD + COMPRADO + NEGOCIADO + PARETO VERDE)
# =========================
if st.session_state.view == "ventas_proveedor":
    topbar1, topbar2, _ = st.columns([2, 2, 8])
    if topbar1.button("⬅️ Regresar al menú", use_container_width=True):
        go("menu")
    if topbar2.button("Actualizar ahora", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.caption("Basado en información programa NEXT")
    st.title("VENTAS POR PROVEEDOR")
    st.markdown('<div class="muted">Cruce por código: VENTAS usa "clave", COMPRAS/FALTANTE usan "cve_art".</div>', unsafe_allow_html=True)

    df_fechas = df.dropna(subset=["fecha"])
    if df_fechas.empty:
        st.error("No hay fechas válidas en VENTAS (columna 'fecha').")
        st.stop()

    min_d = df_fechas["fecha"].min().date()
    max_d = df_fechas["fecha"].max().date()

    f1, f2, _ = st.columns([2, 2, 6])
    d_ini = f1.date_input("Desde", min_d, min_d, max_d, key="vp_d_ini")
    d_fin = f2.date_input("Hasta", max_d, min_d, max_d, key="vp_d_fin")

    df_f = df[(df["fecha"].dt.date >= d_ini) & (df["fecha"].dt.date <= d_fin)].copy()
    dfc_f = dfc[(dfc["fecha"].dt.date >= d_ini) & (dfc["fecha"].dt.date <= d_fin)].copy()

    with st.sidebar:
        st.subheader("Filtros (ventas por proveedor)")
        categorias = safe_unique(df_f, "categoria")
        categoria_sel = st.selectbox("Categoría", ["(Todas)"] + categorias, key="vp_cat")

    if categoria_sel != "(Todas)":
        df_f = df_f[df_f["categoria"] == categoria_sel]
        dfc_f = dfc_f[dfc_f["categoria"] == categoria_sel]

    st.divider()

    # ========= 1) mapping CODIGO -> ESPECIE usando ventas =========
    venta_code_col = pick_code_col(df_f, ["clave", "cve_art"])
    if not venta_code_col:
        st.error("No encuentro columna de código en VENTAS. Debe existir 'clave' (o 'cve_art').")
        st.stop()

    map_ce = (
        df_f[clean_text_series(df_f[venta_code_col]) != ""]
        .groupby(venta_code_col, as_index=False)
        .agg(especie=("especie", first_nonempty))
    )
    map_ce.rename(columns={venta_code_col: "codigo"}, inplace=True)
    map_ce["codigo"] = clean_text_series(map_ce["codigo"])
    map_ce["especie"] = clean_text_series(map_ce["especie"])

    if map_ce["codigo"].eq("").all():
        st.error("La columna de código en VENTAS existe pero viene vacía.")
        st.stop()

    # ========= 2) vendido/utilidad por especie =========
    esp = (
        df_f.groupby("especie", as_index=False)
        .agg(
            vendido=("venta_sin_iva", "sum"),
            utilidad=("utilidad_neta", "sum"),
            costo=("costo", "sum"),
        )
    )
    esp["margen_pct"] = (esp["utilidad"] / esp["vendido"]).fillna(0)
    esp["especie"] = clean_text_series(esp["especie"])

    # ========= 3) comprado por especie (compras via codigo) =========
    comp_code_col = pick_code_col(dfc_f, ["cve_art", "clave"])
    if not comp_code_col:
        comp_esp = pd.DataFrame({"especie": [], "comprado": []})
        st.warning("COMPRAS no trae 'cve_art' ni 'clave'. 'Comprado' quedará en 0.")
    else:
        comp_art = (
            dfc_f[clean_text_series(dfc_f[comp_code_col]) != ""]
            .groupby(comp_code_col, as_index=False)
            .agg(comprado=("compras", "sum"))
        )
        comp_art.rename(columns={comp_code_col: "codigo"}, inplace=True)
        comp_art["codigo"] = clean_text_series(comp_art["codigo"])
        comp_art = comp_art.merge(map_ce, on="codigo", how="left")
        comp_esp = comp_art.groupby("especie", as_index=False).agg(comprado=("comprado", "sum"))
        comp_esp["especie"] = clean_text_series(comp_esp["especie"])

    # ========= 4) negociado por especie (faltante via codigo) =========
    neg_code_col = pick_code_col(dfn, ["cve_art", "clave"])
    if not neg_code_col:
        neg_esp = pd.DataFrame({"especie": [], "negociado": []})
        st.warning("FALTANTE no trae 'cve_art' ni 'clave'. 'Negociado' quedará en 0.")
    else:
        neg_art = (
            dfn[clean_text_series(dfn[neg_code_col]) != ""]
            .groupby(neg_code_col, as_index=False)
            .agg(negociado=("negociado", "sum"))
        )
        neg_art.rename(columns={neg_code_col: "codigo"}, inplace=True)
        neg_art["codigo"] = clean_text_series(neg_art["codigo"])
        neg_art = neg_art.merge(map_ce, on="codigo", how="left")
        neg_esp = neg_art.groupby("especie", as_index=False).agg(negociado=("negociado", "sum"))
        neg_esp["especie"] = clean_text_series(neg_esp["especie"])

    # ========= 5) merge =========
    out = esp.merge(comp_esp, on="especie", how="left").merge(neg_esp, on="especie", how="left")
    out["comprado"] = pd.to_numeric(out.get("comprado"), errors="coerce").fillna(0)
    out["negociado"] = pd.to_numeric(out.get("negociado"), errors="coerce").fillna(0)

    # ========= 6) pareto 80/20 por utilidad =========
    out = out[out["utilidad"] > 0].copy()
    out = out.sort_values("utilidad", ascending=False).reset_index(drop=True)

    total_util = float(out["utilidad"].sum())
    if total_util > 0:
        out["util_acum"] = out["utilidad"].cumsum()
        out["pct_acum"] = out["util_acum"] / total_util
        out["top_80"] = out["pct_acum"] <= 0.80
        idx_cruce = out[out["pct_acum"] > 0.80].index.min()
        if pd.notna(idx_cruce):
            out.loc[idx_cruce, "top_80"] = True
    else:
        out["top_80"] = False

    top80_count = int(out["top_80"].sum())
    top80_util = float(out.loc[out["top_80"], "utilidad"].sum()) if total_util > 0 else 0.0
    top80_pct = (top80_util / total_util) if total_util > 0 else 0.0

    c1, c2, c3 = st.columns([2, 2, 6])
    c1.metric("Especies TOP", f"{top80_count}")
    c2.metric("Utilidad cubierta", f"{top80_pct*100:,.2f}%")
    c3.caption("Verde = especies que acumulan ≥80% REAL de la utilidad neta (-7%).")

    st.divider()
    st.subheader("Especies")

    if out.empty:
        st.info("No hay especies con utilidad positiva en este rango/filtro.")
        st.stop()

    cols = st.columns(5)
    for i, row in out.iterrows():
        with cols[i % 5]:
            nombre = html.escape(str(row["especie"]))
            cls = "hcard top80" if bool(row.get("top_80", False)) else "hcard"
            card = f"""
              <div class="{cls}">
                <div class="hcard-title">{nombre}</div>
                <div class="hcard-line">Vendido: {fmt_money0(row['vendido'])}</div>
                <div class="hcard-line">Utilidad: {fmt_money0(row['utilidad'])}</div>
                <div class="hcard-line">Comprado: {fmt_money0(row['comprado'])}</div>
                <div class="hcard-line">Negociado: {float(row['negociado']):,.0f}</div>
              </div>
            """
            st.markdown(card, unsafe_allow_html=True)

    st.stop()
