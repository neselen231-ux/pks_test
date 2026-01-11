import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from streamlit_autorefresh import st_autorefresh
import datetime as dt

engine = create_engine(
    f"mysql+pymysql://{st.secrets['DB_USER']}:{st.secrets['DB_PASS']}@{st.secrets['DB_HOST']}:{st.secrets['DB_PORT']}/{st.secrets['DB_NAME']}",
    connect_args={
        "ssl": {"ca": "ca.pem"}
    }
)

st.title("PFE stock system")

hide_ui = """
<style>
#MainMenu {visibility: hidden;}      /* 메뉴 */
header {visibility: hidden;}         /* 헤더 */
footer {visibility: hidden;}         /* Footer */

div[data-testid="stStatusWidget"] {display: none;}   /* status badge */
div[data-testid="stDecoration"] {display: none;}     /* hosted badge */
div.viewerBadge_link__1S137 {display: none;}         /* created by */
</style>
"""

st.markdown(hide_ui, unsafe_allow_html=True)
st_autorefresh(interval=50000, key="refresh")
if "changed_lots" not in st.session_state:
    st.session_state["changed_lots"] = []

lot = st.number_input("lot to stock",format="%d", min_value=0)
emplacement = st.text_input("Emplactement")

df = pd.read_sql("SELECT * FROM reception", con=engine)

if st.button("stock input"):
    row = df.loc[df["Lot_number"] == lot, "Emplacement"]
    okq = df.loc[df["Lot_number"] == lot, "Ok_qty"]

    if row.empty:
        st.warning("No Lot")
    else:
        current_emp = str(row.iloc[0])
        okq2 = (okq.iloc[0])
        if current_emp != "Prison" and pd.notna(okq2) and okq2 !=0:
            with engine.begin() as conc:
                conc.execute(
                    text("""
                        UPDATE reception 
                        SET Emplacement = :emplacement, stocking_time = :sto 
                        WHERE Lot_number = :lot
                    """),
                    {'emplacement': emplacement, "lot": int(lot), "sto": dt.datetime.now()}
                )
            st.session_state["changed_lots"].append(int(lot))
            st.success(f"{lot} is stocked at {emplacement}")
        else:
            st.warning(f"{lot} cannot be stocked")

df = pd.read_sql("SELECT * FROM reception", con=engine)

table = df[df["Lot_number"].isin(st.session_state["changed_lots"])]

if st.session_state["changed_lots"]:
    df = pd.read_sql(
        text("SELECT * FROM reception"),
        con=engine
    )

    table = df[df["Lot_number"].isin(st.session_state["changed_lots"])]

    st.table(
        table.loc[:, table.columns[:4].tolist() + table.columns[-1:].tolist()]
    )
