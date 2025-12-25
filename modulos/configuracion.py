# configuracion_app.py
import streamlit as st

from db import obtener_configuracion, actualizar_configuracion
from auth import obtener_todos_los_usuarios, cambiar_estado_usuario

def configuracion_app():
    st.title("⚙️ Configuración del Sistema")

    st.subheader("Tipo de Régimen Tributario")

    # Obtener configuración completa
    config = obtener_configuracion()
    regimen_actual = config.get("regimen", "Nuevo RUS")

    opciones = [
        "Régimen General",
        "Régimen MYPE Tributario",
        "Régimen Especial del Impuesto a la Renta (RER)",
        "Nuevo RUS"
    ]

    # Selectbox con el valor actual
    nuevo_regimen = st.selectbox(
        "Selecciona el régimen tributario:",
        opciones,
        index=opciones.index(regimen_actual) if regimen_actual in opciones else 0
    )

    if st.button("💾 Guardar Cambios"):
        actualizar_configuracion(nuevo_regimen=nuevo_regimen)
        st.success(f"✅ Régimen actualizado a: {nuevo_regimen}")

    st.info(f"**Régimen actual:** {obtener_configuracion()['regimen']}")

    # -------------------------
    # Gestión de usuarios (ADMIN)
    # -------------------------
    st.markdown("---")
    st.subheader("👥 Gestión de usuarios")

    usuarios = obtener_todos_los_usuarios()

    if not usuarios:
        st.info("No hay usuarios registrados")
        return

    for u in usuarios:
        col1, col2, col3 = st.columns([3, 2, 2])

        col1.write(f"👤 {u['username']}")
        col2.write(u["rol"])

        if u["activo"]:
            if col3.button("🚫 Desactivar", key=f"off_{u['id']}"):
                cambiar_estado_usuario(u["id"], False)
                st.rerun()
        else:
            if col3.button("✅ Activar", key=f"on_{u['id']}"):
                cambiar_estado_usuario(u["id"], True)
                st.rerun()