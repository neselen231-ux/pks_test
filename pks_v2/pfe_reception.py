import streamlit as st
from sqlalchemy import create_engine, text
import pandas as pd
import re
from barcode.codex import Code128
from barcode.writer import ImageWriter
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

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

st.title("Reception")

# 2 input boxes
reference = st.text_input("Reference number")
qty = st.number_input("quantity", min_value=0, step=1)
delivery_note = st.text_input("Delivery note",max_chars=20)
Comment = st.text_input("Comment",max_chars=20)

# Reference pattern
pattern = r"^\d{7}[A-Za-z]{2}$"





if st.button("Input"):
    if delivery_note:
        if re.fullmatch(pattern,reference):
            with engine.begin() as conn_2: 
                conn_2.execute(
                    text("INSERT INTO reception (Reference, Quantity, delivery_note, Comment, reception_date, Status) VALUES (:ref, :qty, :dev, :rem, :rep, :sta)"),
                    {"ref": reference.upper(), "qty": int(qty), "dev": delivery_note, "rem": Comment, "rep": dt.datetime.now(), "sta":"to insepct"}
                )
                lot_number = conn_2.execute(
                    text("SELECT LAST_INSERT_ID()")
                ).scalar()
                # ----- Reference Barcode -----
                buf_ref = BytesIO()
                Code128(reference.upper(), writer=ImageWriter()).write(buf_ref)
                buf_ref.seek(0)
                ref_img = Image.open(buf_ref)

                # ----- Lot_number Barcode -----
                buf_lot = BytesIO()
                Code128(str(lot_number), writer=ImageWriter()).write(buf_lot)
                buf_lot.seek(0)
                lot_img = Image.open(buf_lot)
                # ===== 이미지 합치기  =====
                total_width = max(ref_img.width , lot_img.width)
                max_height = ref_img.height + lot_img.height

                combined = Image.new("RGB", (total_width, max_height), "white")
                combined.paste(ref_img, (0, 0))
                combined.paste(lot_img, (0, ref_img.height))

                # ✅ 최종 파일만 저장
                combined_file = BytesIO()
                combined.save(combined_file, format="PNG")
                combined_file.seek(0)

                st.image(combined, caption="Combined Barcode")

                st.download_button(
                    label="📥 Download Barcode",
                    data=combined_file,
                    file_name=f"barcode_{lot_number}_{reference}.png",
                    mime="image/png"
                )
            st.success("DB updated")
        else: st.warning("Reference missing")
    else: st.warning("Delivery note missing")        
            

delete_id = st.number_input("Delete lot",min_value=0)

if st.button("Delete"):
    with engine.begin() as deletion:
        deletion.execute(text("DELETE FROM reception WHERE Lot_number = :lot"),{"lot":int(delete_id)})
    st.rerun()


st.subheader("Reception declaration history")




if "baseline" not in st.session_state:
    with engine.connect() as conn:
        st.session_state["baseline"] = conn.execute(
            text("SELECT MAX(Lot_number) FROM reception")
        ).scalar()
df = pd.read_sql("SELECT * FROM reception", con=engine)
baseline = st.session_state["baseline"]


new_rows = df[df["Lot_number"] > baseline].loc[:, df.columns[:3].tolist() + df.columns[-1:].tolist()]



st.table(new_rows)




















