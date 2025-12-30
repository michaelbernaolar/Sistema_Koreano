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
        criterio = f"%{criterio.lower()}%"
        query += """
            AND (
                LOWER(p.id) LIKE %s OR
                LOWER(p.descripcion) LIKE %s OR
                LOWER(p.catalogo) LIKE %s OR
                LOWER(p.marca) LIKE %s OR
                LOWER(p.modelo) LIKE %s
            )
        """
        params.extend([criterio] * 5)

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

    if criterio:
        criterio = f"%{criterio.lower()}%"
        query += """
            AND (
                LOWER(p.id) LIKE %s OR
                LOWER(p.descripcion) LIKE %s OR
                LOWER(p.catalogo) LIKE %s OR
                LOWER(p.marca) LIKE %s OR
                LOWER(p.modelo) LIKE %s
            )
        """
        params.extend([criterio] * 5)

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
        WHERE p.activo = true
    """, conn)
    conn.close()
    return df