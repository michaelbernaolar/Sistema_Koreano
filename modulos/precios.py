import pandas as pd
import streamlit as st

from db import get_connection
from datetime import datetime
from db import obtener_configuracion

# ------------------------------------------------------
# LÓGICA PRECIO
# ------------------------------------------------------
def get_margen_producto(producto_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT margen_utilidad FROM producto WHERE id = %s", (producto_id,))
    fila = cursor.fetchone()
    conn.close()
    return fila[0] if fila and fila[0] is not None else None


def calcular_precio_venta(costo, margen):
    # Validaciones para evitar NaN
    if costo is None or pd.isna(costo) or costo == 0:
        return None
    if margen is None or pd.isna(margen) or margen >= 1:
        return None

    base = costo / (1 - margen)
    final = base * (1 + 0.18)

    # Redondeo profesional
    final = round(final * 2) / 2
    return final



def guardar_historial(producto_id, precio_anterior, precio_nuevo, margen, costo_promedio):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO historial_precios(producto_id, precio_anterior, precio_nuevo, margen_usado, costo_promedio, fecha)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (producto_id, precio_anterior, precio_nuevo, margen, costo_promedio, datetime.now()))
    conn.commit()
    conn.close()


def actualizar_precio_producto(producto_id, nuevo_precio):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT precio_venta FROM producto WHERE id = %s", (producto_id,))
    fila = cursor.fetchone()
    precio_anterior = fila[0] if fila and fila[0] is not None else None

    cursor.execute("UPDATE public.producto SET precio_venta = %s WHERE id = %s", (nuevo_precio, producto_id))

    conn.commit()
    conn.close()

    return precio_anterior

def actualizar_margen_producto(producto_id, nuevo_margen):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE public.producto SET margen_utilidad = %s WHERE id = %s", (nuevo_margen, producto_id))
    conn.commit()
    conn.close()

def actualizar_valor_venta(pid, precio_venta):
    conn = get_connection()
    cursor = conn.cursor()

    valor_venta = precio_venta / 1.18  # cálculo solicitado

    cursor.execute("""
        UPDATE public.producto
        SET valor_venta = %s
        WHERE id = %s
    """, (valor_venta, pid))

    conn.commit()
    conn.close()

    return valor_venta


