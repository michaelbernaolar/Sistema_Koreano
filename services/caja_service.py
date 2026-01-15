from datetime import timedelta
from db import get_connection
from decimal import Decimal

def obtener_resumen_caja(id_caja):
    conn = get_connection()
    cursor = conn.cursor()

    # -----------------------------
    # Monto de apertura
    # -----------------------------
    cursor.execute("""
        SELECT monto_apertura
        FROM caja
        WHERE id = %s
    """, (id_caja,))
    monto_apertura = cursor.fetchone()[0]

    # -----------------------------
    # Ventas por método de pago
    # -----------------------------
    cursor.execute("""
        SELECT
            metodo_pago,
            COALESCE(SUM(total), 0)
        FROM venta
        WHERE id_caja = %s
          AND estado = 'EMITIDA'
        GROUP BY metodo_pago
    """, (id_caja,))
    ventas_por_metodo = cursor.fetchall()

    por_metodo = []
    total_vendido = Decimal("0")
    ventas_efectivo = Decimal("0")

    for metodo, total in ventas_por_metodo:
        total = Decimal(total)
        por_metodo.append((metodo, total))
        total_vendido += total

        if metodo == "Efectivo":
            ventas_efectivo = total

    # -----------------------------
    # Ingresos manuales (efectivo)
    # -----------------------------
    cursor.execute("""
        SELECT COALESCE(SUM(monto), 0)
        FROM caja_movimiento
        WHERE id_caja = %s
          AND tipo = 'INGRESO'
          AND metodo_pago = 'Efectivo'
    """, (id_caja,))
    ingresos = Decimal(cursor.fetchone()[0])

    # -----------------------------
    # Egresos manuales (efectivo)
    # -----------------------------
    cursor.execute("""
        SELECT COALESCE(SUM(monto), 0)
        FROM caja_movimiento
        WHERE id_caja = %s
          AND tipo = 'EGRESO'
          AND metodo_pago = 'Efectivo'
    """, (id_caja,))
    egresos = Decimal(cursor.fetchone()[0])

    conn.close()

    # -----------------------------
    # Cálculos finales
    # -----------------------------
    efectivo_neto = monto_apertura + ingresos - egresos

    return {
        "por_metodo": por_metodo,
        "total_vendido": total_vendido,
        "efectivo_neto": efectivo_neto,
        "detalle_efectivo": {
            "apertura": monto_apertura,
            "ventas_efectivo": ventas_efectivo,
            "ingresos": ingresos,
            "egresos": egresos
        }
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
            AND c.fecha_cierre >= %s
            AND c.fecha_cierre < %s

        GROUP BY
            c.id,
            c.fecha_apertura,
            c.fecha_cierre,
            c.monto_apertura,
            c.monto_cierre,
            c.usuario_apertura,
            c.usuario_cierre

        ORDER BY c.fecha_cierre DESC
    """, (fecha_ini, fecha_fin))

    rows = cursor.fetchall()
    conn.close()

    return rows