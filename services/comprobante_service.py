from reportlab.lib.pagesizes import mm
from reportlab.pdfgen import canvas
from db import (
    get_connection, obtener_configuracion,
    obtener_venta_por_id, obtener_detalle_venta
)
import streamlit as st

config = obtener_configuracion()
usuario = st.session_state.get("usuario", {})

def wrap_text(c, text, max_width, font="Courier", size=9):
    c.setFont(font, size)
    words = text.split(" ")
    lines = []
    current = ""

    for w in words:
        test = f"{current} {w}".strip()
        if c.stringWidth(test, font, size) <= max_width:
            current = test
        else:
            lines.append(current)
            current = w

    if current:
        lines.append(current)

    return lines

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

    def draw_separator():
        nonlocal y
        c.setFont("Courier", 9)
        sep = "-" * int((width - 10) / 5)
        c.drawString(5, y, sep)
        y -= 13

    # -------------------------
    # Encabezado – Empresa
    # -------------------------
    draw_center(config["nombre_comercial"], 11)
    draw_center(config["razon_social"])
    draw_center(f"RUC: {config['ruc']}")
    for linea in wrap_text(c, config["direccion"], width - 10, "Courier", 9):
        draw_center(linea, 9)
    draw_center(f"Cel: {config['celular']}", 9)

    y -= 6
    draw_separator()

    # ------------------------
    # Título del comprobante
    # -------------------------
    draw_center("TICKET", 11)
    draw_center(f"N° {venta['nro_comprobante']}")
    draw_center(venta["fecha"].strftime("%d/%m/%Y %H:%M"))

    draw_separator()
    draw_left(f"Atendido por: {usuario.get('nombre', '')}")

    draw_separator()

    # -------------------------
    # Cliente
    # -------------------------
    draw_left(f"Cliente: {venta['cliente']}")
    if venta["documento"]:
        draw_left(f"Doc: {venta['documento']}")
    if venta["placa"]:
        draw_left(f"Placa: {venta['placa']}")

    draw_separator()

    # -------------------------
    # Detalle
    # -------------------------

    total_cantidad = 0

    for d in detalle:
        # Fila 1: descripción (completa)
        max_width = width - 10  # margen izquierdo + derecho

        lineas_desc = wrap_text(
            c,
            d["producto"],
            max_width,
            "Courier",
            9
        )

        for linea in lineas_desc:
            draw_left(linea, 9)

        # Cant | PU | Total
        cant = f"{d['cantidad']:.2f}"
        pu = f"{d['precio_unitario']:.2f}"
        tot = f"{d['total']:.2f}"

        c.setFont("Courier", 9)
        c.drawString(5, y, f"{cant} x {pu}")
        c.drawRightString(width - 5, y, f"S/. {tot}")
        y -= 12

        total_cantidad += d["cantidad"] 

    draw_separator()
    draw_left(f"Total ítems: {total_cantidad:.2f}")

    # -------------------------
    # Totales (sin IGV visible)
    # -------------------------
    draw_left(f"TOTAL:       S/. {venta['total']:.2f}", 10)

    draw_separator()
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

# ============================
# HTML
# ============================
def generar_ticket_html(venta_id: int, ancho_mm: int = 80) -> str:
    venta, detalle = obtener_venta_completa(venta_id)

    total_items = sum(d["cantidad"] for d in detalle)
    usuario_nombre = usuario.get("nombre", "")

    sep = "-" * (32 if ancho_mm == 58 else 41)

    detalle_html = ""
    for d in detalle:
        detalle_html += f"""
        {d['producto']}<br>
        {d['cantidad']:.2f} x {d['precio_unitario']:.2f}
        <span style="float:right">S/. {d['total']:.2f}</span><br>
        {sep}<br>
        """

    entregado = venta["pago_cliente"] or venta["total"]
    vuelto = venta["vuelto"] or 0

    return f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
        @page {{
            size: {ancho_mm}mm auto;
            margin: 4mm;
        }}

        body {{
            font-family: monospace;
            width: {ancho_mm}mm;
            margin: 0 auto;
            font-size: 12px;
        }}

        .center {{ text-align: center; }}
        .line {{ text-align: center; }}
        .right {{ text-align: right; }}

        @media print {{
            button {{ display: none; }}
        }}
        </style>
    </head>
    <body>
        <div class="center">
            <b>{config["nombre_comercial"]}</b><br>
            {config["razon_social"]}<br>
            RUC: {config["ruc"]}<br>
            {config["direccion"]}<br>
            Cel: {config["celular"]}
        </div>

        <div class="line">{sep}</div>

        <div class="center">
            <b>TICKET</b><br>
            N° {venta["nro_comprobante"]}<br>
            {venta["fecha"].strftime("%d/%m/%Y %H:%M")}
        </div>

        <div class="line">{sep}</div>

        Atendido por: {usuario_nombre}<br>

        <div class="line">{sep}</div>
        Cliente: {venta["cliente"]}<br>
        Doc: {venta["documento"]}<br>
        Placa: {venta["placa"] or "-"}<br>

        <div class="line">{sep}</div>

        {detalle_html}

        Total ítems: {total_items:.2f}<br>
        <b>TOTAL: S/. {venta["total"]:.2f}</b>

        <div class="line">{sep}</div>
        Pago: {venta["metodo_pago"]}<br>
        Entregado: S/. {entregado:.2f}<br>
        Vuelto: S/. {vuelto:.2f}

        <div class="line">{sep}</div>
        <div class="center">NO OTORGA CRÉDITO FISCAL</div>
        <div class="center">Gracias por su compra</div>
        <div class="line">{sep}</div>
        <div class="line">{sep}</div>
        
        <br>
        <button onclick="window.print()">🖨 Imprimir</button>
    </body>
    </html>
    """
