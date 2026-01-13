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
    fecha = obtener_fecha_lima(fecha)

    conn = get_connection()
    cursor = conn.cursor()

    valor_venta = f(sum(i["Subtotal"] for i in carrito))
    totales = calcular_totales(valor_venta, regimen)

    totales = {
        "valor_venta": totales["valor_venta"],
        "op_gravada": totales["op_gravada"],
        "igv": totales["igv"],
        "total": totales["total"],
    }

    cursor.execute(
        "SELECT estado FROM caja WHERE id = %s",
        (id_caja,)
    )
    estado = cursor.fetchone()

    if not estado or estado[0] != "ABIERTA":
        raise Exception("No hay caja abierta")


    cursor.execute("""
        INSERT INTO public.venta (
            fecha, id_cliente, id_usuario, suma_total, op_gravada, igv, total,
            tipo_comprobante, metodo_pago, nro_comprobante,
            placa_vehiculo, pago_cliente, vuelto, id_caja, estado
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'EMITIDA')
        RETURNING id
    """, (
        fecha,
        int(cliente["id"]), 
        int(usuario["id"]),
        f(totales["valor_venta"]),
        f(totales["op_gravada"]),
        f(totales["igv"]),
        f(totales["total"]),
        tipo_comprobante,
        metodo_pago,
        nro_comprobante,
        placa_vehiculo,
        f(pago_cliente) if metodo_pago == "Efectivo" else None,
        f(vuelto) if metodo_pago == "Efectivo" else None,
        int(id_caja)
    ))

    id_venta = cursor.fetchone()[0]

    cursor.execute("""
        INSERT INTO correlativo_comprobante
        (tipo, serie, numero, estado, fecha, id_venta)
        VALUES (%s, %s, %s, 'EMITIDO', %s, %s)
    """, (
        tipo_comprobante,
        nro_comprobante.split("-")[0],
        int(nro_comprobante.split("-")[1]),
        fecha,
        id_venta
    ))

    for item in carrito:
        if "Nuevo RUS" in regimen:
            precio_unit = item["Precio Unitario"]
            subtotal = item["Subtotal"]
        else:
            precio_unit = round(item["Precio Unitario"] / 1.18, 2)
            subtotal = round(precio_unit * item["Cantidad"], 2)

        cursor.execute("""
            INSERT INTO public.venta_detalle
            (id_venta, id_producto, cantidad, precio_unitario, sub_total, precio_final)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            int(id_venta),
            item["ID Producto"],  
            f(item["Cantidad"]),
            f(precio_unit),
            f(subtotal),
            f(subtotal)
        ))

        registrar_salida_por_venta(
            cursor,
            item["ID Producto"], 
            float(item["Cantidad"]),
            fecha,
            f"Venta {cliente['nombre']} - {nro_comprobante}"
        )

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

    # Validar que no esté anulada
    cursor.execute(
        "SELECT estado FROM venta WHERE id = %s",
        (venta_id,)
    )
    estado = cursor.fetchone()

    if not estado:
        conn.close()
        raise ValueError("Venta no encontrada")

    if estado[0] == "ANULADA":
        conn.close()
        raise ValueError("La venta ya está anulada")

    # Validar reimpresiones
    cursor.execute(
        "SELECT reimpresiones FROM venta WHERE id = %s",
        (venta_id,)
    )
    reimp = cursor.fetchone()[0]

    if reimp > 0:
        conn.close()
        raise ValueError("No se puede anular una venta reimpresa")

    fecha = obtener_fecha_lima()

    # 1️⃣ ANULAR LA VENTA (YA LO TENÍAS)
    cursor.execute("""
        UPDATE venta
        SET
            estado = 'ANULADA',
            motivo_anulacion = %s,
            fecha_anulacion = %s,
            usuario_anulacion = %s
        WHERE id = %s
    """, (motivo, fecha, usuario["nombre"], venta_id))

    # 2️⃣ MARCAR CORRELATIVO COMO ANULADO (NUEVO)
    cursor.execute("""
        UPDATE correlativo_comprobante
        SET estado = 'ANULADO'
        WHERE id_venta = %s
    """, (venta_id,))

    # 3️⃣ REGISTRAR EVENTO DE ANULACIÓN (NUEVO)
    cursor.execute("""
        INSERT INTO venta_evento
        (id_venta, tipo, fecha, usuario, observacion)
        VALUES (%s, 'ANULACION', %s, %s, %s)
    """, (venta_id, fecha, usuario["nombre"], motivo))

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

