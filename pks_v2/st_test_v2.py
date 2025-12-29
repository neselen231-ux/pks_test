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

# 2 input boxes
reference = st.text_input("Reference number")
qty = st.number_input("quantity", min_value=0, step=1)

# Reference pattern
pattern = r"^\d{7}[A-Za-z]{2}$"


if st.button("Input"):
    if re.fullmatch(pattern,reference):
        with engine.begin() as conn_2: 
            conn_2.execute(
                text("INSERT INTO reception (Reference, Quantity) VALUES (:ref, :qty)"),
                {"ref": reference.upper(), "qty": int(qty)}
            )
            
            ## Last lot number
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
            
            # ===== PIL =====
            total_width = max(ref_img.width , lot_img.width)
            max_height = ref_img.height + lot_img.height

            combined = Image.new("RGB", (total_width, max_height), "white")
            combined.paste(ref_img, (0, 0))
            combined.paste(lot_img, (0, ref_img.height))

            # combined file save on BytesIO
            combined_file = BytesIO()
            combined.save(combined_file, format="PNG")
            combined_file.seek(0)

            # Streamlit에 이미지 표시
            st.image(combined, caption="Combined Barcode")

            # 다운로드 버튼 (아이콘 가능)
            st.download_button(
                label="📥 Download Barcode",
                data=combined_file,
                file_name=f"barcode_{lot_number}_{reference}.png",
                mime="image/png"
            )
        st.success("DB updated")
    else:

        st.warning("Reference error")



df = pd.read_sql("SELECT * FROM reception", con=engine)

if "baseline" not in st.session_state:
    with engine.connect() as conn:
        st.session_state["baseline"] = conn.execute(
            text("SELECT MAX(Lot_number) FROM reception")
        ).scalar()

baseline = st.session_state["baseline"]


new_rows = df[df["Lot_number"] > baseline]

st.subheader("Reception declaration history")
st.table(new_rows)













