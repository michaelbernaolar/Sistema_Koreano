from datetime import timedelta
from db import get_connection

def obtener_resumen_caja(id_caja):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT monto_apertura
        FROM caja
        WHERE id = %s
    """, (id_caja,))
    monto_apertura = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COALESCE(SUM(monto), 0)
        FROM caja_movimiento
        WHERE id_caja = %s
          AND tipo = 'INGRESO'
          AND metodo_pago = 'Efectivo'
    """, (id_caja,))
    ingresos = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COALESCE(SUM(monto), 0)
        FROM caja_movimiento
        WHERE id_caja = %s
          AND tipo = 'EGRESO'
          AND metodo_pago = 'Efectivo'
    """, (id_caja,))
    egresos = cursor.fetchone()[0]

    conn.close()

    efectivo_teorico = monto_apertura + ingresos - egresos

    return {
        "apertura": monto_apertura,
        "ingresos": ingresos,
        "egresos": egresos,
        "efectivo_teorico": efectivo_teorico
    }

def obtener_historial_cajas(fecha_ini, fecha_fin):
    conn = get_connection()
    cursor = conn.cursor()

    fecha_fin = fecha_fin + timedelta(days=1)
    
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
            COALESCE(SUM(CASE WHEN v.metodo_pago = 'Plin' THEN v.total ELSE 0 END), 0) AS plin,
            COALESCE(SUM(CASE WHEN v.metodo_pago = 'Transferencia' THEN v.total ELSE 0 END), 0) AS transferencia,
            COALESCE(SUM(CASE WHEN v.metodo_pago = 'Tarjeta' THEN v.total ELSE 0 END), 0) AS tarjeta,

            COALESCE(SUM(v.total), 0) AS total_vendido

        FROM caja c
        LEFT JOIN venta v ON v.id_caja = c.id
            AND v.estado = 'EMITIDA'

        WHERE c.fecha_cierre IS NOT NULL
            AND c.fecha_apertura >= %s
            AND c.fecha_apertura < %s

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