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

# 🔄 자동 새로고침 (3초마다 리런)
st.autorefresh(interval=3000, key="refresh")

# baseline 없으면 처음 1번만 저장
if "baseline" not in st.session_state:
    with engine.connect() as conn:
        st.session_state["baseline"] = conn.execute(
            text("SELECT MAX(Lot_number) FROM reception")
        ).scalar()

baseline = st.session_state["baseline"]

df = pd.read_sql("SELECT * FROM reception", con=engine)
# baseline 이후 데이터만 보기
new_rows = df[df["Lot_number"] > baseline]

st.subheader("📌 앱 켠 이후 추가된 데이터만")
st.table(new_rows)

if st.button("Input"):
    if re.fullmatch(pattern,reference):
        with engine.begin() as conn_2: 
            conn_2.execute(
                text("INSERT INTO reception (Reference, Quantity) VALUES (:ref, :qty)"),
                {"ref": reference.upper(), "qty": int(qty)}
            )
        st.success("DB updated")
    else:

        st.warning("Reference missing")








