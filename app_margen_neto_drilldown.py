# =========================
# EXPLORADOR POR ESPECIE + 80/20 (PARETO CORRECTO)
# =========================
if "especie_click" not in st.session_state:
    st.session_state.especie_click = None

st.subheader("Explorador por ESPECIE (Pareto 80/20 por UTILIDAD)")

# -------- AGRUPACIÓN BASE (SIN REDONDEAR) --------
esp = (
    df_f.groupby("especie", as_index=False)
    .agg(
        utilidad=("utilidad_neta", "sum"),
        venta=("venta_sin_iva", "sum"),
        piezas=("cantidad", "sum"),
    )
)

# margen
esp["margen_pct"] = esp["utilidad"] / esp["venta"]

# 👉 SOLO UTILIDAD POSITIVA PARA PARETO
esp = esp[esp["utilidad"] > 0].copy()

# orden correcto
esp = esp.sort_values("utilidad", ascending=False).reset_index(drop=True)

# -------- PARETO REAL --------
total_util = esp["utilidad"].sum()

if total_util > 0:
    esp["utilidad_acum"] = esp["utilidad"].cumsum()
    esp["pct_acum"] = esp["utilidad_acum"] / total_util

    # top 80% real (incluye la especie que cruza)
    esp["top_80"] = esp["pct_acum"] <= 0.80
    idx_cruce = esp[esp["pct_acum"] > 0.80].index.min()
    if pd.notna(idx_cruce):
        esp.loc[idx_cruce, "top_80"] = True
else:
    esp["utilidad_acum"] = 0
    esp["pct_acum"] = 0
    esp["top_80"] = False

# -------- KPIs PARETO --------
top80_util = esp.loc[esp["top_80"], "utilidad"].sum()
top80_pct = top80_util / total_util if total_util else 0

c1, c2, c3 = st.columns([2, 2, 6])
c1.metric("Especies TOP", int(esp["top_80"].sum()))
c2.metric("Utilidad cubierta", f"{top80_pct*100:,.2f}%")
c3.caption("Verde = especies que construyen ≥80% REAL de la utilidad neta")

# -------- FORMATO SOLO VISUAL --------
esp["venta"] = esp["venta"].round(2)
esp["utilidad"] = esp["utilidad"].round(2)
esp["piezas"] = esp["piezas"].round(0).astype(int)

# -------- CSS TARJETAS --------
st.markdown("""
<style>
.cardwrap button {
    width:100%;
    border-radius:14px;
    padding:18px 14px;
    border:1px solid rgba(255,255,255,0.12);
    background:rgba(255,255,255,0.04);
    color:white;
    white-space:pre-line;
    line-height:1.25;
}
.cardwrap button:hover {
    transform: translateY(-1px);
}
.top80wrap button {
    background: rgba(46,204,113,0.28);
    border:1px solid rgba(46,204,113,0.9);
}
</style>
""", unsafe_allow_html=True)

# -------- TARJETAS --------
cols = st.columns(5)
for i, row in esp.iterrows():
    with cols[i % 5]:
        label = (
            f"{row['especie']}\n\n"
            f"Margen: {row['margen_pct']*100:,.2f}%\n"
            f"Utilidad: ${row['utilidad']:,.0f}"
        )

        cls = "cardwrap top80wrap" if row["top_80"] else "cardwrap"
        st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
        if st.button(label, key=f"esp_{i}", use_container_width=True):
            st.session_state.especie_click = row["especie"]
        st.markdown("</div>", unsafe_allow_html=True)

# -------- LIMPIAR --------
if st.button("Limpiar selección", use_container_width=True):
    st.session_state.especie_click = None
