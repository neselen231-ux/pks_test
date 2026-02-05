import datetime as dt
import streamlit as st
import pandas as pd


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
st.title("Reception download")

st.download_button(
    label="📥 Download reception history",
    data=download_buffer,
    file_name=f"barcode_{reference}.zip" if sup_sn_check else f"barcode_{reference}.png",
    mime="application/zip" if sup_sn_check else "image/png",
