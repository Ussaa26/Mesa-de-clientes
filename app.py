

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
from priorizacion import generar_priorizacion


# =============================================================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
# =============================================================================

st.set_page_config(
    page_title="Mesa de Clientes – Itaú",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Paleta de marca Itaú: blanco + naranja
COLOR_NARANJA = "#FF6900"
COLOR_NARANJA_CLARO = "#FFB266"
COLOR_GRIS = "#8A8A8A"
COLOR_GRIS_CLARO = "#F0F0F0"

st.markdown(f"""
<style>
    /* ---------- Fondo y tipografía general ---------- */
    html, body, [class*="css"] {{
        font-family: 'Segoe UI', sans-serif;
        background-color: #FFFFFF;
    }}

    /* ---------- Sidebar ---------- */
    section[data-testid="stSidebar"] {{
        background-color: #FFFFFF;
        border-right: 1px solid {COLOR_GRIS_CLARO};
    }}
    section[data-testid="stSidebar"] * {{
        color: #1A1A1A !important;
    }}
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {{
        color: {COLOR_NARANJA} !important;
    }}

    /* ---------- Tarjetas de métricas (st.metric) ---------- */
    div[data-testid="metric-container"] {{
        background-color: #FFFFFF;
        border: 1px solid #FFD9B8;
        border-radius: 10px;
        padding: 16px;
        box-shadow: 0 1px 4px rgba(255,105,0,0.06);
    }}

    /* ---------- Tarjeta de cliente (lista de priorización) ---------- */
    .tarjeta-cliente {{
        background: #FFFFFF;
        border: 1px solid {COLOR_GRIS_CLARO};
        border-left: 6px solid {COLOR_NARANJA};
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 14px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }}

    .tarjeta-encabezado {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }}
    .tarjeta-titulo {{
        font-size: 16px;
        font-weight: 700;
        color: #1A1A1A;
    }}
    .tarjeta-puntaje {{
        font-size: 22px;
        font-weight: 800;
        color: {COLOR_NARANJA};
    }}
    .tarjeta-puntaje small {{
        font-size: 12px;
        font-weight: 400;
        color: {COLOR_GRIS};
    }}

    /* ---------- Bloques internos de la tarjeta ---------- */
    .bloque-datos {{
        display: flex;
        gap: 24px;
        flex-wrap: wrap;
        margin: 8px 0;
        font-size: 13px;
        color: #4A4A4A;
    }}
    .bloque-datos b {{
        color: #1A1A1A;
    }}

    .bloque-oferta {{
        background: #FFF6EE;
        border-radius: 8px;
        padding: 10px 14px;
        margin-top: 10px;
        font-size: 13px;
        color: #1A1A1A;
    }}
    .bloque-oferta b {{
        color: {COLOR_NARANJA};
    }}

    /* ---------- Etiquetas (badges) de necesidades ---------- */
    .badge {{
        display: inline-block;
        padding: 3px 12px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
        margin: 6px 6px 0 0;
    }}
    .badge-alerta     {{ background: #FFE3D1; color: #D2480C; }}
    .badge-oportunidad {{ background: #FFF1E0; color: {COLOR_NARANJA}; }}
    .badge-fidelidad  {{ background: #F0F0F0; color: #5A5A5A; }}
    .badge-nuevo      {{ background: #FFEDD9; color: #B85400; }}
    .badge-neutral    {{ background: #F0F0F0; color: #8A8A8A; }}

    /* ---------- Títulos de sección ---------- */
    .titulo-seccion {{
        font-size: 19px;
        font-weight: 700;
        color: #1A1A1A;
        margin: 28px 0 6px 0;
        padding-bottom: 8px;
        border-bottom: 3px solid {COLOR_NARANJA};
    }}
    .subtitulo-seccion {{
        font-size: 13px;
        color: {COLOR_GRIS};
        margin-bottom: 16px;
    }}
</style>
""", unsafe_allow_html=True)


# Mapa de tipo de necesidad -> clase CSS del badge
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
    """
    Carga las 3 bases originales (Operaciones, Clientes/BUC, CIIU),
    convierte la fecha a un formato legible, y devuelve todo cruzado
    en un solo DataFrame.
    """
    df_ops = cargar_operaciones()
    df_clientes = cargar_clientes()
    df_ciiu = cargar_ciiu()

    # La fecha viene en formato numérico de Excel (ej: 43832) -> convertir
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
# 3. SIDEBAR — selección de trader (con buscador)
# =============================================================================

with st.sidebar:
    st.markdown("## 🟠 Itaú Colombia")
    st.markdown("### Mesa de Clientes")
    st.markdown("---")

    st.markdown("**Busca tu cartera:**")
    texto_busqueda = st.text_input(
        "Buscar trader",
        placeholder="Ej: 4042",
        label_visibility="collapsed",
    )

    if texto_busqueda:
        traders_disponibles = [
            t for t in lista_traders
            if texto_busqueda.strip().lower() in str(t).lower()
        ]
        if not traders_disponibles:
            st.warning("No se encontró ningún trader con ese texto.")
            traders_disponibles = lista_traders
    else:
        traders_disponibles = lista_traders

    trader_seleccionado = st.radio(
        label="Selecciona tu cartera:",
        options=traders_disponibles,
        format_func=lambda t: f"Trader {t}",
    )

    st.markdown("---")
    st.caption("Los datos se actualizan automáticamente cuando cambian las fuentes.")


# A partir de aquí, todo el contenido corresponde al trader seleccionado
df_trader = filtrar_por_trader(df, trader_seleccionado, COLUMNA_TRADER)
df_priorizacion = generar_priorizacion(df_trader)


# Contenedor central: deja márgenes a los lados para que no se vea
# todo "estirado" de borde a borde de la pantalla.
_, columna_central, _ = st.columns([1, 6, 1])

with columna_central:

    # =========================================================================
    # 4. RESUMEN GENERAL DE LA CARTERA
    # =========================================================================

    st.markdown(f"## Cartera del Trader {trader_seleccionado}")
    st.caption(
        f"{df_trader['NIT'].nunique()} clientes · "
        f"{len(df_trader)} operaciones registradas"
    )

    col1, col2, col3, col4 = st.columns(4)

    if not df_priorizacion.empty:
        clientes_a_llamar_hoy = int((df_priorizacion["Puntaje"] >= 50).sum())
        monto_total_itau = df_priorizacion["Monto_Itau"].sum()
        oportunidad_total = df_priorizacion["Monto_Mercado"].sum()
    else:
        clientes_a_llamar_hoy = 0
        monto_total_itau = 0
        oportunidad_total = 0

    col1.metric("Clientes en cartera", df_trader["NIT"].nunique())
    col2.metric("Clientes a priorizar hoy", clientes_a_llamar_hoy)
    col3.metric("Monto generado para Itaú", f"{monto_total_itau:,.0f}")
    col4.metric("Oportunidad en Mercado", f"{oportunidad_total:,.0f}")

    st.markdown("---")

    # =========================================================================
    # 5. LISTA DE PRIORIZACIÓN
    # =========================================================================

    st.markdown(
        '<div class="titulo-seccion">📋 A quién llamar hoy (en orden)</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="subtitulo-seccion">'
        'Ordenado de mayor a menor prioridad. El puntaje combina: '
        'oportunidad con la competencia, valor actual para Itaú, '
        'días sin operar y fidelización.'
        '</div>',
        unsafe_allow_html=True,
    )

    if df_priorizacion.empty:
        st.info("Esta cartera no tiene clientes registrados.")
    else:
        for posicion, fila in df_priorizacion.iterrows():

            # --- Badges de necesidades ---
            badges_html = "".join(
                f'<span class="badge {BADGE_CLASES.get(tipo, "badge-neutral")}">{texto}</span>'
                for texto, tipo in fila["Necesidades"]
            )

            # --- Texto de "días sin operar" legible ---
            if fila["Dias_Sin_Operar"] >= 999:
                texto_dias = "Sin registro de fecha"
            else:
                texto_dias = f"{int(fila['Dias_Sin_Operar'])} días sin operar"

            html_tarjeta = (
                '<div class="tarjeta-cliente">'
                '<div class="tarjeta-encabezado">'
                f'<span class="tarjeta-titulo">#{posicion + 1} · Cliente NIT {fila["NIT"]}</span>'
                f'<span class="tarjeta-puntaje">{fila["Puntaje"]}<small>/100</small></span>'
                '</div>'
                '<div class="bloque-datos">'
                f'<span>💰 Valor para Itaú: <b>{fila["Monto_Itau"]:,.0f}</b></span>'
                f'<span>🎯 Oportunidad en Mercado: <b>{fila["Monto_Mercado"]:,.0f}</b></span>'
                f'<span>⏱️ {texto_dias}</span>'
                f'<span>🔄 {int(fila["N_Operaciones"])} operaciones históricas</span>'
                '</div>'
                '<div class="bloque-oferta">'
                f'📞 <b>Qué ofrecer:</b> {fila["Sugerencia_Oferta"]}'
                '</div>'
                f'<div>{badges_html}</div>'
                '</div>'
            )
            st.markdown(html_tarjeta, unsafe_allow_html=True)

    st.markdown("---")

    # =========================================================================
    # 6. GRÁFICO — producto más usado por cliente
    # =========================================================================

    st.markdown(
        '<div class="titulo-seccion">📊 Producto más usado por cliente</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="subtitulo-seccion">'
        'Muestra el producto (SPOT, FORWARD, NEXT DAY) que cada cliente '
        'usa con más frecuencia. Útil para saber qué producto mencionar '
        'al ofrecer algo nuevo.'
        '</div>',
        unsafe_allow_html=True,
    )

    if "Producto" in df_trader.columns and not df_trader.empty:
        # Para cada cliente, encontrar su producto más frecuente
        producto_top = (
            df_trader.groupby(["NIT", "Producto"])
            .size()
            .reset_index(name="Conteo")
            .sort_values(["NIT", "Conteo"], ascending=[True, False])
            .groupby("NIT")
            .first()
            .reset_index()
        )

        # Mantener el mismo orden que la lista de priorización
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
            labels={"NIT": "Cliente (NIT)", "Conteo": "N° de operaciones con ese producto"},
            color_discrete_sequence=[COLOR_NARANJA, COLOR_NARANJA_CLARO, COLOR_GRIS],
        )
        fig_producto.update_traces(textposition="outside")
        fig_producto.update_xaxes(type="category")  # Trata el NIT como categoría, no número continuo
        fig_producto.update_layout(
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF",
            height=380,
            margin=dict(l=10, r=10, t=30, b=10),
            legend_title_text="Producto más usado",
        )
        st.plotly_chart(fig_producto, use_container_width=True, key=f"producto_{trader_seleccionado}")
    else:
        st.info("No hay información de productos para esta cartera.")

    st.markdown("---")

    # =========================================================================
    # 7. DETALLE DE OPERACIONES
    # =========================================================================

    with st.expander("📂 Ver detalle completo de operaciones de esta cartera"):
        st.dataframe(df_trader, use_container_width=True)
