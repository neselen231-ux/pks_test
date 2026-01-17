import streamlit as st
from sqlalchemy import create_engine, text
import pandas as pd
import re
import os
from barcode.codex import Code128
from barcode.writer import ImageWriter
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import datetime as dt

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
sup_lot = st.text_input("Supplier lot",max_chars=40)
Comment = st.text_input("Comment",max_chars=20)


# Reference pattern
pattern = r"^\d{7}[A-Za-z]{2}$"


sup_sn_check = st.checkbox("S/N mode", value = False )


if st.button("Input"):
    if delivery_note:
        if re.fullmatch(pattern,reference):
            with engine.begin() as conn_2: 
                if sup_sn_check == True:
                    for i in range(1,qty+1):
                        if sup_lot:
                            conn_2.execute(
                                text("INSERT INTO reception (Reference, Quantity, delivery_note, Comment, reception_date, Status, sup_lot) VALUES (:ref, :qty, :dev, :rem, :rep, :sta ,:sup)"),
                                {"ref": reference.upper(), "qty": "1", "dev": delivery_note, "rem": Comment, "rep": dt.datetime.now(), "sta":"to insepct", "sup":f"{sup_lot}_{i}"}
                            )
                        else:
                            conn_2.execute(
                                text("INSERT INTO reception (Reference, Quantity, delivery_note, Comment, reception_date, Status) VALUES (:ref, :qty, :dev, :rem, :rep, :sta)"),
                                {"ref": reference.upper(), "qty": "1", "dev": delivery_note, "rem": Comment, "rep": dt.datetime.now(), "sta":"to insepct"}
                            )
                            lot_number = conn_2.execute(
                            text("SELECT LAST_INSERT_ID()")
                            ).scalar()
                            status_value = f"{lot_number}_{i}"
                            conn_2.execute(
                                text("""
                                    UPDATE reception
                                    SET Status = :status
                                    WHERE lot_number = :lot_number
                                """),
                                {"status": status_value, "lot_number": lot_number}
                            )
                else:
                     conn_2.execute(
                            text("INSERT INTO reception (Reference, Quantity, delivery_note, Comment, reception_date, Status, sup_lot) VALUES (:ref, :qty, :dev, :rem, :rep, :sta ,:sup)"),
                            {"ref": reference.upper(), "qty": {qty}, "dev": delivery_note, "rem": Comment, "rep": dt.datetime.now(), "sta":"to insepct", "sup":f"{sup_lot}"}
                        )
                lot_number = conn_2.execute(
                    text("SELECT LAST_INSERT_ID()")
                ).scalar()
                # ----- Reference Barcode -----
                buf_ref = BytesIO()
                Code128(reference.upper(), writer=ImageWriter()).write(buf_ref)
                buf_ref.seek(0)
                ref_img = Image.open(buf_ref).convert("RGB")

                # ===== LOT 이미지들 만들기 =====
                lot_imgs = []


                if sup_sn_check is True:
                    for i in range(1, qty+ 1):
                        buf_lot = BytesIO()
                        if sup_lot:
                            Code128(f"{sup_lot}_{i}", writer=ImageWriter()).write(buf_lot)
                        else:
                            Code128(f"{lot_number}_{i}", writer=ImageWriter()).write(buf_lot)

                        buf_lot.seek(0)
                        img = Image.open(buf_lot).convert("RGB")
                        lot_imgs.append(img)
                else:
                    # sup_sn_check False면 lot 바코드 1개만 생성
                    buf_lot = BytesIO()
                    if sup_lot:
                        Code128(str(sup_lot), writer=ImageWriter()).write(buf_lot)
                    else:
                        Code128(str(lot_number), writer=ImageWriter()).write(buf_lot)

                    buf_lot.seek(0)
                    lot_img = Image.open(buf_lot).convert("RGB")
                    lot_imgs.append(lot_img)

                # ===== combined 캔버스 크기 계산 =====
                max_w = max([ref_img.width] + [img.width for img in lot_imgs])
                total_h = len(lot_imgs) * ref_img.height + sum(img.height for img in lot_imgs)
                
                combined = Image.new("RGB", (max_w, total_h), "white")

                # ===== ref 붙이기 =====
                y = 0
                for img in lot_imgs:
                    combined.paste(ref_img, (0, y))
                    y += ref_img.height
                    combined.paste(img, (0, y))
                    y += img.height

                # ===== Supplier lot N 텍스트 =====
                if sup_lot:
                    FONT_PATH = os.path.join("pks_v2", "fonts", "NanumGothic-Bold.ttf")
                    sticker_text = ImageDraw.Draw(combined)
                    sticker_text.text(
                        (10, ref_img.height - 45),   # 폰트 크기 고려해서 위로 올림
                        "Supplier lot N",
                        fill="black",
                        font=FONT_PATH
                    )

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
            
with st.expander("Delete lot",expanded=False):
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

baseline = st.session_state["baseline"] or 0

new_rows = df[df["Lot_number"] > baseline].loc[:, df.columns[:3].tolist() + df.columns[-2:].tolist()]



st.table(new_rows)



































