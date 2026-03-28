import streamlit as st
import pandas as pd
from urllib.parse import quote

# =========================
# CONFIG (DEBE IR PRIMERO)
# =========================
st.set_page_config(page_title="Panel Comercial SERUR", layout="wide")

# =========================
# LOGIN SIMPLE (PASSWORD)
# =========================
def check_password():
    PASSWORD = "Serur2026*"

    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False

    if st.session_state.auth_ok:
        return True

    st.title("Acceso al Panel Comercial")
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
SHEET_NAME = "Hoja1"

SHEET_ID_NEGOCIADO = SHEET_ID
SHEET_NAME_NEGOCIADO = "FALTANTE"

# =========================
# HELPERS
# =========================
def to_num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0)


def ensure_col(df_, col, default=""):
    if col not in df_.columns:
        df_[col] = default
    return df_


def safe_unique(df_, col):
    if col not in df_.columns:
        return []
    vals = df_[col].dropna().astype(str).str.strip()
    vals = vals[vals != ""].unique().tolist()
    return sorted(vals)


def clean_cols(df_):
    df_.columns = df_.columns.astype(str).str.strip().str.lower()
    return df_


def clean_text_series(s):
    return s.fillna("").astype(str).str.strip()


def nunique_clean(s):
    x = clean_text_series(s).replace("", pd.NA).dropna()
    return int(x.nunique())


def gsheet_csv(sheet_id, sheet_name):
    sheet = quote(sheet_name)
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet}"


def first_nonempty(series):
    x = series.dropna().astype(str).str.strip()
    x = x[x != ""]
    return x.iloc[0] if len(x) else ""


def last_nonempty(series):
    x = series.dropna().astype(str).str.strip()
    x = x[x != ""]
    return x.iloc[-1] if len(x) else ""


def fmt_money0(x):
    return f"${float(x):,.0f}"


def fmt_money2(x):
    return f"${float(x):,.2f}"


def pick_code_col(df_, candidates):
    for c in candidates:
        if c in df_.columns:
            s = clean_text_series(df_[c])
            if not s.eq("").all():
                return c
    for c in candidates:
        if c in df_.columns:
            return c
    return ""


def format_date(v):
    if pd.isna(v):
        return ""
    return pd.to_datetime(v).strftime("%d/%m/%Y")


def topbar():
    c1, c2, _ = st.columns([2, 2, 8])
    if c1.button("⬅️ Regresar al menú", use_container_width=True, key=f"back_{st.session_state.view}"):
        go("menu")
    if c2.button("Actualizar ahora", use_container_width=True, key=f"refresh_{st.session_state.view}"):
        st.cache_data.clear()
        st.rerun()


def apply_text_filters(df_, vendedor_sel, especie_sel, categoria_sel):
    out = df_.copy()

    if vendedor_sel != "(Todos)" and "vendedor" in out.columns:
        out = out[out["vendedor"] == vendedor_sel]
    if especie_sel != "(Todas)" and "especie" in out.columns:
        out = out[out["especie"] == especie_sel]
    if categoria_sel != "(Todas)" and "categoria" in out.columns:
        out = out[out["categoria"] == categoria_sel]

    return out


def get_sales_filters(df_source, prefix, title_sidebar):
    df_fechas = df_source.dropna(subset=["fecha"])
    if df_fechas.empty:
        st.error("No hay fechas válidas en VENTAS (columna 'fecha').")
        st.stop()

    min_d = df_fechas["fecha"].min().date()
    max_d = df_fechas["fecha"].max().date()

    f1, f2, _ = st.columns([2, 2, 8])
    d_ini = f1.date_input("Desde", min_d, min_d, max_d, key=f"{prefix}_d_ini")
    d_fin = f2.date_input("Hasta", max_d, min_d, max_d, key=f"{prefix}_d_fin")

    with st.sidebar:
        st.subheader(title_sidebar)
        vendedores = safe_unique(df_source, "vendedor")
        vendedor_sel = st.selectbox("Vendedor", ["(Todos)"] + vendedores, key=f"{prefix}_ven")

        especies = safe_unique(df_source, "especie")
        especie_sel = st.selectbox("Especie", ["(Todas)"] + especies, key=f"{prefix}_esp")

        categorias = safe_unique(df_source, "categoria")
        categoria_sel = st.selectbox("Categoría", ["(Todas)"] + categorias, key=f"{prefix}_cat")

    df_base = apply_text_filters(df_source, vendedor_sel, especie_sel, categoria_sel)
    df_base = df_base[df_base["fecha"].notna()].copy()

    df_period = df_base[
        (df_base["fecha"].dt.date >= d_ini) &
        (df_base["fecha"].dt.date <= d_fin)
    ].copy()

    return df_base, df_period, d_ini, d_fin


