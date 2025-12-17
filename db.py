# db.py
import psycopg2
import pandas as pd
from datetime import datetime
import os

from dotenv import load_dotenv

load_dotenv()  # ← esto es clave

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL no está definida")

def get_connection():
    return psycopg2.connect(
        DATABASE_URL,
        sslmode="require"  # clave para nube
    )

# -------------------------
# Inicialización de la BD
# -------------------------
def init_db():
    """Crea las tablas necesarias si no existen."""
    conn = get_connection()
    cursor = conn.cursor()

    # Tabla de categorias
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categoria (
        id SERIAL PRIMARY KEY,
        nombre TEXT UNIQUE
    )
    ''')

    # Tabla de cliente
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cliente (
        id TEXT PRIMARY KEY,
        nombre TEXT,
        dni_ruc TEXT,
        telefono TEXT,
        direccion TEXT
    )
    ''')

    # Tabla de proveedor
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS proveedor (
        id TEXT PRIMARY KEY,
        nombre TEXT,
        dni_ruc TEXT,
        telefono TEXT,
        direccion TEXT
    )
    ''')

    # Tabla de producto
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS producto (
        id TEXT PRIMARY KEY,
        descripcion TEXT,
        id_categoria INTEGER,
        catalogo TEXT,
        marca TEXT,
        modelo TEXT,
        ubicacion TEXT,
        unidad_base TEXT,
        stock_actual NUMERIC(12,4),
        precio_venta NUMERIC(12,2),
        imagen TEXT,
        activo INTEGER DEFAULT 1,
        costo_promedio NUMERIC(12,4),
        costo_ultima_compra NUMERIC(12,4),
        valor_inventario NUMERIC(14,2),
        margen_utilidad NUMERIC(5,4) DEFAULT NULL,
        valor_venta NUMERIC(12,2) DEFAULT NULL,
        FOREIGN KEY (id_categoria) REFERENCES categoria(id)
    )
    ''')

    # Tabla de venta
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS venta (
        id SERIAL PRIMARY KEY,
        fecha TIMESTAMP,
        id_cliente TEXT,
        suma_total NUMERIC(14,2),
        descuento NUMERIC(14,2),
        op_gravada NUMERIC(14,2),
        op_gratuita NUMERIC(14,2),
        igv NUMERIC(14,2),       
        total NUMERIC(14,2),
        tipo_comprobante TEXT,
        nro_comprobante TEXT,
        metodo_pago TEXT,
        FOREIGN KEY (id_cliente) REFERENCES cliente(id)
    )
    ''')

    # Tabla de venta_detalle
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS venta_detalle (
        id SERIAL PRIMARY KEY,
        id_venta INTEGER,
        id_producto TEXT,
        cantidad NUMERIC(12,4),
        precio_unitario NUMERIC(12,2),
        sub_total NUMERIC(14,2),
        precio_final NUMERIC(14,2),
        FOREIGN KEY (id_venta) REFERENCES venta(id),
        FOREIGN KEY (id_producto) REFERENCES producto(id)
    )
    ''')

    # Tabla de compras
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS compras (
        id SERIAL PRIMARY KEY,
        fecha TIMESTAMP,
        id_proveedor TEXT,
        nro_doc TEXT,
        tipo_doc TEXT,
        suma_total NUMERIC(12,2),
        descuento NUMERIC(12,2),
        op_gravada NUMERIC(12,2),
        op_gratuita NUMERIC(12,2),
        igv NUMERIC(12,2),       
        total NUMERIC(14,2),
        metodo_pago TEXT,
        FOREIGN KEY (id_proveedor) REFERENCES proveedor(id)
    )
    ''')

    # Tabla de compras_detalle
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS compras_detalle (
        id SERIAL PRIMARY KEY,
        id_compra INTEGER,
        id_producto TEXT,
        cantidad_compra NUMERIC(12,4),
        unidad_compra TEXT,
        factor_conversion NUMERIC(12,4),
        cantidad_final NUMERIC(12,4),
        precio_unitario NUMERIC(12,4),
        subtotal NUMERIC(14,2),
        FOREIGN KEY (id_compra) REFERENCES compras(id),
        FOREIGN KEY (id_producto) REFERENCES producto(id)
    )
    ''')

    # Tabla de producto_proveedor
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS producto_proveedor (
        id SERIAL PRIMARY KEY,
        id_producto TEXT,
        id_proveedor TEXT,
        unidad_compra TEXT,
        factor NUMERIC(12,4),
        precio_compra NUMERIC(12,4),
        lote_min NUMERIC(12,4),
        tiempo_entrega NUMERIC(12,4),
        FOREIGN KEY (id_producto) REFERENCES producto(id),
        FOREIGN KEY (id_proveedor) REFERENCES proveedor(id)
    )
    ''')

    # Tabla de movimientos
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS movimientos (
        id SERIAL PRIMARY KEY,
        id_producto TEXT,
        tipo TEXT,            -- 'entrada' o 'salida'
        cantidad NUMERIC(12,4),
        fecha TIMESTAMP,
        motivo TEXT,
        referencia TEXT,
        costo_unitario NUMERIC(12,4),
        valor_total NUMERIC(14,2), 
        FOREIGN KEY (id_producto) REFERENCES producto(id)
    )
    ''')

    # Tabla de configuración del sistema
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS configuracion (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        tipo_regimen TEXT DEFAULT 'Régimen General',
        igv NUMERIC(5,4) DEFAULT 0.18,
        margen_utilidad NUMERIC(5,4) DEFAULT 0.25,
        incluir_igv_en_precio INTEGER DEFAULT 1
    )
    ''')

    # Insertar registro inicial si no existe
    cursor.execute('''
    INSERT INTO configuracion (id, tipo_regimen, igv, margen_utilidad, incluir_igv_en_precio)
    VALUES (1, 'Régimen General', 0.18, 0.25, 1)
    ON CONFLICT (id) DO NOTHING
    ''')

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historial_precios (
        id SERIAL PRIMARY KEY,
        producto_id TEXT,
        precio_anterior NUMERIC(12,2),
        precio_nuevo NUMERIC(12,2),
        margen_usado NUMERIC(5,4),
        costo_promedio NUMERIC(12,4),
        fecha TIMESTAMP,
        FOREIGN KEY (producto_id) REFERENCES producto(id)
    )
    """)

    conn.commit()
    conn.close()

 


# -------------------------
# Funciones auxiliares
# -------------------------
def generar_codigo_correlativo(tabla, prefijo):
    """Genera código correlativo con prefijo + 5 dígitos"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT id FROM {tabla} ORDER BY id DESC LIMIT 1")
    ultimo = cursor.fetchone()
    conn.close()

    if ultimo:
        ultimo_num = int(ultimo[0].replace(prefijo, ""))
        nuevo_num = ultimo_num + 1
    else:
        nuevo_num = 1
    return f"{prefijo}{nuevo_num:05d}"


# -------------------------
# Categorías
# -------------------------
def obtener_categorias():
    conn = get_connection()
    df = pd.read_sql("SELECT id, nombre FROM categoria ORDER BY nombre", conn)
    conn.close()
    return df

def agregar_categoria(nombre):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO categoria (nombre) VALUES (%s)", (nombre,))
    conn.commit()
    conn.close()

def editar_categoria(id_cat, nuevo_nombre):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE categoria SET nombre=%s WHERE id=%s", (nuevo_nombre, id_cat))
    conn.commit()
    conn.close()

def eliminar_categoria(id_cat):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM categoria WHERE id=%s", (id_cat,))
    conn.commit()
    conn.close()


# -------------------------
# Productos
# -------------------------
def insertar_producto(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO producto (
            id, descripcion, id_categoria, catalogo, marca, modelo,
            ubicacion, unidad_base , stock_actual, precio_venta, imagen, activo
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', data)
    conn.commit()
    conn.close()

def mostrar_todos():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM producto", conn)
    conn.close()
    return df

def existe_codigo(id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM producto WHERE id = %s", (id,))
    fila = cursor.fetchone()
    conn.close()
    return fila

def actualizar_producto(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE producto SET
        descripcion = %s,
        id_categoria = %s,
        catalogo = %s,
        marca = %s,
        modelo = %s,
        ubicacion = %s,
        unidad_base = %s,
        stock_actual = %s,
        precio_venta = %s,
        imagen = %s,
        activo = %s,
        margen_utilidad=%s           
    WHERE id = %s
    ''', data)

    # 🔥 Recalcular precio y valor_venta CON el margen recién actualizado
    producto_id = data[-1]
    precio_anterior, precio_nuevo, margen_usado, costo_prom = recalcular_precios_producto(cursor, producto_id)

    # 📌 Registrar historial
    registrar_historial_precio(cursor, producto_id, precio_anterior, precio_nuevo, margen_usado, costo_prom)

    conn.commit()
    conn.close()