# -----------------------------
# MÓDULO STREAMLIT (UI)
# -----------------------------
def precios_app():

    st.title("💲 Módulo Profesional de Precios")

    config = obtener_configuracion()
    margen_global = config.get("margen_utilidad", 0.30)  # 30% por defecto

    conn = get_connection()

    # ============================================================
    # 0. FILTROS - Igual al módulo de ventas
    # ============================================================
    st.subheader("🎯 Buscar producto para actualizar precio")

    col1, col2, col3, col4 = st.columns([1, 3, 3, 3])
    with col1:
        filtro_codigo = st.text_input("🔍 Código")
    with col2:
        filtro_desc = st.text_input("🔍 Descripción")
    with col3:
        filtro_marca = st.text_input("🔍 Marca")
    with col4:
        filtro_catalogo = st.text_input("🔍 Catálogo")

    query = "SELECT * FROM producto WHERE activo=1"
    params = []

    # Filtros dinámicos
    if filtro_codigo:
        codigo_num = ''.join(filter(str.isdigit, filtro_codigo))
        if codigo_num.isdigit():
            codigo_formateado = f"P{int(codigo_num):05d}"
            query += " AND id = %s"
            params.append(codigo_formateado)
        else:
            query += " AND id LIKE %s"
            params.append(f"%{filtro_codigo}%")

    if filtro_desc:
        query += " AND descripcion LIKE %s"
        params.append(f"%{filtro_desc}%")
    if filtro_marca:
        query += " AND marca LIKE %s"
        params.append(f"%{filtro_marca}%")
    if filtro_catalogo:
        query += " AND catalogo LIKE %s"
        params.append(f"%{filtro_catalogo}%")

    df_prod = pd.read_sql_query(query + " ORDER BY descripcion", conn, params=params)

    if df_prod.empty:
        st.warning("⚠️ No hay productos con esos filtros.")
        conn.close()
        return

    # ============================================================
    # 1. SELECCIÓN DE PRODUCTO
    # ============================================================
    productos_dict = {row["descripcion"]: row for _, row in df_prod.iterrows()}
    producto_sel = st.selectbox("📦 Selecciona un producto", list(productos_dict.keys()))  

    row = productos_dict[producto_sel]
    pid = row["id"]

    st.divider()
    st.subheader("📋 Información del producto")

    st.write(f"🔢 Código: {pid}")
    st.write(f"🏭 Marca: {row['marca']}")
    st.write(f"📖 Catálogo: {row['catalogo']}")

    costo = float(row["costo_promedio"]) if row["costo_promedio"] else 0
    precio_actual = float(row["precio_venta"]) if row["precio_venta"] else 0
    margen_actual = row["margen_utilidad"] if row["margen_utilidad"] else margen_global

    # Mostrar
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💲 Costo promedio", f"S/. {costo:,.2f}")
    with col2:
        st.metric("💵 Precio actual", f"S/. {precio_actual:,.2f}")
    with col3:
        st.metric("🎯 Margen actual:", f" {margen_actual*100:,.2f}%")
    with col4:
        # Estado persistente para almacenar precio_sim
        if "precio_sim" not in st.session_state:
            st.session_state.precio_sim = None

        nuevo_margen_pct = st.number_input(
            "Nuevo margen (%)",
            value=margen_actual * 100,
            min_value=0.0,
            max_value=99.0
        )

        nuevo_margen = nuevo_margen_pct / 100  # convertir a decimal

        if nuevo_margen <= 0 or nuevo_margen >= 1:
            st.error("El margen debe estar entre 1% y 99%.")
            st.stop()
        
    # --------------------------
    # Botón: GUARDAR
    # --------------------------
    colA, colB, colC = st.columns(3)
    with colA:
        # --------------------------
        # Botón: SIMULAR
        # --------------------------
        if st.button("Simular"):
            st.session_state.precio_sim = calcular_precio_venta(costo, nuevo_margen)

            if st.session_state.precio_sim is None:
                st.error("❌ No se pudo calcular el precio. Verifica costo y margen.")
            else:
                st.info(f"💡 Precio sugerido con IGV: **S/. {st.session_state.precio_sim:.2f}**")
            
    with colB:
        if st.button("💾 Guardar precio"):
            if st.session_state.precio_sim is None:
                st.error("⚠ Primero debes simular el precio.")
            else:
                precio_anterior = actualizar_precio_producto(pid, st.session_state.precio_sim)
                actualizar_valor_venta(pid, st.session_state.precio_sim)
                actualizar_margen_producto(pid, nuevo_margen)
                guardar_historial(pid, precio_anterior, st.session_state.precio_sim, nuevo_margen, costo)

                st.success("✔ Precio actualizado correctamente.")
                st.rerun()
    with colC:
        if st.button("❌ Cancelar cambios"):
            st.session_state.precio_sim = None


    st.divider()
    
    # ============================================================
    # 3. HISTORIAL
    # ============================================================
    st.subheader("📜 Historial de cambios")

    df_hist = pd.read_sql_query("""
        SELECT h.fecha,
            h.costo_promedio,                    
            h.precio_anterior,
            h.precio_nuevo,
            (h.precio_nuevo - h.precio_anterior) AS variacion,
            h.margen_usado,
            p.descripcion
        FROM historial_precios h
        JOIN producto p ON p.id = h.producto_id
        WHERE h.producto_id = %s
        ORDER BY h.fecha DESC
    """, conn, params=[pid])

    # ========================
    # Ordenar columnas
    # ========================
    df_hist = df_hist[
        ["fecha", "costo_promedio", "precio_anterior", "precio_nuevo", "variacion", "margen_usado"]
    ]

    # ========================
    # Renombrar columnas
    # ========================
    df_hist = df_hist.rename(columns={
        "fecha": "Fecha",
        "costo_promedio": "Costo Promedio",
        "precio_anterior": "Precio Anterior",
        "precio_nuevo": "Precio Nuevo",
        "variacion": "Variación",
        "margen_usado": "Margen Aplicado"
    })

    # ========================
    # Formato y colores
    # ========================
    def formato_color(val):
        if pd.isna(val):
            return ""
        if val > 0:
            return "background-color: rgba(0, 200, 0, 0.25);"   # verde suave
        elif val < 0:
            return "background-color: rgba(255, 0, 0, 0.25);"   # rojo suave
        else:
            return ""

    df_styled = df_hist.style.map(formato_color, subset=["Variación"])

    st.dataframe(
        df_styled,
        width='stretch',
        column_config={

            "Fecha": st.column_config.DatetimeColumn(
                "Fecha",
                format="YYYY-MM-DD HH:mm",
                width="small"
            ),

            "Costo Promedio": st.column_config.NumberColumn(
                "Costo Promedio",
                format="S/. %.2f",
                width="small"
            ),

            "Precio Anterior": st.column_config.NumberColumn(
                "Precio Anterior",
                format="S/. %.2f",
                width="small"
            ),

            "Precio Nuevo": st.column_config.NumberColumn(
                "Precio Nuevo",
                format="S/. %.2f",
                width="small"
            ),

            "Variación": st.column_config.NumberColumn(
                "Variación",
                format="S/. %.2f",
                width="small",
                help="Diferencia entre el precio nuevo y el precio anterior"
            ),

            "Margen Aplicado": st.column_config.NumberColumn(
                "Margen Aplicado",
                format="%.2f",
                width="small"
            ),
        }
    )

    conn.close()