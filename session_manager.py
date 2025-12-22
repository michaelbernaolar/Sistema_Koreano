import time
import secrets
from streamlit_cookies_manager import EncryptedCookieManager

# Configuración de cookies
cookies = EncryptedCookieManager(
    prefix="koreano_",
    password="clave_super_secreta_123"
)

SESSION_EXPIRATION = 8 * 3600  # 8 horas
TOKENS = {}  # Diccionario temporal token → usuario

# Iniciar sesión: genera un token y lo guarda en cookies
def iniciar_sesion(user):
    token = secrets.token_hex(16)
    TOKENS[token] = {
        "username": user["username"],
        "rol": user["rol"],
        "time": time.time()
    }
    cookies["token"] = token
    cookies.save()
    return token

# Obtener usuario de la sesión activa
def obtener_usuario_sesion():
    if not cookies.ready():
        return None
    token = cookies.get("token")
    if not token or token not in TOKENS:
        return None
    session = TOKENS[token]
    # Verificar expiración
    if time.time() - session["time"] > SESSION_EXPIRATION:
        cerrar_sesion()
        return None
    return {"username": session["username"], "rol": session["rol"]}

# Cerrar sesión: eliminar token y limpiar cookies
def cerrar_sesion():
    token = cookies.get("token")
    if token in TOKENS:
        del TOKENS[token]
    cookies.clear()
