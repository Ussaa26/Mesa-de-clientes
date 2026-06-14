"""
Módulo de priorización y recomendaciones — Mesa de Clientes Itaú
==================================================================

Este archivo contiene TODA la lógica de negocio: cómo se calcula
el puntaje de prioridad de cada cliente y qué se le recomienda
ofrecer al trader. Está separado de la app (interfaz visual) para
que sea fácil de leer, ajustar y validar con el banco sin tocar
el diseño.


CÓMO FUNCIONA EL MODELO DE PRIORIDAD
-------------------------------------
Cada cliente recibe un puntaje de 0 a 100, calculado a partir de
4 factores. Cada factor se "normaliza" (se lleva a una escala de
0 a 1 comparando contra los demás clientes de la misma cartera) y
luego se multiplica por su peso:

    Factor                          Peso    Qué mide
    ------------------------------  -----   ----------------------------------
    Oportunidad en Mercado           30%    Dinero que el cliente mueve con
                                             la competencia (negocio a recuperar)

    Valor actual para Itaú           30%    Dinero que el cliente YA mueve
                                             con Itaú (no perder este cliente)

    Días sin operar                  20%    Riesgo de inactividad

    N° de operaciones (fidelización) 20%    Qué tan frecuente es el cliente

    PUNTAJE FINAL = suma de los 4 factores ponderados (0-100)

Los clientes se ordenan de mayor a menor puntaje: el #1 es a quien
el trader debe llamar primero.


CÓMO FUNCIONA LA RECOMENDACIÓN DE OFERTA
-------------------------------------------
Para cada cliente, se revisa su historial de operaciones y se
identifican sus DOS patrones más frecuentes:

    1. Producto que más usa   -> SPOT / FORWARD / NEXT DAY
    2. Lado que más usa       -> el cliente más COMPRA o más VENDE

Con esos dos datos se construye una frase de sugerencia, por ejemplo:

    "Sugerencia: FORWARD - el cliente suele VENDER (80% histórico)"

Esto le dice al trader, de un vistazo, QUÉ ofrecer cuando llame.


NOTA IMPORTANTE
----------------
Los pesos (30/30/20/20) y los umbrales usados en las "necesidades
inferidas" son una PROPUESTA INICIAL razonable, pensada para que la
app funcione desde ya. Deben validarse con el equipo de la Mesa de
Clientes y ajustarse si el banco define otros criterios.
"""

import pandas as pd


# ===================================================================
# 1. CONFIGURACIÓN DE PESOS Y UMBRALES
# ===================================================================
# Si en el futuro el banco pide cambiar la importancia de cada
# factor, solo se ajustan estos números (deben sumar 100).

PESO_OPORTUNIDAD_MERCADO = 30   # Monto fuera de Itaú (negocio a recuperar)
PESO_VALOR_ACTUAL_ITAU   = 30   # Monto ya generado para Itaú
PESO_DIAS_SIN_OPERAR     = 20   # Riesgo de inactividad
PESO_FIDELIZACION        = 20   # Número de operaciones históricas

# Umbral de días sin operar para considerar "riesgo de reactivación"
UMBRAL_DIAS_REACTIVACION = 30

# Umbral de operaciones para considerar a un cliente "frecuente / fiel"
UMBRAL_OPERACIONES_FIEL = 3


# ===================================================================
# 2. CÁLCULO DEL PUNTAJE DE PRIORIDAD
# ===================================================================

def _normalizar(serie: pd.Series) -> pd.Series:
    """
    Lleva una columna numérica a una escala de 0 a 1.

    El valor más alto del grupo se convierte en 1, el más bajo en 0,
    y los demás quedan proporcionalmente en medio. Esto permite
    comparar factores que tienen escalas muy distintas (días, %,
    montos en millones) de forma justa.
    """
    minimo, maximo = serie.min(), serie.max()
    if maximo == minimo:
        # Si todos los clientes tienen el mismo valor, no hay forma
        # de diferenciarlos por este factor -> se les da un valor neutro
        return pd.Series([0.5] * len(serie), index=serie.index)
    return (serie - minimo) / (maximo - minimo)


