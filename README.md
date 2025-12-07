# 📘 TP1 - Extracción y Almacenamiento de Datos

**Autor:** Pablo Luberriaga  
**Fecha:** Noviembre 2025  
**Fuente:** RAWG Video Games Database API

---

## 📋 Tabla de Contenidos

- [Descripción General](#-descripción-general)
- [Objetivos](#-objetivos)
- [Arquitectura del Proyecto](#-arquitectura-del-proyecto)
- [Endpoints Utilizados](#-endpoints-utilizados)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Instalación y Configuración](#-instalación-y-configuración)
- [Pipeline ETL](#-pipeline-etl)
- [Modelo de Datos](#-modelo-de-datos)
- [Datasets GOLD](#-datasets-gold)
- [Uso](#-uso)
- [Tecnologías Utilizadas](#-tecnologías-utilizadas)

---

## 🎯 Descripción General

Este proyecto implementa un pipeline ETL completo que extrae información de videojuegos desde la API pública de RAWG, procesa los datos en múltiples capas (Bronze, Silver, Gold) y los almacena en formato Delta Lake simulando un entorno de data lake profesional.

El sistema está diseñado para manejar tanto **ingesta completa** (metadatos estáticos) como **ingesta incremental** (juegos actualizados recientemente), preparando los datos para análisis posteriores sobre tendencias, ratings, géneros, plataformas y engagement de usuarios.

---

## 🎯 Objetivos

### Objetivo General
Desarrollar un proceso ETL que permita extraer información estática (metadatos) y dinámica (juegos actualizados recientemente) desde la API pública de RAWG, almacenando los datos en formato Delta Lake para su análisis posterior.

### Objetivos Específicos
1. ✅ Implementar un proceso de extracción incremental (juegos actualizados recientemente)
2. ✅ Implementar una extracción completa (metadata: géneros, plataformas, desarrolladores, etc.)
3. ✅ Convertir los datos a DataFrames de Pandas para su manipulación
4. ✅ Guardar los datasets en formato Delta Lake con arquitectura medallion (Bronze, Silver, Gold)
5. ✅ Preparar datasets analíticos para análisis de videojuegos por género, rating, fecha de lanzamiento, etc.

### Justificación Técnica
RAWG ofrece endpoints con metadatos (géneros, plataformas, desarrolladores) y listados de juegos que varían en el tiempo (ranking, novedades), lo que permite implementar estrategias de ingesta diferenciadas según la naturaleza de los datos.

---

## 🏗️ Arquitectura del Proyecto

El proyecto sigue una **arquitectura medallion** de tres capas:

```
📦 Data Lake (MinIO/S3)
├── 🥉 BRONZE (Raw Data)
│   ├── games/                    # Datos crudos de juegos
│   └── metadata/                 # Metadatos sin procesar
│       ├── genres/
│       ├── developers/
│       ├── publishers/
│       ├── stores/
│       ├── tags/
│       ├── creators/
│       └── platforms/
│
├── 🥈 SILVER (Cleaned & Normalized)
│   ├── games/                    # Tabla de hechos limpia
│   └── metadata/                 # Dimensiones normalizadas
│       ├── genres/
│       ├── developers/
│       ├── publishers/
│       ├── stores/
│       ├── tags/
│       ├── platforms/
│       ├── parent_platforms/
│       ├── creators/
│       ├── creator_positions/
│       └── ratings/
│
└── 🥇 GOLD (Analytics Ready)
    ├── kpis_games/               # KPIs generales
    ├── top_rated/                # Juegos mejor valorados
    ├── top_rated_yearly/         # Top por año
    ├── most_played/              # Más jugados
    ├── top_metacritic/           # Mejores según crítica
    ├── yearly_trends/            # Tendencias anuales
    ├── engagement/               # Métricas de engagement
    ├── platform_stats/           # Estadísticas por plataforma
    └── segment_summary/          # Resumen por segmentos
```

---

## 🌐 Endpoints Utilizados

**URL Base:** `https://api.rawg.io/api`

### Ingesta Full - Metadatos (Datos Estáticos)

| Endpoint      | Descripción                                    |
|---------------|------------------------------------------------|
| `/genres`     | Lista de géneros de videojuegos               |
| `/developers` | Información sobre desarrolladores de juegos   |
| `/publishers` | Información sobre editoras de videojuegos     |
| `/stores`     | Información sobre tiendas de videojuegos      |
| `/tags`       | Etiquetas asociadas a juegos                  |
| `/creators`   | Información sobre creadores de contenido      |
| `/platforms`  | Plataformas de videojuegos                    |

### Ingesta Incremental - Videojuegos (Datos Dinámicos)

| Endpoint | Descripción                      |
|----------|----------------------------------|
| `/games` | Lista de videojuegos publicados  |

---

## 📁 Estructura del Proyecto

```
📦 Proyecto_ETL_RAWG/
├── 📓 PabloLuberriaga_TP1.ipynb    # Notebook principal del pipeline
├── 🐍 utils.py                      # Funciones auxiliares
├── ⚙️ pipeline.conf                 # Archivo de configuración
├── 📄 requirements.txt              # Dependencias del proyecto
└── 📖 README.md                     # Este archivo
```

### Archivos Principales

- **`PabloLuberriaga_TP1.ipynb`**: Notebook Jupyter con el pipeline ETL completo
- **`utils.py`**: Módulo con funciones reutilizables para extracción, transformación y almacenamiento
- **`pipeline.conf`**: Configuración de credenciales (API Key, S3/MinIO)
- **`requirements.txt`**: Librerías necesarias para ejecutar el proyecto

---

## 🔧 Instalación y Configuración

### Prerrequisitos

- Python 3.12+
- Jupyter Notebook
- Acceso a MinIO/S3
- API Key de RAWG (gratuita)

### Instalación

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd Proyecto_ETL_RAWG
```

2. **Crear entorno virtual**
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar credenciales**

Editar el archivo `pipeline.conf`:

```ini
[RAWG]
API_KEY = tu_api_key_aqui

[S3_STORAGE]
AWS_ENDPOINT_URL = http://tu-endpoint:9002
AWS_ACCESS_KEY_ID = tu_access_key
AWS_SECRET_ACCESS_KEY = tu_secret_key
AWS_ALLOW_HTTP = true
AWS_CONDITIONAL_PUT = etag
AWS_S3_ALLOW_UNSAFE_RENAME = true
```

---

## 🔄 Pipeline ETL

### 1. 🥉 Capa BRONZE - Extracción

**Ingesta Full (Metadatos)**
- Extracción completa de dimensiones estáticas
- Almacenamiento en formato crudo (JSON normalizado)
- Estrategia: MERGE (permite actualizaciones futuras)

**Ingesta Incremental (Games)**
- Extracción de juegos actualizados en las últimas 24 horas
- Usa parámetro `updated` de la API
- Estrategia: MERGE por ID (inserta nuevos, actualiza existentes)

### 2. 🥈 Capa SILVER - Transformación

**Limpieza y Normalización:**
- Estandarización de nombres de columnas
- Eliminación de columnas irrelevantes
- Casteo de tipos de datos (Int64, float32, string, boolean, datetime)
- Imputación de valores nulos
- Normalización de estructuras JSON anidadas

**Modelo Dimensional:**
- Tabla de hechos: `games`
- Dimensiones: `genres`, `developers`, `publishers`, `stores`, `tags`, `platforms`, `creators`, etc.
- Relaciones mediante listas de IDs (formato JSON)

### 3. 🥇 Capa GOLD - Analytics

Generación de datasets analíticos listos para consumo:
- KPIs generales del catálogo
- Rankings y tops
- Tendencias temporales
- Métricas de engagement
- Estadísticas por plataforma/tag/segmento

---

## 📊 Modelo de Datos

### Tabla de Hechos: GAMES

| Campo                  | Tipo    | Descripción                           |
|------------------------|---------|---------------------------------------|
| id                     | Int64   | Identificador único del juego         |
| name                   | string  | Nombre del juego                      |
| released_date          | date    | Fecha de lanzamiento                  |
| released_year          | Int64   | Año de lanzamiento                    |
| rating                 | float32 | Rating promedio (0-5)                 |
| metacritic             | float32 | Score de Metacritic                   |
| average_playtime_hours | Int64   | Horas promedio de juego               |
| genres                 | string  | Lista de IDs de géneros (JSON)        |
| platforms              | string  | Lista de IDs de plataformas (JSON)    |
| stores                 | string  | Lista de IDs de tiendas (JSON)        |
| tags                   | string  | Lista de IDs de tags (JSON)           |
| added_to_list          | Int64   | Usuarios que agregaron el juego       |
| esrb_rating_name       | category| Clasificación ESRB                    |

### Dimensiones Principales

**DIM_GENRES**
- id, name, games_count

**DIM_PLATFORMS**
- id, name, games_count

**DIM_DEVELOPERS**
- id, name, games_count

**DIM_PUBLISHERS**
- id, name, games_count, domain

**DIM_TAGS**
- id, name, games_count

---

## 🏆 Datasets GOLD

| Dataset               | Pregunta de Negocio                                                           |
|-----------------------|-------------------------------------------------------------------------------|
| **kpis_games**        | ¿Cuál es el estado general del catálogo de juegos?                          |
| **top_rated**         | ¿Cuáles son los mejores juegos según la valoración de los usuarios?         |
| **top_rated_yearly**  | ¿Qué juegos destacaron año a año según el rating?                            |
| **most_played**       | ¿Qué juegos generan mayor engagement y volumen de usuarios?                  |
| **top_metacritic**    | ¿Qué juegos tienen mejor recepción crítica profesional?                     |
| **yearly_trends**     | ¿Cómo evolucionan las tendencias del mercado gaming?                         |
| **engagement**        | ¿Qué juegos tienen mayor tasa de completado, abandono y actividad?          |
| **platform_stats**    | ¿Qué plataformas muestran mejor rendimiento?                                 |
| **segment_summary**   | ¿Cómo se comportan grupos de juegos según popularidad?                      |

---

## 💻 Uso

### Ejecución del Pipeline Completo

```bash
jupyter notebook PabloLuberriaga_TP1.ipynb
```

Ejecutar las celdas en orden:
1. **Importación de librerías**
2. **Configuración y credenciales**
3. **Extracción - Capa Bronze**
4. **Transformación - Capa Silver**
5. **Analytics - Capa Gold**

### Funciones Principales (utils.py)

```python
# Extracción
get_data(base_url, endpoint, data_field, params, headers)

# Almacenamiento
almacenamiento_datalake_merge(df, path, storage_options, partition_by)
almacenamiento_datalake_overwrite(df, path, storage_options)

# Procesamiento
castear_json(df, col)
limpiar_json(df, col, clave)
procesar_dimension(df_meta, prefix, extra_cols)
agregar_faltantes(df_origen, df_dimension, id_col, name_col)
```

---

## 🛠️ Tecnologías Utilizadas

| Tecnología   | Versión  | Propósito                              |
|--------------|----------|----------------------------------------|
| Python       | 3.12+    | Lenguaje principal                     |
| Pandas       | 2.2.3    | Manipulación de datos                  |
| Delta Lake   | 0.17.3   | Formato de almacenamiento transaccional|
| PyArrow      | 17.0.0   | Formato columnar eficiente             |
| Requests     | 2.32.3   | Llamadas HTTP a la API                 |
| MinIO/S3     | -        | Data Lake distribuido                  |
| Jupyter      | -        | Entorno de desarrollo interactivo      |

---

## 📞 Contacto

**Pablo Luberriaga**  
Noviembre 2025

---

*Proyecto desarrollado con fines académicos utilizando la API pública de RAWG*