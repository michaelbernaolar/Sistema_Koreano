import time
import uuid
import streamlit as st
from db import get_connection

SESSION_EXPIRATION = 8 * 3600  # 8 horas

def iniciar_sesion(user, cookies):
    token = str(uuid.uuid4())
    login_time = time.time()

    conn = get_connection()
    cur = conn.cursor()

    # Cerrar cualquier sesión previa del usuario
    cur.execute(
        "UPDATE usuarios SET token_sesion=NULL WHERE id=%s",
        (user["id"],)
    )

     # Crear nueva sesión
    cur.execute("""
        UPDATE usuarios
        SET token_sesion=%s,
            login_time=%s,
            last_login=NOW()
        WHERE id=%s
    """, (token, login_time, user["id"]))
    conn.commit()
    conn.close()

    cookies["token"] = token
    cookies.save()

    st.session_state["usuario"] = {
        "id": user["id"],
        "username": user["username"],
        "rol": user["rol"]
    }


def obtener_usuario_sesion(cookies):
    if "usuario" in st.session_state:
        return st.session_state["usuario"]

    token = cookies.get("token")
    if not token:
        return None

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, username, rol, login_time, password_updated_at
        FROM usuarios
        WHERE token_sesion = %s
    """, (token,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    id_user, username, rol, login_time, pwd_updated = row

    if time.time() - login_time > SESSION_EXPIRATION:
        cerrar_sesion(id_user, cookies)
        return None
    
    if pwd_updated and login_time < pwd_updated.timestamp():
        cerrar_sesion(id_user, cookies)
        return None
    
    st.session_state["usuario"] = {
        "id": id_user,
        "username": username,
        "rol": rol
    }

    return st.session_state["usuario"]


def cerrar_sesion(id_user, cookies):
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

def obtener_todos_los_usuarios():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, username, rol, activo
        FROM usuarios
        ORDER BY username
    """)
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "username": r[1],
            "rol": r[2],
            "activo": r[3]
        }
        for r in rows
    ]
