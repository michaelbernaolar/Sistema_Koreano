import pandas as pd
import streamlit as st

from datetime import datetime
from db import registrar_salida_por_venta, obtener_configuracion
from modulos.impresion import generar_html_comprobante
from db import get_connection, query_df

def ventas_app():
    st.title("🛒 Registro y Consulta de Ventas")

    tabs = st.tabs(["📝 Registrar Venta", "📋 Consultar Ventas", "📊 Reportes"])

    # ========================
    # TAB 1: Registrar Venta
    # ========================
    with tabs[0]:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("📝 Registrar nueva venta")
            # Obtener régimen desde configuración
            # Leer configuración general
            configuracion = obtener_configuracion()
            regimen = configuracion.get("regimen", "Nuevo RUS")  # Valor por defecto

        # --- Cliente, Régimen y Método de Pago ---
        df_cli = query_df("SELECT id, nombre FROM cliente ORDER BY nombre")
        col1, col2 = st.columns([5, 1])
        with col1:
            cliente_sel = st.selectbox(
                "👤 Cliente",
                [f"{row['id']} | {row['nombre']}" for _, row in df_cli.iterrows()] if not df_cli.empty else ["Sin clientes"]
            )
            cliente_id = int(cliente_sel.split(" | ")[0]) if not df_cli.empty else None

        with col2:
            metodo_pago = st.selectbox(
                "💳 Método de pago",
                ["Efectivo", "Tarjeta", "Transferencia"],
                key="metodo_pago_select"
            )

        # --- Datos del comprobante ---
        col1, col2, col3 = st.columns(3)
        with col1:
            fecha = st.date_input("📅 Fecha", datetime.today())
        with col2:
            nro_comprobante = st.text_input("📑 N° Documento")
        with col3:
            tipo_comprobante = st.selectbox("📄 Tipo de comprobante", ["Boleta", "Factura"])

        # --- Carrito en sesión ---
        if "carrito_ventas" not in st.session_state:
            st.session_state.carrito_ventas = []

        st.markdown("### ➕ Agregar productos a la venta")

        # --- Filtros ---
        col1, col2, col3, col4 = st.columns([1, 3, 3 ,3])
        with col1:
            filtro_codigo = st.text_input("🔍Código")
        with col2:
            filtro_desc = st.text_input("🔍Descripción")
        with col3:
            filtro_marca = st.text_input("🔍Marca")
        with col4:
            filtro_catalogo = st.text_input("🔍Catálogo")

        query_prod = "SELECT id, descripcion, marca, catalogo, precio_venta, stock_actual, costo_promedio, margen_utilidad FROM producto WHERE activo=1"
        params = []

        if filtro_codigo:
            # Elimina espacios y formatea el número
            codigo_num = ''.join(filter(str.isdigit, filtro_codigo))  # extrae solo números
            if codigo_num.isdigit():
                # Formatea con 5 dígitos y agrega el prefijo P
                codigo_formateado = f"P{int(codigo_num):05d}"
                query_prod += " AND id = ?"
                params.append(codigo_formateado)
            else:
                # Si el usuario escribe P00016 completo, también funciona
                query_prod += " AND id LIKE ?"
                params.append(f"%{filtro_codigo.strip()}%")

        if filtro_desc:
            query_prod += " AND descripcion LIKE ?"
            params.append(f"%{filtro_desc}%")
        if filtro_marca:
            query_prod += " AND marca LIKE ?"
            params.append(f"%{filtro_marca}%")
        if filtro_catalogo:
            query_prod += " AND catalogo LIKE ?"
            params.append(f"%{filtro_catalogo}%")

        df_prod = query_df(query_prod + " ORDER BY descripcion", params)

        if df_prod.empty:
            st.warning("⚠️ No hay productos disponibles con esos filtros.")
        else:
            productos_dict = {row['descripcion']: row for _, row in df_prod.iterrows()}
            producto_sel = st.selectbox("📦 Selecciona un producto", list(productos_dict.keys()))
            row = productos_dict[producto_sel]
            id_producto = row['id']
            desc_producto = row['descripcion']
            stock_disp = float(row['stock_actual'])
            costo = float(row['costo_promedio'])
            margen = float(row['margen_utilidad'])*100

            st.write("### 📋 Detalles del producto")
            st.write(f"🔢 Código: {id_producto}")
            st.write(f"🏭 Marca: {row['marca']}")
            st.write(f"📖 Catálogo: {row['catalogo']}")

            # --- Validar y asegurar precio base correcto ---
            try:
                precio_base = float(row['precio_venta'])
                if precio_base <= 0:
                    precio_base = 0.01
            except (ValueError, TypeError):
                precio_base = 0.01

            # --- Mostrar datos de precio y stock ---
            st.write(f"💲 Precio base: {precio_base:.2f} - Costo promedio: {costo:.2f} - Margen: {margen:.1f}%")
            st.write(f"📦 Stock disponible: {stock_disp:.2f}")

            # --- Cantidad y precio en la misma fila ---
            col_cant, col_prec = st.columns([1, 1])

            with col_cant:
                if stock_disp > 0:
                    cantidad = st.number_input(
                        "📌 Cantidad",
                        min_value=0.01,
                        max_value=stock_disp,
                        step=0.01,
                        value=min(1.0, stock_disp),
                        format="%.2f"
                    )
                else:
                    st.error("❌ No hay stock disponible para este producto.")
                    cantidad = 0.0

            with col_prec:
                precio_unit = st.number_input(
                    "💰 Precio de venta unitario",
                    min_value=0.01,
                    step=0.10,
                    value=precio_base,
                    format="%.2f"
                )

            # --- Validación del precio respecto al costo ---
            # Validación para agregar al carrito
            boton_carrito = True
            if precio_unit < costo:
                st.warning(f"⚠️ El precio ingresado ({precio_unit:.2f}) es menor al costo ({costo:.2f}).")
                boton_carrito = False
            else:
                boton_carrito = True

            if st.button("➕ Agregar al carrito", disabled=not boton_carrito):
                subtotal = float(cantidad) * float(precio_unit)
                st.session_state.carrito_ventas.append({
                    "ID Producto": id_producto,
                    "Descripción": desc_producto,
                    "Cantidad": float(cantidad),
                    "Precio Unitario": float(precio_unit),
                    "Subtotal": float(subtotal)
                })
                st.success(f"✅ {cantidad} x {desc_producto} agregado al carrito")

        # --- Mostrar carrito ---
        if st.session_state.carrito_ventas:
            df_carrito = pd.DataFrame(st.session_state.carrito_ventas)
            st.subheader("🛒 Carrito de Venta")
            st.dataframe(df_carrito, width="stretch", hide_index=True)

            # --- Calcular totales ---
            valor_venta = df_carrito["Subtotal"].sum()

            if "Nuevo RUS" in regimen:
                # En el RUS no se calcula IGV
                suma_total = valor_venta
                op_gravada = valor_venta
                igv = 0.00
                total = valor_venta
            else:
                # En el régimen general los precios incluyen IGV
                suma_total = round(valor_venta / 1.18, 2)
                op_gravada = round(valor_venta / 1.18, 2)
                igv = round(op_gravada * 0.18, 2)
                total = round(op_gravada + igv, 2)

            # Mostrar métricas
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("💵 Valor Venta (con IGV)", f"S/. {valor_venta:,.2f}")
            with col2:
                st.metric("💰 Op. Gravada", f"S/. {op_gravada:,.2f}")
            with col3:
                st.metric("💸 IGV (18%)", f"S/. {igv:,.2f}")
            with col4:
                st.metric("🧾 Total", f"S/. {total:,.2f}")

            # ============================
            # Calculadora de cambio (solo efectivo)
            # ============================
            vuelto = 0.0  # valor por defecto
            boton_guardar = False

            if metodo_pago == "Efectivo":
                st.subheader("💵 Pago en efectivo")
                pago_cliente = st.number_input(
                    "💰 Monto entregado por el cliente",
                    min_value=0.0,
                    value=0.0,
                    step=0.10,
                    format="%.2f"
                )

                if pago_cliente > 0:
                    if pago_cliente < total:
                        st.warning(f"⚠️ El pago es menor al total a cobrar (S/. {total:,.2f})")
                        boton_guardar= False  # no se puede guardar
                    else:
                        vuelto = round(pago_cliente - total, 2)
                        st.success(f"💸 Vuelto a entregar: S/. {vuelto:,.2f}")
                        boton_guardar = True
            else:
                # Métodos de pago no efectivo
                boton_guardar = True


            # ============================
            # TODO EN UNA SOLA FILA
            # ============================
            col1, col2, col3 = st.columns([1, 1, 1])

                        # 🗑 Vaciar carrito
            with col1:
                st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
                if st.button("🗑 Vaciar carrito", type="secondary"):
                    st.session_state.carrito_ventas = []

            # 💾 Guardar venta
            with col2:
                st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
                if st.button("💾 Guardar e imprimir comprobante", type="primary", disabled=not boton_guardar):

                    # 1) Guardar venta
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO venta (
                            fecha, id_cliente, suma_total, op_gravada, igv, total,
                            tipo_comprobante, metodo_pago, nro_comprobante, pago_cliente, vuelto
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        fecha, cliente_id, suma_total, op_gravada, igv, total,
                        tipo_comprobante, metodo_pago, nro_comprobante,
                        pago_cliente if metodo_pago == "Efectivo" else None,
                        vuelto if metodo_pago == "Efectivo" else None
                    ))
                    id_venta = cursor.lastrowid
                    st.session_state["venta_actual_id"] = id_venta

                    # 2) Guardar detalles
                    for item in st.session_state.carrito_ventas:
                        if "Nuevo RUS" in regimen:
                            precio_sin_igv = item["Precio Unitario"]
                            subtotal_sin_igv = item["Subtotal"]
                        else:
                            precio_sin_igv = round(item["Precio Unitario"] / 1.18, 2)
                            subtotal_sin_igv = round(precio_sin_igv * item["Cantidad"], 2)

                        cursor.execute("""
                            INSERT INTO venta_detalle (id_venta, id_producto, cantidad, precio_unitario, sub_total, precio_final)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (id_venta, item["ID Producto"], item["Cantidad"], precio_sin_igv, subtotal_sin_igv, subtotal_sin_igv))

                        registrar_salida_por_venta(
                            cursor,
                            id_producto=item["ID Producto"],
                            cantidad_salida=item["Cantidad"],
                            fecha=fecha,
                            referencia=f"Venta cliente {cliente_id} - {nro_comprobante}"
                        )

                    conn.commit()
                    conn.close()

                    # Vaciar carrito
                    st.session_state.carrito_ventas = []

                    # 3) GENERAR COMPROBANTE SIN RERUN
                    comprobante_html = generar_html_comprobante(id_venta)
                    st.success(f"✅ Venta registrada correctamente (ID: {id_venta})")
                    st.markdown(comprobante_html, unsafe_allow_html=True)



    # ========================
    # TAB 2: Consultar Ventas
    # ========================
    with tabs[1]:
        st.subheader("📋 Consultar ventas")
        col1, col2, col3 = st.columns(3)
        with col1:
            fecha_ini = st.date_input("Desde", datetime.today().replace(day=1))
        with col2:
            fecha_fin = st.date_input("Hasta", datetime.today())
        with col3:
            cliente_filtro = st.text_input("Cliente")

        query = """
            SELECT v.id, v.fecha, c.nombre AS cliente, v.nro_comprobante, v.tipo_comprobante, v.metodo_pago, v.total
            FROM venta v
            LEFT JOIN cliente c ON v.id_cliente = c.id
            WHERE date(v.fecha) BETWEEN ? AND ?
        """
        params = [fecha_ini, fecha_fin]
        if cliente_filtro:
            query += " AND c.nombre LIKE ?"
            params.append(f"%{cliente_filtro}%")
        
        df_ventas = query_df(query, params)

        st.dataframe(df_ventas, width="stretch", hide_index=True)

    # ========================
    # TAB 3: Reportes
    # ========================
    with tabs[2]:
        st.subheader("📊 Reportes de Ventas")
        tipo_reporte = st.selectbox("Selecciona reporte", ["Por cliente", "Por producto", "Diario", "Mensual"])

        if tipo_reporte == "Por cliente":
            df = query_df("""
                SELECT c.nombre AS cliente, SUM(v.total) AS total_ventas
                FROM venta v
                LEFT JOIN cliente c ON v.id_cliente = c.id
                GROUP BY c.nombre
                ORDER BY total_ventas DESC
            """)
            if not df.empty:
                st.bar_chart(df.set_index("cliente"))
            else:
                st.warning("⚠️ No hay datos para mostrar en este reporte")

        elif tipo_reporte == "Por producto":
            df = query_df("""
                SELECT p.descripcion, SUM(d.cantidad * d.precio_unitario) AS total_ventas
                FROM venta_detalle d
                JOIN producto p ON d.id_producto = p.id
                GROUP BY p.descripcion
                ORDER BY total_ventas DESC
            """)
            if not df.empty:
                st.bar_chart(df.set_index("descripcion"))
            else:
                st.warning("⚠️ No hay datos para mostrar en este reporte")

        elif tipo_reporte == "Diario":
            df = query_df("""
                SELECT DATE(fecha) AS dia, SUM(total) AS total_dia
                FROM venta
                GROUP BY DATE(fecha)
                ORDER BY dia
            """)
            if not df.empty:
                st.line_chart(df.set_index("dia"))
            else:
                st.warning("⚠️ No hay datos para mostrar en este reporte")

        elif tipo_reporte == "Mensual":
            df = query_df("""
                SELECT strftime('%Y-%m', fecha) AS mes, SUM(total) AS total_mes
                FROM venta
                GROUP BY mes
                ORDER BY mes
            """)
            if not df.empty:
                st.line_chart(df.set_index("mes"))
            else:
                st.warning("⚠️ No hay datos para mostrar en este reporte")
