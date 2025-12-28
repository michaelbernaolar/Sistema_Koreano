from reportlab.lib.pagesizes import mm
from reportlab.pdfgen import canvas
from db import get_connection
from db import obtener_configuracion
import streamlit as st

config = obtener_configuracion()
usuario = st.session_state.get("usuario", {})

def generar_ticket_pdf(venta_id, ruta):
    venta, detalle = obtener_venta_completa(venta_id)

    width = 80 * mm
    height = 200 * mm

    c = canvas.Canvas(ruta, pagesize=(width, height))
    y = height - 10

    def draw_left(txt, size=9):
        nonlocal y
        c.setFont("Courier", size)
        c.drawString(5, y, txt)
        y -= size + 4

    def draw_center(txt, size=9):
        nonlocal y
        c.setFont("Courier", size)
        c.drawCentredString(width / 2, y, txt)
        y -= size + 4

    # -------------------------
    # Encabezado – Empresa
    # -------------------------
    draw_center(config["nombre_comercial"], 11)
    draw_center(config["razon_social"])
    draw_center(f"RUC: {config['ruc']}")
    draw_center(config["direccion"])
    draw_center(f"Cel: {config['celular']}")

    y -= 6
    draw_left("-" * 32)

    # -------------------------
    # Título del comprobante
    # -------------------------
    draw_center("TICKET", 11)
    draw_center(f"N° {venta['nro_comprobante']}")
    draw_center(venta["fecha"].strftime("%d/%m/%Y %H:%M"))

    draw_left("-" * 32)
    draw_left(f"Atendido por: {usuario.get('nombre', '')}")

    draw_left("-" * 32)

    # -------------------------
    # Cliente
    # -------------------------
    draw_left(f"Cliente: {venta['cliente']}")
    if venta["documento"]:
        draw_left(f"Doc: {venta['documento']}")
    if venta["placa"]:
        draw_left(f"Placa: {venta['placa']}")

    draw_left("-" * 32)

    # -------------------------
    # Detalle
    # -------------------------
    draw_left("Prod.      Cant  P.Unit  Total", 8)

    total_cantidad = 0

    for d in detalle:
        nombre = d["producto"][:10]
        total_cantidad += d["cantidad"]

        draw_left(
            f"{nombre:<10}"
            f"{d['cantidad']:>5.2f}"
            f"{d['precio_unitario']:>8.2f}"
            f"{d['total']:>8.2f}",
            8
        )

    draw_left("-" * 32)
    draw_left(f"Total ítems: {total_cantidad:.2f}")

    # -------------------------
    # Totales (sin IGV visible)
    # -------------------------
    draw_left(f"TOTAL:       S/. {venta['total']:.2f}", 10)

    draw_left("-" * 32)

    # -------------------------
    # Pago
    # -------------------------
    draw_left(f"Pago: {venta['metodo_pago']}")
    if venta["metodo_pago"] == "Efectivo":
        draw_left(f"Entregado: S/. {venta['pago_cliente']:.2f}")
        draw_left(f"Vuelto:    S/. {venta['vuelto']:.2f}")

    y -= 6

    # -------------------------
    # Frase SUNAT obligatoria
    # -------------------------
    draw_center("NO OTORGA CRÉDITO FISCAL", 8)

    y -= 6
    draw_center("Gracias por su compra", 8)

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
                v.suma_total,
                v.op_gravada,
                v.igv,
                v.total,
                v.metodo_pago,
                v.tipo_comprobante,
                v.nro_comprobante,
                v.placa_vehiculo,
                v.pago_cliente,
                v.vuelto,
                c.nombre,
                c.dni_ruc
            FROM venta v
            LEFT JOIN cliente c ON c.id = v.id_cliente
            WHERE v.id = %s
        """, (venta_id,))
        v = cursor.fetchone()

        venta = {
            "id": v[0],
            "fecha": v[1],                      # ya incluye hora
            "suma_total": float(v[2]),
            "op_gravada": float(v[3]),
            "igv": float(v[4]),
            "total": float(v[5]),
            "metodo_pago": v[6],
            "tipo_comprobante": v[7],
            "nro_comprobante": v[8],
            "placa": v[9],
            "pago_cliente": v[10],
            "vuelto": v[11],
            "cliente": v[12] or "CLIENTE VARIOS",
            "documento": v[13] or ""
        }
        
        cursor.execute("""
            SELECT
                p.descripcion,
                d.cantidad,
                d.precio_unitario,
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
                "precio_unitario": float(r[2]),
                "total": float(r[3]),
            }
            for r in cursor.fetchall()
        ]

        return venta, detalle
    finally:
        conn.close()