def calcular_metricas_por_cliente(df_trader: pd.DataFrame) -> pd.DataFrame:
    """
    Agrupa las operaciones por cliente (NIT) y calcula, para cada uno:

    - Monto_Itau:        cuánto ha movido CON Itaú (Monto_Entidad)
    - Monto_Mercado:     cuánto ha movido CON la competencia
    - Monto_Total:       suma de ambos
    - Dias_Sin_Operar:   días desde su última operación
    - N_Operaciones:     cuántas operaciones tiene en total
    - Pct_Mercado:       % de su monto total que está en Mercado

    Devuelve un DataFrame con una fila por cliente (NIT).
    """
    hoy = pd.Timestamp.now()
    filas = []

    for nit, grupo in df_trader.groupby("NIT"):

        # --- Montos: separar lo que es con Itaú vs con el Mercado ---
        monto_itau = grupo["Monto_Entidad"].sum() if "Monto_Entidad" in grupo.columns else 0
        monto_total = grupo["Monto_Total_"].sum() if "Monto_Total_" in grupo.columns else 0
        monto_mercado = max(monto_total - monto_itau, 0)

        # --- Días sin operar: hoy - fecha de la última operación ---
        if "Fecha" in grupo.columns and grupo["Fecha"].notna().any():
            dias_sin_operar = (hoy - grupo["Fecha"].max()).days
        else:
            dias_sin_operar = 999  # Sin fecha registrada -> se trata como "máxima inactividad"

        # --- % del monto total que corresponde a Mercado ---
        pct_mercado = (monto_mercado / monto_total * 100) if monto_total > 0 else 0

        filas.append({
            "NIT": nit,
            "Monto_Itau": monto_itau,
            "Monto_Mercado": monto_mercado,
            "Monto_Total": monto_total,
            "Dias_Sin_Operar": dias_sin_operar,
            "N_Operaciones": len(grupo),
            "Pct_Mercado": round(pct_mercado, 1),
        })

    return pd.DataFrame(filas)


def calcular_puntaje_prioridad(df_metricas: pd.DataFrame) -> pd.DataFrame:
    """
    A partir de las métricas por cliente, calcula el Puntaje de
    Prioridad (0-100) combinando los 4 factores con sus pesos.

    Agrega las columnas:
        - score_oportunidad
        - score_valor_actual
        - score_dias
        - score_fidelizacion
        - Puntaje  (suma de los anteriores, 0-100)

    Y ordena el resultado de mayor a menor puntaje.
    """
    if df_metricas.empty:
        return df_metricas

    df = df_metricas.copy()

    df["score_oportunidad"]  = _normalizar(df["Monto_Mercado"])    * PESO_OPORTUNIDAD_MERCADO
    df["score_valor_actual"] = _normalizar(df["Monto_Itau"])       * PESO_VALOR_ACTUAL_ITAU
    df["score_dias"]         = _normalizar(df["Dias_Sin_Operar"])  * PESO_DIAS_SIN_OPERAR
    df["score_fidelizacion"] = _normalizar(df["N_Operaciones"])    * PESO_FIDELIZACION

    df["Puntaje"] = (
        df["score_oportunidad"]
        + df["score_valor_actual"]
        + df["score_dias"]
        + df["score_fidelizacion"]
    ).round(1)

    return df.sort_values("Puntaje", ascending=False).reset_index(drop=True)


# ===================================================================
# 3. RECOMENDACIÓN DE OFERTA (qué decir en la llamada)
# ===================================================================

def calcular_recomendacion_oferta(df_trader: pd.DataFrame, nit) -> dict:
    """
    Analiza el historial de un cliente específico (por NIT) y
    devuelve su patrón más frecuente de:

        - Producto más usado   (ej: SPOT, FORWARD, NEXT DAY)
        - Lado más usado        (ej: BANCO COMPRA / BANCO VENDE)
        - % de veces que ese patrón se repite

    Devuelve un diccionario con esa información, listo para
    mostrar como sugerencia al trader.
    """
    ops_cliente = df_trader[df_trader["NIT"] == nit]

    resultado = {
        "producto_frecuente": None,
        "pct_producto": 0,
        "lado_frecuente": None,
        "pct_lado": 0,
    }

    if ops_cliente.empty:
        return resultado

    # --- Producto más frecuente ---
    if "Producto" in ops_cliente.columns:
        conteo_producto = ops_cliente["Producto"].value_counts()
        if not conteo_producto.empty:
            resultado["producto_frecuente"] = conteo_producto.index[0]
            resultado["pct_producto"] = round(conteo_producto.iloc[0] / len(ops_cliente) * 100, 0)

    # --- Lado más frecuente (compra / vende) ---
    if "Lado" in ops_cliente.columns:
        conteo_lado = ops_cliente["Lado"].value_counts()
        if not conteo_lado.empty:
            resultado["lado_frecuente"] = conteo_lado.index[0]
            resultado["pct_lado"] = round(conteo_lado.iloc[0] / len(ops_cliente) * 100, 0)

    return resultado