def get_hist_until(df_base, d_fin):
    return df_base[df_base["fecha"].dt.date <= d_fin].copy()


def build_catalog_map(df_source):
    code_col = pick_code_col(df_source, ["clave", "cve_art"])
    if not code_col:
        return pd.DataFrame(columns=["codigo", "especie", "categoria", "articulo"])

    base = df_source.copy()
    base = base[clean_text_series(base[code_col]) != ""].copy()

    if base.empty:
        return pd.DataFrame(columns=["codigo", "especie", "categoria", "articulo"])

    out = (
        base.groupby(code_col, as_index=False)
        .agg(
            especie=("especie", first_nonempty),
            categoria=("categoria", first_nonempty),
            articulo=("articulo", first_nonempty),
        )
        .rename(columns={code_col: "codigo"})
    )

    out["codigo"] = clean_text_series(out["codigo"])
    out["especie"] = clean_text_series(out["especie"])
    out["categoria"] = clean_text_series(out["categoria"])
    out["articulo"] = clean_text_series(out["articulo"])
    return out


def build_opportunity(df_negociado, catalog_map):
    neg_code_col = pick_code_col(df_negociado, ["cve_art", "clave"])
    if not neg_code_col:
        return pd.DataFrame(columns=["codigo", "especie", "categoria", "articulo", "negociado"])

    opp = (
        df_negociado[clean_text_series(df_negociado[neg_code_col]) != ""]
        .groupby(neg_code_col, as_index=False)
        .agg(negociado=("negociado", "sum"))
        .rename(columns={neg_code_col: "codigo"})
    )

    opp["codigo"] = clean_text_series(opp["codigo"])
    opp = opp.merge(catalog_map, on="codigo", how="left")

    for col in ["especie", "categoria", "articulo"]:
        opp = ensure_col(opp, col, "")
        opp[col] = clean_text_series(opp[col])

    opp["negociado"] = to_num(opp["negociado"])
    return opp


def metric_row(items):
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        col.metric(label, value)


def show_table(title, df_show):
    st.subheader(title)
    if df_show.empty:
        st.info("Sin datos para mostrar.")
    else:
        st.dataframe(df_show, use_container_width=True, hide_index=True)


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
    df = ensure_col(df, "clave", "")
    df = ensure_col(df, "cve_art", "")

    df["fecha"] = pd.to_datetime(df.get("fecha"), errors="coerce", dayfirst=True)
    df["cantidad"] = to_num(df.get("cantidad"))
    df["importe"] = to_num(df.get("importe"))
    df["cos_rep"] = to_num(df.get("cos_rep"))

    df["venta_sin_iva"] = df["cantidad"] * df["importe"]

    for col in ["especie", "categoria", "articulo", "vendedor", "cliente", "clave", "cve_art"]:
        df[col] = clean_text_series(df[col])

    return df


@st.cache_data(ttl=120)
def load_negociado():
    url = gsheet_csv(SHEET_ID_NEGOCIADO, SHEET_NAME_NEGOCIADO)
    n = pd.read_csv(url)
    n = clean_cols(n)

    n = ensure_col(n, "cve_art", "")
    n = ensure_col(n, "clave", "")
    n = ensure_col(n, "(expression)", 0)

    n["cve_art"] = clean_text_series(n["cve_art"])
    n["clave"] = clean_text_series(n["clave"])
    n["negociado"] = to_num(n["(expression)"])

    return n[["cve_art", "clave", "negociado"]].copy()


