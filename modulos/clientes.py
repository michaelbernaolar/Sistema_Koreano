# clientes.py
import streamlit as st
import pandas as pd

from db import get_connection, generar_codigo_correlativo



def clientes_app():
    st.title("👥 Gestión de Clientes")

    # Conexión a la BD
    conn = get_connection()
    cursor = conn.cursor()


    tab1, tab2, tab3 = st.tabs(["➕ Agregar", "✏️ Modificar / Eliminar", "📊 Listado"])

    # ------------------------
    # TAB 1 - AGREGAR
    # ------------------------
    with tab1:
        st.subheader("➕ Registrar nuevo cliente")
        
        with st.form("form_cliente", clear_on_submit=True):
            id = generar_codigo_correlativo("cliente", "CLI")
            st.text_input("Código (autogenerado)", value=id, disabled=True)
            nombre = st.text_input("Nombre / Razón social")
            dni_ruc = st.text_input("DNI / RUC")
            telefono = st.text_input("Teléfono")
            direccion = st.text_input("Dirección")

            if st.form_submit_button("💾 Guardar cliente"):
                if id and nombre and dni_ruc:
                    cursor.execute("""
                        INSERT INTO cliente (id, nombre, dni_ruc, telefono, direccion)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (id, nombre, dni_ruc, telefono, direccion))
                    conn.commit()
                    st.success("✅ Cliente guardado correctamente")
                    st.rerun()
                else:
                    st.error("⚠️ Debes ingresar al menos el código y el nombre")

    # ------------------------
    # TAB 2 - MODIFICAR / ELIMINAR
    # ------------------------
    with tab2:
        st.subheader("✏️ Buscar y gestionar clientes")

        df_cli = pd.read_sql_query("SELECT * FROM cliente ORDER BY nombre", conn)

        if not df_cli.empty:
            busqueda = st.text_input("🔍 Buscar cliente por nombre o DNI/RUC")
            if busqueda:
                df_filtrado = df_cli[df_cli["nombre"].str.contains(busqueda, case=False) |
                                     df_cli["dni_ruc"].str.contains(busqueda, case=False)]
            else:
                df_filtrado = df_cli

            st.dataframe(df_filtrado, width='stretch', hide_index=True)

            if not df_filtrado.empty:
                seleccion = st.selectbox("Selecciona un cliente", df_filtrado["nombre"].tolist())

                if seleccion:
                    datos = df_cli[df_cli["nombre"] == seleccion].iloc[0]

                    with st.form("editar_cliente"):
                        nuevo_nombre = st.text_input("Nombre / Razón social", datos["nombre"])
                        nuevo_dni_ruc = st.text_input("DNI / RUC", datos["dni_ruc"])
                        nuevo_telefono = st.text_input("Teléfono", datos["telefono"])
                        nueva_direccion = st.text_input("Dirección", datos["direccion"])

                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("💾 Guardar cambios"):
                                cursor.execute("""
                                    UPDATE cliente
                                    SET nombre=%s, dni_ruc=%s, telefono=%s, direccion=%s
                                    WHERE id=%s
                                """, (nuevo_nombre, nuevo_dni_ruc, nuevo_telefono, nueva_direccion, datos["id"]))
                                conn.commit()
                                st.success("✅ Cliente actualizado correctamente")
                                st.rerun()

                        with col2:
                            if st.form_submit_button("🗑️ Eliminar cliente"):
                                cursor.execute("DELETE FROM cliente WHERE id=%s", (datos["id"],))
                                conn.commit()
                                st.warning("⚠️ Cliente eliminado")
                                st.rerun()

        else:
            st.info("No hay clientes registrados.")

    # ------------------------
    # TAB 3 - LISTADO
    # ------------------------
    with tab3:
        st.subheader("📊 Listado completo de clientes")

        df_cli = pd.read_sql_query("SELECT * FROM cliente ORDER BY nombre", conn)
        if not df_cli.empty:
            st.dataframe(df_cli, width='stretch', hide_index=True)
        else:
            st.info("No hay clientes en la base de datos.")

    conn.close()
