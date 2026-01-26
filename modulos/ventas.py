# modulos/ventas.py
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timedelta
from typing import Any
from decimal import Decimal

from db import (
    query_df, select_cliente, obtener_cliente_por_id,
    obtener_configuracion, obtener_fecha_lima
)

from services.producto_service import (
    buscar_producto_avanzado, contar_productos,
    obtener_filtros_productos, to_float
)
from services.venta_service import (
    calcular_totales, guardar_venta, agregar_item_venta, obtener_valor_venta, obtener_detalle_venta,
    inicializar_estado_venta, resetear_venta, precio_valido, obtener_ventas_abiertas, crear_venta_abierta, 
    puede_guardar_venta, eliminar_item_servicio, eliminar_items_servicio, eliminar_venta_abierta, placa_a_mayusculas
)
from services.comprobante_service import (
    generar_ticket_html, obtener_siguiente_correlativo, buscar_comprobantes,
    generar_ticket_pdf, registrar_reimpresion
)
from ui.styles import (
    aplicar_estilos_input_busqueda, aplicar_estilos_selectbox
)   


def ventas_app():

    aplicar_estilos_input_busqueda()
    aplicar_estilos_selectbox()
    
    if "caja_abierta_id" not in st.session_state:
        st.warning("⚠️ No hay una caja abierta")
        if st.button("Ir a Caja"):
            st.session_state.modulo = "💵 Caja"
            st.rerun()
        st.stop()
        
    st.title("🛒 Ventas")
    usuario = st.session_state.get("usuario")

    if not usuario:
        st.error("❌ No hay un usuario autenticado")
        st.stop()

    st.session_state.setdefault("placa_vehiculo", "")
    st.session_state.setdefault("venta_abierta_id", None)

    inicializar_estado_venta(st.session_state)
    tabs = st.tabs(["📝 Registrar Venta", "📋 Consultar Ventas", "📄 Comprobante", "📊 Reportes"])

    # =======================
    # TAB 1: Registrar Venta
    # ========================
    with tabs[0]:
        st.session_state.setdefault("carrito_ventas", [])
        st.session_state.setdefault("metodo_pago_select", "Yape")
        st.session_state.setdefault("criterio_busqueda", "")

        tipo_venta = st.radio(
            "Tipo de venta",
            ["POS", "Taller"],
            horizontal=True
        )
        # ===============================
        # DETECTAR CAMBIO DE TIPO DE VENTA
        # ===============================
        tipo_anterior = st.session_state.get("tipo_venta_anterior")

        if tipo_anterior != tipo_venta:
            # Limpieza total al cambiar de modo
            st.session_state["carrito_ventas"] = []
            st.session_state.pop("venta_abierta_id", None)

            if tipo_venta == "POS":
                st.session_state["placa_vehiculo"] = ""

            st.session_state["venta_guardada"] = False
            st.session_state["pdf_generado"] = False
            st.session_state["ruta_pdf"] = None

            # 🔥 LIMPIEZA DE BÚSQUEDA (CLAVE)
            st.session_state["criterio_busqueda"] = ""
            st.session_state["filtro_marca"] = "Todos"
            st.session_state["filtro_categoria"] = "Todos"
            st.session_state["filtro_stock"] = "Todos"

            st.session_state["metodo_pago_select"] = "Yape"

        st.session_state["tipo_venta_anterior"] = tipo_venta

        # ===============================
        # SERVICIOS / VENTAS EN CURSO
        # ===============================
        df_abiertas = pd.DataFrame()  # ← CLAVE

        if tipo_venta == "Taller":
            df_abiertas = obtener_ventas_abiertas()

            if not df_abiertas.empty:
                df_abiertas["fecha"] = pd.to_datetime(df_abiertas["fecha"]).dt.strftime("%d/%m %H:%M")
                
                st.subheader("🛠 En proceso")
                st.dataframe(df_abiertas, hide_index=True, width='stretch')

                st.markdown("Selección de orden")
                col_sel, col_del, col_space = st.columns([2, 1, 6])               

                with col_sel:
                    venta_sel = st.selectbox(
                        "",
                        df_abiertas["orden"].tolist(),
                        format_func=lambda x: f"#{x}",
                        key="select_orden",
                        label_visibility="collapsed"
                    )

                    # Si cambia la orden, actualizar placa
                    if st.session_state.get("venta_abierta_id") != venta_sel:
                        st.session_state["venta_abierta_id"] = venta_sel

                        placa = df_abiertas.loc[
                            df_abiertas["orden"] == venta_sel, "placa"
                        ].values[0]

                        st.session_state["placa_vehiculo"] = placa

                with col_del:
                    if st.button("❌ Eliminar", key="eliminar_venta"):
                        try:
                            eliminar_venta_abierta(st.session_state["venta_abierta_id"])
                            st.success(f"Orden #{st.session_state['venta_abierta_id']} eliminada correctamente")
                            st.session_state.pop("venta_abierta_id", None)
                            st.session_state["placa_vehiculo"] = ""
                            st.rerun()
                        except Exception as e:
                            st.error(f"No se pudo eliminar la orden: {str(e)}")

                df_detalle = obtener_detalle_venta(venta_sel)

                # Convertir a carrito visual (solo para mostrar)
                df_carrito_taller = df_detalle.copy()
            else:
                st.info("No hay servicios en curso")

        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("📝 Registrar")
            # Obtener régimen desde configuración
            # Leer configuración general
            configuracion = obtener_configuracion()
            regimen = configuracion.get("regimen", "Nuevo RUS")  # Valor por defecto

        # --- Datos del comprobante --
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
                tipo_comprobante = "Ticket"   # ← DEFINES PRIMERO
                serie = "T"
                st.text_input(
                    "📄 Tipo de comprobante",
                    value=tipo_comprobante,
                    disabled=True
                )
            else:
                tipo_comprobante = st.selectbox(
                    "📄 Tipo de comprobante",
                    ["Boleta", "Factura"]
                )
                serie = "B" if tipo_comprobante == "Boleta" else "F"
        with col3:
            if "Nuevo RUS" in regimen:
                nro_comprobante, numero_correlativo = obtener_siguiente_correlativo(tipo_comprobante.upper(), serie)
                st.text_input("📑 N° Comprobante", value=nro_comprobante, disabled=True)
            else:
                nro_comprobante = st.text_input("📑 N° Comprobante")

        # --- Cliente, Régimen y Método de Pago ---
        col1, col2, col3 = st.columns([5, 2, 2])
        with col1:
            cliente_id = select_cliente()

        if cliente_id is None:
            st.stop()

        cliente = obtener_cliente_por_id(cliente_id)
        if cliente is None:
            st.error("❌ Cliente no encontrado")
            st.stop()

        es_varios = cliente.get("dni_ruc") == "99999999"
        with col2:
            if es_varios:
                nro_documento = cliente["dni_ruc"]  # 99999999
                st.text_input(
                    "📑 N° Documento",
                    value=nro_documento,
                    disabled=True
                )
            else:
                nro_documento = st.text_input("📑 N° Documento")
        with col3:
            placa_vehiculo = None
            if es_varios:
                st.text_input(
                    "🚗 Placa del vehículo (obligatoria)",
                    key="placa_vehiculo",
                    max_chars=10,
                    on_change=placa_a_mayusculas
                )

        # ===============================
        # ABRIR ORDEN DE SERVICIO
        # ===============================
        if st.button("🚗 Abrir orden de servicio"):
            if not st.session_state["placa_vehiculo"]:
                st.warning("Ingrese la placa del vehículo")
            else:
                id_venta = crear_venta_abierta(
                    cliente_id=cliente_id,
                    placa_vehiculo=st.session_state["placa_vehiculo"],
                    usuario_id=usuario["id"],
                    id_caja=st.session_state["caja_abierta_id"]
                )
                st.session_state["venta_abierta_id"] = id_venta
                st.success(f"Orden de servicio #{id_venta} creada")

        # --- Carrito en sesión --
        st.markdown("### ➕ Agregar productos")

        with st.expander("Filtros de productos"):
            df_filtros = obtener_filtros_productos()

            # Crear columnas para los tres filtros
            col_marca, col_categoria, col_stock = st.columns([1,1,1])  # proporciones ajustables

            # --- MARCA ---
            with col_marca:
                marcas = ["Todos"] + sorted(df_filtros["marca"].dropna().unique().tolist())
                filtro_marca = st.selectbox("Marca", marcas, key="filtro_marca")

                if filtro_marca != "Todos":
                    df_filtros = df_filtros[df_filtros["marca"] == filtro_marca]

            # --- CATEGORÍA ---
            with col_categoria:
                categorias = ["Todos"] + sorted(df_filtros["categoria"].dropna().unique().tolist())
                filtro_categoria = st.selectbox("Categoría", categorias, key="filtro_categoria")

                if filtro_categoria != "Todos":
                    df_filtros = df_filtros[df_filtros["categoria"] == filtro_categoria]

            # --- STOCK ---
            with col_stock:
                filtro_stock = st.selectbox("Stock", ["Todos", "Con stock", "Sin stock"], key="filtro_stock")

        criterio = st.text_input(
            "Buscar por palabra clave (código, descripción, modelo, etc.)",
            key="criterio_busqueda"
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
            productos_dict = {}
            for row in df_prod.itertuples():
                stock = to_float(row.stock_actual, 0.0)

                stock_label = f"{stock:.2f}" if stock > 0 else "SIN STOCK"

                label = f"{row.id} | {row.descripcion} | Stock: {stock_label}"
                productos_dict[label] = row
            
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
            id_producto = row.id
            desc_producto = row.descripcion
            stock_disp = to_float(row.stock_actual)
            costo = to_float(row.costo_promedio)
            margen = to_float(row.margen_utilidad) * 100

            st.write("### 📋 Detalles del producto")
            st.write(f"🔢 Código: {id_producto}")
            st.write(f"🧾 Descripción: {desc_producto}")
            st.write(f"🏭 Marca: {row.marca}")
            st.write(f"📖 Catálogo: {row.catalogo}")

            # --- Validar y asegurar precio base correcto ---
            try:
                precio_base = max(to_float(row.precio_venta, 0.0), 0.0)
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
                        min_value=1.0,
                        max_value=stock_disp,
                        step=1.0,        # ← SOLO controla + / -
                        value=1.0,
                        format="%.2f"
                    )
                else:
                    st.error("❌ No hay stock disponible para este producto.")
                    cantidad = 0.0

            with col_prec:
                precio_unit = st.number_input(
                    "💰 Precio de venta unitario",
                    min_value=0.0,
                    step=0.10,
                    value=precio_base,
                    format="%.2f"
                )

            # --- Validación del precio respecto al costo ---
            # Validación para agregar al carrito
            boton_carrito = True
            if not precio_valido(precio_unit, costo):
                st.warning(f"⚠️ El precio ingresado ({precio_unit:.2f}) es menor al costo ({costo:.2f}).")
                boton_carrito = False
            else:
                boton_carrito = True

            if st.button("➕ Agregar a la venta", disabled=not boton_carrito):
                if tipo_venta == "Taller":
                    df_abiertas = obtener_ventas_abiertas()
                    if "venta_abierta_id" not in st.session_state:
                        st.error("❌ Primero debes abrir una orden de servicio")
                        st.stop()

                    agregar_item_venta(
                        id_venta=st.session_state["venta_abierta_id"],
                        id_producto=id_producto,
                        cantidad=cantidad,
                        precio_unit=precio_unit
                    )

                else:  # POS
                    st.session_state.carrito_ventas.append({
                        "ID Producto": id_producto,
                        "Descripción": desc_producto,
                        "Cantidad": cantidad,
                        "Precio Unitario": precio_unit,
                        "Subtotal": round(cantidad * precio_unit, 2)
                    })
                st.session_state["criterio_busqueda"] = ""
                st.success("Producto agregado correctamente")

        # --- Mostrar carrito ---
        st.subheader("🛒 Carrito de Venta")

        if tipo_venta == "POS":
            df_carrito = pd.DataFrame(st.session_state.carrito_ventas)
        else:
            if "venta_abierta_id" not in st.session_state:
                st.info("Abra o seleccione una orden de servicio")
                df_carrito = pd.DataFrame()
            else:
                df_carrito = obtener_detalle_venta(st.session_state["venta_abierta_id"])

        if df_carrito.empty:
            st.info("🧹 Carrito vacío")
        else:
            # 🔹 RENOMBRAR COLUMNAS PARA MOSTRAR
            columnas_cortas = {
                "ID Producto": "ID",
                "Cantidad": "Cant.",
                "Precio Unitario": "P.U.",
                "Descripción": "Descripción",
                "Subtotal": "Subt."
            }
            df_mostrar = df_carrito.rename(columns=columnas_cortas)

            st.dataframe(df_mostrar, hide_index=True, width='stretch')
        
        # --- Eliminar producto del servicio (SOLO TALLER) ---
        if tipo_venta == "Taller" and not df_carrito.empty:

            col_sel, col_btn = st.columns([3, 1])

            with col_sel:
                producto_eliminar = st.selectbox(
                    "Código",
                    df_carrito["ID Producto"].tolist(),
                    help="Seleccione el código del producto a eliminar",
                    label_visibility="collapsed"
                )

            with col_btn:
                if st.button("❌ Eliminar", key=f"eliminar_producto_{producto_eliminar}", type="secondary"):
                    eliminar_item_servicio(
                        st.session_state["venta_abierta_id"],
                        producto_eliminar
                    )
                    st.success("Producto eliminado")
                    st.rerun()

        valor_venta_dec = Decimal("0.00")

        if not df_carrito.empty:
            if tipo_venta == "POS":
                valor_venta_dec = obtener_valor_venta(
                    carrito=st.session_state.carrito_ventas
                )
            else:
                valor_venta_dec = obtener_valor_venta(
                    id_venta=st.session_state["venta_abierta_id"]
                )

            totales = calcular_totales(valor_venta_dec, regimen)

            op_gravada = float(totales["op_gravada"])
            igv = float(totales["igv"])
            total = float(totales["total"])
        
            # Expander para detalles de la venta
            with st.expander("Detalle Venta"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("💵 Valor Venta", f"S/. {valor_venta_dec:,.2f}")
                with col2:
                    st.metric("💰 Op. Gravada", f"S/. {op_gravada:,.2f}")
                with col3:
                    st.metric("💸 IGV (18%)", f"S/. {igv:,.2f}")

            # Mostrar solo el total de forma principal
            st.metric("🧾 Total", f"S/. {total:,.2f}")

            # ============================
            # Calculadora de cambio (solo efectivo)
            # ============================
            pago_cliente = 0.0
            vuelto = 0.0
            
            if metodo_pago == "Efectivo":
                pago_cliente = st.number_input(
                    "💰 Monto entregado por el cliente",
                    min_value=0.0,
                    step=0.1,
                    format="%.2f",
                    key="pago_cliente"
                )

                if pago_cliente > 0:
                    if pago_cliente >= total:
                        vuelto = round(pago_cliente - total, 2)
                        st.success(f"💸 Vuelto: S/. {vuelto:,.2f}")
                    else:
                        st.warning("⚠️ El pago es menor al total")
            
            st.session_state.setdefault("venta_guardada", False)
            st.session_state.setdefault("pdf_generado", False)
            st.session_state.setdefault("ruta_pdf", None)

            carrito_validacion = (
                st.session_state.carrito_ventas
                if tipo_venta == "POS"
                else df_carrito.to_dict("records")
            )

            puede_guardar, motivo = puede_guardar_venta(
                carrito=carrito_validacion, 
                metodo_pago=metodo_pago, 
                total=total, 
                pago_cliente=pago_cliente
            )

            # ============================
            # VALIDACIÓN DE CAJA ABIERTA
            # ============================
            hay_caja_abierta = "caja_abierta_id" in st.session_state

            disabled_guardar = (
                not puede_guardar
                or not hay_caja_abierta
                or st.session_state.get("venta_guardada", False)
            )
            # ============================
            # BOTONES EN UNA SOLA FILA
            # ============================
            col1, col2, col3, col4, col5, col6 = st.columns([1, 1.4, 1.4, 1.4, 1.4, 1])

            with col1:
                if tipo_venta == "POS":
                    if st.button("🗑 Vaciar carrito", disabled=st.session_state["venta_guardada"]):
                        st.session_state.carrito_ventas = []

                if tipo_venta == "Taller":
                    if st.button("🗑 Vaciar carrito"):
                        eliminar_items_servicio(st.session_state["venta_abierta_id"])
                        st.success("Se limpio correctamente")
                        st.rerun() 
            with col2:    
                if st.button(
                    "💾 Guardar venta",
                    type="primary",
                    disabled=disabled_guardar
                ):
                    if "caja_abierta_id" not in st.session_state:
                        st.error("❌ No hay caja abierta")
                        st.stop()

                    if tipo_venta == "Taller" and not st.session_state["placa_vehiculo"]:
                        st.error("❌ La orden de taller debe tener placa")
                        st.stop()

                    fecha = obtener_fecha_lima()

                    carrito_guardar = (
                        st.session_state.carrito_ventas
                        if tipo_venta == "POS"
                        else None  # Taller se guarda desde BD
                    )
                    id_venta = guardar_venta(
                        fecha=fecha,
                        cliente=cliente,
                        regimen=regimen,
                        tipo_comprobante=tipo_comprobante,
                        metodo_pago=metodo_pago,
                        nro_comprobante=nro_comprobante,
                        placa_vehiculo=st.session_state["placa_vehiculo"],
                        pago_cliente=pago_cliente,
                        vuelto=vuelto,
                        carrito=carrito_guardar,
                        usuario=usuario,
                        id_caja=st.session_state["caja_abierta_id"],
                        id_venta_existente=st.session_state.get("venta_abierta_id")
                    )
                    st.session_state["venta_actual_id"] = id_venta
                    st.session_state["venta_guardada"] = True
                    st.success(f"✅ Venta registrada (ID {id_venta})")
                    st.rerun()
                if not puede_guardar and motivo:
                    st.info(f"ℹ️ {motivo}")

            with col3:
                if st.button("🧾 Imprimir"):
                    if "venta_actual_id" in st.session_state:
                        html = generar_ticket_html(
                            st.session_state["venta_actual_id"]
                        )

                        auto_print_html = f"""
                        <iframe id="printFrame" style="display:none;"></iframe>
                        <script>
                            const frame = document.getElementById("printFrame");
                            frame.contentDocument.open();
                            frame.contentDocument.write(`{html}`);
                            frame.contentDocument.close();
                            frame.onload = function () {{
                                frame.contentWindow.focus();
                                frame.contentWindow.print();
                            }};
                        </script>
                        """
                        components.html(auto_print_html, height=0)
            with col4:
                if st.button("🔁 Reimprimir"):
                    if "venta_actual_id" in st.session_state:
                        registrar_reimpresion(st.session_state["venta_actual_id"], usuario)
                        html = generar_ticket_html(st.session_state["venta_actual_id"])
                        components.html(html, height=600)
            with col5:
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
            with col6:
                if st.button("✔️ Finalizar"):
                    resetear_venta(st.session_state)
                    st.rerun()

            # -------- LIMPIAR BANDERA DE RESET VISUAL --------
            if st.session_state.get("reset_en_progreso"):
                st.session_state.pop("reset_en_progreso")

    # ========================
    # TAB 2: Consultar Ventas
    # =======================
    with tabs[1]:
        st.subheader("📋 Consultar ventas")
        col1, col2, col3 = st.columns(3)
        with col1:
            fecha_ini = st.date_input("Desde", datetime.today().replace(day=1))
        with col2:
            fecha_fin = st.date_input("Hasta", datetime.today())
        with col3:
            comprobante_filtro = st.text_input("N° Comprobante", placeholder="Ej: T-000123")

        fecha_fin = fecha_fin + timedelta(days=1)

        query = """
            SELECT v.id, v.fecha, c.nombre AS cliente, v.nro_comprobante, v.tipo_comprobante, v.metodo_pago, v.total
            FROM venta v
            LEFT JOIN cliente c ON v.id_cliente = c.id
            WHERE v.estado = 'EMITIDA'
            AND v.fecha >= %s
            AND v.fecha < %s
        """
        params: list[Any] = [fecha_ini, fecha_fin]
        
        if comprobante_filtro.strip():
            query += " AND v.nro_comprobante ILIKE %s"
            params.append(f"%{comprobante_filtro.strip()}%")
        
        query += " ORDER BY v.fecha DESC"
        df_ventas = query_df(query, params)

        st.dataframe(df_ventas, width='stretch', hide_index=True)

        venta_id_anular = st.number_input(
            "ID de venta a anular",
            min_value=1,
            step=1
        )

        motivo = st.text_area("Motivo de anulación (obligatorio)")

        if st.button("❌ Anular venta"):
            if not motivo.strip():
                st.error("Debe ingresar un motivo")
            else:
                try:
                    from services.venta_service import anular_venta
                    anular_venta(venta_id_anular, motivo, usuario)
                    st.success("Venta anulada correctamente")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
    # =======================
    # TAB 3: Comprobante
    # =======================
    with tabs[2]:
        st.subheader("📄 Comprobante")

        nro_comprobante = st.text_input(
            "Número de comprobante",
            placeholder="Ej: T-00005, T*05, T*05*"
        ).strip()

        if nro_comprobante:
            resultados = buscar_comprobantes(nro_comprobante)

            if not resultados:
                st.session_state.pop("ver_comprobante_id", None)
                st.session_state["resultados_comprobantes"] = []
                st.error("❌ Comprobante no encontrado")

            elif len(resultados) == 1:
                st.session_state["ver_comprobante_id"] = resultados[0][0]
                st.session_state["resultados_comprobantes"] = []

            else:
                st.session_state.pop("ver_comprobante_id", None)
                st.session_state["resultados_comprobantes"] = resultados

        # --- TABLA DE RESULTADOS (cuando hay varios) ---
        if st.session_state.get("resultados_comprobantes"):
            st.info("🔎 Se encontraron varios comprobantes")

            df = pd.DataFrame(
                st.session_state["resultados_comprobantes"],
                columns=["ID", "Comprobante", "Fecha", "Total"]
            )

            seleccion = st.dataframe(
                df,
                hide_index=True,
                width='stretch',
                on_select="rerun",
                selection_mode="single-row"
            )

            if seleccion and seleccion["selection"]["rows"]:
                fila = seleccion["selection"]["rows"][0]
                vid = df.iloc[fila]["ID"]
                st.session_state["ver_comprobante_id"] = vid
                st.session_state["resultados_comprobantes"] = []

        # --- MOSTRAR COMPROBANTE ---
        if "ver_comprobante_id" in st.session_state:
            vid = st.session_state["ver_comprobante_id"]

            html = generar_ticket_html(vid)
            components.html(html, height=600)

            col1, col2 = st.columns(2)

            with col1:
                if st.button("🖨 Reimprimir"):
                    registrar_reimpresion(vid, usuario)
                    st.success("Reimpresión registrada")
                    st.rerun()

            with col2:
                ruta = f"ticket_{vid}.pdf"
                generar_ticket_pdf(vid, ruta)

                with open(ruta, "rb") as f:
                    st.download_button(
                        "⬇️ Descargar PDF",
                        f,
                        file_name=ruta,
                        mime="application/pdf"
                    )
    # =======================
    # TAB 4: Reportes
    # =======================
    with tabs[3]:
        st.subheader("📊 Reportes de Ventas")
        tipo_reporte = st.selectbox("Selecciona reporte", ["Por cliente", "Por producto", "Diario", "Mensual"])

        if tipo_reporte == "Por cliente":
            df = query_df("""
                SELECT c.nombre AS cliente, SUM(v.total) AS total_ventas
                FROM venta v
                LEFT JOIN cliente c ON v.id_cliente = c.id
                WHERE v.estado = 'EMITIDA'
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
                JOIN venta v ON v.id = d.id_venta
                JOIN producto p ON d.id_producto = p.id
                WHERE v.estado = 'EMITIDA'
                GROUP BY p.descripcion
                ORDER BY total_ventas DESC
            """)
            if not df.empty:
                st.bar_chart(df.set_index("descripcion"))
            else:
                st.warning("⚠️ No hay datos para mostrar en este reporte")

        elif tipo_reporte == "Diario":
            df = query_df("""
                SELECT
                    DATE(fecha) AS dia,
                    COUNT(*) FILTER (WHERE estado='EMITIDA') AS ventas_emitidas,
                    COUNT(*) FILTER (WHERE estado='ANULADA') AS ventas_anuladas,
                    SUM(total) FILTER (WHERE estado='EMITIDA') AS total_vendido
                FROM venta
                GROUP BY dia
                ORDER BY dia
            """)

            if not df.empty:
                st.metric("Ventas emitidas", int(df.iloc[-1]["ventas_emitidas"]))
                st.metric("Ventas anuladas", int(df.iloc[-1]["ventas_anuladas"]))
                st.metric("Total vendido", f"S/. {df.iloc[-1]['total_vendido'] or 0:,.2f}")
                st.line_chart(df.set_index("dia"))
            else:
                st.warning("⚠️ No hay datos")

        elif tipo_reporte == "Mensual":
            df = query_df("""
                SELECT to_char(fecha, 'YYYY-MM') AS mes, SUM(total) AS total_mes
                FROM venta
                WHERE estado = 'EMITIDA'
                GROUP BY mes
                ORDER BY mes
            """)
            if not df.empty:
                st.line_chart(df.set_index("mes"))
            else:
                st.warning("⚠️ No hay datos para mostrar en este reporte")
