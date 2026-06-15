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

COLOR_NARANJA = "#FF6900"
COLOR_NARANJA_CLARO = "#FFB266"
COLOR_GRIS = "#8A8A8A"
COLOR_GRIS_CLARO = "#F0F0F0"

st.markdown(f"""
<style>
    /* --- Reset y tipografía --- */
    html, body, [class*="css"] {{
        font-family: 'Segoe UI', sans-serif;
        background-color: #FFFFFF;
    }}

    /* --- Ocultar sidebar completamente --- */
    section[data-testid="stSidebar"] {{
        display: none;
    }}

    /* --- Quitar padding superior por defecto de Streamlit --- */
    .block-container {{
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        max-width: 100% !important;
    }}

    /* --- Topbar --- */
    .topbar {{
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 20px;
        border-bottom: 1px solid {COLOR_GRIS_CLARO};
        background: #FFFFFF;
        margin-bottom: 12px;
    }}
    .topbar-logo {{
        font-size: 16px;
        font-weight: 700;
        color: {COLOR_NARANJA};
    }}
    .topbar-sep {{
        font-size: 13px;
        color: {COLOR_GRIS};
    }}

    /* --- Tarjetas de métricas --- */
    div[data-testid="metric-container"] {{
        background-color: #FAFAFA;
        border: 1px solid #FFD9B8;
        border-radius: 10px;
        padding: 12px 16px;
    }}

    /* --- Lista de priorización con scroll interno --- */
    .prio-scroll-container {{
        overflow-y: auto;
        max-height: 480px;
        padding-right: 4px;
    }}

    /* --- Tarjeta de cliente --- */
    .tarjeta-cliente {{
        background: #FFFFFF;
        border: 1px solid {COLOR_GRIS_CLARO};
        border-left: 5px solid {COLOR_NARANJA};
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 10px;
    }}
    .tarjeta-encabezado {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;
    }}
    .tarjeta-titulo {{
        font-size: 14px;
        font-weight: 700;
        color: #1A1A1A;
    }}
    .tarjeta-puntaje {{
        font-size: 20px;
        font-weight: 800;
        color: {COLOR_NARANJA};
    }}
    .tarjeta-puntaje small {{
        font-size: 11px;
        font-weight: 400;
        color: {COLOR_GRIS};
    }}
    .bloque-datos {{
        display: flex;
        gap: 16px;
        flex-wrap: wrap;
        font-size: 12px;
        color: #4A4A4A;
        margin-bottom: 4px;
    }}
    .bloque-datos b {{ color: #1A1A1A; }}
    .bloque-oferta {{
        background: #FFF6EE;
        border-radius: 6px;
        padding: 7px 10px;
        margin-top: 8px;
        font-size: 12px;
        color: #1A1A1A;
    }}
    .bloque-oferta b {{ color: {COLOR_NARANJA}; }}
    .badge {{
        display: inline-block;
        padding: 2px 10px;
        border-radius: 10px;
        font-size: 10px;
        font-weight: 600;
        margin: 5px 4px 0 0;
    }}
    .badge-alerta     {{ background: #FFE3D1; color: #D2480C; }}
    .badge-oportunidad {{ background: #FFF1E0; color: {COLOR_NARANJA}; }}
    .badge-fidelidad  {{ background: #F0F0F0; color: #5A5A5A; }}
    .badge-nuevo      {{ background: #FFEDD9; color: #B85400; }}
    .badge-neutral    {{ background: #F0F0F0; color: #8A8A8A; }}

    /* --- Títulos de panel --- */
    .panel-titulo {{
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: {COLOR_GRIS};
        margin-bottom: 8px;
        padding-bottom: 6px;
        border-bottom: 2px solid {COLOR_NARANJA};
    }}

    /* --- Panel derecho: secciones --- */
    .panel-seccion {{
        margin-bottom: 16px;
    }}

    /* --- Buscador colapsado (parte inferior) --- */
    .ficha-cliente {{
        background: #FFFFFF;
        border: 1px solid {COLOR_GRIS_CLARO};
        border-left: 5px solid {COLOR_NARANJA};
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 12px;
    }}
    .ficha-titulo {{
        font-size: 15px;
        font-weight: 700;
        color: #1A1A1A;
        margin-bottom: 10px;
        padding-bottom: 8px;
        border-bottom: 1px solid {COLOR_GRIS_CLARO};
    }}
    .ficha-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 10px;
        margin-bottom: 12px;
    }}
    .ficha-dato {{
        background: #FAFAFA;
        border-radius: 8px;
        padding: 8px 12px;
    }}
    .ficha-dato-etiqueta {{
        font-size: 10px;
        color: {COLOR_GRIS};
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 3px;
    }}
    .ficha-dato-valor {{
        font-size: 15px;
        font-weight: 700;
        color: #1A1A1A;
    }}
    .ficha-sector {{
        background: #FFF6EE;
        border-radius: 8px;
        padding: 8px 12px;
        margin-bottom: 12px;
        font-size: 12px;
        color: #1A1A1A;
    }}
    .ficha-sector b {{ color: {COLOR_NARANJA}; }}

    /* --- Ranking table --- */
    .ranking-titulo {{
        font-size: 12px;
        font-weight: 700;
        color: #1A1A1A;
        margin: 6px 0 4px 0;
    }}

    /* --- Ayuda --- */
    .caja-ayuda {{
        background: #FFF6EE;
        border: 1px solid #FFD9B8;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 11px;
        color: #5A5A5A;
        margin-top: 8px;
    }}
</style>
""", unsafe_allow_html=True)

