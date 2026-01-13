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


def obtener_historial_cajas():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            fecha_apertura,
            fecha_cierre,
            monto_apertura,
            monto_cierre,
            usuario_apertura,
            usuario_cierre,
            (monto_cierre - monto_apertura) AS diferencia
        FROM caja
        WHERE fecha_cierre IS NOT NULL
        ORDER BY fecha_cierre DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return rows
