import time
from streamlit_cookies_manager import EncryptedCookieManager

SESSION_EXPIRATION = 8 * 3600  # 8 horas

# Configurar cookies
cookies = EncryptedCookieManager(prefix="koreano_", password="clave_super_secreta_123")
TOKENS = {}  # token -> usuario

def iniciar_sesion(user):
    token = user["username"] + "_" + str(time.time())
    TOKENS[token] = {"username": user["username"], "rol": user["rol"], "login_time": time.time()}
    cookies["token"] = token
    cookies.save()
    return token

def obtener_usuario_sesion():
    if not cookies.ready():
        return None
    token = cookies.get("token")
    if not token or token not in TOKENS:
        return None
    user = TOKENS[token]
    # Verificar expiración
    if time.time() - user["login_time"] > SESSION_EXPIRATION:
        cerrar_sesion()
        return None
    return user

def cerrar_sesion():
    token = cookies.get("token")
    if token in TOKENS:
        del TOKENS[token]
    cookies.clear()
