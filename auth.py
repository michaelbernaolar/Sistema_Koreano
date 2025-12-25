import bcrypt
from db import get_connection

# -------------------------
# Password helpers
# -------------------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

def verificar_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8")
    )

# -------------------------
# Login
# -------------------------
def autenticar_usuario(username, password):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, username, password_hash, rol, activo, password_updated_at
        FROM usuarios
        WHERE username = %s
    """, (username,))

    user = cursor.fetchone()
    conn.close()

    if not user:
        return None

    id_user, username, password_hash, rol, activo, pwd_updated = user

    if not activo:
        return None

    if verificar_password(password, password_hash):
        return {
            "id": id_user,
            "username": username,
            "rol": rol,
            "forzar_cambio_password": pwd_updated is None
        }
    
    return None

def obtener_usuario_por_username(username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT username, rol FROM usuarios WHERE username = %s",
        (username,)
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        return {"username": row[0], "rol": row[1]}
    return None

def validar_password(password: str):
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres"
    if password.isnumeric():
        return False, "La contraseña no puede ser solo números"
    return True, ""

def cambiar_password(user_id, password_actual, password_nuevo):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT password_hash FROM usuarios WHERE id = %s",
        (user_id,)
    )
    row = cur.fetchone()

    if not row or not verificar_password(password_actual, row[0]):
        conn.close()
        return False

    nuevo_hash = hash_password(password_nuevo)

    cur.execute("""
        UPDATE usuarios
        SET password_hash=%s,
            password_updated_at=NOW(),
            token_sesion=NULL
        WHERE id=%s
    """, (nuevo_hash, user_id))

    conn.commit()
    conn.close()
    return True

def crear_usuario(username, nombre, rol, password="Temp1234"):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO usuarios (username, nombre, rol, password_hash, activo)
        VALUES (%s, %s, %s, %s, TRUE)
    """, (username, nombre, rol, hash_password(password)))

    conn.commit()
    conn.close()

def cambiar_estado_usuario(user_id, activo):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE usuarios SET activo=%s WHERE id=%s",
        (activo, user_id)
    )
    conn.commit()
    conn.close()

def resetear_password_admin(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE usuarios
        SET password_hash=%s,
            password_updated_at=NULL,
            token_sesion=NULL
        WHERE id=%s
    """, (hash_password("Temp1234"), user_id))

    conn.commit()
    conn.close()

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
