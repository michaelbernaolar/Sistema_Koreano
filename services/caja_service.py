from db import get_connection

def obtener_resumen_caja(id_caja):
    conn = get_connection()
    cursor = conn.cursor()

    # Monto de apertura
    cursor.execute("""
        SELECT monto_apertura
        FROM caja
        WHERE id = %s
    """, (id_caja,))
    monto_apertura = float(cursor.fetchone()[0])

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

    # Efectivo y vuelto
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

    # ✅ CÁLCULO CORRECTO
    efectivo_esperado = monto_apertura + float(efectivo_total) - float(vuelto)

    conn.close()

    return {
        "por_metodo": por_metodo,
        "total_vendido": float(total_vendido),
        "efectivo_neto": float(efectivo_esperado),
        "monto_apertura": monto_apertura
    }