def actualizar_costo_promedio(cursor, id_producto, cantidad_entrada, costo_unitario_entrada):
    cursor.execute("SELECT stock_actual, costo_promedio FROM producto WHERE id = %s", (id_producto,))
    fila = cursor.fetchone()
    if not fila:
        return

    stock_actual, costo_promedio_actual = fila
    stock_actual = stock_actual or 0
    costo_promedio_actual = costo_promedio_actual or 0

    # 🔹 Si el producto es nuevo o no tiene costo previo
    if costo_promedio_actual == 0 or stock_actual == 0:
        nuevo_costo_promedio = costo_unitario_entrada
    else:
        total_valor_anterior = stock_actual * costo_promedio_actual
        total_valor_nuevo = cantidad_entrada * costo_unitario_entrada
        nuevo_costo_promedio = (total_valor_anterior + total_valor_nuevo) / (stock_actual + cantidad_entrada)

    nuevo_stock = stock_actual + cantidad_entrada

    cursor.execute("""
        UPDATE producto
        SET 
            stock_actual = %s, 
            costo_promedio = %s, 
            costo_ultima_compra = %s,
            valor_inventario = %s
        WHERE id = %s
    """, (
        nuevo_stock,
        round(nuevo_costo_promedio, 4),
        round(costo_unitario_entrada, 4),
        round(nuevo_stock * nuevo_costo_promedio, 2),
        id_producto
    ))

    return round(nuevo_costo_promedio, 4)