def texto_sugerencia_oferta(recomendacion: dict) -> str:
    """
    Convierte el diccionario de recomendación en una frase legible
    para el trader, por ejemplo:

        "FORWARD · el cliente suele VENDER (80% de sus operaciones)"

    Si no hay suficiente información, devuelve un mensaje neutro.
    """
    producto = recomendacion.get("producto_frecuente")
    lado = recomendacion.get("lado_frecuente")
    pct_producto = recomendacion.get("pct_producto", 0)
    pct_lado = recomendacion.get("pct_lado", 0)

    if not producto and not lado:
        return "Sin historial suficiente para sugerir una oferta."

    partes = []
    if producto:
        partes.append(f"{producto} ({pct_producto:.0f}% de sus operaciones)")
    if lado:
        partes.append(f"{lado.title()} ({pct_lado:.0f}% de sus operaciones)")

    return " · ".join(partes)


# ===================================================================
# 4. NECESIDADES / ALERTAS DEL CLIENTE
# ===================================================================

def inferir_necesidades(fila_metricas: pd.Series) -> list:
    """
    A partir de las métricas de un cliente, infiere "etiquetas" de
    necesidad que ayudan al trader a entender el contexto rápido.

    Devuelve una lista de tuplas (texto, tipo_visual), donde
    tipo_visual sirve para darle un color distinto en la interfaz.
    """
    necesidades = []

    if fila_metricas["Dias_Sin_Operar"] > UMBRAL_DIAS_REACTIVACION:
        necesidades.append(("Reactivación – cliente inactivo", "alerta"))

    if fila_metricas["Pct_Mercado"] > 50:
        necesidades.append(("Oportunidad – opera más con la competencia", "oportunidad"))

    if fila_metricas["N_Operaciones"] >= UMBRAL_OPERACIONES_FIEL and fila_metricas["Pct_Mercado"] < 30:
        necesidades.append(("Cliente fiel – posible cross-sell", "fidelidad"))

    if fila_metricas["N_Operaciones"] == 1:
        necesidades.append(("Cliente nuevo – seguimiento inicial", "nuevo"))

    if not necesidades:
        necesidades.append(("Sin alertas urgentes", "neutral"))

    return necesidades


# ===================================================================
# 5. FUNCIÓN PRINCIPAL — todo en un solo paso
# ===================================================================

def generar_priorizacion(df_trader: pd.DataFrame) -> pd.DataFrame:
    """
    Punto de entrada único: recibe las operaciones de un trader y
    devuelve un DataFrame, una fila por cliente, con:

        - Todas las métricas (montos, días, operaciones, % mercado)
        - El puntaje de prioridad (0-100)
        - La recomendación de oferta ya en texto
        - Las necesidades inferidas

    Ordenado de mayor a menor prioridad (el #1 es a quien llamar primero).
    """
    if df_trader.empty:
        return pd.DataFrame()

    df_metricas = calcular_metricas_por_cliente(df_trader)
    df_puntaje = calcular_puntaje_prioridad(df_metricas)

    # Agregar recomendación de oferta y necesidades, cliente por cliente
    sugerencias = []
    necesidades_lista = []

    for _, fila in df_puntaje.iterrows():
        recomendacion = calcular_recomendacion_oferta(df_trader, fila["NIT"])
        sugerencias.append(texto_sugerencia_oferta(recomendacion))
        necesidades_lista.append(inferir_necesidades(fila))

    df_puntaje["Sugerencia_Oferta"] = sugerencias
    df_puntaje["Necesidades"] = necesidades_lista

    return df_puntaje
