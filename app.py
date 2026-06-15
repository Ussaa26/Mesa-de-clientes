

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

    /* ---------- Caja de ayuda / explicación ---------- */
    .caja-ayuda {{
        background: #FFF6EE;
        border: 1px solid #FFD9B8;
        border-radius: 8px;
        padding: 10px 14px;
        margin: 10px 0 4px 0;
        font-size: 12.5px;
        color: #5A5A5A;
    }}

    /* ---------- Ficha de cliente (buscador) ---------- */
    .ficha-cliente {{
        background: #FFFFFF;
        border: 1px solid {COLOR_GRIS_CLARO};
        border-left: 6px solid {COLOR_NARANJA};
        border-radius: 10px;
        padding: 18px 22px;
        margin-bottom: 14px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }}
    .ficha-titulo {{
        font-size: 17px;
        font-weight: 700;
        color: #1A1A1A;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid {COLOR_GRIS_CLARO};
    }}
    .ficha-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 14px;
        margin-bottom: 14px;
    }}
    .ficha-dato {{
        background: #FAFAFA;
        border-radius: 8px;
        padding: 10px 14px;
    }}
    .ficha-dato-etiqueta {{
        font-size: 11px;
        color: {COLOR_GRIS};
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }}
    .ficha-dato-valor {{
        font-size: 16px;
        font-weight: 700;
        color: #1A1A1A;
    }}
    .ficha-sector {{
        background: #FFF6EE;
        border-radius: 8px;
        padding: 10px 14px;
        margin-bottom: 14px;
        font-size: 13px;
        color: #1A1A1A;
    }}
    .ficha-sector b {{
        color: {COLOR_NARANJA};
    }}

    /* ---------- Tabla de ranking Top N ---------- */
    .ranking-titulo {{
        font-size: 14px;
        font-weight: 700;
        color: #1A1A1A;
        margin: 10px 0 6px 0;
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

    st.markdown(
        '<div class="caja-ayuda">'
        'ℹ️ <b>¿Qué significan estos valores?</b> '
        '"Monto generado para Itaú" es la suma de lo que todos los '
        'clientes de esta cartera ya movieron CON Itaú. '
        '"Oportunidad en Mercado" es la suma de lo que esos mismos '
        'clientes movieron con OTROS BANCOS — es decir, negocio que '
        'Itaú podría intentar capturar.'
        '</div>',
        unsafe_allow_html=True,
    )

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
                '<div class="bloque-datos">'
                f'<span>🏢 Sector económico: <b>{fila["Sector_Economico"]}</b></span>'
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
    # 7. RANKINGS TOP N — clientes más activos por moneda y por producto
    # =========================================================================

    st.markdown(
        '<div class="titulo-seccion">🏆 Top clientes más activos de esta cartera</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="subtitulo-seccion">'
        'Ranking de los clientes con más operaciones registradas, '
        'filtrado por moneda y por producto. Útil para identificar '
        'rápidamente a los clientes más recurrentes en cada categoría.'
        '</div>',
        unsafe_allow_html=True,
    )

    top_n = st.slider(
        "¿Cuántos clientes mostrar en cada ranking?",
        min_value=3, max_value=15, value=5, step=1,
    )

    col_moneda, col_producto = st.columns(2)

    # --- Ranking por moneda (USD/COP y EUR/COP) ---
    with col_moneda:
        st.markdown(
            '<div class="ranking-titulo">💱 Por moneda (USD/COP y EUR/COP)</div>',
            unsafe_allow_html=True,
        )

        if "Moneda" in df_trader.columns:
            monedas_disponibles = sorted(df_trader["Moneda"].dropna().unique().tolist())
            monedas_objetivo = [m for m in monedas_disponibles if m in ("USD/COP", "EUR/COP")]

            if not monedas_objetivo:
                monedas_objetivo = monedas_disponibles  # si no existen esos nombres exactos, usar todas

            ranking_moneda = ranking_clientes_por_moneda(df_trader, monedas_objetivo, top_n=top_n)

            if ranking_moneda.empty:
                st.info("No hay operaciones registradas en estas monedas.")
            else:
                ranking_moneda_mostrar = ranking_moneda.rename(columns={
                    "NIT": "Cliente (NIT)",
                    "Moneda": "Moneda",
                    "N_Operaciones": "N° de operaciones",
                })
                st.dataframe(ranking_moneda_mostrar, use_container_width=True, hide_index=True)
        else:
            st.info("No hay columna 'Moneda' en los datos.")

    # --- Ranking por producto (SPOT y FORWARD) ---
    with col_producto:
        st.markdown(
            '<div class="ranking-titulo">📦 Por producto (Spot y Forward)</div>',
            unsafe_allow_html=True,
        )

        if "Producto" in df_trader.columns:
            productos_disponibles = sorted(df_trader["Producto"].dropna().unique().tolist())
            productos_objetivo = [
                p for p in productos_disponibles
                if p.strip().upper() in ("SPOT", "FORWARD")
            ]

            if not productos_objetivo:
                productos_objetivo = productos_disponibles  # si no coinciden los nombres, usar todos

            ranking_producto = ranking_clientes_por_producto(df_trader, productos_objetivo, top_n=top_n)

            if ranking_producto.empty:
                st.info("No hay operaciones registradas en estos productos.")
            else:
                ranking_producto_mostrar = ranking_producto.rename(columns={
                    "NIT": "Cliente (NIT)",
                    "Producto": "Producto",
                    "N_Operaciones": "N° de operaciones",
                })
                st.dataframe(ranking_producto_mostrar, use_container_width=True, hide_index=True)
        else:
            st.info("No hay columna 'Producto' en los datos.")

    st.markdown("---")

    # =========================================================================
    # 8. BUSCADOR DE CLIENTE — consultar un cliente específico de la cartera
    # =========================================================================

    st.markdown(
        '<div class="titulo-seccion">🔍 Buscar un cliente de tu cartera</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="subtitulo-seccion">'
        'Útil cuando no vas a contactar a un cliente hoy, pero quieres '
        'consultar su información: historial, sector, moneda y producto '
        'más usados.'
        '</div>',
        unsafe_allow_html=True,
    )

    lista_nits_cartera = sorted(df_trader["NIT"].dropna().unique().tolist())

    nit_buscado = st.selectbox(
        "Selecciona un cliente (NIT)",
        options=["-- Selecciona un cliente --"] + lista_nits_cartera,
        label_visibility="collapsed",
    )

    if nit_buscado != "-- Selecciona un cliente --":
        ops_cliente = df_trader[df_trader["NIT"] == nit_buscado]

        # Calcular las mismas métricas que en la lista de priorización,
        # pero solo para este cliente
        metricas_cliente = calcular_metricas_por_cliente(ops_cliente)
        recomendacion = calcular_recomendacion_oferta(df_trader, nit_buscado)
        sugerencia = texto_sugerencia_oferta(recomendacion)
        sector = obtener_sector_economico(df_trader, nit_buscado)

        if not metricas_cliente.empty:
            datos = metricas_cliente.iloc[0]

            if datos["Dias_Sin_Operar"] >= 999:
                texto_dias_cliente = "Sin registro de fecha"
            else:
                texto_dias_cliente = f"{int(datos['Dias_Sin_Operar'])} días sin operar"

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

                '</div>'  # cierra ficha-grid

                '<div class="ficha-sector">'
                f'🏢 <b>Sector económico:</b> {sector}'
                '</div>'

                '<div class="bloque-oferta">'
                f'📞 <b>Patrones históricos:</b> {sugerencia}'
                '</div>'

                '</div>'  # cierra ficha-cliente
            )
            st.markdown(html_ficha, unsafe_allow_html=True)

            with st.expander("Ver todas las operaciones de este cliente"):
                st.dataframe(ops_cliente, use_container_width=True)

    st.markdown("---")

    # =========================================================================
    # 9. DETALLE DE OPERACIONES
    # =========================================================================

    with st.expander("📂 Ver detalle completo de operaciones de esta cartera"):
        st.dataframe(df_trader, use_container_width=True)