def registrar_salida_por_venta(cursor, id_producto, cantidad_salida, fecha, referencia):
    """Registra una salida por venta y actualiza el inventario."""
    # Obtener datos actuales del producto
    cursor.execute("SELECT stock_actual, costo_promedio FROM producto WHERE id = %s", (id_producto,))
    fila = cursor.fetchone()
    if not fila:
        return

    stock_actual, costo_promedio = fila
    stock_actual = stock_actual or 0
    costo_promedio = costo_promedio or 0

    # Calcular nuevo stock
    nuevo_stock = stock_actual - cantidad_salida
    if nuevo_stock < 0:
        nuevo_stock = 0  # evitar negativos

    # Valor de salida (para movimientos)
    valor_total = round(cantidad_salida * costo_promedio, 2)

    # Actualizar producto
    cursor.execute("""
        UPDATE producto
        SET stock_actual = %s, valor_inventario = %s
        WHERE id = %s
    """, (
        nuevo_stock,
        round(nuevo_stock * costo_promedio, 2),
        id_producto
    ))

    # Registrar movimiento
    cursor.execute("""
        INSERT INTO movimientos (id_producto, tipo, cantidad, fecha, motivo, referencia, costo_unitario, valor_total)
        VALUES (%s, 'salida', %s, %s, %s, %s, %s, %s)
    """, (id_producto, cantidad_salida, fecha, "Venta", referencia, costo_promedio, valor_total))


