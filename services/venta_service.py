# venta_service.py
from datetime import datetime, date
from decimal import Decimal
from db import get_connection, registrar_salida_por_venta, obtener_fecha_lima, query_df

def f(value):
    return float(value) if value is not None else None

# services/venta_service.py
def calcular_totales(valor_venta: Decimal, regimen: str):
    if "Nuevo RUS" in regimen:
        return {
            "valor_venta": valor_venta,
            "op_gravada": valor_venta,
            "igv": Decimal("0.00"),
            "total": valor_venta
        }
    else:
        op_gravada = (valor_venta / Decimal("1.18")).quantize(Decimal("0.01"))
        igv = (op_gravada * Decimal("0.18")).quantize(Decimal("0.01"))
        total = (op_gravada + igv).quantize(Decimal("0.01"))

        return {
            "valor_venta": valor_venta,
            "op_gravada": op_gravada,
            "igv": igv,
            "total": total
        }
    
def parsear_comprobante(nro_comprobante: str):
    try:
        serie, numero = nro_comprobante.split("-")
        return serie, int(numero)
    except Exception:
        raise Exception(
            "Formato de comprobante inválido. Use SERIE-NUMERO (ej: T-000001)"
        )
    
def guardar_venta(
    fecha,
    cliente,
    regimen,
    tipo_comprobante,
    metodo_pago,
    nro_comprobante,
    placa_vehiculo,
    pago_cliente,
    vuelto,
    carrito,
    usuario,
    id_caja,
    id_venta_existente=None
):
    fecha = obtener_fecha_lima()

    conn = get_connection()
    cursor = conn.cursor()

    def to_decimal(value):
        if value is None:
            return None
        return Decimal(str(value))

    # Calcular totales correctamente
    if id_venta_existente:
        df = query_df(
            "SELECT COALESCE(SUM(sub_total),0) total FROM venta_detalle WHERE id_venta=%s",
            (id_venta_existente,)
        )
        valor_venta = Decimal(str(df.iloc[0]["total"]))
    else:
        valor_venta = sum(
            (Decimal(str(i["Subtotal"])) for i in carrito),
            Decimal("0.00")
        )
    tot = calcular_totales(valor_venta, regimen)

    # 🔒 Normalizar totales (evita np.float64)
    tot = {
        "valor_venta": to_decimal(tot["valor_venta"]),
        "op_gravada": to_decimal(tot["op_gravada"]),
        "igv": to_decimal(tot["igv"]),
        "total": to_decimal(tot["total"]),
    }

    # Validar caja abierta
    cursor.execute("SELECT estado FROM caja WHERE id = %s", (id_caja,))
    estado = cursor.fetchone()
    if not estado or estado[0] != "ABIERTA":
        raise Exception("No hay caja abierta")

    pago_cliente_db = (
        to_decimal(pago_cliente)
        if metodo_pago == "Efectivo" and pago_cliente is not None
        else None
    )

    vuelto_db = (
        to_decimal(vuelto)
        if metodo_pago == "Efectivo" and vuelto is not None
        else None
    )

    # ----------------------
    # Insertar venta
    # ----------------------
    if id_venta_existente:
        cursor.execute("""
            UPDATE venta
            SET
                suma_total = %s,
                op_gravada = %s,
                igv = %s,
                total = %s,
                tipo_comprobante = %s,
                metodo_pago = %s,
                nro_comprobante = %s,
                pago_cliente = %s,
                vuelto = %s,
                estado = 'EMITIDA'
            WHERE id = %s
            RETURNING id
        """, (
            tot["valor_venta"],
            tot["op_gravada"],
            tot["igv"],
            tot["total"],
            tipo_comprobante,
            metodo_pago,
            nro_comprobante,
            pago_cliente_db,
            vuelto_db,
            id_venta_existente
        ))
    else:
        cursor.execute("""
            INSERT INTO venta (
                fecha, id_cliente, id_usuario,
                suma_total, op_gravada, igv, total,
                tipo_comprobante, metodo_pago, nro_comprobante,
                placa_vehiculo, pago_cliente, vuelto, id_caja, estado
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'EMITIDA')
            RETURNING id
        """, (
            fecha,
            cliente["id"],
            int(usuario["id"]),
            tot["valor_venta"],
            tot["op_gravada"],
            tot["igv"],
            tot["total"],
            tipo_comprobante,
            metodo_pago,
            nro_comprobante,
            placa_vehiculo,
            pago_cliente_db,
            vuelto_db,
            id_caja
        ))

    row = cursor.fetchone()
    if row is None:
        raise Exception("No se obtuvo resultado de la consulta")
    id_venta = row[0]

    # ----------------------
    # Actualizar correlativo
    # ----------------------
    # Insertar/actualizar correlativo **solo después de guardar la venta**
    serie, numero = parsear_comprobante(nro_comprobante)

    cursor.execute("""
        INSERT INTO correlativo_comprobante (
            tipo, serie, numero, estado, fecha, id_venta
        )
        VALUES (%s, %s, %s, 'EMITIDO', %s, %s)
        ON CONFLICT (tipo, serie, numero)
        DO UPDATE SET
            id_venta = EXCLUDED.id_venta,
            estado = 'EMITIDO',
            fecha = EXCLUDED.fecha
    """, (
        tipo_comprobante.upper(),
        serie,
        numero,
        fecha,
        id_venta
    ))

    # ----------------------
    # Insertar detalle de venta y registrar salidas
    # ----------------------
    if not id_venta_existente:
        for item in carrito:
            cantidad = Decimal(str(item["Cantidad"]))
            precio_unit = Decimal(str(item["Precio Unitario"]))

            if "Nuevo RUS" not in regimen:
                precio_unit = (precio_unit / Decimal("1.18")).quantize(Decimal("0.01"))

            subtotal = (precio_unit * cantidad).quantize(Decimal("0.01"))

            cursor.execute("""
                INSERT INTO venta_detalle
                (id_venta, id_producto, cantidad, precio_unitario, sub_total, precio_final)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (
                id_venta,
                item["ID Producto"],
                cantidad,
                precio_unit,
                subtotal,
                subtotal
            ))

            registrar_salida_por_venta(
                cursor,
                item["ID Producto"],
                cantidad,
                fecha,
                f"Venta {nro_comprobante}"
            )

    # ----------------------
    # Registrar ingreso en caja
    # ----------------------
    if metodo_pago == "Efectivo":
        cursor.execute("""
            INSERT INTO caja_movimiento (
                id_caja, fecha, tipo, metodo_pago,
                monto, referencia, id_venta, usuario
            )
            VALUES (%s,%s,'INGRESO','Efectivo',%s,%s,%s,%s)
        """, (
            id_caja,
            fecha,
            tot["total"],
            f"Venta {nro_comprobante}",
            id_venta,
            usuario["username"]
        ))

    conn.commit()
    conn.close()
    return id_venta

def inicializar_estado_venta(state):
    state.setdefault("carrito_ventas", [])
    state.setdefault("venta_guardada", False)
    state.setdefault("pdf_generado", False)
    state.setdefault("ruta_pdf", None)

def resetear_venta(state):
    state["reset_en_progreso"] = True
    state["carrito_ventas"] = []
    state["venta_guardada"] = False
    state["pdf_generado"] = False
    state["ruta_pdf"] = None
    state.pop("venta_actual_id", None)

def precio_valido(precio, costo):
    return precio >= 0

def anular_venta(venta_id, motivo, usuario):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT estado, reimpresiones, total, metodo_pago, id_caja, nro_comprobante
        FROM venta
        WHERE id = %s
    """, (venta_id,))
    row = cursor.fetchone()

    if not row:
        raise ValueError("Venta no encontrada")

    estado, reimp, total, metodo_pago, id_caja, nro = row

    if estado == "ANULADA":
        raise ValueError("La venta ya está anulada")

    if reimp > 0:
        raise ValueError("No se puede anular una venta reimpresa")

    fecha = obtener_fecha_lima()

    # Anular venta
    cursor.execute("""
        UPDATE venta
        SET estado='ANULADA',
            motivo_anulacion=%s,
            fecha_anulacion=%s,
            usuario_anulacion=%s
        WHERE id=%s
    """, (motivo, fecha, usuario["nombre"], venta_id))

    # Detalles
    cursor.execute("""
        SELECT id_producto, cantidad
        FROM venta_detalle
        WHERE id_venta = %s
    """, (venta_id,))
    detalles = cursor.fetchall()

    for id_producto, cantidad in detalles:
        # devolver stock
        cursor.execute("""
            UPDATE producto
            SET stock_actual = stock_actual + %s
            WHERE id = %s
        """, (cantidad, id_producto))

        # registrar kardex
        cursor.execute("""
            SELECT costo_promedio
            FROM producto
            WHERE id = %s
        """, (id_producto,))

        row = cursor.fetchone()
        if row is None:
            raise Exception("No se pudo obtener el costo")
        costo = row[0]

        cursor.execute("""
            INSERT INTO movimientos
            (id_producto, tipo, cantidad, fecha, motivo, referencia, costo_unitario, valor_total)
            VALUES (%s,'entrada',%s,%s,'Anulación de venta',%s,%s,%s)
        """, (
            id_producto,
            cantidad,
            fecha,
            f"Venta {nro}",
            costo,
            cantidad * costo
        ))

    # Correlativo
    cursor.execute("""
        UPDATE correlativo_comprobante
        SET estado='ANULADO'
        WHERE id_venta=%s
    """, (venta_id,))

    # Evento
    cursor.execute("""
        INSERT INTO venta_evento
        (id_venta, tipo, fecha, usuario, observacion)
        VALUES (%s,'ANULACION',%s,%s,%s)
    """, (venta_id, fecha, usuario["nombre"], motivo))

    # Caja: EGRESO
    if metodo_pago == "Efectivo":
        cursor.execute("""
            INSERT INTO caja_movimiento
            (id_caja, fecha, tipo, metodo_pago, monto, referencia, id_venta, usuario)
            VALUES (%s,%s,'EGRESO','Efectivo',%s,%s,%s,%s)
        """, (
            id_caja,
            fecha,
            total,
            f"Anulación {nro}",
            venta_id,
            usuario["nombre"]
        ))

    conn.commit()
    conn.close()

