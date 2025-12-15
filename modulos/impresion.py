from db import get_connection

def obtener_venta_completa(venta_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Obtener datos de la venta
        cursor.execute("""
            SELECT v.id, v.fecha, v.tipo_comprobante, v.id_cliente, v.total,
                   c.nombre, c.dni_ruc
            FROM venta v
            LEFT JOIN cliente c ON c.id = v.id_cliente
            WHERE v.id = %s
        """, (venta_id,))
        venta = cursor.fetchone()

        # Obtener detalle
        cursor.execute("""
            SELECT p.descripcion, dv.cantidad, dv.precio_unitario
            FROM venta_detalle dv
            JOIN producto p ON p.id = dv.id_producto
            WHERE dv.id_venta = %s
        """, (venta_id,))
        detalles = cursor.fetchall()

        return venta, detalles
    finally:
        conn.close()


def generar_html_comprobante(venta_id):
    venta, detalles = obtener_venta_completa(venta_id)

    if not venta:
        return "<h3>Error: venta no encontrada.</h3>"

    venta_id, fecha, tipo, cliente_id, total, cliente_nombre, cliente_doc = venta

    filas = ""
    for item in detalles:
        nombre, cantidad, precio = item
        subtotal = cantidad * precio
        filas += f"""
        <tr>
            <td>{nombre}</td>
            <td>{cantidad}</td>
            <td>{precio:.2f}</td>
            <td>{subtotal:.2f}</td>
        </tr>
        """

    comprobante_html = f"""
    <div style='font-family: Arial; width: 450px; margin:auto; border:1px solid #ccc; padding:20px'>
        <h2 style='text-align:center'>COMPROBANTE {tipo.upper()}</h2>
        <p><strong>N°:</strong> {venta_id}</p>
        <p><strong>Fecha:</strong> {fecha}</p>
        <p><strong>Cliente:</strong> {cliente_nombre or '---'}</p>
        <p><strong>Documento:</strong> {cliente_doc or '---'}</p>

        <table style='width:100%; border-collapse: collapse; margin-top:20px'>
            <thead>
                <tr style='border-bottom:1px solid black'>
                    <th style='text-align:left'>Producto</th>
                    <th>Cant.</th>
                    <th>Precio</th>
                    <th>Subtotal</th>
                </tr>
            </thead>
            <tbody>
                {filas}
            </tbody>
        </table>

        <h3 style='text-align:right; margin-top:20px'>
            TOTAL: S/. {total:.2f}
        </h3>
    </div>
    """

    return comprobante_html
