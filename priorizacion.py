

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
        - Moneda más usada      (ej: USD, EUR)
        - % de veces que cada patrón se repite

    Devuelve un diccionario con esa información, listo para
    mostrar como sugerencia al trader.
    """
    ops_cliente = df_trader[df_trader["NIT"] == nit]

    resultado = {
        "producto_frecuente": None,
        "pct_producto": 0,
        "lado_frecuente": None,
        "pct_lado": 0,
        "moneda_frecuente": None,
        "pct_moneda": 0,
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

    # --- Moneda más frecuente ---
    if "Moneda" in ops_cliente.columns:
        conteo_moneda = ops_cliente["Moneda"].value_counts()
        if not conteo_moneda.empty:
            resultado["moneda_frecuente"] = conteo_moneda.index[0]
            resultado["pct_moneda"] = round(conteo_moneda.iloc[0] / len(ops_cliente) * 100, 0)

    return resultado


def texto_sugerencia_oferta(recomendacion: dict) -> str:
    """
    Convierte el diccionario de recomendación en una frase legible
    para el trader, por ejemplo:

        "FORWARD · el cliente suele VENDER · Moneda más usada: USD (90%)"

    Si no hay suficiente información, devuelve un mensaje neutro.
    """
    producto = recomendacion.get("producto_frecuente")
    lado = recomendacion.get("lado_frecuente")
    moneda = recomendacion.get("moneda_frecuente")
    pct_producto = recomendacion.get("pct_producto", 0)
    pct_lado = recomendacion.get("pct_lado", 0)
    pct_moneda = recomendacion.get("pct_moneda", 0)

    if not producto and not lado and not moneda:
        return "Sin historial suficiente para sugerir una oferta."

    partes = []
    if producto:
        partes.append(f"{producto} ({pct_producto:.0f}% de sus operaciones)")
    if lado:
        partes.append(f"{lado.title()} ({pct_lado:.0f}% de sus operaciones)")
    if moneda:
        partes.append(f"Moneda: {moneda} ({pct_moneda:.0f}% de sus operaciones)")

    return " · ".join(partes)


# ===================================================================
# 4. NECESIDADES / ALERTAS DEL CLIENTE
# ===================================================================

def obtener_sector_economico(df_trader: pd.DataFrame, nit) -> str:
    """
    Devuelve el nombre del sector económico (columna DES_CIIU) del
    cliente, tal como viene en los datos cruzados con la tabla CIIU.

    Este dato es informativo: muestra al trader la actividad
    económica real del cliente (no es una inferencia del sistema),
    para que el trader use su propio criterio.

    Si no hay información disponible, devuelve "No disponible".
    """
    ops_cliente = df_trader[df_trader["NIT"] == nit]

    if ops_cliente.empty or "DES_CIIU" not in ops_cliente.columns:
        return "No disponible"

    valor = ops_cliente["DES_CIIU"].dropna()

    if valor.empty:
        return "No disponible"

    texto = str(valor.iloc[0]).strip()

    if texto.lower() in ("nan", "sin informacion", "sin información", ""):
        return "No disponible"

    return texto


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
# 5. RANKINGS TOP N — clientes más activos por moneda y por producto
# ===================================================================

def ranking_clientes_por_moneda(df_trader: pd.DataFrame, monedas: list, top_n: int = 5) -> pd.DataFrame:
    """
    Devuelve el ranking de los clientes (NIT) con más operaciones en
    las monedas indicadas (ej: ['USD/COP', 'EUR/COP']).

    A diferencia de un conteo simple, aquí se agrupa por
    (Cliente, Moneda), de modo que cada fila del ranking indica
    CLARAMENTE en qué moneda específica tiene esas operaciones
    ese cliente. Si un cliente opera en varias monedas, aparecerá
    una fila por cada combinación Cliente-Moneda.

    Columnas devueltas: NIT, Moneda, N_Operaciones
    Ordenado de mayor a menor N_Operaciones (Top N).
    """
    columnas_vacias = ["NIT", "Moneda", "N_Operaciones"]

    if df_trader.empty or "Moneda" not in df_trader.columns:
        return pd.DataFrame(columns=columnas_vacias)

    filtrado = df_trader[df_trader["Moneda"].isin(monedas)]

    if filtrado.empty:
        return pd.DataFrame(columns=columnas_vacias)

    ranking = (
        filtrado.groupby(["NIT", "Moneda"])
        .size()
        .reset_index(name="N_Operaciones")
        .sort_values("N_Operaciones", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )

    return ranking


def ranking_clientes_por_producto(df_trader: pd.DataFrame, productos: list, top_n: int = 5) -> pd.DataFrame:
    """
    Devuelve el ranking de los clientes (NIT) con más operaciones en
    los productos indicados (ej: ['SPOT', 'FORWARD']).

    A diferencia de un conteo simple, aquí se agrupa por
    (Cliente, Producto), de modo que cada fila del ranking indica
    CLARAMENTE en qué producto específico tiene esas operaciones
    ese cliente. Si un cliente opera en varios productos, aparecerá
    una fila por cada combinación Cliente-Producto.

    Columnas devueltas: NIT, Producto, N_Operaciones
    Ordenado de mayor a menor N_Operaciones (Top N).
    """
    columnas_vacias = ["NIT", "Producto", "N_Operaciones"]

    if df_trader.empty or "Producto" not in df_trader.columns:
        return pd.DataFrame(columns=columnas_vacias)

    filtrado = df_trader[df_trader["Producto"].isin(productos)]

    if filtrado.empty:
        return pd.DataFrame(columns=columnas_vacias)

    ranking = (
        filtrado.groupby(["NIT", "Producto"])
        .size()
        .reset_index(name="N_Operaciones")
        .sort_values("N_Operaciones", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )

    return ranking


# ===================================================================
# 6. FUNCIÓN PRINCIPAL — todo en un solo paso
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

    # Agregar recomendación de oferta, necesidades y sector económico
    sugerencias = []
    necesidades_lista = []
    sectores = []

    for _, fila in df_puntaje.iterrows():
        recomendacion = calcular_recomendacion_oferta(df_trader, fila["NIT"])
        sugerencias.append(texto_sugerencia_oferta(recomendacion))
        necesidades_lista.append(inferir_necesidades(fila))
        sectores.append(obtener_sector_economico(df_trader, fila["NIT"]))

    df_puntaje["Sugerencia_Oferta"] = sugerencias
    df_puntaje["Necesidades"] = necesidades_lista
    df_puntaje["Sector_Economico"] = sectores

    return df_puntaje
