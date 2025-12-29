import streamlit as st
from sqlalchemy import create_engine, text
import pandas as pd
import re

hide_ui = """
<style>
#MainMenu {visibility: hidden;}     /* 좌측 상단 메뉴 */
footer {visibility: hidden;}        /* 하단 footer */
header {visibility: hidden;}        /* 상단 Streamlit 헤더 */
</style>
"""
st.markdown(hide_ui, unsafe_allow_html=True)

engine = create_engine(
    f"mysql+pymysql://{st.secrets['DB_USER']}:{st.secrets['DB_PASS']}@{st.secrets['DB_HOST']}:{st.secrets['DB_PORT']}/{st.secrets['DB_NAME']}",
    connect_args={
        "ssl": {"ca": "ca.pem"}
    }
)

st.title("PKS Reception")

# 2 input boxes
reference = st.text_input("Reference number")
qty = st.number_input("quantity", min_value=0, step=1)

# Reference pattern
pattern = r"^\d{7}[A-Za-z]{2}$"

if st.button("Input"):
    if re.fullmatch(pattern,reference):
        with engine.begin() as conn: 
            conn.execute(
                text("INSERT INTO reception (Reference, Quantity) VALUES (:ref, :qty)"),
                {"ref": text(reference.upper()), "qty": int(qty)}
            )
        st.success("DB updated")
    else:

        st.warning("Reference missing")




