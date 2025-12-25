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
        SELECT id, username, password_hash, rol, activo
        FROM usuarios
        WHERE username = %s
    """, (username,))

    user = cursor.fetchone()
    conn.close()

    if not user:
        return None

    id_user, username, password_hash, rol, activo = user

    if not activo:
        return None

    if verificar_password(password, password_hash):
        return {
            "id": id_user,
            "username": username,
            "rol": rol
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
