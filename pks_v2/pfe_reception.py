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
import zipfile

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

options = {
    "module_width": 0.2,     
    "module_height": 4,   
    "quiet_zone": 1.0,       
    "font_size": 5,          
    "text_distance": 2.0}

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

                buf_ref = BytesIO()
                Code128(reference.upper(), writer=ImageWriter()).write(buf_ref,options)
                buf_ref.seek(0)
                ref_img = Image.open(buf_ref).convert("RGB")

                if sup_sn_check is True:
                    download_buffer = BytesIO()
                    with zipfile.ZipFile(download_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                        for i in range(1, qty + 1):
                            buf_lot = BytesIO()

                            if sup_lot:
                                Code128(f"{sup_lot}_{i}", writer=ImageWriter()).write(buf_lot,options)
                                filename = f"{sup_lot}_{i}_{reference}_barcodes.png"
                            else:
                                Code128(f"{lot_number}_{i}", writer=ImageWriter()).write(buf_lot,options)
                                filename = f"{lot_number}_{i}_{reference}_barcodes.png"

                            buf_lot.seek(0)
                            lot_img = Image.open(buf_lot).convert("RGB")

                            # ✅ combined 캔버스 크기 계산 (ref + lot 기준)
                            max_w = max(ref_img.width, lot_img.width)
                            total_h = ref_img.height + lot_img.height

                            combined = Image.new("RGB", (max_w, total_h), "white")
                            combined.paste(ref_img, (0, 0))
                            combined.paste(lot_img, (0, ref_img.height))

                            img_bytes = BytesIO()
                            combined.save(img_bytes, format="PNG")
                            img_bytes.seek(0)

                            zf.writestr(filename, img_bytes.read())

                    download_buffer.seek(0)

                else:
                    image_bytes = BytesIO()
                    if sup_lot:
                        Code128(str(sup_lot), writer=ImageWriter()).write(image_bytes,options)
                    else:
                        Code128(str(lot_number), writer=ImageWriter()).write(image_bytes,options)

                    image_bytes.seek(0)
                    lot_img = Image.open(image_bytes).convert("RGB")

                    max_w = max(ref_img.width, lot_img.width)+200
                    total_h = ref_img.height + lot_img.height


                    
                    combined = Image.new("RGB", (max_w, total_h), "white")

                    text_sticker = ImageDraw.Draw(combined)
                    text_sticker.text((15,0),f"Reception date : {dt.datetime.now().date()}",fill="black")
                    
                    
                    combined.paste(ref_img, (100, 0))
                    combined.paste(lot_img, (100, ref_img.height))

                    download_buffer = BytesIO()
                    combined.save(download_buffer, format="PNG")
                    download_buffer.seek(0)

                    st.image(download_buffer, caption="Combined Barcode")





                # ===== Supplier lot N 텍스트 =====
                #if sup_lot:
                #    ffont = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 30)
                #    sticker_text = ImageDraw.Draw(combined)
                #    sticker_text.text(
                #        (3, 3),   # 폰트 크기 고려해서 위로 올림
                #        "Supplier lot N",
                #        fill="black",
                #        font=ffont
                #    )




                st.download_button(
                    label="📥 Download Barcode",
                    data=download_buffer,
                    file_name=f"barcode_{reference}.zip" if sup_sn_check else f"barcode_{reference}.png",
                    mime="application/zip" if sup_sn_check else "image/png",
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







df = pd.read_sql("SELECT * FROM reception", con=engine)



new_rows = df.iloc[-10:,:3]


with st.expander("last 10 receptions",expanded=False):
    st.table(new_rows)





























































