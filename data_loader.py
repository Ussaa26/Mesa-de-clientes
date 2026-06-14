
import pandas as pd
import gdown
import os
import tempfile


RUTA_OPERACIONES = "https://docs.google.com/spreadsheets/d/1w_SMaC88aWgV0ZMG6kI17qu8I6ToCvgV/export?format=xlsx"
RUTA_CLIENTES = "https://docs.google.com/spreadsheets/d/1-BoqjiefDtqQ0ILX-JFx1yZ30nHLmHQF/export?format=xlsx"
RUTA_CIIU = "https://docs.google.com/spreadsheets/d/10n3IllrQRzMWzOcAL1tZ_cmvjXIzAze4/export?format=xlsx"


def _normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Quita espacios extra en los nombres de columnas."""
    df.columns = [c.strip() for c in df.columns]
    return df


def _descargar_y_leer(file_id: str) -> pd.DataFrame:
    """
    Descarga un archivo de Google Drive por su ID usando gdown
    (más confiable que leer directamente desde una URL para
    archivos grandes), y lo carga como DataFrame.
    """
    carpeta_temp = tempfile.gettempdir()
    ruta_destino = os.path.join(carpeta_temp, f"{file_id}.xlsx")

    url = f"https://drive.google.com/uc?id={file_id}"
    gdown.download(url, ruta_destino, quiet=True, fuzzy=True)

    df = pd.read_excel(ruta_destino)
    return _normalizar_columnas(df)


def cargar_operaciones() -> pd.DataFrame:
    """Carga la base de operaciones (Fecha, NIT, Producto, Lado, Entidad, Moneda, Montos)."""
    return _descargar_y_leer(ID_OPERACIONES)


def cargar_clientes() -> pd.DataFrame:
    """Carga la base de perfiles de clientes/BUC (ID, Segmento, Cod_Cartera, CIIU_BUC, etc.)."""
    return _descargar_y_leer(ID_CLIENTES)


def cargar_ciiu() -> pd.DataFrame:
    """Carga el catálogo CIIU (código -> nombre del sector económico)."""
    return _descargar_y_leer(ID_CIIU)


def cruzar_bases(
    df_operaciones: pd.DataFrame,
    df_clientes: pd.DataFrame,
    df_ciiu: pd.DataFrame,
) -> pd.DataFrame:
    """
    Cruza las 3 bases en cadena:

    1) Operaciones <-> Clientes/BUC   por NIT (operaciones) = ID (clientes)
    2) Resultado    <-> CIIU          por CIIU_BUC (clientes) = COD_ACT_CIIU_NOCLI (ciiu)
    """
    df = df_operaciones.merge(
        df_clientes,
        left_on="NIT",
        right_on="ID",
        how="left",
        suffixes=("", "_cliente"),
    )

    df = df.merge(
        df_ciiu,
        left_on="CIIU_BUC",
        right_on="COD_ACT_CIIU_NOCLI",
        how="left",
        suffixes=("", "_ciiu"),
    )

    return df


def obtener_lista_traders(df: pd.DataFrame, columna_trader: str = "Cod_Cartera") -> list:
    """Devuelve la lista de traders únicos (valores de Cod_Cartera) presentes en los datos."""
    return sorted(df[columna_trader].dropna().unique().tolist())


def filtrar_por_trader(df: pd.DataFrame, trader_id, columna_trader: str = "Cod_Cartera") -> pd.DataFrame:
    """Filtra el dataframe consolidado para mostrar solo los registros de un trader específico."""
    return df[df[columna_trader] == trader_id]


def cargar_datos_completos():
    """Carga las 3 bases, las cruza en cadena, y devuelve el dataframe consolidado."""
    df_ops = cargar_operaciones()
    df_clientes = cargar_clientes()
    df_ciiu = cargar_ciiu()
    df_consolidado = cruzar_bases(df_ops, df_clientes, df_ciiu)
    return df_consolidado