BADGE_CLASES = {
    "alerta": "badge-alerta",
    "oportunidad": "badge-oportunidad",
    "fidelidad": "badge-fidelidad",
    "nuevo": "badge-nuevo",
    "neutral": "badge-neutral",
}


# =============================================================================
# 2. CARGA DE DATOS
# =============================================================================

@st.cache_data(ttl=3600)
def cargar_datos_consolidados() -> pd.DataFrame:
    df_ops = cargar_operaciones()
    df_clientes = cargar_clientes()
    df_ciiu = cargar_ciiu()
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
# 3. TOPBAR — logo + selector de cartera (un solo selectbox)
# =============================================================================

col_logo, col_sep, col_selector, col_info = st.columns([2, 0.3, 2, 5])

with col_logo:
    st.markdown('<div class="topbar-logo">🟠 Itaú Colombia</div>', unsafe_allow_html=True)

with col_sep:
    st.markdown('<div class="topbar-sep" style="padding-top:4px">|</div>', unsafe_allow_html=True)

with col_selector:
    trader_seleccionado = st.selectbox(
        label="Cartera",
        options=lista_traders,
        format_func=lambda t: f"Trader {t}",
        label_visibility="collapsed",
    )

with col_info:
    st.markdown(
        '<div style="font-size:12px;color:#8A8A8A;padding-top:6px">Mesa de Clientes</div>',
        unsafe_allow_html=True,
    )

st.markdown("<hr style='margin:0 0 12px 0;border:none;border-top:1px solid #F0F0F0'>", unsafe_allow_html=True)


# =============================================================================
# 4. DATOS DEL TRADER SELECCIONADO
# =============================================================================

df_trader = filtrar_por_trader(df, trader_seleccionado, COLUMNA_TRADER)
df_priorizacion = generar_priorizacion(df_trader)

if not df_priorizacion.empty:
    monto_total_itau = df_priorizacion["Monto_Itau"].sum()
    oportunidad_total = df_priorizacion["Monto_Mercado"].sum()
    cliente_top_nit = df_priorizacion.iloc[0]["NIT"]
    cliente_top_puntaje = df_priorizacion.iloc[0]["Puntaje"]
else:
    monto_total_itau = 0
    oportunidad_total = 0
    cliente_top_nit = "—"
    cliente_top_puntaje = 0


# =============================================================================
# 5. LAYOUT PRINCIPAL: COLUMNA IZQUIERDA + COLUMNA DERECHA
# =============================================================================

