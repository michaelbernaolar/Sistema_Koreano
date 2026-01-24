import streamlit as st

def aplicar_estilos_input_busqueda():
    st.markdown(
        """
        <style>
        div[data-baseweb="input"] > div {
            background-color: #1f2937;
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