def redondear_050(valor):
    """Redondea hacia el múltiplo más cercano de 0.50."""
    return round(valor * 2) / 2

def recalcular_precios_producto(cursor, id_producto):
    # Obtener configuración global
    cursor.execute("SELECT igv, margen_utilidad FROM configuracion WHERE id = 1")
    config = cursor.fetchone()
    igv_global = config[0]
    margen_global = config[1]

    # Obtener datos del producto
    cursor.execute("""
        SELECT costo_promedio, margen_utilidad, precio_venta
        FROM producto 
        WHERE id = %s
    """, (id_producto,))
    fila = cursor.fetchone()

    if not fila:
        return None

    costo_promedio, margen_producto, precio_anterior = fila

    # Si el producto NO tiene margen asignado → usar el global
    margen = margen_producto if margen_producto not in (None, 0) else margen_global

    if margen >= 1:
        raise ValueError("El margen debe ser decimal (ej 0.20 para 20%)")

    # Cálculo
    valor_venta = costo_promedio / (1 - margen)
    precio_nuevo = redondear_050(valor_venta * (1 + igv_global))

    # Guardar en BD
    cursor.execute("""
        UPDATE producto
        SET valor_venta = %s, precio_venta = %s
        WHERE id = %s
    """, (round(valor_venta, 2), round(precio_nuevo, 2), id_producto))

    # ✨  ESTA ES LA CLAVE: retornar datos
    return precio_anterior, precio_nuevo, margen, costo_promedio


def recalcular_todos_los_precios():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM producto WHERE activo = 1")
    productos = cursor.fetchall()

    for (id_prod,) in productos:
        recalcular_precios_producto(cursor, id_prod)

    conn.commit()
    conn.close()


# -------------------------
# Configuración del sistema
# -------------------------
def obtener_configuracion():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT tipo_regimen, igv, margen_utilidad, incluir_igv_en_precio FROM configuracion WHERE id = 1")
    fila = cursor.fetchone()
    conn.close()

    if fila:
        return {
            "regimen": fila[0],
            "igv": fila[1],
            "margen_utilidad": fila[2],
            "incluir_igv_en_precio": bool(fila[3])
        }
    else:
        return {
            "regimen": "Régimen General",
            "igv": 0.18,
            "margen_utilidad": 0.25,
            "incluir_igv_en_precio": True
        }

def actualizar_configuracion(nuevo_regimen=None, nuevo_igv=None, nuevo_margen=None, incluir_igv=None):
    conn = get_connection()
    cursor = conn.cursor()
    if nuevo_regimen is not None:
        cursor.execute("UPDATE configuracion SET tipo_regimen = %s WHERE id = 1", (nuevo_regimen,))
    if nuevo_igv is not None:
        cursor.execute("UPDATE configuracion SET igv = %s WHERE id = 1", (nuevo_igv,))
    if nuevo_margen is not None:
        cursor.execute("UPDATE configuracion SET margen_utilidad = %s WHERE id = 1", (nuevo_margen,))
    if incluir_igv is not None:
        cursor.execute("UPDATE configuracion SET incluir_igv_en_precio = %s WHERE id = 1", (1 if incluir_igv else 0,))
    conn.commit()
    conn.close()


def registrar_historial_precio(cursor, producto_id, precio_anterior, precio_nuevo, margen_usado, costo_promedio):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO historial_precios (producto_id, precio_anterior, precio_nuevo, margen_usado, costo_promedio, fecha)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (producto_id, precio_anterior, precio_nuevo, margen_usado, costo_promedio, fecha))

def backup_productos_csv():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM producto", conn)
    conn.close()
    df.to_csv("backup_productos.csv", index=False)

def query_df(sql, params=None):
    conn = get_connection()
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df

def to_float(value, default=0.0):
    return float(value) if value is not None else default