df = load_ventas()
dfn = load_negociado()
catalog_map = build_catalog_map(df)
opp_full = build_opportunity(dfn, catalog_map)

# =========================
# NAVEGACIÓN
# =========================
if "view" not in st.session_state:
    st.session_state.view = "menu"


def go(view_name):
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
        padding:20px 18px !important;
        border:1px solid rgba(255,255,255,0.14) !important;
        background: rgba(255,255,255,0.05) !important;
        color: white !important;
        font-size:17px !important;
      }
      .menuwrap button:hover{
        border-color: rgba(255,255,255,0.24) !important;
        transform: translateY(-1px) !important;
      }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# MENU
# =========================
if st.session_state.view == "menu":
    st.title("Panel Comercial SERUR")
    st.caption("Gerente de ventas")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown('<div class="menuwrap">', unsafe_allow_html=True)
        if st.button("VENTAS COMERCIALES"):
            go("ventas_comerciales")
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="menuwrap">', unsafe_allow_html=True)
        if st.button("CLIENTES Y CARTERA"):
            go("clientes_cartera")
        st.markdown("</div>", unsafe_allow_html=True)

    with c3:
        st.markdown('<div class="menuwrap">', unsafe_allow_html=True)
        if st.button("PORTAFOLIO COMERCIAL"):
            go("portafolio_comercial")
        st.markdown("</div>", unsafe_allow_html=True)

    with c4:
        st.markdown('<div class="menuwrap">', unsafe_allow_html=True)
        if st.button("OPORTUNIDAD PERDIDA"):
            go("oportunidad_perdida")
        st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    st.button("Actualizar ahora", on_click=st.cache_data.clear)
    st.caption("Dashboard protegido con contraseña")
    st.stop()