col_izq, col_der = st.columns([3, 2], gap="medium")


# ── COLUMNA IZQUIERDA ────────────────────────────────────────────────────────

with col_izq:

    # --- Métricas resumen ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Clientes", df_trader["NIT"].nunique())
    m2.metric("Top de hoy", f"NIT {cliente_top_nit}", f"{cliente_top_puntaje}/100")
    m3.metric("Monto Itaú", f"{monto_total_itau:,.0f}")
    m4.metric("Oportunidad", f"{oportunidad_total:,.0f}")

    st.markdown(
        '<div class="caja-ayuda">'
        'ℹ️ <b>Monto Itaú</b>: lo que los clientes ya movieron con Itaú. '
        '<b>Oportunidad</b>: lo que operaron con otros bancos — negocio capturable.'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Lista de priorización con scroll interno ---
    st.markdown('<div class="panel-titulo">📋 A quién llamar hoy — orden de prioridad</div>', unsafe_allow_html=True)

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
                '<div class="tarjeta-cliente">'
                '<div class="tarjeta-encabezado">'
                f'<span class="tarjeta-titulo">#{posicion + 1} · Cliente NIT {fila["NIT"]}</span>'
                f'<span class="tarjeta-puntaje">{fila["Puntaje"]}<small>/100</small></span>'
                '</div>'
                '<div class="bloque-datos">'
                f'<span>💰 Itaú: <b>{fila["Monto_Itau"]:,.0f}</b></span>'
                f'<span>🎯 Mercado: <b>{fila["Monto_Mercado"]:,.0f}</b></span>'
                f'<span>⏱️ {texto_dias}</span>'
                f'<span>🔄 {int(fila["N_Operaciones"])} ops.</span>'
                '</div>'
                '<div class="bloque-datos">'
                f'<span>🏢 {fila["Sector_Economico"]}</span>'
                '</div>'
                '<div class="bloque-oferta">'
                f'📞 <b>Qué ofrecer:</b> {fila["Sugerencia_Oferta"]}'
                '</div>'
                f'<div>{badges_html}</div>'
                '</div>'
            )

        st.markdown(
            f'<div class="prio-scroll-container">{tarjetas_html}</div>',
            unsafe_allow_html=True,
        )


# ── COLUMNA DERECHA ──────────────────────────────────────────────────────────

