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
qty = st.number_input("quantity", min_value=1, step=1)
delivery_note = st.text_input("Delivery note",max_chars=20)
sup_lot = st.text_input("Supplier lot",max_chars=40)
Comment = st.text_input("Comment",max_chars=20)
project = st.selectbox("Project",["","Als 105","Als 525","Als common","Hess 3P","Hess 4P","Hess common","TBC"])


# Reference pattern
pattern = r"^\d{7}[A-Za-z]{2}$"

options = {
    "module_width": 0.2,     
    "module_height": 4,   
    "quiet_zone": 1.0,       
    "font_size": 5,          
    "text_distance": 2.0}

sup_sn_check = st.checkbox("S/N mode", value = False )

ffont = ImageFont.truetype("pks_v2/fonts/NanumGothic-Regular.ttf", 25)
ffont2 = ImageFont.truetype("pks_v2/fonts/NanumGothic-Regular.ttf", 15)
OP_lots = []  ### ✅ FIX: 각 INSERT의 OP_lot들을 저장

if st.button("Input"):
    if delivery_note and project:
        if re.fullmatch(pattern, reference):
            with engine.begin() as conn_2:
                # -------------------------
                # INSERT 파트
                # -------------------------

                if sup_sn_check == True:


                    for i in range(1, qty + 1):
                        if sup_lot:
                            conn_2.execute(
                                text("""INSERT INTO reception
                                        (Reference, Quantity, delivery_note, Comment, reception_date, Status, sup_lot, program)
                                        VALUES (:ref, :qty, :dev, :rem, :rep, :sta, :sup, :prog)"""),
                                {"ref": reference.upper(), "qty": "1", "dev": delivery_note,
                                 "rem": Comment, "rep": dt.datetime.now(), "sta": "to insepct",
                                 "sup": f"{sup_lot}_{i}", "prog": project}
                            )
                            OP_lot = conn_2.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                            OP_lots.append(OP_lot)  ### ✅ FIX: 매 insert ID 저장

                            status_value = f"{OP_lot}_{i}"
                            conn_2.execute(
                                text("""
                                    UPDATE reception
                                    SET Status = :status
                                    WHERE OP_lot = :OP_lot
                                """),
                                {"status": status_value, "OP_lot": OP_lot}
                            )

                        else:
                            conn_2.execute(
                                text("""INSERT INTO reception
                                        (Reference, Quantity, delivery_note, Comment, reception_date, Status, program)
                                        VALUES (:ref, :qty, :dev, :rem, :rep, :sta, :prog)"""),
                                {"ref": reference.upper(), "qty": "1", "dev": delivery_note,
                                 "rem": Comment, "rep": dt.datetime.now(), "sta": "to insepct","prog": project}
                            )

                            OP_lot = conn_2.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                            OP_lots.append(OP_lot)  ### ✅ FIX: 매 insert ID 저장

                            status_value = f"{OP_lot}_{i}"
                            conn_2.execute(
                                text("""
                                    UPDATE reception
                                    SET Status = :status
                                    WHERE OP_lot = :OP_lot
                                """),
                                {"status": status_value, "OP_lot": OP_lot}
                            )

                else:
                    conn_2.execute(
                        text("""INSERT INTO reception
                                (Reference, Quantity, delivery_note, Comment, reception_date, Status, sup_lot, program)
                                VALUES (:ref, :qty, :dev, :rem, :rep, :sta, :sup, :prog)"""),
                        {"ref": reference.upper(), "qty": qty, "dev": delivery_note,
                         "rem": Comment, "rep": dt.datetime.now(), "sta": "to insepct",
                         "sup": f"{sup_lot}", "prog": project}
                    )

                OP_lot = conn_2.execute(text("SELECT LAST_INSERT_ID()")).scalar()

                # -------------------------
                # REFERENCE 바코드 생성
                # -------------------------
                buf_ref = BytesIO()
                Code128("P"+reference.upper(), writer=ImageWriter()).write(buf_ref, options)
                buf_ref.seek(0)
                ref_img = Image.open(buf_ref).convert("RGB")

                # -------------------------
                # SN 케이스: zip 여러개 생성
                # -------------------------
                if sup_sn_check is True:
                    download_buffer = BytesIO()

                    with zipfile.ZipFile(download_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                        for i in range(1, qty + 1):
                            buf_lot = BytesIO()
                            sup_lots = BytesIO()
                            if sup_lot:
                                Code128(f"S{this_lot}", writer=ImageWriter()).write(buf_lot, options)
                                filename = f"{this_lot}_{reference}_barcodes.png"  ### ✅ FIX

                            buf_lot.seek(0)
                            lot_img = Image.open(buf_lot).convert("RGB")

                            # ✅ combined 캔버스 크기 계산
                            max_w = max(ref_img.width, lot_img.width, sup_img.width) + 280
                            total_h = ref_img.height + lot_img.height + sup_img.height

                            combined = Image.new("RGB", (max_w, total_h), "white")
                            combined.paste(ref_img, (165, 25))
                            combined.paste(lot_img, (165, ref_img.height+15))

                            text_sticker = ImageDraw.Draw(combined)
                            text_sticker.text(
                                (105, 0),
                                f"{dt.datetime.now().date()}   proejct : {project}",
                                fill="black",
                                font=ffont
                            )
                            text_sticker.text(
                                (85, 45),
                                "Reference",
                                fill="black",
                                font=ffont2
                            )
                            text_sticker.text(
                                (85, ref_img.height+35),
                                "OPM lot",
                                fill="black",
                                font=ffont2
                            )
                            text_sticker.text(
                                (85, ref_img.height+115),
                                "Supplier lot",
                                fill="black",
                                font=ffont2
                            )

                            img_bytes = BytesIO()
                            combined.save(img_bytes, format="PNG")
                            img_bytes.seek(0)

                            zf.writestr(filename, img_bytes.read())

                    download_buffer.seek(0)

                # -------------------------
                # SN 아닌 케이스: 단일 바코드 생성
                # -------------------------
                else:
                    #vendor check
                    vendor_list = pd.read_csv("vendorlist2.csv",sep=";")
                    vendor = vendor_list.loc[vendor_list["Part number"] == reference,"Supplier"].iloc[0]

                    if not sup_lot:
                        sup_lot="NA"
                    image_bytes = BytesIO()
                    qty_lots = BytesIO()
                    vendor_bytes = BytesIO()
                    
                    Code128("Q"+str(qty), writer=ImageWriter()).write(qty_lots, options)
                    Code128("S"+str(OP_lot), writer=ImageWriter()).write(image_bytes, options)
                    Code128("V"+str(vendor), writer=ImageWriter()).write(vendor_bytes, options)
                        
                    qty_lots.seek(0)
                    qty_img = Image.open(qty_lots).convert("RGB")
                    image_bytes.seek(0)
                    lot_img = Image.open(image_bytes).convert("RGB")
                    vendor_bytes.seek(0)
                    vendor_img = Image.open(vendor_bytes).convert("RGB")

                    
                    max_w = max(ref_img.width, lot_img.width, qty_img.width, vendor_img.width) + 250
                    total_h = ref_img.height + lot_img.height + qty_img.height + vendor_img.height

                    combined = Image.new("RGB", (max_w, total_h), "white")

                    text_sticker = ImageDraw.Draw(combined)
                    text_sticker.text(
                        (105, 0),
                        f"{dt.datetime.now().date()}   proejct : {project}",
                        fill="black",
                        font=ffont
                    )
                    text_sticker.text(
                        (85, 45),
                        "Reference",
                        fill="black",
                        font=ffont2
                    )
                    text_sticker.text(
                        (85, ref_img.height+35),
                        "OPM lot",
                        fill="black",
                        font=ffont2
                    )
                    text_sticker.text(
                        (85, ref_img.height+115),
                        "Supplier lot",
                        fill="black",
                        font=ffont2
                    )

                    combined.paste(ref_img, (165, 25))
                    combined.paste(lot_img, (165, ref_img.height+15))
                    combined.paste(qty_img, (165, qty_img.height+95))
                    combined.paste(vendor_img, (165, vendor_img.height+140))


                    download_buffer = BytesIO()
                    combined.save(download_buffer, format="PNG")
                    download_buffer.seek(0)

                    st.image(download_buffer, caption="Combined Barcode")









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
            deletion.execute(text("DELETE FROM reception WHERE OP_lot = :lot"),{"lot":int(delete_id)})
        st.rerun()







df = pd.read_sql("SELECT * FROM reception", con=engine)



new_rows = df.iloc[-10:,[-2,0,1,2]]


with st.expander("last 10 receptions",expanded=False):
    st.table(new_rows)

















































































































