# =========================
# VISTA: VENTAS COMERCIALES
# =========================
if st.session_state.view == "ventas_comerciales":
    topbar()
    st.caption("Basado en información programa NEXT")
    st.title("Ventas comerciales")

    df_base, df_period, d_ini, d_fin = get_sales_filters(df, "vc", "Filtros | ventas comerciales")
    df_hist = get_hist_until(df_base, d_fin)
    sku_col = pick_code_col(df_period, ["clave", "cve_art"]) or pick_code_col(df_base, ["clave", "cve_art"])

    venta = float(df_period["venta_sin_iva"].sum())
    piezas = int(round(df_period["cantidad"].sum()))
    clientes_activos = nunique_clean(df_period["cliente"])
    vendedores_activos = nunique_clean(df_period["vendedor"])
    skus_movidos = nunique_clean(df_period[sku_col]) if sku_col else 0
    especies_movidas = nunique_clean(df_period["especie"])
    categorias_movidas = nunique_clean(df_period["categoria"])

    hist_clientes = nunique_clean(df_hist["cliente"])
    cobertura_cartera = (clientes_activos / hist_clientes) if hist_clientes else 0

    metric_row([
        ("Venta", fmt_money2(venta)),
        ("Piezas", f"{piezas:,}"),
        ("Clientes", f"{clientes_activos:,}"),
        ("Vendedores", f"{vendedores_activos:,}"),
        ("SKUs movidos", f"{skus_movidos:,}"),
    ])
    metric_row([
        ("Especies", f"{especies_movidas:,}"),
        ("Categorías", f"{categorias_movidas:,}"),
        ("Cobertura comercial", f"{cobertura_cartera*100:,.1f}%"),
    ])

    st.divider()

    if df_period.empty:
        st.info("No hay ventas en el rango seleccionado.")
        st.stop()

    vend_period = df_period[clean_text_series(df_period["vendedor"]) != ""].copy()
    vend_hist = df_hist[clean_text_series(df_hist["vendedor"]) != ""].copy()

    if not vend_period.empty:
        vend = (
            vend_period.groupby("vendedor", as_index=False)
            .agg(
                venta=("venta_sin_iva", "sum"),
                piezas=("cantidad", "sum"),
                clientes=("cliente", nunique_clean),
                especies=("especie", nunique_clean),
                categorias=("categoria", nunique_clean),
            )
        )

        if sku_col:
            vend_skus = (
                vend_period.groupby("vendedor")[sku_col]
                .apply(nunique_clean)
                .reset_index(name="skus_movidos")
            )
            vend = vend.merge(vend_skus, on="vendedor", how="left")
        else:
            vend["skus_movidos"] = 0

        cartera_hist = (
            vend_hist.groupby("vendedor", as_index=False)
            .agg(cartera_historica=("cliente", nunique_clean))
        )

        vend = vend.merge(cartera_hist, on="vendedor", how="left")
        vend["cartera_historica"] = to_num(vend["cartera_historica"])
        vend["cobertura_cartera_%"] = (
            (vend["clientes"] / vend["cartera_historica"].replace(0, pd.NA)) * 100
        ).fillna(0)

        mejor_venta = float(vend["venta"].max()) if not vend.empty else 0
        vend["brecha_vs_mejor"] = mejor_venta - vend["venta"]
        vend = vend.sort_values(["venta", "clientes"], ascending=[False, False]).reset_index(drop=True)

        vend_show = vend.copy()
        vend_show["venta"] = vend_show["venta"].map(fmt_money2)
        vend_show["piezas"] = vend_show["piezas"].round(0).astype(int)
        vend_show["clientes"] = vend_show["clientes"].astype(int)
        vend_show["skus_movidos"] = vend_show["skus_movidos"].astype(int)
        vend_show["especies"] = vend_show["especies"].astype(int)
        vend_show["categorias"] = vend_show["categorias"].astype(int)
        vend_show["cartera_historica"] = vend_show["cartera_historica"].round(0).astype(int)
        vend_show["cobertura_cartera_%"] = vend_show["cobertura_cartera_%"].map(lambda x: f"{x:,.1f}%")
        vend_show["brecha_vs_mejor"] = vend_show["brecha_vs_mejor"].map(fmt_money2)

        show_table("Comparativo entre vendedores", vend_show)

    c1, c2, c3 = st.columns(3)

    with c1:
        if sku_col:
            top_skus = (
                df_period.groupby(sku_col, as_index=False)
                .agg(
                    articulo=("articulo", first_nonempty),
                    especie=("especie", first_nonempty),
                    categoria=("categoria", first_nonempty),
                    piezas=("cantidad", "sum"),
                    venta=("venta_sin_iva", "sum"),
                    clientes=("cliente", nunique_clean),
                )
                .rename(columns={sku_col: "sku"})
                .sort_values(["venta", "piezas"], ascending=[False, False])
                .head(15)
            )
            top_skus["piezas"] = top_skus["piezas"].round(0).astype(int)
            top_skus["venta"] = top_skus["venta"].map(fmt_money2)
            top_skus["clientes"] = top_skus["clientes"].astype(int)
            show_table("Top SKUs", top_skus)
        else:
            st.subheader("Top SKUs")
            st.info("No existe código usable en ventas para armar el ranking de SKUs.")

    with c2:
        top_clientes = (
            df_period[clean_text_series(df_period["cliente"]) != ""]
            .groupby("cliente", as_index=False)
            .agg(
                venta=("venta_sin_iva", "sum"),
                piezas=("cantidad", "sum"),
                especies=("especie", nunique_clean),
            )
            .sort_values(["venta", "piezas"], ascending=[False, False])
            .head(15)
        )
        top_clientes["venta"] = top_clientes["venta"].map(fmt_money2)
        top_clientes["piezas"] = top_clientes["piezas"].round(0).astype(int)
        top_clientes["especies"] = top_clientes["especies"].astype(int)
        show_table("Top clientes", top_clientes)

    with c3:
        top_especies = (
            df_period[clean_text_series(df_period["especie"]) != ""]
            .groupby("especie", as_index=False)
            .agg(
                venta=("venta_sin_iva", "sum"),
                piezas=("cantidad", "sum"),
                clientes=("cliente", nunique_clean),
            )
            .sort_values(["venta", "piezas"], ascending=[False, False])
            .head(15)
        )
        top_especies["venta"] = top_especies["venta"].map(fmt_money2)
        top_especies["piezas"] = top_especies["piezas"].round(0).astype(int)
        top_especies["clientes"] = top_especies["clientes"].astype(int)
        show_table("Top especies", top_especies)

    st.stop()

