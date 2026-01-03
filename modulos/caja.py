# modulos/caja.py
import streamlit as st
from services.venta_service import abrir_caja, cerrar_caja, obtener_caja_abierta

def caja_app(usuario):
    st.title("💵 Apertura y Cierre de Caja")

    caja_abierta_id = obtener_caja_abierta()

    if caja_abierta_id:
        st.success(f"✅ Caja ABIERTA (ID: {caja_abierta_id})")

        monto_cierre = st.number_input(
            "💰 Monto de cierre",
            min_value=0.0,
            step=1.0,
            format="%.2f"
        )

        if st.button("🔒 Cerrar caja", type="primary"):
            cerrar_caja(caja_abierta_id, monto_cierre, usuario["username"])
            st.session_state.pop("caja_abierta_id", None)
            st.success("Caja cerrada correctamente")
            st.rerun()

    else:
        st.warning("⚠️ No hay caja abierta")

        monto_apertura = st.number_input(
            "💰 Monto de apertura",
            min_value=0.0,
            step=1.0,
            format="%.2f"
        )

        if st.button("🔓 Abrir caja", type="primary"):
            caja_id = abrir_caja(monto_apertura, usuario)
            st.session_state["caja_abierta_id"] = caja_id
            st.success(f"Caja abierta (ID: {caja_id})")
            st.rerun()