with col_der:

    # --- Gráfico: producto más usado por cliente ---
    st.markdown('<div class="panel-titulo">📊 Producto más usado por cliente</div>', unsafe_allow_html=True)

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

        fig_producto = px.bar(
            producto_top,
            x="NIT",
            y="Conteo",
            color="Producto",
            text="Producto",
            labels={"NIT": "NIT", "Conteo": "Operaciones"},
            color_discrete_sequence=[COLOR_NARANJA, COLOR_NARANJA_CLARO, COLOR_GRIS],
        )
        fig_producto.update_traces(textposition="outside", textfont_size=10)
        fig_producto.update_xaxes(type="category", tickfont=dict(size=10))
        fig_producto.update_yaxes(tickfont=dict(size=10))
        fig_producto.update_layout(
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF",
            height=220,
            margin=dict(l=4, r=4, t=16, b=4),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=10),
            ),
            legend_title_text="",
        )
        st.plotly_chart(fig_producto, use_container_width=True, key=f"prod_{trader_seleccionado}")
    else:
        st.info("No hay información de productos para esta cartera.")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Rankings Top N ---
    st.markdown('<div class="panel-titulo">🏆 Top clientes más activos</div>', unsafe_allow_html=True)

    top_n = st.slider(
        "Clientes a mostrar",
        min_value=3, max_value=10, value=5, step=1,
        key=f"slider_{trader_seleccionado}",
    )

    rank_col1, rank_col2 = st.columns(2)

    with rank_col1:
        st.markdown('<div class="ranking-titulo">💱 Por moneda</div>', unsafe_allow_html=True)
        if "Moneda" in df_trader.columns:
            monedas_disponibles = sorted(df_trader["Moneda"].dropna().unique().tolist())
            monedas_objetivo = [m for m in monedas_disponibles if m in ("USD/COP", "EUR/COP")] or monedas_disponibles
            ranking_moneda = ranking_clientes_por_moneda(df_trader, monedas_objetivo, top_n=top_n)
            if ranking_moneda.empty:
                st.caption("Sin datos.")
            else:
                st.dataframe(
                    ranking_moneda.rename(columns={"NIT": "NIT", "Moneda": "Moneda", "N_Operaciones": "Ops"}),
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.caption("Sin columna 'Moneda'.")

    with rank_col2:
        st.markdown('<div class="ranking-titulo">📦 Por producto</div>', unsafe_allow_html=True)
        if "Producto" in df_trader.columns:
            productos_disponibles = sorted(df_trader["Producto"].dropna().unique().tolist())
            productos_objetivo = [
                p for p in productos_disponibles
                if p.strip().upper() in ("SPOT", "FORWARD")
            ] or productos_disponibles
            ranking_producto = ranking_clientes_por_producto(df_trader, productos_objetivo, top_n=top_n)
            if ranking_producto.empty:
                st.caption("Sin datos.")
            else:
                st.dataframe(
                    ranking_producto.rename(columns={"NIT": "NIT", "Producto": "Producto", "N_Operaciones": "Ops"}),
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.caption("Sin columna 'Producto'.")


# =============================================================================
# 6. SECCIÓN INFERIOR COLAPSADA — buscador + detalle de operaciones
# =============================================================================

st.markdown("<hr style='margin:16px 0 8px 0;border:none;border-top:1px solid #F0F0F0'>", unsafe_allow_html=True)

with st.expander("🔍 Buscar un cliente específico de tu cartera"):

    lista_nits_cartera = sorted(df_trader["NIT"].dropna().unique().tolist())
    nit_buscado = st.selectbox(
        "Selecciona un cliente (NIT)",
        options=["-- Selecciona un cliente --"] + lista_nits_cartera,
        label_visibility="collapsed",
        key=f"nit_{trader_seleccionado}",
    )

    if nit_buscado != "-- Selecciona un cliente --":
        ops_cliente = df_trader[df_trader["NIT"] == nit_buscado]
        metricas_cliente = calcular_metricas_por_cliente(ops_cliente)
        recomendacion = calcular_recomendacion_oferta(df_trader, nit_buscado)
        sugerencia = texto_sugerencia_oferta(recomendacion)
        sector = obtener_sector_economico(df_trader, nit_buscado)

        if not metricas_cliente.empty:
            datos = metricas_cliente.iloc[0]
            texto_dias_cliente = (
                "Sin registro de fecha"
                if datos["Dias_Sin_Operar"] >= 999
                else f"{int(datos['Dias_Sin_Operar'])} días sin operar"
            )
            html_ficha = (
                '<div class="ficha-cliente">'
                f'<div class="ficha-titulo">👤 Cliente NIT {nit_buscado}</div>'
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
                f'<div class="ficha-dato-valor">{texto_dias_cliente}</div>'
                '</div>'
                '<div class="ficha-dato">'
                '<div class="ficha-dato-etiqueta">Operaciones históricas</div>'
                f'<div class="ficha-dato-valor">{int(datos["N_Operaciones"])}</div>'
                '</div>'
                '</div>'
                '<div class="ficha-sector">'
                f'🏢 <b>Sector económico:</b> {sector}'
                '</div>'
                '<div class="bloque-oferta">'
                f'📞 <b>Patrones históricos:</b> {sugerencia}'
                '</div>'
                '</div>'
            )
            st.markdown(html_ficha, unsafe_allow_html=True)

            with st.expander("Ver todas las operaciones de este cliente"):
                st.dataframe(ops_cliente, use_container_width=True)

with st.expander("📂 Ver detalle completo de operaciones de esta cartera"):
    st.dataframe(df_trader, use_container_width=True)
