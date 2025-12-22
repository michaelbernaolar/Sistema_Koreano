import time
import streamlit as st

SESSION_EXPIRATION = 8 * 3600  # 8 horas

def iniciar_sesion(user):
    st.session_state["usuario"] = {
        "username": user["username"],
        "rol": user["rol"],
        "login_time": time.time()
    }

def obtener_usuario_sesion():
    usuario = st.session_state.get("usuario")
    if usuario:
        if time.time() - usuario.get("login_time", 0) > SESSION_EXPIRATION:
            cerrar_sesion()
            return None
        else:
            # actualizar tiempo de sesión
            usuario["login_time"] = time.time()
            st.session_state["usuario"] = usuario
            return usuario
    return None

def cerrar_sesion():
    if "usuario" in st.session_state:
        del st.session_state["usuario"]

