# configuracion_app.py
import streamlit as st

from db import obtener_configuracion, actualizar_configuracion

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
