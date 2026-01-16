# proveedores.py
import streamlit as st
import pandas as pd

from db import generar_codigo_correlativo, get_connection

def proveedores_app():
    st.title("📇 Gestión de Proveedores")

    tab1, tab2, tab3 = st.tabs(["➕ Agregar", "✏️ Modificar / Eliminar", "📊 Listado"])

    # ------------------------
    # TAB 1 - AGREGAR
    # ------------------------
    with tab1:
        st.subheader("➕ Registrar nuevo proveedor")

        with st.form("form_proveedor", clear_on_submit=True):
            codigo = st.text_input("Código proveedor", value=generar_codigo_correlativo("proveedor", "PRV"))
            nombre = st.text_input("Nombre / Razón social")
            dni_ruc = st.text_input("DNI / RUC")
            telefono = st.text_input("Teléfono")
            direccion = st.text_input("Dirección")

            if st.form_submit_button("💾 Guardar proveedor"):
                if codigo and nombre and dni_ruc:
                    conn = get_connection()
                    cursor = conn.cursor()

                    cursor.execute(
                        "INSERT INTO proveedor (id, nombre, dni_ruc, telefono, direccion) VALUES (%s, %s, %s, %s, %s)",
                        (codigo, nombre, dni_ruc, telefono, direccion)
                    )
                    conn.commit()
                    conn.close()
                    st.success("✅ Proveedor guardado correctamente")
                    st.rerun()
                else:
                    st.error("⚠️ Debes ingresar al menos el código y el nombre")

    # ------------------------
    # TAB 2 - MODIFICAR / ELIMINAR
    # ------------------------
    with tab2:
        st.subheader("✏️ Buscar y gestionar proveedores")
        
        conn = get_connection()
        df_prov = pd.read_sql_query("SELECT * FROM proveedor ORDER BY nombre", conn)
        conn.close()
        
        if not df_prov.empty:
            # Campo de búsqueda
            busqueda = st.text_input("🔍 Buscar proveedor por nombre o RUC")
            if busqueda:
                df_prov.fillna("", inplace=True)
                df_filtrado = df_prov[df_prov["nombre"].str.contains(busqueda, case=False) |
                                    df_prov["dni_ruc"].str.contains(busqueda, case=False)]
            else:
                df_filtrado = df_prov

            st.dataframe(df_filtrado, width='stretch', hide_index=True)

            # Seleccionar proveedor
            seleccion = st.selectbox("Selecciona un proveedor", df_filtrado["nombre"].tolist())

            if seleccion:
                datos = df_prov[df_prov["nombre"] == seleccion].iloc[0]

                with st.form("editar_proveedor"):
                    nuevo_nombre = st.text_input("Nombre / Razón social", datos["nombre"])
                    nuevo_dni_ruc = st.text_input("DNI / RUC", datos["dni_ruc"])
                    nuevo_telefono = st.text_input("Teléfono", datos["telefono"])
                    nueva_direccion = st.text_input("Dirección", datos["direccion"])

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("💾 Guardar cambios"):
                            conn = get_connection()
                            cursor = conn.cursor()

                            cursor.execute("""
                                UPDATE proveedor
                                SET nombre=%s, dni_ruc=%s, telefono=%s, direccion=%s
                                WHERE id=%s
                            """, (nuevo_nombre, nuevo_dni_ruc, nuevo_telefono, nueva_direccion, datos["id"]))
                            conn.commit()
                            conn.close()
                            st.success("✅ Proveedor actualizado correctamente")
                            st.rerun()

                    with col2:
                        if st.form_submit_button("🗑️ Eliminar proveedor"):
                            conn = get_connection()
                            cursor = conn.cursor()

                            cursor.execute("DELETE FROM proveedor WHERE id=%s", (datos["id"],))
                            conn.commit()
                            conn.close()

                            st.warning("⚠️ Proveedor eliminado")
                            st.rerun()
        else:
            st.info("No hay proveedores registrados.")

    # ------------------------
    # TAB 3 - LISTADO
    # ------------------------
    with tab3:
        st.subheader("📊 Listado completo de proveedores")

        conn = get_connection()
        df_prov = pd.read_sql_query("SELECT * FROM proveedor ORDER BY nombre", conn)
        conn.close()
        if not df_prov.empty:
            st.dataframe(df_prov, width='stretch', hide_index=True)
        else:
            st.info("No hay proveedores en la base de datos.")

    conn.close()


