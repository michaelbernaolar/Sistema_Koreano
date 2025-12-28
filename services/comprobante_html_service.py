from db import obtener_venta_por_id, obtener_detalle_venta

def generar_ticket_html(venta_id: int) -> str:
    venta = obtener_venta_por_id(venta_id)
    detalle = obtener_detalle_venta(venta_id)

    filas = ""
    for d in detalle:
        filas += f"""
        <tr>
            <td>{d['descripcion']}</td>
            <td style="text-align:right">{d['cantidad']:.2f}</td>
            <td style="text-align:right">{d['precio_unitario']:.2f}</td>
            <td style="text-align:right">{d['subtotal']:.2f}</td>
        </tr>
        """

    html = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: monospace;
                width: 80mm;
                margin: auto;
            }}
            h2, p {{
                text-align: center;
                margin: 4px 0;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 12px;
            }}
            td {{
                padding: 2px 0;
            }}
            .total {{
                border-top: 1px dashed #000;
                margin-top: 6px;
                padding-top: 6px;
                text-align: right;
                font-weight: bold;
            }}
            @media print {{
                button {{ display: none; }}
            }}
        </style>
    </head>
    <body>
        <h2>MI NEGOCIO</h2>
        <p>RUC: 12345678901</p>
        <p>{venta['fecha']}</p>
        <p>{venta['tipo_comprobante']} Nº {venta['nro_comprobante']}</p>

        <hr>

        <table>
            {filas}
        </table>

        <div class="total">
            TOTAL: S/. {venta['total']:.2f}
        </div>

        <p>Gracias por su compra</p>

        <button onclick="window.print()">🖨 Imprimir</button>
    </body>
    </html>
    """

    return html
