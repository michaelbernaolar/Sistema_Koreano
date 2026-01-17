import streamlit as st
import pandas as pd

from db import get_connection
from datetime import datetime
from db import actualizar_costo_promedio
from db import obtener_configuracion
from db import recalcular_precios_producto
from db import registrar_historial_precio

from modulos.ventas import to_float
from services.producto_service import (
    buscar_producto_avanzado, contar_productos,
    obtener_filtros_productos
)

def compras_app():
    conn = get_connection()
    # Leer configuración general
    configuracion = obtener_configuracion()
    regimen = configuracion.get("regimen", "Nuevo RUS")  # Valor por defecto

    cursor = conn.cursor()
    st.title("📦 Registro y Consulta de Compras")

    tabs = st.tabs(["📝 Registrar Compra", "📋 Consultar Compras", "📊 Reportes"])

    # ========================
    # TAB 1: Registrar Compra
    # ========================
    with tabs[0]:
        df_prov = pd.read_sql_query("SELECT id, nombre FROM proveedor ORDER BY nombre", conn)
        df_prod = pd.read_sql_query("SELECT id, descripcion, unidad_base, stock_actual FROM producto ORDER BY descripcion", conn)

        if df_prov.empty:
            st.warning("⚠️ No hay proveedores registrados. Agrega uno en 📇 Proveedores.")
        elif df_prod.empty:
            st.warning("⚠️ No hay productos registrados. Agrega uno en 📦 Productos.")
        else:
            if "carrito_compras" not in st.session_state:
                st.session_state.carrito_compras = []

            col1, col2, col3 = st.columns(3)
            with col1:
                fecha = st.date_input("📅 Fecha", datetime.today())
            with col2:
                proveedor_sel = st.selectbox(
                    "🏢 Proveedor",
                    [f"{row['id']} | {row['nombre']}" for _, row in df_prov.iterrows()]
                )
                id_proveedor, nombre_proveedor = proveedor_sel.split(" | ")
            with col3:
                nro_doc = st.text_input("📑 N° Documento")

            
            col1, col2, col3 = st.columns(3)
            with col1:
                tipo_doc = st.selectbox("📄 Tipo de Documento", ["Factura", "Boleta", "Nota"])
            with col2:
                metodo_pago = st.selectbox("💳 Método de Pago", ["Contado", "Crédito", "Transferencia"])            
            with col3:
                # --- Reglas de IGV simplificadas ---
                if tipo_doc == "Factura":
                    st.info("📄 Factura: la base es sin IGV y se calcula 18%.")
                    tipo_igv = "FACTURA"
                elif tipo_doc == "Boleta":
                    st.info("📄 Boleta: el precio ingresado es TOTAL (IGV incluido).")
                    tipo_igv = "BOLETA"
                else:  # Nota de venta u otros
                    st.info("📄 Nota: no incluye IGV.")
                    tipo_igv = "NOTA"

            st.markdown("### ➕ Agregar producto a la compra")

            df_filtros = obtener_filtros_productos()

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
            criterio = st.text_input("Buscar por palabra clave (código, descripción, modelo, etc.)")

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

                ver_todos = st.checkbox(f"📄 Ver todos los resultados ({total_productos})")

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
                # ==============================
                # SELECCIÓN DEL PRODUCTO
                # ==============================
                productos_dict = {
                    f"{row.id} | {row.descripcion}": row
                    for row in df_prod.itertuples()
                }

                producto_sel = st.selectbox(
                    "📦 Selecciona un producto",
                    list(productos_dict.keys())
                )

                row = productos_dict[producto_sel]

                id_producto = row.id
                desc_producto = row.descripcion
                stock_disp = to_float(row.stock_actual)

                # ==============================
                # RELACIÓN PRODUCTO–PROVEEDOR
                # ==============================
                df_rel = pd.read_sql_query("""
                    SELECT unidad_compra, factor, precio_compra 
                    FROM producto_proveedor 
                    WHERE id_producto=%s AND id_proveedor=%s
                """, conn, params=[id_producto, id_proveedor])

                # ==============================
                # UNIDAD DE COMPRA
                # ==============================
                if not df_rel.empty:
                    unidad_opciones = df_rel["unidad_compra"].tolist() + ["Otro"]

                    col1, col2 = st.columns(2)
                    with col1:
                        unidad_compra = st.selectbox("📏 Unidad de compra", unidad_opciones)
                    with col2:
                        if unidad_compra != "Otro":
                            factor = float(
                                df_rel[df_rel["unidad_compra"] == unidad_compra]["factor"].iloc[0]
                            )
                            st.text_input("🔢 Factor conversión", value=factor, disabled=True)
                        else:
                            factor = st.number_input("🔢 Factor conversión", min_value=1.0, step=1.0)
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        unidad_compra = st.text_input("📏 Unidad de compra")
                    with col2:
                        factor = st.number_input("🔢 Factor conversión", min_value=1.0, step=1.0)

                # ==============================
                # CANTIDAD Y PRECIO
                # ==============================
                col_cant, col_prec = st.columns(2)

                with col_cant:
                    cantidad_compra = st.number_input(
                        "📌 Cantidad (unidad compra)",
                        min_value=1.0,
                        step=1.0,
                        value=1.0
                    )

                with col_prec:
                    precio_unitario = st.number_input(
                        "💲 Precio por unidad",
                        min_value=0.01,
                        step=0.10,
                        value=0.10
                    )

                if st.button("➕ Agregar al carrito"):
                        cantidad_final = cantidad_compra * factor
                        precio_sin_igv = precio_unitario
                        subtotal = precio_sin_igv * cantidad_compra

                        st.session_state.carrito_compras.append({
                            "ID Producto": id_producto,
                            "Descripción": desc_producto,
                            "Unidad Compra": unidad_compra,
                            "Factor": factor,
                            "Cantidad Compra": cantidad_compra,
                            "Cantidad Final": cantidad_final,
                            "Precio U. Compra": round(precio_sin_igv, 2),
                            "Subtotal": round(subtotal, 2)
                        })
                        st.success(f"✅ {cantidad_compra} {unidad_compra} de {desc_producto} agregado al carrito")    

            # === Mostrar carrito y totales ===
            if st.session_state.carrito_compras:
                df_carrito = pd.DataFrame(st.session_state.carrito_compras)
                st.subheader("🛒 Carrito de Compras")
                # Mostrar también precio con IGV para claridad (no se guarda así en BD)
                df_carrito_display = df_carrito.copy()
                st.dataframe(df_carrito_display, width='stretch', hide_index=True)

                # Totales (suma de SUBTOTALES guardados, que están SIN IGV)
                suma_total = df_carrito["Subtotal"].sum()
                descuento = st.number_input("🔻 Descuento", min_value=0.0, step=0.10)
                op_gratuita = 0.0

            
                # === CÁLCULO GLOBAL SEGÚN TIPO DE DOCUMENTO ===                
                if tipo_doc == "Factura":
                    op_gravada = suma_total - descuento
                    igv = round(op_gravada * 0.18, 2)
                    total = op_gravada + igv

                elif tipo_doc == "Boleta":
                    op_gravada = round(suma_total/1.18,2)
                    igv = round(op_gravada * 0.18, 2)
                    total = suma_total

                else:  # Nota revisar
                    igv = 0.0
                    total = op_gravada

                # Mostrar resumen
                st.markdown("### 💰 Resumen de la Compra")

                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric("💵 Valor Venta", f"S/. {suma_total:,.2f}")
                with col2:
                    st.metric("🧾 Total Descuento", f"S/. {descuento:,.2f}")
                with col3:
                    st.metric("💰 Op. Gravada", f"S/. {op_gravada:,.2f}")
                with col4:
                    st.metric("💸 IGV (18%)", f"S/. {igv:,.2f}")
                with col5:
                    st.metric("🧾 Total", f"S/. {total:,.2f}")

                # Botones de acción
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🗑 Vaciar carrito"):
                        st.session_state.carrito_compras = []
                with col2:
                    if st.button("💾 Guardar compra"):
                        
                        cursor.execute("""
                            INSERT INTO compras (
                                fecha, id_proveedor, nro_doc, tipo_doc,
                                suma_total, descuento, op_gravada, op_gratuita,
                                igv, total, metodo_pago
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            fecha, id_proveedor, nro_doc, tipo_doc,
                            suma_total, descuento, op_gravada, op_gratuita,
                            igv, total, metodo_pago
                        ))


                        id_compra = cursor.fetchone()[0]

                        for item in st.session_state.carrito_compras:
                            cursor.execute("""
                                INSERT INTO compras_detalle (
                                    id_compra, id_producto, cantidad_compra, unidad_compra, 
                                    factor_conversion, cantidad_final, precio_unitario, subtotal
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                id_compra, item["ID Producto"], item["Cantidad Compra"], item["Unidad Compra"],
                                item["Factor"], item["Cantidad Final"], item["Precio U. Compra"], item["Subtotal"]
                            ))

                            # 🔹 Costo unitario de entrada 
                            if regimen == "Nuevo RUS":
                                if tipo_doc == "Factura":   
                                    costo_unitario_entrada = item["Precio U. Compra"] * 1.18
                                else:
                                    costo_unitario_entrada = item["Precio U. Compra"]
                            else:
                                costo_unitario_entrada = item["Precio U. Compra"]


                            # 🔹 Actualizar stock y costo promedio (reemplaza el UPDATE producto)
                            actualizar_costo_promedio(cursor, item["ID Producto"], item["Cantidad Final"], costo_unitario_entrada)
                            resultado = recalcular_precios_producto(cursor, item["ID Producto"])
                            if resultado:
                                precio_anterior, precio_nuevo, margen, costo_promedio = resultado

                                registrar_historial_precio(
                                    cursor,
                                    item["ID Producto"],
                                    precio_anterior,
                                    precio_nuevo,
                                    margen,
                                    costo_promedio
                                )

                            # 🔹 Registrar movimiento de entrada con costos
                            cursor.execute("""
                                INSERT INTO public.movimientos (
                                    id_producto, tipo, cantidad, fecha, motivo, referencia, 
                                    costo_unitario, valor_total
                                )
                                VALUES (%s, 'entrada', %s, %s, %s, %s, %s, %s)
                            """, (
                                item["ID Producto"],
                                item["Cantidad Final"],
                                fecha,
                                f"Compra {nombre_proveedor}",
                                nro_doc,
                                costo_unitario_entrada,
                                item["Cantidad Final"] * costo_unitario_entrada
                            ))

                        conn.commit()
                        st.success("✅ Compra registrada correctamente")
                        st.session_state.carrito_compras = []
                        st.rerun()


    # ========================
    # TAB 2: Consultar Compras
    # ========================
    with tabs[1]:
        st.subheader("📋 Consultar Compras")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            fecha_ini = st.date_input("Desde", datetime.today().replace(day=1))
        with col2:
            fecha_fin = st.date_input("Hasta", datetime.today())
        with col3:
            proveedor_filtro = st.text_input("Proveedor")
        with col4:
            producto_filtro = st.text_input("Producto")

        query = """
            SELECT c.id, c.fecha, p.nombre AS proveedor, c.nro_doc, c.tipo_doc, c.total
            FROM compras c
            JOIN proveedor p ON c.id_proveedor = p.id
            WHERE date(c.fecha) BETWEEN %s AND %s
        """
        params = [fecha_ini, fecha_fin]

        if proveedor_filtro:
            query += " AND p.nombre LIKE %s"
            params.append(f"%{proveedor_filtro}%")
        if producto_filtro:
            query += """ AND c.id IN (
                SELECT id_compra FROM compras_detalle d 
                JOIN producto pr ON d.id_producto = pr.id 
                WHERE pr.descripcion LIKE %s
            )"""
            params.append(f"%{producto_filtro}%")

        df_compras = pd.read_sql_query(query, conn, params=params)
        st.dataframe(df_compras, width='stretch', hide_index=True)

    # ========================
    # TAB 3: Reportes
    # ========================
    with tabs[2]:
        st.subheader("📊 Reportes de Compras")
        tipo_reporte = st.selectbox("Selecciona reporte", ["Por proveedor", "Por producto", "Mensual"])

        if tipo_reporte == "Por proveedor":
            df = pd.read_sql_query("""
                SELECT p.nombre AS proveedor, SUM(c.total) AS total_compras
                FROM compras c
                JOIN proveedor p ON c.id_proveedor = p.id
                GROUP BY p.nombre
                ORDER BY total_compras DESC
            """, conn)
            if not df.empty:
                st.bar_chart(df.set_index("proveedor"))
            else:
                st.info("📭 No hay datos de compras por proveedor aún.")

        elif tipo_reporte == "Por producto":
            df = pd.read_sql_query("""
                SELECT pr.descripcion, SUM(d.cantidad_final * d.precio_unitario) AS total_compras
                FROM compras_detalle d
                JOIN producto pr ON d.id_producto = pr.id
                GROUP BY pr.descripcion
                ORDER BY total_compras DESC
            """, conn)
            if not df.empty:
                st.bar_chart(df.set_index("descripcion"))
            else:
                st.info("📭 No hay datos de compras por producto aún.")

        elif tipo_reporte == "Mensual":
            df = pd.read_sql_query("""
                SELECT to_char(fecha, 'YYYY-MM') AS mes, SUM(total) AS total_mes
                FROM compras
                GROUP BY mes
                ORDER BY mes
            """, conn)
            if not df.empty:
                st.line_chart(df.set_index("mes"))
            else:
                st.info("📭 No hay datos mensuales para mostrar.")

    conn.close()
