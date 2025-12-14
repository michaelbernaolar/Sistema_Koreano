# db.py
import sqlite3
import pandas as pd
from datetime import datetime
import os

# Ruta absoluta basada en la carpeta del proyecto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "inventario.db")

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

# -------------------------
# Inicialización de la BD
# -------------------------
def init_db():
    """Crea las tablas necesarias si no existen."""
    conn = get_connection()
    cursor = conn.cursor()

    # Tabla de producto (inventario)
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
        stock_actual REAL,
        precio_venta REAL,
        imagen TEXT,
        activo INTEGER DEFAULT 1,
        costo_promedio REAL,
        costo_ultima_compra REAL,
        valor_inventario REAL,
        margen_utilidad REAL DEFAULT NULL,
        valor_venta Real DEFAULT NULL,
        FOREIGN KEY (id_categoria) REFERENCES categoria(id)
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

    # Tabla de venta
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS venta (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        id_cliente TEXT,
        suma_total REAL,
        descuento REAL,
        op_gravada REAL,
        op_gratuita REAL,
        igv REAL,       
        total REAL,
        tipo_comprobante TEXT,
        nro_comprobante TEXT,
        metodo_pago TEXT,
        FOREIGN KEY (id_cliente) REFERENCES cliente(id)
    )
    ''')

    # Tabla de venta_detalle
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS venta_detalle (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_venta INTEGER,
        id_producto TEXT,
        cantidad INTEGER,
        precio_unitario REAL,
        sub_total REAL,
        precio_final REAL,
        FOREIGN KEY (id_venta) REFERENCES venta(id),
        FOREIGN KEY (id_producto) REFERENCES producto(id)
    )
    ''')

    # Tabla de compras
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS compras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha DATETIME,
        id_proveedor TEXT,
        nro_doc TEXT,
        tipo_doc TEXT,
        suma_total REAL,
        descuento REAL,
        op_gravada REAL,
        op_gratuita REAL,
        igv REAL,       
        total REAL,
        metodo_pago TEXT,
        FOREIGN KEY (id_proveedor) REFERENCES proveedor(id)
    )
    ''')

    # Tabla de compras_detalle
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS compras_detalle (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_compra INTEGER,
        id_producto TEXT,
        cantidad_compra REAL,
        unidad_compra TEXT,
        factor_conversion REAL,
        cantidad_final REAL,
        precio_unitario REAL,
        subtotal REAL,
        FOREIGN KEY (id_compra) REFERENCES compras(id),
        FOREIGN KEY (id_producto) REFERENCES producto(id)
    )
    ''')

    # Tabla de producto_proveedor
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS producto_proveedor (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_producto INTEGER,
        id_proveedor INTEGER,
        unidad_compra TEXT,
        factor REAL,
        precio_compra REAL,
        lote_min REAL,
        tiempo_entrega REAL,
        FOREIGN KEY (id_producto) REFERENCES producto(id),
        FOREIGN KEY (id_proveedor) REFERENCES proveedor(id)
    )
    ''')

    # Tabla de movimientos
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS movimientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_producto TEXT,
        tipo TEXT,            -- 'entrada' o 'salida'
        cantidad REAL,
        fecha DATETIME,
        motivo TEXT,
        referencia TEXT,
        costo_unitario REAL,
        valor_total REAL,           
        FOREIGN KEY (id_producto) REFERENCES producto(id)
    )
    ''')

    # Tabla de categorias
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categoria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE
    )
    ''')

    # Tabla de configuración del sistema
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS configuracion (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        tipo_regimen TEXT DEFAULT 'Régimen General',
        igv REAL DEFAULT 0.18,
        margen_utilidad REAL DEFAULT 0.25,
        incluir_igv_en_precio INTEGER DEFAULT 1
    )
    ''')

    # Insertar registro inicial si no existe
    cursor.execute('''
    INSERT OR IGNORE INTO configuracion (id, tipo_regimen, igv, margen_utilidad, incluir_igv_en_precio)
    VALUES (1, 'Régimen General', 0.18, 0.25, 1)
    ''')

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historial_precios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        producto_id INTEGER,
        precio_anterior REAL,
        precio_nuevo REAL,
        margen_usado REAL,
        costo_promedio REAL,
        fecha TEXT,
        FOREIGN KEY(producto_id) REFERENCES producto(id)
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
    cursor.execute("INSERT INTO categoria (nombre) VALUES (?)", (nombre,))
    conn.commit()
    conn.close()

