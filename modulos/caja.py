# modulos/caja.py
import streamlit as st
import pandas as pd
from decimal import Decimal
from services.venta_service import (
    abrir_caja, cerrar_caja,
    obtener_caja_abierta
)

from services.caja_service import (
    obtener_resumen_caja, obtener_historial_cajas
)


def caja_app(usuario):
    st.title("💵 Gestión de Caja")

    tab_actual, tab_historial = st.tabs([
        "📦 Caja actual",
        "📚 Historial de cajas"
    ])

    # =========================
    # TAB 1 – CAJA ACTUAL
    # =========================
    with tab_actual:
        caja_abierta = obtener_caja_abierta()

        if caja_abierta:
            st.success(f"✅ Caja ABIERTA (ID: {caja_abierta['id']})")
            st.metric(
                "🔓 Monto de apertura",
                f"S/. {caja_abierta['monto_apertura']:,.2f}"
            )
            st.subheader("📊 Resumen de Caja")

            resumen = obtener_resumen_caja(caja_abierta["id"])

            df = pd.DataFrame(
                resumen["por_metodo"],
                columns=["Método de pago", "Total"]
            )

            st.dataframe(df, hide_index=True)

            st.metric(
                "🧾 Total vendido (todos los métodos)",
                f"S/. {resumen['total_vendido']:,.2f}"
            )

            st.metric(
                "💵 Efectivo esperado en caja",
                f"S/. {resumen['efectivo_neto']:,.2f}"
            )

            monto_cierre = st.number_input(
            "💵 Efectivo contado en caja",
                min_value=0.0,
                step=1.0,
                format="%.2f"
            )
            monto_cierre = Decimal(str(monto_cierre))

            diferencia = monto_cierre - resumen["efectivo_neto"]

            if monto_cierre > 0:
                if diferencia == 0:
                    st.success("✅ Caja cuadrada")
                elif diferencia > 0:
                    st.warning(f"⚠️ Sobrante: S/. {float(diferencia):,.2f}")
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

    # =========================
    # TAB 2 – HISTORIAL
    # =========================
    with tab_historial:
        st.subheader("📚 Historial de cajas")

        col1, col2 = st.columns(2)
        with col1:
            fecha_ini = st.date_input("Desde")
        with col2:
            fecha_fin = st.date_input("Hasta")

        historial = obtener_historial_cajas(fecha_ini, fecha_fin)

        if not historial:
            st.info("No hay registros en el rango seleccionado")
            st.stop()

        df = pd.DataFrame(
            historial,
            columns=[
                "ID",
                "Fecha apertura",
                "Fecha cierre",
                "Monto apertura",
                "Monto cierre",
                "Usuario apertura",
                "Usuario cierre",
                "Efectivo",
                "Yape",
                "Plin",
                "Transferencia",
                "Tarjeta",
                "Total Vendido"
            ]
        )

        st.dataframe(df, hide_index=True, width='stretch')

        col1, col2, col3, col4, col5, col6 = st.columns(6)

        col1.metric("💵 Total Efectivo", f"S/. {df['Efectivo'].sum():,.2f}")
        col2.metric("📱 Total Yape", f"S/. {df['Yape'].sum():,.2f}")
        col3.metric("📱 Total Plin", f"S/. {df['Plin'].sum():,.2f}")
        col4.metric("📱 Total Transferencia", f"S/. {df['Transferencia'].sum():,.2f}")
        col5.metric("💳 Total Tarjeta", f"S/. {df['Tarjeta'].sum():,.2f}")
        col6.metric("🧾 Total General", f"S/. {df['Total Vendido'].sum():,.2f}")