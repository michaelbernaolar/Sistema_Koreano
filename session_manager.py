# session_manager.py
import time
import streamlit as st

SESSION_EXPIRATION = 8 * 3600  # 8 horas

# Iniciar sesión: guarda usuario en session_state
def iniciar_sesion(user):
    st.session_state["usuario"] = {
        "username": user["username"],
        "rol": user["rol"],
        "login_time": time.time()
    }

# Obtener usuario de la sesión activa
def obtener_usuario_sesion():
    usuario = st.session_state.get("usuario")
    if usuario:
        # Verificar expiración
        if time.time() - usuario.get("login_time", 0) > SESSION_EXPIRATION:
            cerrar_sesion()
            return None
    return usuario

# Cerrar sesión: elimina usuario de session_state
def cerrar_sesion():
    if "usuario" in st.session_state:
        del st.session_state["usuario"]
