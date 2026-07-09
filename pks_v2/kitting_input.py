import datetime as dt
import streamlit as st
import pandas as pd
from io import BytesIO
from sqlalchemy import create_engine, text
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

    url = "https://raw.githubusercontent.com/neselen231-ux/pks_test/main/pks_v2/ktting_list/3PTK0_1.csv"
    kit_df = pd.read_csv(url,sep=";")

    with engine.begin() as conn:

        # 현재 가장 큰 kit_number 조회
        result = conn.execute(text("SELECT COALESCE(MAX(kit_number), 0) FROM kitting"))
        kit_number = result.scalar() + 1

        # CSV의 모든 행 INSERT
        for _, row in kit_df.iterrows():

            conn.execute(
                text("""
                    INSERT INTO kitting
                    (reference,description,qty, place, nlot,
                     kitting, pb_type, kit_number, comment, date)
                    VALUES
                    (:ref, :des, :qty, :pla, :nlt,
                     :kit, :pbt, :kitn, :com, :dat)
                """),
                {
                    "ref": row["reference"],
                    "des": row["description"],
                    "qty": row["qty"],
                    "pla": row["Place"],
                    "nlt": row["Nlot"],
                    "kit": row["Kitting"],
                    "pbt": row["pb_type"],
                    "kitn": kit_number,
                    "com": row["Comment"],
                    "dat": dt.datetime.now(ZoneInfo("Europe/Paris")),
                },
            )

    st.success(f"Kitting {kit_number} added.")

    # SQL에 추가
    #df.to_sql(
    #    "vendorlist",
    #    con=engine,
    #    if_exists="append",   # append / replace 선택
    #    index=False
    #)

    st.success("Import completed")
