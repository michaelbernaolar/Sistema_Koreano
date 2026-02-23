# services/producto_service.py
import pandas as pd
from db import get_connection
from streamlit import cache_data

def obtener_valores_unicos(columna):
    conn = get_connection()
    df = pd.read_sql_query(
        f"SELECT DISTINCT {columna} FROM producto WHERE {columna} IS NOT NULL",
        conn
    )
    conn.close()
    return df[columna].dropna().sort_values().tolist()

def procesar_criterio_comodin(criterio: str):
    if not criterio:
        return []

    criterio = criterio.lower().strip()

    # eliminar múltiples *
    while "**" in criterio:
        criterio = criterio.replace("**", "*")

    # dividir por *
    palabras = [p.strip() for p in criterio.split("*") if p.strip()]

    return palabras


def buscar_producto_avanzado(
    criterio=None,
    marca=None,
    categoria=None,
    stock=None,
    limit=20
):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT p.id, p.descripcion, p.id_categoria, c.nombre as categoria, 
               p.catalogo, p.marca, p.modelo, p.ubicacion, p.precio_venta,
               p.costo_promedio,p.margen_utilidad, p.stock_actual, p.imagen, p.activo, p.unidad_base
        FROM producto p 
        LEFT JOIN categoria c ON p.id_categoria = c.id 
        WHERE 1=1
    """
    params = []

    if criterio:
        palabras = procesar_criterio_comodin(criterio)

        for palabra in palabras:
            like = f"%{palabra}%"

            query += """
                AND (
                    LOWER(CAST(p.id AS TEXT)) LIKE %s OR
                    LOWER(p.descripcion) LIKE %s OR
                    LOWER(p.catalogo) LIKE %s OR
                    LOWER(p.marca) LIKE %s OR
                    LOWER(p.modelo) LIKE %s
                )
            """
            params.extend([like] * 5)

    if marca and marca != "Todos":
        query += " AND p.marca = %s"
        params.append(marca)

    if categoria and categoria != "Todos":
        query += " AND c.nombre = %s"
        params.append(categoria)

    if stock == "Con stock":
        query += " AND p.stock_actual > 0"
    elif stock == "Sin stock":
        query += " AND p.stock_actual = 0"

    query += " ORDER BY p.id LIMIT %s"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()

    df = pd.DataFrame(rows, columns=[col[0] for col in cursor.description])
    conn.close()
    return df


def contar_productos(
    criterio=None,
    marca=None,
    categoria=None,
    stock=None
):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT COUNT(*)
        FROM producto p
        LEFT JOIN categoria c ON p.id_categoria = c.id
        WHERE 1=1
    """
    params = []

    # 🔎 MISMA LÓGICA QUE buscar_producto_avanzado
    if criterio:
        palabras = procesar_criterio_comodin(criterio)

        for palabra in palabras:
            like = f"%{palabra}%"

            query += """
                AND (
                    LOWER(CAST(p.id AS TEXT)) LIKE %s OR
                    LOWER(p.descripcion) LIKE %s OR
                    LOWER(p.catalogo) LIKE %s OR
                    LOWER(p.marca) LIKE %s OR
                    LOWER(p.modelo) LIKE %s
                )
            """
            params.extend([like] * 5)

    if marca and marca != "Todos":
        query += " AND p.marca = %s"
        params.append(marca)

    if categoria and categoria != "Todos":
        query += " AND c.nombre = %s"
        params.append(categoria)

    if stock == "Con stock":
        query += " AND p.stock_actual > 0"
    elif stock == "Sin stock":
        query += " AND p.stock_actual = 0"

    cursor.execute(query, params)
    total = cursor.fetchone()[0]

    conn.close()
    return total

@cache_data(ttl=300)
def obtener_filtros_productos():
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT DISTINCT
            p.marca,
            c.nombre AS categoria
        FROM producto p
        LEFT JOIN categoria c ON p.id_categoria = c.id
        WHERE p.activo = 1
    """, conn)
    conn.close()
    return df

def to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
