import streamlit as st
import os
import time
from db import init_db
from auth import autenticar_usuario, obtener_usuario_por_username
from session_manager import iniciar_sesion, obtener_usuario_sesion, cerrar_sesion
from streamlit_cookies_manager import CookieManager

# Configuración de la página
st.set_page_config(page_title="Sistema de Gestión", layout="wide")

cookies = CookieManager(prefix="koreano_")
if not cookies.ready():
    st.stop()

# Verificar sesión
usuario = obtener_usuario_sesion(cookies)
if not usuario:
    st.title("🔐 Acceso al sistema")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        user = autenticar_usuario(username, password)
        if user:
            iniciar_sesion(user, cookies)
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")

    st.stop()


# Importar módulos
from modulos.proveedores import proveedores_app
from modulos.productos import productos_app
from modulos.clientes import clientes_app
from modulos.compras import compras_app
from modulos.ventas import ventas_app
from modulos.configuracion import configuracion_app
from modulos.precios import precios_app

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# Inicializar BD
if "db_initialized" not in st.session_state:
    init_db()
    st.session_state.db_initialized = True


if st.sidebar.button("Cerrar sesión"):
    cerrar_sesion(usuario["id"], cookies)
    st.rerun()

st.sidebar.markdown("---")

# -------------------------
# Sidebar con LOGO y BOTONES
# -------------------------
logo_path = os.path.join(BASE_DIR, "imagenes", "logo.png")
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, width='stretch')

if usuario:
    st.sidebar.write(f"👤 Usuario: {usuario['username']}")
    st.sidebar.write(f"🔑 Rol: {usuario['rol']}")

# Estado del módulo actual
if "modulo" not in st.session_state:
    st.session_state.modulo = "🏠 Inicio"

if st.session_state.modulo == "⚙️ Configuración" and usuario["rol"] != "admin":
    st.warning("No tienes permisos para acceder a este módulo")
    st.stop()

# Módulos disponibles
modulos = [
    "🏠 Inicio",
    "📦 Productos",
    "📇 Proveedores",
    "📦 Compras",
    "👥 Clientes",
    "💳 Punto de Venta",
    "⚙️ Configuración",
    "Cálculo de precios"
]

if usuario["rol"] != "admin":
    modulos.remove("⚙️ Configuración")

# Crear los botones de navegación en el sidebar
for modulo in modulos:
    if st.sidebar.button(modulo, key=modulo, help=f"Ir a {modulo}", width='stretch'):
        st.session_state.modulo = modulo
        st.rerun()

st.sidebar.markdown("---")

# -------------------------
# Dashboard principal (Inicio)
# -------------------------
if st.session_state.modulo == "🏠 Inicio":
    st.markdown("<h2 style='margin-bottom:0.5rem;'>📊 Sistema de Gestión</h2>", unsafe_allow_html=True)
    st.subheader("📌 Selecciona un módulo")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📦 Productos", width='stretch'):
            st.session_state.modulo = "📦 Productos"
            st.rerun()
        if st.button("👥 Clientes", width='stretch'):
            st.session_state.modulo = "👥 Clientes"
            st.rerun()
        if st.button("Cálculo de precios", width='stretch'):
            st.session_state.modulo = "Cálculo de precios"
            st.rerun()

    with col2:
        if st.button("📇 Proveedores", width='stretch'):
            st.session_state.modulo = "📇 Proveedores"
            st.rerun()
        if st.button("💳 Punto de Venta", width='stretch'):
            st.session_state.modulo = "💳 Punto de Venta"
            st.rerun()

    with col3:
        if st.button("📦 Compras", width='stretch'):
            st.session_state.modulo = "📦 Compras"
            st.rerun()
        if usuario["rol"] == "admin":
            if st.button("⚙️ Configuración", width='stretch'):
                st.session_state.modulo = "⚙️ Configuración"
                st.rerun()

# -------------------------
# Módulos
# -------------------------
elif st.session_state.modulo == "📦 Productos":
    productos_app()
elif st.session_state.modulo == "📇 Proveedores":
    proveedores_app()
elif st.session_state.modulo == "📦 Compras":
    compras_app()
elif st.session_state.modulo == "👥 Clientes":
    clientes_app()
elif st.session_state.modulo == "💳 Punto de Venta":
    ventas_app()
elif st.session_state.modulo == "⚙️ Configuración":
    configuracion_app()
elif st.session_state.modulo == "Cálculo de precios":
    precios_app()

# -------------------------
# Pie de página
# -------------------------
def mostrar_pie_pagina():
    st.markdown("---")
    st.caption("📌 Sistema de ventas Koreano v1.0 - Todos los derechos reservados")

mostrar_pie_pagina()