def cerrar_caja(id_caja, monto, usuario):
    conn = get_connection()
    cursor = conn.cursor()

    fecha = obtener_fecha_lima()

    cursor.execute("""
        UPDATE caja
        SET
            fecha_cierre = %s,
            monto_cierre = %s,
            usuario_cierre = %s,
            estado = 'CERRADA'
        WHERE id = %s
    """, (fecha, monto, usuario["username"], id_caja))

    conn.commit()
    conn.close()

def abrir_caja(monto, usuario):
    conn = get_connection()
    cursor = conn.cursor()

    fecha = obtener_fecha_lima()

    cursor.execute("""
        INSERT INTO caja (fecha_apertura, monto_apertura, usuario_apertura, estado)
        VALUES (%s, %s, %s, 'ABIERTA')
        RETURNING id
    """, (fecha, monto, usuario["username"]))

    row = cursor.fetchone()
    if row is None:
        raise Exception("No hay caja abierta para el usuario")
    caja_id = row[0] 
    
    conn.commit()
    conn.close()
    return caja_id

def obtener_caja_abierta():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, monto_apertura, fecha_apertura, usuario_apertura
        FROM caja
        WHERE estado = 'ABIERTA'
        ORDER BY fecha_apertura DESC
        LIMIT 1
    """)

    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "id": row[0],
            "monto_apertura": float(row[1]),
            "fecha_apertura": row[2],
            "usuario_apertura": row[3]
        }

    return None

def crear_venta_abierta(cliente_id, placa_vehiculo, usuario_id, id_caja):
    conn = get_connection()
    cursor = conn.cursor()
    fecha = obtener_fecha_lima()

    cursor.execute("""
        INSERT INTO venta (
            fecha, id_cliente, id_usuario,
            suma_total, op_gravada, igv, total,
            estado, placa_vehiculo, id_caja
        )
        VALUES (%s,%s,%s,0,0,0,0,'ABIERTA',%s,%s)
        RETURNING id
    """, (
        fecha,
        cliente_id,
        usuario_id,
        placa_vehiculo,
        id_caja
    ))

    id_venta = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return id_venta

def agregar_item_venta(id_venta, id_producto, cantidad, precio_unit):
    conn = get_connection()
    cursor = conn.cursor()

    subtotal = Decimal(str(cantidad)) * Decimal(str(precio_unit))

    cursor.execute("""
        INSERT INTO venta_detalle
        (id_venta, id_producto, cantidad, precio_unitario, sub_total, precio_final)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (
        id_venta,
        id_producto,
        cantidad,
        precio_unit,
        subtotal,
        subtotal
    ))
    conn.commit()
    conn.close()

