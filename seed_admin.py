from auth import hash_password
from db import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
INSERT INTO usuarios (username, password_hash, nombre, rol)
VALUES (%s, %s, %s, %s)
ON CONFLICT (username) DO NOTHING
""", (
    "admin",
    hash_password("admin123"),
    "Administrador",
    "admin"
))

conn.commit()
conn.close()

print("Usuario admin creado (si no existía)")
