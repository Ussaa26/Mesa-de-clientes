"""
=============================================================================
 MESA DE CLIENTES — ITAÚ COLOMBIA
 Dashboard de priorización diaria de clientes para traders
=============================================================================
Layout basado en el mockup:
  - Topbar compacta con selector de cartera
  - Métricas en franja superior
  - Columna izquierda: lista de priorización con scroll
  - Columna derecha: tabs (Producto más usado / Top clientes)
  - Sección inferior colapsada: buscador + detalle de operaciones
=============================================================================
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from data_loader import (
    cargar_operaciones,
    cargar_clientes,
    cargar_ciiu,
    cruzar_bases,
    obtener_lista_traders,
    filtrar_por_trader,
)
from priorizacion import (
    generar_priorizacion,
    calcular_metricas_por_cliente,
    calcular_recomendacion_oferta,
    texto_sugerencia_oferta,
    obtener_sector_economico,
    ranking_clientes_por_moneda,
    ranking_clientes_por_producto,
)


# =============================================================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
# =============================================================================

st.set_page_config(
    page_title="Mesa de Clientes – Itaú",
    layout="wide",
    initial_sidebar_state="collapsed",
)

COLOR_NARANJA       = "#FF6900"
COLOR_NARANJA_CLARO = "#FFB266"
COLOR_GRIS          = "#8A8A8A"
COLOR_GRIS_CLARO    = "#F0F0F0"

st.markdown(f"""
<style>
/* ── Reset y tipografía ── */
html, body, [class*="css"] {{
    font-family: 'Segoe UI', sans-serif;
    background-color: #FFFFFF;
}}

/* ── Ocultar sidebar ── */
section[data-testid="stSidebar"] {{ display: none; }}

/* ── Padding superior del contenedor ──
   IMPORTANTE: se deja un margen (3rem) para que el topbar
   (incluyendo el selectbox del trader) no quede tapado por
   la barra de herramientas propia de Streamlit (Fork / GitHub / menú). */
.block-container {{
    padding-top: 3rem !important;
    padding-bottom: 1rem !important;
    max-width: 100% !important;
}}

/* ── Topbar ── */
.topbar {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 20px;
    border-bottom: 1px solid {COLOR_GRIS_CLARO};
    background: #FFFFFF;
    margin-bottom: 0;
}}
.topbar-logo {{
    font-size: 15px;
    font-weight: 700;
    color: {COLOR_NARANJA};
    white-space: nowrap;
}}
.topbar-sep {{
    color: {COLOR_GRIS};
    font-size: 13px;
}}
.topbar-app {{
    font-size: 12px;
    color: {COLOR_GRIS};
}}

/* ── Métricas ── */
div[data-testid="metric-container"] {{
    background: #FAFAFA;
    border: 1px solid #FFD9B8;
    border-radius: 8px;
    padding: 10px 14px;
}}
div[data-testid="metric-container"] [data-testid="stMetricLabel"] {{
    font-size: 11px !important;
    color: {COLOR_GRIS} !important;
}}
div[data-testid="metric-container"] [data-testid="stMetricValue"] {{
    font-size: 17px !important;
    font-weight: 600 !important;
}}

/* ── Caja de ayuda ── */
.caja-ayuda {{
    background: #FFF6EE;
    border: 1px solid #FFD9B8;
    border-radius: 6px;
    padding: 7px 11px;
    font-size: 11px;
    color: #5A5A5A;
    margin: 6px 0 10px 0;
}}

/* ── Etiqueta de sección ── */
.section-label {{
    font-size: 11px;
    font-weight: 600;
    color: {COLOR_GRIS};
    text-transform: uppercase;
    letter-spacing: .4px;
    padding: 8px 0 6px 0;
    border-bottom: 2px solid {COLOR_NARANJA};
    margin-bottom: 10px;
}}

/* ── Lista de priorización con scroll ── */
.prio-scroll {{
    overflow-y: auto;
    max-height: 520px;
    padding-right: 4px;
}}

