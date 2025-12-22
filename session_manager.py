import time
import streamlit as st
import uuid
from db import get_connection

SESSION_EXPIRATION = 8 * 3600  # 8 horas

# Iniciar sesión
def iniciar_sesion(user):
    token = str(uuid.uuid4())
    login_time = time.time()
    
    # Guardar en session_state
    st.session_state["usuario"] = {
        "id": user["id"],
        "username": user["username"],
        "rol": user["rol"],
        "token": token,
        "login_time": login_time
    }
    
    # Guardar token y login_time en la DB
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE usuarios SET token_sesion=%s, login_time=%s WHERE id=%s",
        (token, login_time, user["id"])
    )
    conn.commit()
    conn.close()
    
    # Guardar token en URL para compartir enlaces si quieres
    st.query_params = {"token": token}

# Obtener usuario por token
def obtener_usuario_sesion():
    # Primero revisa session_state
    if "usuario" in st.session_state:
        usuario = st.session_state["usuario"]
        # Verificar expiración
        if time.time() - usuario["login_time"] <= SESSION_EXPIRATION:
            return usuario
        else:
            cerrar_sesion(usuario["id"])
            return None

    # Si no hay session_state, revisar token en URL
    token = st.query_params.get("token", [None])[0]
    if not token:
        return None

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, rol, login_time FROM usuarios WHERE token_sesion=%s",
        (token,)
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None

    id_user, username, rol, login_time = row
    if time.time() - login_time > SESSION_EXPIRATION:
        cerrar_sesion(id_user)
        return None

    # actualizar login_time para prolongar sesión
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET login_time=%s WHERE id=%s", (time.time(), id_user))
    conn.commit()
    conn.close()

    # Guardar también en session_state
    st.session_state["usuario"] = {
        "id": id_user,
        "username": username,
        "rol": rol,
        "token": token,
        "login_time": time.time()
    }

    return st.session_state["usuario"]

# Cerrar sesión
def cerrar_sesion(id_user=None):
    if id_user:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET token_sesion=NULL WHERE id=%s", (id_user,))
        conn.commit()
        conn.close()

    if "usuario" in st.session_state:
        del st.session_state["usuario"]

    st.query_params = {}

