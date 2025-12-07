import requests
from deltalake import write_deltalake, DeltaTable
import pyarrow as pa
import ast
import pandas as pd
import pyarrow as pa
import numpy as np  


# DATA EXTRACTION FUNCTION

def get_data(base_url, endpoint, data_field=None, params=None, headers=None):
  
    """
    Realiza una solicitud GET a una API para extraer datos y maneja paginación/errores.

    Esta función construye la URL final, realiza la solicitud, valida la respuesta
    HTTP y extrae el campo de datos principal si se especifica.
    
    Args:
        base_url: La URL base de la API (ej: "https://api.rawg.io/api").
        endpoint: El recurso específico al que se accederá (ej: "games").
        data_field: Nombre de la clave principal en la respuesta JSON que contiene 
                    la lista de resultados (ej: "results"). Si es None, retorna el JSON completo.
        params: Diccionario de parámetros de consulta (query parameters) a enviar 
                en la solicitud (ej: {'key': 'YOUR_KEY', 'dates': '2025-01-01,2025-12-31'}).
        headers: Diccionario de encabezados (headers) para la solicitud.

    Returns:
        list | dict | None: Los datos obtenidos de la API en formato JSON 
        (generalmente una lista de resultados o un diccionario), o **None** si ocurre un error.

    Raises:
        requests.exceptions.RequestException: Capturada internamente. Indica un error
        de red o un código de estado HTTP no exitoso (4xx o 5xx).
    """

    try:
        # Armo endpoint
        endpoint_url = f"{base_url}/{endpoint}"
        # Hago el request
        response = requests.get(endpoint_url, params=params, headers=headers)
        response.raise_for_status()  # Levanta una excepción si hay un error en la respuesta HTTP.

        # Verificar si los datos están en formato JSON.
        try:
            data = response.json()
            if data_field:
              data = data[data_field]
        except:
            print("El formato de respuesta no es el esperado")
            return None
        return data

    except requests.exceptions.RequestException as e:
        # Capturar cualquier error de solicitud, como errores HTTP.
        print(f"La petición ha fallado. Código de error : {e}")
        return None


# DATA STORAGE FUNCTIONS

def almacenamiento_datalake_merge(df, path, storage_options,partition_by=None):
    """
    Args:
        df: DataFrame de Pandas con los datos nuevos o actualizados.
        path: La ruta completa (URI S3/MinIO) donde se almacena la tabla Delta.
        storage_options: Diccionario con las opciones de conexión al almacenamiento (ej: credenciales S3).
        partition_by: Lista opcional de nombres de columnas para particionar la tabla 
                      físicamente. Solo se aplica cuando la tabla es **creada por primera vez**.

    Returns:
        None: La función no devuelve un valor, pero escribe la tabla en el Data Lake.
    """
    # Convertimos df a string para evitar problemas con Null

    if DeltaTable.is_deltatable(path, storage_options=storage_options,):
        print("📂 La tabla Delta ya existe. Ejecutando MERGE...")

        # Traigo la tabla actual en Pandas
        actual_data_table = DeltaTable(path, storage_options=storage_options)
        
        #Para el conteo
        df_actual = actual_data_table.to_pandas()
        df_actual = df_actual.fillna("").astype(str)
        ids_anteriores = set(df_actual["id"].tolist()) # mec reo una lista con los ids

        # Transformo los datos nuevos en Arrow
        new_data = pa.Table.from_pandas(df)
        ids_nuevos = set(df["id"].tolist())

        # Aplico el merge
        (
            actual_data_table.merge(
                source=new_data,
                source_alias="src",
                target_alias="tgt",
                predicate="src.id = tgt.id"
            )
            .when_matched_update_all()       # actualiza todos los campos
            .when_not_matched_insert_all()   # inserta nuevos registros
            .execute()
        )

        # Conteo aproximado
        updated = len(ids_anteriores.intersection(ids_nuevos)) # Cuento los ids comununes usa la interjeccion de conjuntos
        inserted = len(ids_nuevos - ids_anteriores) #cuento nuevos ids diferencia de conjuntos
        print(f"✅ Merge ejecutado correctamente. {inserted} registros insertados, {updated} registros actualizados.")

    else:
        print("🆕 No existe la tabla. Creando una nueva en Delta Lake...")

        write_deltalake(
            path,
            df,
            mode="error",
            storage_options=storage_options,
            partition_by=partition_by
        )
        print(f"✅ Tabla creada en {path}. {len(df)} registros insertados.")

def almacenamiento_datalake_overwrite(df, path, storage_options):
    """
    Sobrescribe la carpeta delta en 'path' con el contenido del DataFrame.
    Si existe, la reemplaza; si no existe, crea una nueva.
    """
    write_deltalake(
        path,
        df,
        mode="overwrite",
        storage_options=storage_options
    )