/* ── Tarjeta de cliente ── */
.card {{
    border: 1px solid {COLOR_GRIS_CLARO};
    border-left: 4px solid {COLOR_NARANJA};
    border-radius: 8px;
    padding: 10px 12px;
    margin-bottom: 8px;
    background: #FFFFFF;
}}
.card-head {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 5px;
}}
.card-name {{
    font-size: 13px;
    font-weight: 600;
    color: #1A1A1A;
}}
.card-score {{
    font-size: 16px;
    font-weight: 700;
    color: {COLOR_NARANJA};
}}
.card-score span {{
    font-size: 11px;
    color: {COLOR_GRIS};
    font-weight: 400;
}}
.card-row {{
    display: flex;
    gap: 14px;
    flex-wrap: wrap;
    font-size: 11px;
    color: #4A4A4A;
    margin-bottom: 4px;
}}
.card-row b {{ color: #1A1A1A; }}
.card-offer {{
    background: #FFF6EE;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 11px;
    color: #1A1A1A;
    margin-top: 6px;
}}
.card-offer b {{ color: {COLOR_NARANJA}; }}

/* ── Badges ── */
.badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 10px;
    font-weight: 600;
    margin: 4px 3px 0 0;
}}
.badge-alerta      {{ background: #FFE3D1; color: #D2480C; }}
.badge-oportunidad {{ background: #FFF1E0; color: {COLOR_NARANJA}; }}
.badge-fidelidad   {{ background: #F0F0F0; color: #5A5A5A; }}
.badge-nuevo       {{ background: #FFEDD9; color: #B85400; }}
.badge-neutral     {{ background: #F0F0F0; color: #8A8A8A; }}

/* ── Ficha de cliente (buscador) ── */
.ficha-cliente {{
    border: 1px solid {COLOR_GRIS_CLARO};
    border-left: 5px solid {COLOR_NARANJA};
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 12px;
    background: #FFFFFF;
}}
.ficha-titulo {{
    font-size: 14px;
    font-weight: 700;
    color: #1A1A1A;
    margin-bottom: 10px;
    padding-bottom: 6px;
    border-bottom: 1px solid {COLOR_GRIS_CLARO};
}}
.ficha-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 10px;
    margin-bottom: 10px;
}}
.ficha-dato {{
    background: #FAFAFA;
    border-radius: 6px;
    padding: 8px 10px;
}}
.ficha-dato-etiqueta {{
    font-size: 10px;
    color: {COLOR_GRIS};
    text-transform: uppercase;
    letter-spacing: .4px;
    margin-bottom: 3px;
}}
.ficha-dato-valor {{
    font-size: 15px;
    font-weight: 700;
    color: #1A1A1A;
}}
.ficha-sector {{
    background: #FFF6EE;
    border-radius: 6px;
    padding: 7px 10px;
    margin-bottom: 10px;
    font-size: 12px;
    color: #1A1A1A;
}}
.ficha-sector b {{ color: {COLOR_NARANJA}; }}
</style>
""", unsafe_allow_html=True)

BADGE_CLASES = {
    "alerta":      "badge-alerta",
    "oportunidad": "badge-oportunidad",
    "fidelidad":   "badge-fidelidad",
    "nuevo":       "badge-nuevo",
    "neutral":     "badge-neutral",
}


# =============================================================================
# 2. CARGA DE DATOS
# =============================================================================

@st.cache_data(ttl=3600)
def cargar_datos_consolidados() -> pd.DataFrame:
    df_ops      = cargar_operaciones()
    df_clientes = cargar_clientes()
    df_ciiu     = cargar_ciiu()
    if "Fecha" in df_ops.columns:
        df_ops["Fecha"] = pd.to_datetime(
            df_ops["Fecha"], origin="1899-12-30", unit="D", errors="coerce"
        )
    return cruzar_bases(df_ops, df_clientes, df_ciiu)


try:
    df = cargar_datos_consolidados()
except Exception as e:
    st.error(f"No se pudieron cargar los datos: {e}")
    st.info("Verifica que los 3 enlaces en data_loader.py estén activos y compartidos correctamente.")
    st.stop()

COLUMNA_TRADER = "Cod_Cartera"

if COLUMNA_TRADER not in df.columns:
    st.error(f"No se encontró la columna '{COLUMNA_TRADER}' en los datos consolidados.")
    st.stop()

lista_traders = obtener_lista_traders(df, COLUMNA_TRADER)


# =============================================================================
# 3. TOPBAR — logo + selector de cartera
# =============================================================================

col_logo, col_sep, col_app, col_spacer, col_sel = st.columns([1.2, 0.15, 1.2, 4, 1.5])

with col_logo:
    st.markdown('<div class="topbar-logo" style="padding-top:6px">🟠 Itaú Colombia</div>', unsafe_allow_html=True)
with col_sep:
    st.markdown('<div class="topbar-sep" style="padding-top:8px">|</div>', unsafe_allow_html=True)
with col_app:
    st.markdown('<div class="topbar-app" style="padding-top:9px">Mesa de Clientes</div>', unsafe_allow_html=True)
with col_sel:
    trader_seleccionado = st.selectbox(
        label="Cartera",
        options=lista_traders,
        format_func=lambda t: f"Trader {t}",
        label_visibility="collapsed",
        key="trader_selector",
    )

st.markdown(
    "<hr style='margin:0 0 10px 0; border:none; border-top:1px solid #F0F0F0'>",
    unsafe_allow_html=True,
)


# =============================================================================
# 4. DATOS DEL TRADER SELECCIONADO
# =============================================================================

df_trader      = filtrar_por_trader(df, trader_seleccionado, COLUMNA_TRADER)
df_priorizacion = generar_priorizacion(df_trader)

if not df_priorizacion.empty:
    monto_total_itau   = df_priorizacion["Monto_Itau"].sum()
    oportunidad_total  = df_priorizacion["Monto_Mercado"].sum()
    cliente_top_nit    = df_priorizacion.iloc[0]["NIT"]
    cliente_top_puntaje = df_priorizacion.iloc[0]["Puntaje"]
else:
    monto_total_itau   = 0
    oportunidad_total  = 0
    cliente_top_nit    = "—"
    cliente_top_puntaje = 0


# =============================================================================
# 5. MÉTRICAS — franja superior
# =============================================================================

m1, m2, m3, m4 = st.columns(4)
m1.metric("Clientes en cartera",     df_trader["NIT"].nunique())
m2.metric("Cliente top de hoy",      f"NIT {cliente_top_nit}", f"Puntaje {cliente_top_puntaje}/100")
m3.metric("Monto generado para Itaú", f"{monto_total_itau:,.0f}")
m4.metric("Oportunidad en Mercado",   f"{oportunidad_total:,.0f}")

st.markdown(
    '<div class="caja-ayuda">'
    'ℹ️ <b>Monto Itaú</b>: lo que los clientes ya operaron CON Itaú. '
    '<b>Oportunidad</b>: lo que operaron con otros bancos — negocio capturable.'
    '</div>',
    unsafe_allow_html=True,
)


# =============================================================================
# 6. LAYOUT PRINCIPAL — columna izquierda (lista) + columna derecha (panel)
# =============================================================================

col_izq, col_der = st.columns([3, 2], gap="medium")


# ── COLUMNA IZQUIERDA — Lista de priorización ───────────────────────────────

with col_izq:
    n_clientes = df_trader["NIT"].nunique()
    n_ops      = len(df_trader)
    st.markdown(
        f'<div class="section-label">'
        f'📋 A quién llamar hoy — {n_clientes} clientes · {n_ops} operaciones'
        f'</div>',
        unsafe_allow_html=True,
    )

    if df_priorizacion.empty:
        st.info("Esta cartera no tiene clientes registrados.")
    else:
        tarjetas_html = ""
        for posicion, fila in df_priorizacion.iterrows():
            badges_html = "".join(
                f'<span class="badge {BADGE_CLASES.get(tipo, "badge-neutral")}">{texto}</span>'
                for texto, tipo in fila["Necesidades"]
            )
            texto_dias = (
                "Sin registro de fecha"
                if fila["Dias_Sin_Operar"] >= 999
                else f"{int(fila['Dias_Sin_Operar'])} días sin operar"
            )
            tarjetas_html += (
                '<div class="card">'
                  '<div class="card-head">'
                    f'<span class="card-name">#{posicion + 1} · NIT {fila["NIT"]}</span>'
                    f'<span class="card-score">{fila["Puntaje"]}<span>/100</span></span>'
                  '</div>'
                  '<div class="card-row">'
                    f'<span>💰 Itaú: <b>{fila["Monto_Itau"]:,.0f}</b></span>'
                    f'<span>🎯 Mercado: <b>{fila["Monto_Mercado"]:,.0f}</b></span>'
                    f'<span>⏱️ {texto_dias}</span>'
                  '</div>'
                  '<div class="card-row">'
                    f'<span>🏢 {fila["Sector_Economico"]}</span>'
                    f'<span>🔄 <b>{int(fila["N_Operaciones"])}</b> ops.</span>'
                  '</div>'
                  '<div class="card-offer">'
                    f'📞 <b>Qué ofrecer:</b> {fila["Sugerencia_Oferta"]}'
                  '</div>'
                  f'<div>{badges_html}</div>'
                '</div>'
            )
        st.markdown(
            f'<div class="prio-scroll">{tarjetas_html}</div>',
            unsafe_allow_html=True,
        )


# ── COLUMNA DERECHA — Tabs: Producto más usado / Top clientes ───────────────

with col_der:
    tab_producto, tab_top = st.tabs(["📊 Producto más usado", "🏆 Top clientes"])

    # ── Tab 1: Gráfico producto más usado por cliente ──
    with tab_producto:
        st.caption("Producto principal por cliente (N° de operaciones)")

        if "Producto" in df_trader.columns and not df_trader.empty:
            producto_top = (
                df_trader.groupby(["NIT", "Producto"])
                .size()
                .reset_index(name="Conteo")
                .sort_values(["NIT", "Conteo"], ascending=[True, False])
                .groupby("NIT")
                .first()
                .reset_index()
            )
            if not df_priorizacion.empty:
                orden_nits = df_priorizacion["NIT"].tolist()
                producto_top["orden"] = producto_top["NIT"].map(
                    {nit: i for i, nit in enumerate(orden_nits)}
                )
                producto_top = producto_top.sort_values("orden")

            fig = px.bar(
                producto_top,
                x="NIT",
                y="Conteo",
                color="Producto",
                text="Producto",
                labels={"NIT": "NIT", "Conteo": "Ops"},
                color_discrete_sequence=[COLOR_NARANJA, COLOR_NARANJA_CLARO, COLOR_GRIS],
            )
            fig.update_traces(textposition="outside", textfont_size=9)
            fig.update_xaxes(type="category", tickfont=dict(size=9))
            fig.update_yaxes(tickfont=dict(size=9))
            fig.update_layout(
                plot_bgcolor="#FFFFFF",
                paper_bgcolor="#FFFFFF",
                height=260,
                margin=dict(l=4, r=4, t=20, b=4),
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1, font=dict(size=9),
                ),
                legend_title_text="",
            )
            st.plotly_chart(fig, use_container_width=True, key=f"prod_{trader_seleccionado}")
        else:
            st.info("No hay información de productos para esta cartera.")

    # ── Tab 2: Rankings Top N ──
    with tab_top:
        top_n = st.slider(
            "Clientes a mostrar",
            min_value=3, max_value=10, value=5, step=1,
            key=f"slider_{trader_seleccionado}",
        )

        st.markdown("**💱 Top por moneda**")
        if "Moneda" in df_trader.columns:
            monedas_disponibles = sorted(df_trader["Moneda"].dropna().unique().tolist())
            monedas_objetivo = [m for m in monedas_disponibles if m in ("USD/COP", "EUR/COP")] or monedas_disponibles
            ranking_moneda = ranking_clientes_por_moneda(df_trader, monedas_objetivo, top_n=top_n)
            if ranking_moneda.empty:
                st.caption("Sin datos de moneda.")
            else:
                st.dataframe(
                    ranking_moneda.rename(columns={"N_Operaciones": "Ops"}),
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.caption("Sin columna 'Moneda'.")

        st.markdown("**📦 Top por producto**")
        if "Producto" in df_trader.columns:
            productos_disponibles = sorted(df_trader["Producto"].dropna().unique().tolist())
            productos_objetivo = [
                p for p in productos_disponibles
                if p.strip().upper() in ("SPOT", "FORWARD")
            ] or productos_disponibles
            ranking_producto = ranking_clientes_por_producto(df_trader, productos_objetivo, top_n=top_n)
            if ranking_producto.empty:
                st.caption("Sin datos de producto.")
            else:
                st.dataframe(
                    ranking_producto.rename(columns={"N_Operaciones": "Ops"}),
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.caption("Sin columna 'Producto'.")


# =============================================================================
# 7. SECCIÓN INFERIOR COLAPSADA — buscador + detalle de operaciones
# =============================================================================

st.markdown(
    "<hr style='margin:14px 0 6px 0; border:none; border-top:1px solid #F0F0F0'>",
    unsafe_allow_html=True,
)

with st.expander("🔍 Buscar cliente específico / Ver detalle de operaciones"):

    buscar_col, detalle_col = st.columns([1, 1], gap="large")

    # ── Buscador de cliente ──
    with buscar_col:
        st.markdown("**Buscar cliente en esta cartera**")
        lista_nits = sorted(df_trader["NIT"].dropna().unique().tolist())
        nit_buscado = st.selectbox(
            "Selecciona un NIT",
            options=["-- Selecciona --"] + lista_nits,
            label_visibility="collapsed",
            key=f"nit_{trader_seleccionado}",
        )

        if nit_buscado != "-- Selecciona --":
            ops_cliente     = df_trader[df_trader["NIT"] == nit_buscado]
            metricas_cli    = calcular_metricas_por_cliente(ops_cliente)
            recomendacion   = calcular_recomendacion_oferta(df_trader, nit_buscado)
            sugerencia      = texto_sugerencia_oferta(recomendacion)
            sector          = obtener_sector_economico(df_trader, nit_buscado)

            if not metricas_cli.empty:
                datos = metricas_cli.iloc[0]
                texto_dias_cli = (
                    "Sin registro de fecha"
                    if datos["Dias_Sin_Operar"] >= 999
                    else f"{int(datos['Dias_Sin_Operar'])} días sin operar"
                )
                st.markdown(
                    '<div class="ficha-cliente">'
                    f'<div class="ficha-titulo">👤 NIT {nit_buscado}</div>'
                    '<div class="ficha-grid">'
                      '<div class="ficha-dato">'
                        '<div class="ficha-dato-etiqueta">Valor para Itaú</div>'
                        f'<div class="ficha-dato-valor">{datos["Monto_Itau"]:,.0f}</div>'
                      '</div>'
                      '<div class="ficha-dato">'
                        '<div class="ficha-dato-etiqueta">Monto en Mercado</div>'
                        f'<div class="ficha-dato-valor">{datos["Monto_Mercado"]:,.0f}</div>'
                      '</div>'
                      '<div class="ficha-dato">'
                        '<div class="ficha-dato-etiqueta">Última actividad</div>'
                        f'<div class="ficha-dato-valor">{texto_dias_cli}</div>'
                      '</div>'
                      '<div class="ficha-dato">'
                        '<div class="ficha-dato-etiqueta">Operaciones</div>'
                        f'<div class="ficha-dato-valor">{int(datos["N_Operaciones"])}</div>'
                      '</div>'
                    '</div>'
                    '<div class="ficha-sector">'
                      f'🏢 <b>Sector:</b> {sector}'
                    '</div>'
                    '<div class="card-offer">'
                      f'📞 <b>Patrones históricos:</b> {sugerencia}'
                    '</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )

                with st.expander("Ver operaciones de este cliente"):
                    st.dataframe(ops_cliente, use_container_width=True)

    # ── Detalle completo de la cartera ──
    with detalle_col:
        st.markdown("**Detalle completo de operaciones de esta cartera**")
        st.dataframe(df_trader, use_container_width=True)
