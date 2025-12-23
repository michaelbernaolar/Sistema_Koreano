import time
import uuid
import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager
from db import get_connection

SESSION_EXPIRATION = 8 * 3600  # 8 horas

cookies = EncryptedCookieManager(
    prefix="koreano_",
    password="clave_segura_cambia_esto"
)

if not cookies.ready():
    st.stop()

def iniciar_sesion(user):
    token = str(uuid.uuid4())
    login_time = time.time()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE usuarios SET token_sesion=%s, login_time=%s WHERE id=%s",
        (token, login_time, user["id"])
    )
    conn.commit()
    conn.close()

    cookies["token"] = token
    cookies.save()

    st.session_state["usuario"] = {
        "id": user["id"],
        "username": user["username"],
        "rol": user["rol"]
    }

def obtener_usuario_sesion():
    # 1. Cache rápido
    if "usuario" in st.session_state:
        return st.session_state["usuario"]

    # 2. Cookie
    token = cookies.get("token")
    if not token:
        return None

    # 3. Validar en DB
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, username, rol, login_time
        FROM usuarios
        WHERE token_sesion = %s
    """, (token,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    id_user, username, rol, login_time = row

    if time.time() - login_time > SESSION_EXPIRATION:
        cerrar_sesion(id_user)
        return None

    # 4. Cachear
    st.session_state["usuario"] = {
        "id": id_user,
        "username": username,
        "rol": rol
    }

    return st.session_state["usuario"]


def cerrar_sesion(id_user=None):
    if id_user:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE usuarios SET token_sesion = NULL WHERE id = %s",
            (id_user,)
        )
        conn.commit()
        conn.close()

    cookies["token"] = ""
    cookies.save()
    st.session_state.clear()