# =========================
# VISTA: CLIENTES Y CARTERA
# =========================
if st.session_state.view == "clientes_cartera":
    topbar()
    st.caption("Basado en información programa NEXT")
    st.title("Clientes y cartera")

    df_base, df_period, d_ini, d_fin = get_sales_filters(df, "cc", "Filtros | clientes y cartera")
    df_hist = get_hist_until(df_base, d_fin)

    period_clientes = df_period[clean_text_series(df_period["cliente"]) != ""].copy()
    hist_clientes = df_hist[clean_text_series(df_hist["cliente"]) != ""].copy()

    clientes_activos = nunique_clean(period_clientes["cliente"])
    cartera_historica = nunique_clean(hist_clientes["cliente"])
    cobertura = (clientes_activos / cartera_historica) if cartera_historica else 0

    if hist_clientes.empty:
        st.info("No hay clientes con historial en el filtro seleccionado.")
        st.stop()

    primeras_compras = (
        hist_clientes.groupby("cliente", as_index=False)
        .agg(primera_compra=("fecha", "min"))
    )
    nuevos = primeras_compras[
        (primeras_compras["primera_compra"].dt.date >= d_ini) &
        (primeras_compras["primera_compra"].dt.date <= d_fin)
    ].copy()

    estado = (
        hist_clientes.groupby("cliente", as_index=False)
        .agg(
            ultima_compra=("fecha", "max"),
            venta_historica=("venta_sin_iva", "sum"),
            piezas_historicas=("cantidad", "sum"),
            ultimo_vendedor=("vendedor", last_nonempty),
        )
    )

    activos_set = set(clean_text_series(period_clientes["cliente"]).replace("", pd.NA).dropna().tolist())
    estado["dias_sin_compra"] = (
        pd.Timestamp(d_fin) - pd.to_datetime(estado["ultima_compra"])
    ).dt.days

    estado["estado"] = "Activo"
    estado.loc[~estado["cliente"].isin(activos_set) & estado["dias_sin_compra"].between(31, 60), "estado"] = "En riesgo"
    estado.loc[~estado["cliente"].isin(activos_set) & (estado["dias_sin_compra"] > 60), "estado"] = "Dormido"

    en_riesgo = estado[estado["estado"] == "En riesgo"].copy().sort_values("dias_sin_compra", ascending=False)
    dormidos = estado[estado["estado"] == "Dormido"].copy().sort_values("dias_sin_compra", ascending=False)

    metric_row([
        ("Clientes activos", f"{clientes_activos:,}"),
        ("Cartera histórica", f"{cartera_historica:,}"),
        ("Cobertura cartera", f"{cobertura*100:,.1f}%"),
        ("Clientes nuevos", f"{len(nuevos):,}"),
        ("En riesgo", f"{len(en_riesgo):,}"),
        ("Dormidos", f"{len(dormidos):,}"),
    ])

    st.divider()

    cartera_v_hist = (
        hist_clientes[clean_text_series(hist_clientes["vendedor"]) != ""]
        .groupby("vendedor", as_index=False)
        .agg(cartera_historica=("cliente", nunique_clean))
    )

    cartera_v_act = (
        period_clientes[clean_text_series(period_clientes["vendedor"]) != ""]
        .groupby("vendedor", as_index=False)
        .agg(
            clientes_activos=("cliente", nunique_clean),
            venta=("venta_sin_iva", "sum"),
            piezas=("cantidad", "sum"),
        )
    )

    cartera_v = cartera_v_hist.merge(cartera_v_act, on="vendedor", how="left")
    cartera_v["clientes_activos"] = to_num(cartera_v["clientes_activos"])
    cartera_v["venta"] = to_num(cartera_v["venta"])
    cartera_v["piezas"] = to_num(cartera_v["piezas"])
    cartera_v["cobertura_%"] = (
        (cartera_v["clientes_activos"] / cartera_v["cartera_historica"].replace(0, pd.NA)) * 100
    ).fillna(0)

    cartera_v = cartera_v.sort_values(["clientes_activos", "venta"], ascending=[False, False]).reset_index(drop=True)
    cartera_v_show = cartera_v.copy()
    cartera_v_show["cartera_historica"] = cartera_v_show["cartera_historica"].astype(int)
    cartera_v_show["clientes_activos"] = cartera_v_show["clientes_activos"].round(0).astype(int)
    cartera_v_show["venta"] = cartera_v_show["venta"].map(fmt_money2)
    cartera_v_show["piezas"] = cartera_v_show["piezas"].round(0).astype(int)
    cartera_v_show["cobertura_%"] = cartera_v_show["cobertura_%"].map(lambda x: f"{x:,.1f}%")
    show_table("Cobertura comercial por vendedor", cartera_v_show)

    c1, c2, c3 = st.columns(3)

    with c1:
        nuevos_show = nuevos.sort_values("primera_compra", ascending=False).head(20).copy()
        nuevos_show["primera_compra"] = nuevos_show["primera_compra"].map(format_date)
        show_table("Clientes nuevos", nuevos_show)

    with c2:
        riesgo_show = en_riesgo[["cliente", "ultimo_vendedor", "ultima_compra", "dias_sin_compra", "venta_historica"]].head(20).copy()
        if not riesgo_show.empty:
            riesgo_show["ultima_compra"] = riesgo_show["ultima_compra"].map(format_date)
            riesgo_show["dias_sin_compra"] = riesgo_show["dias_sin_compra"].astype(int)
            riesgo_show["venta_historica"] = riesgo_show["venta_historica"].map(fmt_money2)
        show_table("Clientes en riesgo", riesgo_show)

    with c3:
        dormidos_show = dormidos[["cliente", "ultimo_vendedor", "ultima_compra", "dias_sin_compra", "venta_historica"]].head(20).copy()
        if not dormidos_show.empty:
            dormidos_show["ultima_compra"] = dormidos_show["ultima_compra"].map(format_date)
            dormidos_show["dias_sin_compra"] = dormidos_show["dias_sin_compra"].astype(int)
            dormidos_show["venta_historica"] = dormidos_show["venta_historica"].map(fmt_money2)
        show_table("Clientes dormidos", dormidos_show)

    st.stop()

