import streamlit as st

def aplicar_estilos_input_busqueda():
    st.markdown(
        """
        <style>
        div[data-baseweb="input"] > div {
            background-color: #f0f2f6;
            border: 1px solid #4b5563;
            border-radius: 6px;
        }

        div[data-baseweb="input"] input {
            color: #ffffff;
            font-weight: 500;
        }

        div[data-baseweb="input"] input::placeholder {
            color: #9ca3af;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

def aplicar_estilos_selectbox():
    st.markdown(
        """
        <style>
        /* Contenedor del selectbox */
        div[data-baseweb="select"] > div {
            background-color: #f0f2f6;
            border: 1px solid #4b5563;
            border-radius: 6px;
        }

        /* Texto seleccionado */
        div[data-baseweb="select"] span {
            color: #111827;
            font-weight: 500;
        }

        /* Placeholder */
        div[data-baseweb="select"] [data-placeholder="true"] {
            color: #6b7280;
        }

        /* Dropdown */
        div[data-baseweb="popover"] {
            background-color: #ffffff;
        }

        /* Opciones */
        div[data-baseweb="menu"] div {
            color: #111827;
        }

        /* Hover opción */
        div[data-baseweb="menu"] div:hover {
            background-color: #e5e7eb;
        }
        </style>
        """,
        unsafe_allow_html=True
    )