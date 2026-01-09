# modulos/caja.py
import streamlit as st
import pandas as pd
from services.venta_service import (
    abrir_caja,
    cerrar_caja,
    obtener_caja_abierta
)

from services.caja_service import obtener_resumen_caja

def caja_app(usuario):
    st.title("💵 Apertura y Cierre de Caja")

    caja_abierta = obtener_caja_abierta()

    if caja_abierta:
        st.success(f"✅ Caja ABIERTA (ID: {caja_abierta['id']})")
        st.subheader("📊 Resumen de Caja")

        resumen = obtener_resumen_caja(caja_abierta["id"])

        df = pd.DataFrame(
            resumen["por_metodo"],
            columns=["Método de pago", "Total"]
        )

        st.dataframe(df, hide_index=True)

        st.metric(
            "💵 Efectivo esperado en caja",
            f"S/. {resumen['efectivo_neto']:,.2f}"
        )

        monto_cierre = st.number_input(
            "💰 Monto de cierre",
            min_value=0.0,
            step=1.0,
            format="%.2f"
        )

        diferencia = monto_cierre - resumen["efectivo_neto"]

        if monto_cierre > 0:
            if diferencia == 0:
                st.success("✅ Caja cuadrada")
            elif diferencia > 0:
                st.warning(f"⚠️ Sobrante: S/. {diferencia:,.2f}")
            else:
                st.error(f"❌ Faltante: S/. {abs(diferencia):,.2f}")

        if st.button("🔒 Cerrar caja", type="primary"):
            cerrar_caja(
                caja_abierta["id"],   # 👈 SOLO el ID
                monto_cierre,
                usuario
            )
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