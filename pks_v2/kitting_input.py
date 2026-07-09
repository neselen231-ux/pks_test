import datetime as dt
import streamlit as st
import pandas as pd
from io import BytesIO
from sqlalchemy import create_engine
import os
from urllib.parse import urlparse

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

engine = create_engine(
    f"mysql+pymysql://{st.secrets['DB_USER']}:{st.secrets['DB_PASS']}@{st.secrets['DB_HOST']}:{st.secrets['DB_PORT']}/{st.secrets['DB_NAME']}",
    connect_args={
        "ssl": {"ca": "ca.pem"}
    }
)
st.title("Kitting input")

if st.button("Add kitting"):

    # GitHub raw URL
    url = "https://raw.githubusercontent.com/neselen231-ux/pks_test/main/pks_v2/3PTK0_1.csv"
    filename = os.path.basename(urlparse(url).path)
    
    # CSV 읽기
    kit_df = pd.read_csv(url)

    # 같은 csv 저장 (선택)
    kit_df.to_csv(
    f"pks_v2/kitting_ongoing/src/{dt.datetime.today():%Y%m%d_%H%M%S}_{filename}",
    index=False
    )

    # SQL에 추가
    #df.to_sql(
    #    "vendorlist",
    #    con=engine,
    #    if_exists="append",   # append / replace 선택
    #    index=False
    #)

    st.success("Import completed")
