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

st.set_page_config(page_title="Mesa de Clientes - Itaú", layout="wide")

st.title("📊 Mesa de Clientes - Dashboard de Priorización")

# -----------------------------------------------------------------
# CARGA DE DATOS
# -----------------------------------------------------------------
# Por ahora carga desde /data. Más adelante se reemplaza por OneDrive.
try:
    df_ops = cargar_operaciones()
    df_clientes = cargar_clientes()
    df_ciiu = cargar_ciiu()
    df = cruzar_bases(df_ops, df_clientes, df_ciiu)
except FileNotFoundError as e:
    st.error(f"No se encontraron los archivos de datos: {e}")
    st.info("Asegúrate de tener 'operaciones.xlsx', 'clientes.xlsx' y 'ciiu.xlsx' en la carpeta /data")
    st.stop()

# -----------------------------------------------------------------
# IDENTIFICAR TRADERS
# -----------------------------------------------------------------
COLUMNA_TRADER = "Cod_Cartera"  # Ajustar si el campo se llama diferente

if COLUMNA_TRADER not in df.columns:
    st.error(f"No se encontró la columna '{COLUMNA_TRADER}' en los datos cruzados.")
    st.stop()

traders = obtener_lista_traders(df, COLUMNA_TRADER)

# -----------------------------------------------------------------
# CREAR PESTAÑAS DINÁMICAS POR TRADER
# -----------------------------------------------------------------
tabs = st.tabs([f"Trader {t}" for t in traders])

for tab, trader_id in zip(tabs, traders):
    with tab:
        df_trader = filtrar_por_trader(df, trader_id, COLUMNA_TRADER)

        st.subheader(f"Cartera del Trader {trader_id}")

        # ---- RESUMEN GENERAL ----
        col1, col2, col3 = st.columns(3)

        n_clientes = df_trader["NIT"].nunique()
        n_operaciones = len(df_trader)
        monto_total = df_trader["Monto_Total_"].sum() if "Monto_Total_" in df_trader.columns else 0

        col1.metric("Clientes en cartera", n_clientes)
        col2.metric("Operaciones registradas", n_operaciones)
        col3.metric("Monto total movido", f"{monto_total:,.0f}")

        st.divider()

        # ---- MÉTRICAS: ENTIDAD VS MERCADO ----
        st.markdown("### 🏦 Distribución Entidad vs Mercado")
        st.caption(
            "'Entidad' = el cliente operó con Itaú. "
            "'Mercado' = el cliente operó con otro banco (oportunidad comercial)."
        )

        if "Entidad" in df_trader.columns:
            distribucion_entidad = (
                df_trader.groupby("Entidad")
                .size()
                .reset_index(name="Cantidad")
            )

            fig_entidad = px.pie(
                distribucion_entidad,
                names="Entidad",
                values="Cantidad",
                title="Operaciones: Entidad vs Mercado",
                hole=0.4,
            )
            st.plotly_chart(fig_entidad, use_container_width=True, key=f"fig_entidad_{trader_id}")
        else:
            st.warning("No se encontró la columna 'Entidad' en los datos.")

        st.divider()

        # ---- MÉTRICAS: LADO (BANCO VENDE / BANCO COMPRA) ----
        st.markdown("### 🔄 Distribución por tipo de operación (Lado)")

        if "Lado" in df_trader.columns:
            distribucion_lado = (
                df_trader.groupby("Lado")
                .size()
                .reset_index(name="Cantidad")
            )

            fig_lado = px.bar(
                distribucion_lado,
                x="Lado",
                y="Cantidad",
                title="Cantidad de operaciones por tipo (Lado)",
                text="Cantidad",
            )
            st.plotly_chart(fig_lado, use_container_width=True, key=f"fig_lado_{trader_id}")
        else:
            st.warning("No se encontró la columna 'Lado' en los datos.")

        st.divider()

        # ---- FRECUENCIA DE OPERACIÓN POR CLIENTE ----
        st.markdown("### 📈 Frecuencia de operación por cliente")

        frecuencia = (
            df_trader.groupby("NIT")
            .size()
            .reset_index(name="N_Operaciones")
            .sort_values("N_Operaciones", ascending=False)
        )

        st.dataframe(frecuencia, use_container_width=True)

        st.divider()

        # ---- TABLA COMPLETA DEL TRADER ----
        st.markdown("### 📋 Detalle de operaciones")
        st.dataframe(df_trader, use_container_width=True)