def obtener_ventas_abiertas():
    return query_df("""
        SELECT 
            v.id AS orden,
            c.nombre AS cliente,
            v.placa_vehiculo AS placa,
            v.fecha
        FROM venta v
        JOIN cliente c ON c.id = v.id_cliente
        WHERE v.estado = 'ABIERTA'
        ORDER BY v.fecha
    """)

def obtener_valor_venta(carrito=None, id_venta=None):
    if carrito is not None:
        return sum(
            (Decimal(str(i["Subtotal"])) for i in carrito),
            Decimal("0.00")
        )

    if id_venta is not None:
        df = query_df(
            "SELECT COALESCE(SUM(sub_total),0) total FROM venta_detalle WHERE id_venta=%s",
            (id_venta,)
        )
        return Decimal(str(df.iloc[0]["total"]))

    return Decimal("0.00")

def obtener_detalle_venta(id_venta):
    return query_df("""
        SELECT
            d.id_producto AS "ID Producto",
            p.descripcion AS "Descripción",
            d.cantidad AS "Cantidad",
            d.precio_unitario AS "Precio Unitario",
            d.sub_total AS "Subtotal"
        FROM venta_detalle d
        JOIN producto p ON p.id = d.id_producto
        WHERE d.id_venta = %s
        ORDER BY d.id
    """, (id_venta,))

