import streamlit as st
import pandas as pd
import os

import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from db import to_float
from db import get_connection
from db import (
    generar_codigo_correlativo, obtener_categorias,
    agregar_categoria, editar_categoria, eliminar_categoria,
    insertar_producto, mostrar_todos, existe_codigo, actualizar_producto,
    get_connection
)


def productos_app():
    st.title("📦 Gestión de Productos")

    tab_search, tab_add, tab_inv, tab_cat = st.tabs([
        "🔍 Buscar Producto",
        "➕ Agregar Producto",
        "📊 Inventario",
        "📂 Categorías"
    ])
    # ------------------------
    # SUBMENÚ: BUSCAR PRODUCTO
    # ------------------------
    with tab_search:
        st.subheader("🔍 Buscar Producto")
        
        @st.cache_data(ttl=60)
        def obtener_valores_unicos(columna):
            conn = get_connection()
            df = pd.read_sql_query(f"SELECT DISTINCT {columna} FROM producto WHERE {columna} IS NOT NULL", conn)
            conn.close()
            return df[columna].dropna().sort_values().tolist()

        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_marca = st.selectbox("Marca", ["Todos"] + obtener_valores_unicos("marca"))
        with col2:
            categorias_df = obtener_categorias()
            lista_categorias = ["Todos"] + categorias_df["nombre"].tolist()
            filtro_categoria = st.selectbox("Categoría", lista_categorias)
        with col3:
            filtro_stock = st.selectbox(
                "Stock disponible",
                ["Todos", "Con stock", "Sin stock"]
           )

        criterio = st.text_input("Buscar por palabra clave (código, descripción, modelo, etc.)")

        LIMITE_INICIAL = 20
        ver_mas = st.checkbox("📄 Ver más resultados")
        limite = 100 if ver_mas else LIMITE_INICIAL

        def buscar_producto_avanzado(criterio, marca=None, categoria=None, stock=None, limit=20):
            conn = get_connection()
            cursor = conn.cursor()

            query = """
                SELECT p.id, p.descripcion, p.id_categoria, c.nombre as categoria, 
                       p.catalogo, p.marca, p.modelo, p.ubicacion, 
                       p.precio_venta, p.stock_actual, p.imagen, p.activo, p.unidad_base
                FROM producto p 
                LEFT JOIN categoria c ON p.id_categoria = c.id 
                WHERE 1=1
            """
            params = []

            if criterio:
                criterio = f"%{criterio.lower()}%"
                query += """
                    AND (
                        LOWER(p.id) LIKE %s OR
                        LOWER(p.descripcion) LIKE %s OR
                        LOWER(p.catalogo) LIKE %s OR
                        LOWER(p.marca) LIKE %s OR
                        LOWER(p.modelo) LIKE %s
                    )
                """
                params.extend([criterio] * 5)

            if marca and marca != "Todos":
                query += " AND p.marca = %s"
                params.append(marca)

            if categoria and categoria != "Todos":
                query += " AND c.nombre = %s"
                params.append(categoria)

            if stock == "Con stock":
                query += " AND p.stock_actual > 0"
            elif stock == "Sin stock":
                query += " AND p.stock_actual = 0"
                
            query += " ORDER BY p.id LIMIT %s"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            df = pd.DataFrame(rows, columns=[col[0] for col in cursor.description])
            conn.close()
            return df

        def contar_productos(criterio, marca=None, categoria=None, stock=None):
            conn = get_connection()
            cursor = conn.cursor()

            query = """
                SELECT COUNT(*)
                FROM producto p
                LEFT JOIN categoria c ON p.id_categoria = c.id
                WHERE 1=1
            """
            params = []

            if criterio:
                criterio = f"%{criterio.lower()}%"
                query += """
                    AND (
                        LOWER(p.id) LIKE %s OR
                        LOWER(p.descripcion) LIKE %s OR
                        LOWER(p.catalogo) LIKE %s OR
                        LOWER(p.marca) LIKE %s OR
                        LOWER(p.modelo) LIKE %s
                    )
                """
                params.extend([criterio] * 5)

            if marca and marca != "Todos":
                query += " AND p.marca = %s"
                params.append(marca)

            if categoria and categoria != "Todos":
                query += " AND c.nombre = %s"
                params.append(categoria)

            if stock == "Con stock":
                query += " AND p.stock_actual > 0"
            elif stock == "Sin stock":
                query += " AND p.stock_actual = 0"

            cursor.execute(query, params)
            total = cursor.fetchone()[0]
            conn.close()
            return total

        hay_filtros = any([
            bool(criterio),
            filtro_marca != "Todos",
            filtro_categoria != "Todos",
            filtro_stock != "Todos"
        ])

        df = pd.DataFrame()
        total = 0

        if hay_filtros:
            total = contar_productos(
                criterio,
                filtro_marca,
                filtro_categoria,
                filtro_stock
            )
            
            LIMITE_INICIAL = 20
            ver_mas = st.checkbox(f"📄 Ver todos los resultados ({total})")
            limite = total if ver_mas else LIMITE_INICIAL

            df = buscar_producto_avanzado(
                criterio,
                filtro_marca,
                filtro_categoria,
                filtro_stock,
                limit=limite
            )

        hay_filtros = any([
            bool(criterio),
            filtro_marca != "Todos",
            filtro_categoria != "Todos",
            filtro_stock != "Todos"
        ])

        if total > 0:
            if total > len(df):
                st.info(f"🔎 Resultados encontrados: {total} | Mostrando {len(df)}")
            else:
                st.info(f"🔎 Resultados encontrados: {total}")

        if not df.empty:
            st.markdown("### 🧾 Resultados")
            df_filtrado = df[["id", "descripcion", "marca", "modelo", "catalogo", "categoria", "stock_actual"]].copy()
            df_filtrado.set_index("id", inplace=True)
            st.dataframe(df_filtrado, width='stretch')
            
            st.markdown("### ✏️ Editar producto")

            producto_seleccionado = st.selectbox(
                "Selecciona un producto para editar",
                df["id"].tolist()
            )

            row = df[df["id"] == producto_seleccionado].iloc[0]

            categorias_df = obtener_categorias()
            opciones_cat = categorias_df["nombre"].tolist()

            cat_actual = row["categoria"] if row["categoria"] in opciones_cat else opciones_cat[0]

            with st.form("editar_producto"):
                descripcion = st.text_input("Descripción", row["descripcion"])
                catalogo = st.text_input("Catálogo", row["catalogo"])
                categoria_seleccionada = st.selectbox(
                    "Categoría",
                    opciones_cat,
                    index=opciones_cat.index(cat_actual)
                )
                marca = st.text_input("Marca", row["marca"])
                modelo = st.text_input("Modelo", row["modelo"])
                ubicacion = st.text_input("Ubicación", row["ubicacion"])


                precio_venta = st.number_input(
                    "Precio de venta",
                    value=to_float(row["precio_venta"]),
                    step=0.1
                )

                activo = st.selectbox(
                    "Estado",
                    ["Activo", "Inactivo"],
                    index=0 if row["activo"] == 1 else 1
                )

                guardar = st.form_submit_button("💾 Guardar cambios")


            if guardar:
                id_categoria = int(
                    categorias_df[categorias_df["nombre"] == categoria_seleccionada]["id"].iloc[0]
                )

                estado_activo = 1 if activo == "Activo" else 0

                data = (
                    descripcion,
                    id_categoria,
                    catalogo,
                    marca,
                    modelo,
                    ubicacion,
                    row["unidad_base"],
                    row["stock_actual"],
                    precio_venta,
                    row["imagen"],
                    estado_activo,
                    row["id"]
                )

                actualizar_producto(data)
                st.success("✅ Producto actualizado correctamente")
                st.rerun()

            st.markdown("### 🖼️ Imagen del producto")

            if row["imagen"] and os.path.exists(row["imagen"]):
                st.image(row["imagen"], width=200)

            imagen_nueva = st.file_uploader(
                "Actualizar imagen (opcional)",
                type=["jpg", "png", "jpeg"]
            )

            if imagen_nueva:
                os.makedirs("imagenes", exist_ok=True)
                img_ext = os.path.splitext(imagen_nueva.name)[1]
                img_path = os.path.join("imagenes", f"{row['id']}{img_ext}")

                with open(img_path, "wb") as f:
                    f.write(imagen_nueva.read())

                actualizar_producto((
                    descripcion,
                    id_categoria,
                    catalogo,
                    marca,
                    modelo,
                    ubicacion,
                    row["unidad_base"],
                    row["stock_actual"],
                    precio_venta,
                    img_path,
                    estado_activo,
                    row["id"]
                ))
                st.success("✅ Imagen actualizada correctamente")
                st.rerun()


            # for _, row in df.iterrows():
            #     with st.expander(f"📦 {row['id']} | {row['descripcion']}"):
            #         cols = st.columns([1, 2])
            #         with cols[0]:
            #             if row["imagen"] and os.path.exists(row["imagen"]):
            #                 st.image(row["imagen"], width=200, caption="Imagen del producto")
            #             stock_nivel = row["stock_actual"]
            #             if stock_nivel < 5:
            #                 st.markdown(f"🛑 **Stock crítico:** {stock_nivel} unidades")
            #             elif stock_nivel < 20:
            #                 st.markdown(f"⚠️ **Stock bajo:** {stock_nivel} unidades")
            #             else:
            #                 st.markdown(f"✅ **Stock suficiente:** {stock_nivel} unidades")
            #         with cols[1]:
            #             with st.form(f"editar_{row['id']}"):
            #                 descripcion = st.text_input("Descripción", row["descripcion"])

            #                 categorias_df = obtener_categorias()
            #                 opciones_cat = categorias_df["nombre"].tolist()
            #                 cat_actual = row["categoria"] if row["categoria"] else "(Sin categoría)"

            #                 categoria_seleccionada = st.selectbox(
            #                     "Categoría",
            #                     opciones_cat if opciones_cat else ["(Sin categorías)"],
            #                     index=opciones_cat.index(cat_actual) if cat_actual in opciones_cat else 0
            #                 )

            #                 id_categoria = int(categorias_df[categorias_df["nombre"] == categoria_seleccionada]["id"].iloc[0]) \
            #                     if not categorias_df.empty else None

            #                 catalogo = st.text_input("Catálogo", row["catalogo"])
            #                 marca = st.text_input("Marca", row["marca"])
            #                 modelo = st.text_input("Modelo", row["modelo"])
            #                 ubicacion = st.text_input("Ubicación", row["ubicacion"])
            #                 precio_venta = st.number_input("Precio de Venta", value=to_float(row["precio_venta"]), step=0.1)
            #                 imagen_nueva = st.file_uploader("Actualizar imagen (opcional)", type=["jpg", "png", "jpeg"])
            #                 activo = st.selectbox("Activo", [1, 0], index=0 if row["activo"] == 1 else 1)

            #                 actualizar = st.form_submit_button("Actualizar")
            #                 if actualizar:
            #                     if imagen_nueva:
            #                         os.makedirs("imagenes", exist_ok=True)
            #                         img_ext = os.path.splitext(imagen_nueva.name)[1]
            #                         img_path = os.path.join("imagenes", f"{row['id']}{img_ext}")
            #                         with open(img_path, "wb") as f:
            #                             f.write(imagen_nueva.read())
            #                         ruta_imagen = img_path

            #                         # 🔄 Forzamos recarga inmediata para que se vea la nueva imagen
            #                         data = (
            #                             descripcion, id_categoria, catalogo, marca, modelo, ubicacion,
            #                             row["unidad_base"], row["stock_actual"], precio_venta, ruta_imagen, int(activo), row["id"]
            #                         )
            #                         actualizar_producto(data)
            #                         st.success("✅ Imagen y datos actualizados correctamente.")
            #                         st.rerun()
            #                     else:
            #                         ruta_imagen = row["imagen"]
            #                         data = (
            #                             descripcion, id_categoria, catalogo, marca, modelo, ubicacion,
            #                             row["unidad_base"], row["stock_actual"], precio_venta, ruta_imagen, int(activo), row["id"]
            #                         )
            #                         actualizar_producto(data)
            #                         st.success("✅ Producto actualizado correctamente.")
            #                         st.rerun()
        elif hay_filtros:
            st.warning("🔎 No se encontraron productos con esos filtros.")
        else:
            st.info("👆 Usa los filtros o escribe un criterio para buscar productos.")

    # ------------------------
    # SUBMENÚ: AGREGAR PRODUCTO
    # ------------------------
    with tab_add:
        st.subheader("➕ Agregar Producto")

        with st.form("form_producto"):
            st.markdown("###  Datos importantes del producto")

            tab_info, tab_precios_existencias = st.tabs(["📋 Identificación", "💰 Precios y 📊 Stock"])

            with tab_info:
                col1, col2 = st.columns([2, 1])
                with col1:
                    id = generar_codigo_correlativo("producto", "P")
                    st.text_input("Código (autogenerado)", value=id, disabled=True)
                    descripcion = st.text_input("Descripción", max_chars=100)

                    categorias_df = obtener_categorias()
                    lista_categorias = categorias_df["nombre"].tolist()
                    categoria = st.selectbox("Categoría", lista_categorias if lista_categorias else ["(Sin categorías)"])
                    unidad_base = st.selectbox("Unidad de medida", ["unidad", "caja", "litro", "kg"])

                with col2:
                    catalogo = st.text_input("Catálogo")
                    marca = st.text_input("Marca")
                    modelo = st.text_input("Modelo")
                    ubicacion = st.text_input("Ubicación")

            with tab_precios_existencias:
                st.markdown("### Precios y disponibilidad")
                col3, col4 = st.columns(2)
                with col3:
                    precio_venta = st.number_input("Precio de Venta (S/.)", min_value=0.0, step=0.1, format="%.2f")
                with col4:
                    stock_actual = st.number_input("Stock inicial", min_value=0, step=1)
                    st.metric("Stock inicial estimado", f"{stock_actual} unidades")

            st.markdown("---")
            st.markdown("### Imagen (opcional)")
            imagen = st.file_uploader("Subir imagen del producto", type=["jpg", "png", "jpeg"])

            submitted = st.form_submit_button("💾 Guardar producto")
            if submitted:
                registro_existente = existe_codigo(id)
                if registro_existente:
                    st.warning(f"Ya existe un producto con el código **{id}**.")
                    st.stop()

                if imagen:
                    os.makedirs("imagenes", exist_ok=True)
                    img_ext = os.path.splitext(imagen.name)[1]
                    img_path = os.path.join("imagenes", f"{id}{img_ext}")
                    with open(img_path, "wb") as f:
                        f.write(imagen.read())
                    ruta_imagen = img_path
                else:
                    ruta_imagen = ""

                id_categoria = (
                    int(categorias_df[categorias_df["nombre"] == categoria]["id"].iloc[0])
                    if not categorias_df.empty else None
                )

                data = (
                    id, descripcion, id_categoria, catalogo,
                    marca, modelo, ubicacion,
                    unidad_base, stock_actual, precio_venta,
                    ruta_imagen, 1
                )
                insertar_producto(data)
                st.success("Producto guardado correctamente.")
                st.rerun()
    # ------------------------
    # SUBMENÚ: INVENTARIO
    # ------------------------
    with tab_inv:
        st.subheader("📊 Inventario")

        if st.button("📊 Cargar inventario"):
            df = mostrar_todos()
            if not df.empty:
                df = df.copy()
                df.set_index("id", inplace=True)
                st.dataframe(df, width='stretch')
            else:
                st.info("No hay producto en el inventario.")

    # ------------------------
    # SUBMENÚ: CATEGORÍAS
    # ------------------------
    with tab_cat:
        st.subheader("📂 Gestión de Categorías")

        tab1, tab2 = st.tabs(["➕ Agregar", "✏️ Modificar / Eliminar"])

        with tab1:
            st.markdown("### ➕ Agregar nueva categoría")
            nueva = st.text_input("Nombre de la categoría", key="nueva_cat")
            if st.button("Agregar categoría", key="btn_agregar_cat"):
                if nueva.strip():
                    agregar_categoria(nueva.strip())
                    st.success("✅ Categoría agregada correctamente")
                    st.rerun()
                else:
                    st.warning("⚠️ Ingresa un nombre válido")

        with tab2:
            st.markdown("### ✏️ Buscar y gestionar categorías")
            categorias_df = obtener_categorias()

            busqueda = st.text_input("🔍 Buscar categoría", key="buscar_cat")
            if busqueda:
                categorias_filtradas = categorias_df[categorias_df["nombre"].str.contains(busqueda, case=False)]
            else:
                categorias_filtradas = categorias_df

            st.dataframe(categorias_filtradas[["id", "nombre"]], width='stretch', hide_index=True)

            if not categorias_filtradas.empty:
                seleccion = st.selectbox(
                    "Selecciona una categoría",
                    categorias_filtradas["nombre"].tolist(),
                    key="select_cat"
                )

                nuevo_nombre = st.text_input("✏️ Nuevo nombre", value=seleccion, key="nuevo_nombre_cat")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 Guardar cambios", key="btn_guardar_cat"):
                        id_cat = int(categorias_df[categorias_df["nombre"] == seleccion]["id"].iloc[0])
                        editar_categoria(id_cat, nuevo_nombre.strip())
                        st.success("✅ Categoría actualizada")
                        st.rerun()

                with col2:
                    if st.button("🗑️ Eliminar categoría", key="btn_eliminar_cat"):
                        id_cat = int(categorias_df[categorias_df["nombre"] == seleccion]["id"].iloc[0])
                        eliminar_categoria(id_cat)
                        st.warning("⚠️ Categoría eliminada")
                        st.rerun()
    