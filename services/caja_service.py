from db import get_connection

def obtener_resumen_caja(id_caja):
    conn = get_connection()
    cursor = conn.cursor()

    # Ventas por método de pago
    cursor.execute("""
        SELECT metodo_pago, COALESCE(SUM(total), 0)
        FROM venta
        WHERE id_caja = %s
          AND estado = 'EMITIDA'
        GROUP BY metodo_pago
        ORDER BY metodo_pago
    """, (id_caja,))

    por_metodo = cursor.fetchall()

    # Total vendido (todos los métodos)
    total_vendido = sum(float(total) for _, total in por_metodo)

    # Efectivo total y vuelto
    cursor.execute("""
        SELECT
            COALESCE(SUM(total), 0),
            COALESCE(SUM(vuelto), 0)
        FROM venta
        WHERE id_caja = %s
          AND metodo_pago = 'Efectivo'
          AND estado = 'EMITIDA'
    """, (id_caja,))

    efectivo_total, vuelto = cursor.fetchone()

    conn.close()

    return {
        "por_metodo": por_metodo,
        "efectivo_neto": float(efectivo_total - vuelto),
        "total_vendido": float(total_vendido)
    }