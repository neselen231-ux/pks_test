import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from streamlit_autorefresh import st_autorefresh

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
st_autorefresh(interval=55000, key="refresh")
engine = create_engine(
    f"mysql+pymysql://{st.secrets['DB_USER']}:{st.secrets['DB_PASS']}@{st.secrets['DB_HOST']}:{st.secrets['DB_PORT']}/{st.secrets['DB_NAME']}",
    connect_args={
        "ssl": {"ca": "ca.pem"}
    }
)
st.title("PFE stock system")

st.subheader("Lots to stock")
df = pd.read_sql("SELECT * FROM reception", con=engine)
st.table(df[(df["Emplacement"].isna()) & (df["Lot_number"].notna())])

if "changed_lots" not in st.session_state:
    st.session_state["changed_lots"] = []

lot = st.number_input("lot to stock",min_value=0)
emplacement = st.text_input("Emplactement")



if st.button("stock input"):
    with engine.begin() as conc:
        conc.execute(text(f"UPDATE reception SET Emplacement = :emplacement WHERE Lot_number = :lot"),{'emplacement' : emplacement, "lot" : lot })
        st.session_state["changed_lots"].append(lot)
        st.success(f"{lot} is stocked at {emplacement}")



table = df[df["Lot_number"].isin(st.session_state["changed_lots"])]

st.subheader("Stocked lots")
if st.session_state["changed_lots"]:
    df = pd.read_sql(
        text("SELECT * FROM reception"),
        con=engine
    )

    table = df[df["Lot_number"].isin(st.session_state["changed_lots"])]

    st.table(
        table.loc[:, table.columns[:4].tolist() + table.columns[-1:].tolist()]
    )
