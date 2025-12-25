import streamlit as st
from auth import cambiar_password, validar_password
from session_manager import cerrar_sesion

def mi_cuenta_app(usuario, cookies):
    st.subheader("👤 Mi cuenta")

    st.markdown("### 🔐 Cambiar contraseña")

    pwd_actual = st.text_input("Contraseña actual", type="password")
    pwd_nueva = st.text_input("Nueva contraseña", type="password")
    pwd_confirmar = st.text_input("Confirmar nueva contraseña", type="password")

    if st.button("Actualizar contraseña"):
        if pwd_nueva != pwd_confirmar:
            st.error("Las contraseñas no coinciden")
            return

        ok, msg = validar_password(pwd_nueva)
        if not ok:
            st.error(msg)
            return

        if cambiar_password(usuario["id"], pwd_actual, pwd_nueva):
            st.success("Contraseña actualizada. Inicia sesión nuevamente.")
            cerrar_sesion(usuario["id"], cookies)
            st.rerun()
        else:
            st.error("Contraseña actual incorrecta")
