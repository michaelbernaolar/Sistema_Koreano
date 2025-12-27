from reportlab.lib.pagesizes import mm
from reportlab.pdfgen import canvas
from db import get_connection

def generar_ticket_pdf(venta_id, ruta):
    venta, detalle = obtener_venta_completa(venta_id)
    width = 80 * mm
    height = 200 * mm

    c = canvas.Canvas(ruta, pagesize=(width, height))
    y = height - 10

    def draw(txt, size=9):
        nonlocal y
        c.setFont("Courier", size)
        c.drawString(5, y, txt)
        y -= size + 4

    draw("MI NEGOCIO", 11)
    draw("RUC: 10999999999")
    draw("-" * 32)

    draw("TICKET DE VENTA", 10)
    draw(f"N° {venta['id']}")
    draw(venta["fecha"].strftime("%d/%m/%Y %H:%M"))
    draw("-" * 32)

    draw(f"Cliente: {venta['cliente']}")
    draw(f"Doc: {venta['documento']}")
    draw("-" * 32)

    draw("Producto        Cant  Subt", 8)

    for d in detalle:
        nombre = d["producto"][:14]
        draw(f"{nombre:<14} {d['cantidad']:>4} {d['subtotal']:>7.2f}", 8)

    draw("-" * 32)
    draw(f"TOTAL S/. {venta['total']:.2f}", 10)
    draw("-" * 32)

    draw(f"Pago: {venta['metodo_pago']}")
    draw("Gracias por su compra")

    c.showPage()
    c.save()

    return ruta

def obtener_venta_completa(venta_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                v.id,
                v.fecha,
                v.total,
                v.metodo_pago,
                v.tipo_comprobante,
                COALESCE(c.nombre, 'CLIENTE VARIOS'),
                COALESCE(c.dni_ruc, '')
            FROM venta v
            LEFT JOIN cliente c ON c.id = v.id_cliente
            WHERE v.id = %s
        """, (venta_id,))
        v = cursor.fetchone()

        venta = {
            "id": v[0],
            "fecha": v[1],
            "total": float(v[2]),
            "metodo_pago": v[3],
            "tipo_comprobante": v[4],
            "cliente": v[5],
            "documento": v[6],
        }

        cursor.execute("""
            SELECT
                p.descripcion,
                d.cantidad,
                d.sub_total
            FROM venta_detalle d
            JOIN producto p ON p.id = d.id_producto
            WHERE d.id_venta = %s
            ORDER BY d.id
        """, (venta_id,))

        detalle = [
            {
                "producto": r[0],
                "cantidad": float(r[1]),
                "subtotal": float(r[2]),
            }
            for r in cursor.fetchall()
        ]

        return venta, detalle
    finally:
        conn.close()