def puede_guardar_venta(
    carrito,
    metodo_pago,
    total,
    pago_cliente_txt
):
    if not carrito:
        return False, "El carrito está vacío"

    if metodo_pago == "Efectivo":
        if not pago_cliente_txt:
            return False, "Ingrese el monto entregado"

        try:
            pago = float(pago_cliente_txt)
        except ValueError:
            return False, "Monto entregado inválido"

        if pago < total:
            return False, "El pago es menor al total"

    return True, None

def eliminar_items_servicio(id_venta):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM venta_detalle
        WHERE id_venta = %s
    """, (id_venta,))

    conn.commit()
    conn.close()

def eliminar_item_servicio(id_venta, id_producto):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM venta_detalle
        WHERE ctid IN (
            SELECT ctid
            FROM venta_detalle
            WHERE id_venta = %s
              AND id_producto = %s
            ORDER BY ctid
            LIMIT 1
        )
    """, (id_venta, id_producto))

    conn.commit()
    conn.close()

def eliminar_venta_abierta(venta_id):
    """
    Elimina completamente una venta abierta (sin afectar caja ni comprobante)
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Verificar si existe y está abierta
    cursor.execute("SELECT estado FROM venta WHERE id = %s", (venta_id,))
    row = cursor.fetchone()
    if not row:
        raise ValueError("Venta no encontrada")
    estado = row[0]

    if estado != "ABIERTA":
        raise ValueError("Solo se pueden eliminar ventas abiertas")

    # Eliminar detalle
    cursor.execute("DELETE FROM venta_detalle WHERE id_venta = %s", (venta_id,))
    # Eliminar venta
    cursor.execute("DELETE FROM venta WHERE id = %s", (venta_id,))

    conn.commit()
    conn.close()
