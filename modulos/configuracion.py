# configuracion_app.py
import streamlit as st

from db import obtener_configuracion, actualizar_configuracion
from auth import (
    obtener_todos_los_usuarios,
    cambiar_estado_usuario,
    crear_usuario,
    resetear_password_admin
)

def configuracion_app():
    st.title("⚙️ Configuración del Sistema")

    st.subheader("Tipo de Régimen Tributario")

    # Obtener configuración completa
    config = obtener_configuracion()
    regimen_actual = config.get("regimen", "Nuevo RUS")

    opciones = [
        "Régimen General",
        "Régimen MYPE Tributario",
        "Régimen Especial del Impuesto a la Renta (RER)",
        "Nuevo RUS"
    ]

    # Selectbox con el valor actual
    nuevo_regimen = st.selectbox(
        "Selecciona el régimen tributario:",
        opciones,
        index=opciones.index(regimen_actual) if regimen_actual in opciones else 0
    )

    if st.button("💾 Guardar Cambios"):
        actualizar_configuracion(nuevo_regimen=nuevo_regimen)
        st.success(f"✅ Régimen actualizado a: {nuevo_regimen}")

    st.info(f"**Régimen actual:** {obtener_configuracion()['regimen']}")

    # -------------------------
    # Gestión de usuarios (ADMIN)
    # -------------------------
    st.markdown("---")
    st.subheader("👥 Gestión de usuarios")

    st.markdown("### ➕ Crear nuevo usuario")

    with st.form("crear_usuario_form"):
        username = st.text_input("Usuario")
        nombre = st.text_input("Nombre")
        rol = st.selectbox("Rol", ["admin", "usuario"])
        submitted = st.form_submit_button("Crear usuario")

        if submitted:
            if not username or not nombre:
                st.error("Usuario y nombre son obligatorios")
            else:
                crear_usuario(username, nombre, rol)
                st.success("Usuario creado. Contraseña temporal: Temp1234")
                st.rerun()

    usuarios = obtener_todos_los_usuarios()
    usuario_actual = st.session_state.get("usuario")

    if not usuarios:
        st.info("No hay usuarios registrados")
        return

    for u in usuarios:
        col1, col2, col3, col4 = st.columns([3, 2, 2, 2])

        col1.write(f"👤 {u['username']}")
        col2.write(u["rol"])

        if usuario_actual and usuario_actual["id"] == u["id"]:
            col3.write("—")  # No permitir auto-desactivarse
        else:
            if u["activo"]:
                if col3.button("🚫 Desactivar", key=f"off_{u['id']}"):
                    cambiar_estado_usuario(u["id"], False)
                    st.rerun()
            else:
                if col3.button("✅ Activar", key=f"on_{u['id']}"):
                    cambiar_estado_usuario(u["id"], True)
                    st.rerun()

        if col4.button("🔑 Reset Password", key=f"reset_{u['id']}"):
            st.session_state["confirm_reset"] = u

    if "confirm_reset" in st.session_state:
        u = st.session_state["confirm_reset"]
        st.warning(f"¿Confirmar reset de contraseña para {u['username']}?")

        col_a, col_b = st.columns(2)

        if col_a.button("Sí, resetear"):
            resetear_password_admin(u["id"])
            del st.session_state["confirm_reset"]
            st.success("Contraseña reseteada. Temporal: Temp1234")
            st.rerun()

        if col_b.button("Cancelar"):
            del st.session_state["confirm_reset"]