import pandas as pd
import streamlit as st
import os
import pytz
from datetime import datetime

from db import (
    get_connection, query_df,
    select_cliente, obtener_cliente_por_id,
    registrar_salida_por_venta, obtener_configuracion,
    obtener_siguiente_correlativo_ticket,obtener_fecha_lima
)

from services.producto_service import (
    buscar_producto_avanzado,
    contar_productos,
    obtener_valores_unicos
)
from services.venta_service import (
    calcular_totales,
    guardar_venta
)
from services.comprobante_service import (
    generar_ticket_html,
    generar_ticket_pdf
)

@st.cache_data(ttl=300)
def productos_para_filtros():
    query = """
        SELECT
            p.marca,
            c.nombre AS categoria,
            p.stock_actual
        FROM producto p
        LEFT JOIN categoria c ON p.id_categoria = c.id
    """
    return query_df(query)

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

        # --- Datos del comprobante ---
        col1, col2, col3 = st.columns(3)
        nro_comprobante = ""  
        with col1:
            metodo_pago = st.selectbox(
                "💳 Método de pago",
                ["Efectivo", "Yape", "Plin", "Tarjeta", "Transferencia"],
                key="metodo_pago_select"
            )
        with col2:
            if "Nuevo RUS" in regimen:
                tipo_comprobante = "Ticket"
                st.text_input("📄 Tipo de comprobante", value=tipo_comprobante, disabled=True)
            else:
                tipo_comprobante = st.selectbox("📄 Tipo de comprobante",["Boleta", "Factura"])
        with col3:
            if "Nuevo RUS" in regimen:
                nro_comprobante = obtener_siguiente_correlativo_ticket()
                st.text_input("📑 N° Comprobante", value=nro_comprobante, disabled=True)
            else:
                nro_comprobante = st.text_input("📑 N° Documento")

        # --- Cliente, Régimen y Método de Pago ---
        col1, col2, col3 = st.columns([5, 2, 2])
        with col1:
            cliente_id = select_cliente()

        if cliente_id is None:
            st.stop()

        cliente = obtener_cliente_por_id(cliente_id)
        es_varios = cliente["dni_ruc"] == "99999999"
        with col2:
            if es_varios:
                nro_comprobante = cliente["dni_ruc"]  # 99999999
                st.text_input(
                    "📑 N° Documento",
                    value=nro_comprobante,
                    disabled=True
                )
            else:
                nro_comprobante = st.text_input("📑 N° Documento")

        with col3:
            placa_vehiculo = None
            if es_varios:
                placa_vehiculo = st.text_input(
                    "🚗 Placa del vehículo (obligatoria)",
                    max_chars=10
                ).upper()

        # --- Carrito en sesión ---
        st.session_state.setdefault("carrito_ventas", [])

        st.markdown("### ➕ Agregar productos a la venta")
        df_filtros = productos_para_filtros()

        col1, col2, col3 = st.columns(3)

        # --- CATEGORÍA (primer filtro) ---
        with col2:
            categorias = ["Todos"] + sorted(
                df_filtros["categoria"].dropna().unique().tolist()
            )
            filtro_categoria = st.selectbox("Categoría", categorias)

            if filtro_categoria != "Todos":
                df_filtros = df_filtros[df_filtros["categoria"] == filtro_categoria]

        # --- MARCA (depende de categoría) ---
        with col1:
            marcas = ["Todos"] + sorted(
                df_filtros["marca"].dropna().unique().tolist()
            )
            filtro_marca = st.selectbox("Marca", marcas)

            if filtro_marca != "Todos":
                df_filtros = df_filtros[df_filtros["marca"] == filtro_marca]

        # --- STOCK (depende de los dos anteriores) ---
        with col3:
            filtro_stock = st.selectbox(
                "Stock",
                ["Todos", "Con stock", "Sin stock"]
            )
            if filtro_stock == "Con stock":
                df_filtros = df_filtros[df_filtros["stock_actual"] > 0]
            elif filtro_stock == "Sin stock":
                df_filtros = df_filtros[df_filtros["stock_actual"] <= 0]

        criterio = st.text_input(
            "Buscar por palabra clave (código, descripción, modelo, etc.)"
        )

        LIMITE_INICIAL = 20

        hay_filtros = any([
            bool(criterio),
            filtro_marca != "Todos",
            filtro_categoria != "Todos",
            filtro_stock != "Todos"
        ])

        df_prod = pd.DataFrame()
        total_productos = 0

        if hay_filtros:
            total_productos = contar_productos(
                criterio,
                filtro_marca,
                filtro_categoria,
                filtro_stock
            )

            ver_todos = st.checkbox(
                f"📄 Ver todos los resultados ({total_productos})"
            )

            limite = total_productos if ver_todos else LIMITE_INICIAL

            df_prod = buscar_producto_avanzado(
                criterio,
                filtro_marca,
                filtro_categoria,
                filtro_stock,
                limit=limite
            )

        if df_prod.empty: 
            st.warning("⚠️ No hay productos disponibles con esos filtros.")
        else:
            productos_dict = {
                f"{row['id']} | {row['descripcion']}": row
                for _, row in df_prod.iterrows()
            }
            
            opciones = list(productos_dict.keys())

            producto_sel = st.selectbox(
                "📦 Selecciona un producto",
                opciones,
                index=0 if opciones else None
            )

            if producto_sel not in productos_dict:
                st.warning("🔄 La selección cambió, vuelve a elegir el producto.")
                st.stop()

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

            if st.button(
                "➕ Agregar al carrito",
                disabled=not boton_carrito or st.session_state.get("venta_guardada", False)
            ):
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
        if st.session_state.carrito_ventas or st.session_state.get("venta_guardada"):
            df_carrito = pd.DataFrame(st.session_state.carrito_ventas)
            st.subheader("🛒 Carrito de Venta")
            st.dataframe(df_carrito, width="stretch", hide_index=True)

            # --- Calcular totales ---
            valor_venta = df_carrito["Subtotal"].sum()

            totales = calcular_totales(valor_venta, regimen)

            op_gravada = totales["op_gravada"]
            igv = totales["igv"]
            total = totales["total"]
            suma_total = totales["valor_venta"]

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
            pago_cliente = None

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
            
            st.session_state.setdefault("venta_guardada", False)
            st.session_state.setdefault("pdf_generado", False)
            st.session_state.setdefault("ruta_pdf", None)

            # ============================
            # BOTONES EN UNA SOLA FILA
            # ============================
            col1, col2, col3, col4, col5 = st.columns([1, 1.4, 1.4, 1.4, 1])

            with col1:
                if st.button(
                    "🗑 Vaciar carrito",
                    disabled=st.session_state.get("venta_guardada", False)
                ):
                    st.session_state.carrito_ventas = []
            with col2:
                if st.button(
                    "💾 Guardar venta",
                    type="primary",
                    disabled=not boton_guardar or st.session_state["venta_guardada"]
                ):
                    fecha = obtener_fecha_lima()

                    if tipo_comprobante == "Ticket":
                        nro_comprobante = obtener_siguiente_correlativo_ticket()

                    id_venta = guardar_venta(
                        fecha=fecha,
                        cliente=cliente,
                        regimen=regimen,
                        tipo_comprobante=tipo_comprobante,
                        metodo_pago=metodo_pago,
                        nro_comprobante=nro_comprobante,
                        placa_vehiculo=placa_vehiculo,
                        pago_cliente=pago_cliente,
                        vuelto=vuelto,
                        carrito=st.session_state.carrito_ventas
                    )

                    st.session_state["venta_actual_id"] = id_venta
                    st.session_state["venta_guardada"] = True

                    st.success(f"✅ Venta registrada correctamente (ID: {id_venta})")

            with col3:
                if st.button(
                    "🧾 Imprimir",
                    disabled=not st.session_state["venta_guardada"]
                ):
                    if "venta_actual_id" in st.session_state:
                        html = generar_ticket_html(st.session_state["venta_actual_id"])
                        st.components.v1.html(html, height=600, scrolling=True)
                    else:
                        st.warning("Primero guarda la venta")

            with col4:
                if not st.session_state["pdf_generado"]:
                    if st.button(
                        "📄 Generar PDF",
                        disabled=not st.session_state["venta_guardada"]
                    ):
                        if "venta_actual_id" in st.session_state:
                            ruta_pdf = f"ticket_{st.session_state['venta_actual_id']}.pdf"
                            generar_ticket_pdf(st.session_state["venta_actual_id"], ruta_pdf)

                            st.session_state["ruta_pdf"] = ruta_pdf
                            st.session_state["pdf_generado"] = True
                        else:
                            st.warning("Primero guarda la venta")
                else:
                    with open(st.session_state["ruta_pdf"], "rb") as f:
                        st.download_button(
                            "⬇️ Descargar PDF",
                            f,
                            file_name=st.session_state["ruta_pdf"],
                            mime="application/pdf"
                        )
            with col5:
                if st.button(
                    "✔️ Finalizar",
                    disabled=not st.session_state.get("venta_guardada", False)
                ):
                    # Vaciar carrito y estados de venta
                    st.session_state.carrito_ventas = []
                    st.session_state["venta_guardada"] = False
                    st.session_state["pdf_generado"] = False
                    st.session_state["ruta_pdf"] = None
                    st.session_state.pop("venta_actual_id", None)

                    # Limpiar filtros y búsquedas
                    for key in list(st.session_state.keys()):
                        if key.startswith(("filtro_", "buscar_", "producto_", "criterio")):
                            st.session_state.pop(key, None)

                    # NO tocar:
                    # - cliente
                    # - metodo_pago_select (Efectivo)

                    st.rerun()

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
            WHERE v.fecha BETWEEN %s AND %s
        """
        params = [fecha_ini, fecha_fin]
        if cliente_filtro:
            query += " AND c.nombre LIKE %s"
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
                SELECT to_char(fecha, 'YYYY-MM') AS mes, SUM(total) AS total_mes
                FROM venta
                GROUP BY mes
                ORDER BY mes
            """)
            if not df.empty:
                st.line_chart(df.set_index("mes"))
            else:
                st.warning("⚠️ No hay datos para mostrar en este reporte")
