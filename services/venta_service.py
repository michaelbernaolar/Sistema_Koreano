from datetime import datetime, date
from db import get_connection, registrar_salida_por_venta
import pytz

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
    carrito
):
    lima = pytz.timezone("America/Lima")
    if isinstance(fecha, date) and not isinstance(fecha, datetime):
        fecha = datetime.combine(fecha, datetime.min.time())
    # Asegurarse de que la fecha tenga timezone
    if fecha.tzinfo is None:
        fecha = lima.localize(fecha)

    # Convertir a UTC antes de guardar en DB
    fecha_utc = fecha.astimezone(pytz.UTC)

    conn = get_connection()
    cursor = conn.cursor()

    valor_venta = f(sum(i["Subtotal"] for i in carrito))
    totales = calcular_totales(valor_venta, regimen)

    totales = {
        "valor_venta": f(totales["valor_venta"]),
        "op_gravada": f(totales["op_gravada"]),
        "igv": f(totales["igv"]),
        "total": f(totales["total"]),
    }

    cursor.execute("""
        INSERT INTO public.venta (
            fecha, id_cliente, suma_total, op_gravada, igv, total,
            tipo_comprobante, metodo_pago, nro_comprobante,
            placa_vehiculo, pago_cliente, vuelto
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
    """, (
        fecha_utc,
        cliente["id"],
        f(totales["valor_venta"]),
        f(totales["op_gravada"]),
        f(totales["igv"]),
        f(totales["total"]),
        tipo_comprobante,
        metodo_pago,
        nro_comprobante,
        placa_vehiculo,
        f(pago_cliente) if metodo_pago == "Efectivo" else None,
        f(vuelto) if metodo_pago == "Efectivo" else None
    ))

    id_venta = cursor.fetchone()[0]

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
            item["Cantidad"],
            fecha,
            f"Venta {cliente['nombre']} - {nro_comprobante}"
        )

    conn.commit()
    conn.close()
    return id_venta
