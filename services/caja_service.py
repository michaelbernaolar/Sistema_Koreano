from db import get_connection

def obtener_resumen_caja(id_caja):
    conn = get_connection()
    cursor = conn.cursor()

    # Monto apertura
    cursor.execute("""
        SELECT monto_apertura
        FROM caja
        WHERE id = %s
    """, (id_caja,))
    monto_apertura = float(cursor.fetchone()[0])

    # Ventas por método (solo informativo)
    cursor.execute("""
        SELECT metodo_pago, COALESCE(SUM(total), 0)
        FROM venta
        WHERE id_caja = %s
          AND estado = 'EMITIDA'
        GROUP BY metodo_pago
    """, (id_caja,))
    por_metodo = cursor.fetchall()

    total_vendido = sum(float(total) for _, total in por_metodo)

    # 💵 EFECTIVO CORRECTO
    cursor.execute("""
        SELECT COALESCE(SUM(pago_cliente - vuelto), 0)
        FROM venta
        WHERE id_caja = %s
          AND metodo_pago = 'Efectivo'
          AND estado = 'EMITIDA'
    """, (id_caja,))

    efectivo_ventas = float(cursor.fetchone()[0])

    efectivo_esperado = monto_apertura + efectivo_ventas

    conn.close()

    return {
        "monto_apertura": monto_apertura,
        "por_metodo": por_metodo,
        "total_vendido": total_vendido,
        "efectivo_neto": efectivo_esperado
    }


def obtener_historial_cajas(fecha_ini, fecha_fin):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            c.id,
            c.fecha_apertura,
            c.fecha_cierre,
            c.monto_apertura,
            c.monto_cierre,
            c.usuario_apertura,
            c.usuario_cierre,

            COALESCE(SUM(CASE WHEN v.metodo_pago = 'Efectivo' THEN v.total ELSE 0 END), 0) AS efectivo,
            COALESCE(SUM(CASE WHEN v.metodo_pago = 'Yape' THEN v.total ELSE 0 END), 0) AS yape,
            COALESCE(SUM(CASE WHEN v.metodo_pago = 'Plina' THEN v.total ELSE 0 END), 0) AS plin,
            COALESCE(SUM(CASE WHEN v.metodo_pago = 'Transferencia' THEN v.total ELSE 0 END), 0) AS transferencia,
            COALESCE(SUM(CASE WHEN v.metodo_pago = 'Tarjeta' THEN v.total ELSE 0 END), 0) AS tarjeta,

            COALESCE(SUM(v.total), 0) AS total_vendido

        FROM caja c
        LEFT JOIN venta v ON v.id_caja = c.id
            AND v.estado = 'EMITIDA'

        WHERE c.fecha_cierre IS NOT NULL
          AND DATE(c.fecha_apertura) BETWEEN %s AND %s

        GROUP BY
            c.id,
            c.fecha_apertura,
            c.fecha_cierre,
            c.monto_apertura,
            c.monto_cierre

        ORDER BY c.fecha_cierre DESC
    """, (fecha_ini, fecha_fin))

    rows = cursor.fetchall()
    conn.close()

    return rows