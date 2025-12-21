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