# =========================
# VISTA: PORTAFOLIO COMERCIAL
# =========================
if st.session_state.view == "portafolio_comercial":
    topbar()
    st.caption("Basado en información programa NEXT")
    st.title("Portafolio comercial")

    df_base, df_period, d_ini, d_fin = get_sales_filters(df, "pc", "Filtros | portafolio comercial")
    df_hist = get_hist_until(df_base, d_fin)
    sku_col = pick_code_col(df_period, ["clave", "cve_art"]) or pick_code_col(df_hist, ["clave", "cve_art"])

    if df_period.empty:
        st.info("No hay ventas en el rango seleccionado.")
        st.stop()

    skus_periodo = nunique_clean(df_period[sku_col]) if sku_col else 0
    especies_periodo = nunique_clean(df_period["especie"])
    categorias_periodo = nunique_clean(df_period["categoria"])
    clientes_periodo = nunique_clean(df_period["cliente"])

    skus_hist = nunique_clean(df_hist[sku_col]) if sku_col else 0
    cobertura_portafolio = (skus_periodo / skus_hist) if skus_hist else 0

    metric_row([
        ("SKUs movidos", f"{skus_periodo:,}"),
        ("Especies movidas", f"{especies_periodo:,}"),
        ("Categorías movidas", f"{categorias_periodo:,}"),
        ("Clientes impactados", f"{clientes_periodo:,}"),
        ("Cobertura portafolio", f"{cobertura_portafolio*100:,.1f}%"),
    ])

    st.divider()

    vend_port = df_period[clean_text_series(df_period["vendedor"]) != ""].copy()
    if not vend_port.empty:
        port = (
            vend_port.groupby("vendedor", as_index=False)
            .agg(
                venta=("venta_sin_iva", "sum"),
                piezas=("cantidad", "sum"),
                clientes=("cliente", nunique_clean),
                especies=("especie", nunique_clean),
                categorias=("categoria", nunique_clean),
            )
        )

        if sku_col:
            skus_v = (
                vend_port.groupby("vendedor")[sku_col]
                .apply(nunique_clean)
                .reset_index(name="skus_movidos")
            )
            port = port.merge(skus_v, on="vendedor", how="left")
        else:
            port["skus_movidos"] = 0

        mejor_vendedor_venta = float(port["venta"].max()) if not port.empty else 0
        port["brecha_vs_mejor"] = mejor_vendedor_venta - port["venta"]
        port = port.sort_values(["skus_movidos", "venta"], ascending=[False, False]).reset_index(drop=True)

        port_show = port.copy()
        port_show["venta"] = port_show["venta"].map(fmt_money2)
        port_show["piezas"] = port_show["piezas"].round(0).astype(int)
        port_show["clientes"] = port_show["clientes"].astype(int)
        port_show["especies"] = port_show["especies"].astype(int)
        port_show["categorias"] = port_show["categorias"].astype(int)
        port_show["skus_movidos"] = port_show["skus_movidos"].astype(int)
        port_show["brecha_vs_mejor"] = port_show["brecha_vs_mejor"].map(fmt_money2)
        show_table("Portafolio por vendedor", port_show)

    c1, c2, c3 = st.columns(3)

    with c1:
        if sku_col:
            top_port_skus = (
                df_period.groupby(sku_col, as_index=False)
                .agg(
                    articulo=("articulo", first_nonempty),
                    especie=("especie", first_nonempty),
                    categoria=("categoria", first_nonempty),
                    piezas=("cantidad", "sum"),
                    clientes=("cliente", nunique_clean),
                    venta=("venta_sin_iva", "sum"),
                )
                .rename(columns={sku_col: "sku"})
                .sort_values(["clientes", "venta", "piezas"], ascending=[False, False, False])
                .head(20)
            )
            top_port_skus["piezas"] = top_port_skus["piezas"].round(0).astype(int)
            top_port_skus["clientes"] = top_port_skus["clientes"].astype(int)
            top_port_skus["venta"] = top_port_skus["venta"].map(fmt_money2)
            show_table("Top SKUs del portafolio", top_port_skus)
        else:
            st.subheader("Top SKUs del portafolio")
            st.info("No existe código usable en ventas para armar el portafolio por SKU.")

    with c2:
        top_categorias = (
            df_period[clean_text_series(df_period["categoria"]) != ""]
            .groupby("categoria", as_index=False)
            .agg(
                venta=("venta_sin_iva", "sum"),
                piezas=("cantidad", "sum"),
                clientes=("cliente", nunique_clean),
                especies=("especie", nunique_clean),
            )
            .sort_values(["venta", "clientes"], ascending=[False, False])
            .head(20)
        )
        top_categorias["venta"] = top_categorias["venta"].map(fmt_money2)
        top_categorias["piezas"] = top_categorias["piezas"].round(0).astype(int)
        top_categorias["clientes"] = top_categorias["clientes"].astype(int)
        top_categorias["especies"] = top_categorias["especies"].astype(int)
        show_table("Top categorías", top_categorias)

    with c3:
        top_especies_port = (
            df_period[clean_text_series(df_period["especie"]) != ""]
            .groupby("especie", as_index=False)
            .agg(
                venta=("venta_sin_iva", "sum"),
                piezas=("cantidad", "sum"),
                clientes=("cliente", nunique_clean),
                categorias=("categoria", nunique_clean),
            )
            .sort_values(["venta", "clientes"], ascending=[False, False])
            .head(20)
        )
        top_especies_port["venta"] = top_especies_port["venta"].map(fmt_money2)
        top_especies_port["piezas"] = top_especies_port["piezas"].round(0).astype(int)
        top_especies_port["clientes"] = top_especies_port["clientes"].astype(int)
        top_especies_port["categorias"] = top_especies_port["categorias"].astype(int)
        show_table("Top especies del portafolio", top_especies_port)

    st.stop()