# DATA PROCESSING FUNCTIONS

def castear_json(df, col):
    """
    Convierte strings que representan listas/dicts en objetos reales (list/dict).
    """
    df[col] = df[col].apply(
        lambda x: ast.literal_eval(x) if isinstance(x, str) else x
    )
    return df

def limpiar_json(df, col, clave="id"):
    """
    Normaliza una columna que contiene listas de diccionarios, extrayendo únicamente 
    el valor de una clave específica (generalmente un ID).

    Esta función maneja estructuras anidadas comunes en APIs, buscando la 'clave' en:
    1. El nivel superior del diccionario.
    2. Un subdiccionario anidado dentro del diccionario principal.

    Args:
        df (pd.DataFrame): DataFrame de Pandas que contiene la columna a procesar.
        col (str): Nombre de la columna que contiene listas de diccionarios JSON (ej: 'genres', 'platforms').
        clave (str, optional): La clave cuyo valor se desea extraer (por defecto, "id").

    Returns:
        pd.DataFrame: El DataFrame original con la columna 'col' transformada. 
                      La columna contendrá ahora listas planas de los IDs extraídos (o None si no se encuentran).
    """
    def extraer_id(item):
        # Caso 1  la clave está directamente en el dict
        if clave in item:
            return item[clave]
        
        # Caso 2  buscar subdiccionarios con esa clave
        for v in item.values():
            if isinstance(v, dict) and clave in v:
                return v[clave]
        
        return None  # Si no se encuentra el ID
    
    df[col] = df[col].apply(
        lambda lst: [extraer_id(x) for x in lst] if isinstance(lst, list) else []
    )
    
    return df

def procesar_dimension(df_meta, prefix, extra_cols=[]):
    # ---- 1. Selección de columnas ----
    base_cols = ["id", "name", "games_count"]
    cols = base_cols + extra_cols

    df_dim = df_meta[cols].copy()

    # 2 Casteo dats
    df_dim["id"] = pd.to_numeric(df_dim["id"], errors="coerce").astype("Int64")
    df_dim["games_count"] = pd.to_numeric(df_dim["games_count"], errors="coerce").astype("Int64")
    df_dim["name"] = df_dim["name"].astype("string")
  

    # 3 Arreglo nombres y relleno nulos
    df_dim["name"] = df_dim["name"].str.strip().str.lower().str.title()
   

    # 4 Elimino nulos en caso de que no tengan id o nombre
    df_dim = df_dim[df_dim["name"].notna()]
    df_dim = df_dim[df_dim["id"].notna()]

    # 5 Elimino duplicados
    df_dim = df_dim.drop_duplicates(subset=["id"])

    return df_dim

def agregar_faltantes(df_origen, df_dimension, id_col='id', name_col='name', count_col=None, extra_cols=None):
    """"
    Normaliza una columna que contiene listas de diccionarios, extrayendo el ID.

    Convierte listas de objetos JSON complejos (ej: [{'id': 1, 'name': 'A'}]) 
    en una lista plana de identificadores (ej: [1]). Es tolerante a estructuras
    anidadas comunes en APIs.

    Args:
        df (pd.DataFrame): DataFrame de entrada.
        col (str): Nombre de la columna con los datos JSON a limpiar.
        clave (str, optional): La clave cuyo valor se desea extraer (por defecto, "id").

    Returns:
        pd.DataFrame: DataFrame con la columna especificada transformada a listas de IDs.
    """
    
    # Arreglo tipos de datos
    df_dim = df_dimension[[id_col, name_col]].copy()
    df_dim[id_col] = df_dim[id_col].astype(int)
    df_origen[id_col] = df_origen[id_col].astype(int)
    
    # Identifico faltantes
    faltantes = df_dim[~df_dim[id_col].isin(df_origen[id_col])].copy()
    
    # Creo columnas de conteo si no existen
    if count_col and count_col not in df_origen.columns:
        df_origen[count_col] = -1
    if count_col:
        faltantes[count_col] = -1
    
    # Creo columnas extra si no existen
    if extra_cols:
        for col in extra_cols:
            if col not in df_origen.columns:
                df_origen[col] = 'unknown'
            faltantes[col] = 'unknown'
    
    print(f"⚠️ {len(faltantes)} registros faltantes identificados.")
    # Concatenar solo los faltantes
    df_origen = pd.concat([df_origen, faltantes], ignore_index=True)
    
    # Ordenar por ID
    df_origen = df_origen.sort_values(id_col).reset_index(drop=True)
    
    return df_origen

