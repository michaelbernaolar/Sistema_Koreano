# venta_service.py
from datetime import datetime, date
from db import get_connection, registrar_salida_por_venta, obtener_fecha_lima

def f(value):
    return float(value) if value is not None else None

# services/venta_service.py
def calcular_totales(valor_venta: float, regimen: str):
    if "Nuevo RUS" in regimen:
        return {
            "valor_venta": valor_venta,
            "op_gravada": valor_venta,
            "igv": 0.0,
            "total": valor_venta
        }
    else:
        op_gravada = round(valor_venta / 1.18, 2)
        igv = round(op_gravada * 0.18, 2)
        total = round(op_gravada + igv, 2)
        return {
            "valor_venta": valor_venta,
            "op_gravada": op_gravada,
            "igv": igv,
            "total": total
        }

from decimal import Decimal

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
    id_caja
):
    fecha = obtener_fecha_lima()

    conn = get_connection()
    cursor = conn.cursor()

    # Calcular totales correctamente
    valor_venta = Decimal(sum(Decimal(str(i["Subtotal"])) for i in carrito))
    tot = calcular_totales(valor_venta, regimen)

    cursor.execute(
        "SELECT estado FROM caja WHERE id = %s",
        (id_caja,)
    )
    estado = cursor.fetchone()
    if not estado or estado[0] != "ABIERTA":
        raise Exception("No hay caja abierta")

    # Insertar venta
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
        int(cliente["id"]),
        int(usuario["id"]),
        tot["valor_venta"],
        tot["op_gravada"],
        tot["igv"],
        tot["total"],
        tipo_comprobante,
        metodo_pago,
        nro_comprobante,
        placa_vehiculo,
        pago_cliente if metodo_pago == "Efectivo" else None,
        vuelto if metodo_pago == "Efectivo" else None,
        id_caja
    ))

    id_venta = cursor.fetchone()[0]

    # Correlativo
    serie, numero = nro_comprobante.split("-")
    cursor.execute("""
        INSERT INTO correlativo_comprobante
        (tipo, serie, numero, estado, fecha, id_venta)
        VALUES (%s,%s,%s,'EMITIDO',%s,%s)
    """, (
        tipo_comprobante,
        serie,
        int(numero),
        fecha,
        id_venta
    ))

    # Detalle + stock
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

    # Caja: INGRESO
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
            usuario["nombre"]
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
    return precio >= costo

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
        costo = cursor.fetchone()[0]

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

    caja_id = cursor.fetchone()[0]
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