# =========================
# VISTA: OPORTUNIDAD PERDIDA
# =========================
if st.session_state.view == "oportunidad_perdida":
    topbar()
    st.caption("Basado en información programa NEXT")
    st.title("Oportunidad perdida")
    st.info("Esta vista usa FALTANTE. Hoy esa fuente solo trae código y negociado; no trae fecha, cliente ni vendedor.")

    opp = opp_full.copy()

    with st.sidebar:
        st.subheader("Filtros | oportunidad perdida")
        especies_opp = safe_unique(opp, "especie")
        especie_sel = st.selectbox("Especie", ["(Todas)"] + especies_opp, key="op_esp")
        categorias_opp = safe_unique(opp, "categoria")
        categoria_sel = st.selectbox("Categoría", ["(Todas)"] + categorias_opp, key="op_cat")

    if especie_sel != "(Todas)":
        opp = opp[opp["especie"] == especie_sel]
    if categoria_sel != "(Todas)":
        opp = opp[opp["categoria"] == categoria_sel]

    total_opp = float(opp["negociado"].sum()) if not opp.empty else 0
    skus_opp = nunique_clean(opp["codigo"]) if "codigo" in opp.columns else 0
    especies_opp_n = nunique_clean(opp["especie"]) if "especie" in opp.columns else 0
    categorias_opp_n = nunique_clean(opp["categoria"]) if "categoria" in opp.columns else 0

    metric_row([
        ("Negociado / faltante", fmt_money2(total_opp)),
        ("SKUs con oportunidad", f"{skus_opp:,}"),
        ("Especies", f"{especies_opp_n:,}"),
        ("Categorías", f"{categorias_opp_n:,}"),
    ])

    st.divider()

    if opp.empty:
        st.info("No hay oportunidad perdida para el filtro seleccionado.")
        st.stop()

    c1, c2, c3 = st.columns(3)

    with c1:
        top_opp_skus = (
            opp.groupby("codigo", as_index=False)
            .agg(
                articulo=("articulo", first_nonempty),
                especie=("especie", first_nonempty),
                categoria=("categoria", first_nonempty),
                negociado=("negociado", "sum"),
            )
            .rename(columns={"codigo": "sku"})
            .sort_values("negociado", ascending=False)
            .head(20)
        )
        top_opp_skus["negociado"] = top_opp_skus["negociado"].map(fmt_money2)
        show_table("Top SKUs con oportunidad", top_opp_skus)

    with c2:
        top_opp_especies = (
            opp[clean_text_series(opp["especie"]) != ""]
            .groupby("especie", as_index=False)
            .agg(
                negociado=("negociado", "sum"),
                skus=("codigo", nunique_clean),
            )
            .sort_values("negociado", ascending=False)
            .head(20)
        )
        top_opp_especies["negociado"] = top_opp_especies["negociado"].map(fmt_money2)
        top_opp_especies["skus"] = top_opp_especies["skus"].astype(int)
        show_table("Top especies con oportunidad", top_opp_especies)

    with c3:
        top_opp_categorias = (
            opp[clean_text_series(opp["categoria"]) != ""]
            .groupby("categoria", as_index=False)
            .agg(
                negociado=("negociado", "sum"),
                skus=("codigo", nunique_clean),
            )
            .sort_values("negociado", ascending=False)
            .head(20)
        )
        top_opp_categorias["negociado"] = top_opp_categorias["negociado"].map(fmt_money2)
        top_opp_categorias["skus"] = top_opp_categorias["skus"].astype(int)
        show_table("Top categorías con oportunidad", top_opp_categorias)

    st.stop()