def editar_categoria(id_cat, nuevo_nombre):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE categoria SET nombre=? WHERE id=?", (nuevo_nombre, id_cat))
    conn.commit()
    conn.close()

def eliminar_categoria(id_cat):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM categoria WHERE id=?", (id_cat,))
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
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    cursor.execute("SELECT * FROM producto WHERE id = ?", (id,))
    fila = cursor.fetchone()
    conn.close()
    return fila

def actualizar_producto(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE producto SET
        descripcion = ?,
        id_categoria = ?,
        catalogo = ?,
        marca = ?,
        modelo = ?,
        ubicacion = ?,
        unidad_base = ?,
        stock_actual = ?,
        precio_venta = ?,
        imagen = ?,
        activo = ?,
        margen_utilidad=?           
    WHERE id = ?
    ''', data)

    # 🔥 Recalcular precio y valor_venta CON el margen recién actualizado
    producto_id = data[-1]
    precio_anterior, precio_nuevo, margen_usado, costo_prom = recalcular_precios_producto(cursor, producto_id)

    # 📌 Registrar historial
    registrar_historial_precio(cursor, producto_id, precio_anterior, precio_nuevo, margen_usado, costo_prom)

    conn.commit()
    conn.close()

def actualizar_costo_promedio(cursor, id_producto, cantidad_entrada, costo_unitario_entrada):
    cursor.execute("SELECT stock_actual, costo_promedio FROM producto WHERE id = ?", (id_producto,))
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
            stock_actual = ?, 
            costo_promedio = ?, 
            costo_ultima_compra = ?,
            valor_inventario = ?
        WHERE id = ?
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
    cursor.execute("SELECT stock_actual, costo_promedio FROM producto WHERE id = ?", (id_producto,))
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
        SET stock_actual = ?, valor_inventario = ?
        WHERE id = ?
    """, (
        nuevo_stock,
        round(nuevo_stock * costo_promedio, 2),
        id_producto
    ))

    # Registrar movimiento
    cursor.execute("""
        INSERT INTO movimientos (id_producto, tipo, cantidad, fecha, motivo, referencia, costo_unitario, valor_total)
        VALUES (?, 'salida', ?, ?, ?, ?, ?, ?)
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
        WHERE id = ?
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
        SET valor_venta = ?, precio_venta = ?
        WHERE id = ?
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
        cursor.execute("UPDATE configuracion SET tipo_regimen = ? WHERE id = 1", (nuevo_regimen,))
    if nuevo_igv is not None:
        cursor.execute("UPDATE configuracion SET igv = ? WHERE id = 1", (nuevo_igv,))
    if nuevo_margen is not None:
        cursor.execute("UPDATE configuracion SET margen_utilidad = ? WHERE id = 1", (nuevo_margen,))
    if incluir_igv is not None:
        cursor.execute("UPDATE configuracion SET incluir_igv_en_precio = ? WHERE id = 1", (1 if incluir_igv else 0,))
    conn.commit()
    conn.close()


def registrar_historial_precio(cursor, producto_id, precio_anterior, precio_nuevo, margen_usado, costo_promedio):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO historial_precios (producto_id, precio_anterior, precio_nuevo, margen_usado, costo_promedio, fecha)
        VALUES (?, ?, ?, ?, ?, ?)
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
