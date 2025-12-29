import streamlit as st
from sqlalchemy import create_engine, text
import pandas as pd

engine = create_engine(
    f"mysql+pymysql://{st.secrets['DB_USER']}:{st.secrets['DB_PASS']}@{st.secrets['DB_HOST']}:{st.secrets['DB_PORT']}/{st.secrets['DB_NAME']}",
    connect_args={
        "ssl": {"ca": "ca.pem"}
    }
)

st.title("PKS Reception")

# 입력란 2개
reference = st.text_input("Reference number")
qty = st.number_input("quantity", min_value=0, step=1)

if st.button("Input"):
    if reference:
        with engine.begin() as conn: 
            conn.execute(
                text("INSERT INTO reception (name, age) VALUES (:ref, :qty)"),
                {"ref": int(reference), "qty": int(qty)}
            )
        st.success("DB updated")
    else:

        st.warning("Reference missing")
