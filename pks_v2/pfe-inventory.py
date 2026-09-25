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
import socket
import treepoem





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
st.title("PFE inventory")

# 2 input boxes

with st.form("input_form"):
    inv_lot = st.text_input("OP lot")
    inv_emp = st.text_input("Storage location")
    sup_sn_check = st.checkbox("S/N mode", value = False )
    submit = st.form_submit_button("Input")




## vendorlist ##

vendor_list = pd.read_csv("vendorlist2.csv",sep=";")
usage_list = pd.read_csv("usage.csv",sep=";")
##



options = {
    "module_width": 0.15,     
    "module_height": 2,   
    "quiet_zone": 1.5,       
    "font_size": 5,          
    "text_distance": 2.5}



ffont = ImageFont.truetype("pks_v2/fonts/NanumGothic-Regular.ttf", 27)
ffont2 = ImageFont.truetype("pks_v2/fonts/NanumGothic-Regular.ttf", 22)

if submit:
    if inv_lot:
        inv_lot = inv_lot.strip()
        with engine.begin() as conn:

            # 1️⃣ reference 조회
            result = conn.execute(
                text("""
                    SELECT Reference 
                    FROM reception
                    WHERE OP_lot = :inv_lot
                """),
                {"inv_lot": inv_lot}
            )

            reference = result.scalar()

            # reference 없을 경우 방지
            if reference is None:
                st.error(f"OP lot '{inv_lot}' not found")
                st.stop()

            reference = str(reference)

            # 2️⃣ vendor 찾기
            vendor_match = vendor_list.loc[
                vendor_list["Part number"] == reference, "Supplier"
            ]

            vendor = vendor_match.iloc[0] if not vendor_match.empty else "VNUL"

            # 3️⃣ usage 찾기
            usage_match = usage_list.loc[
                usage_list["reference"] == reference[:7], "usage"
            ]

            usage = ",".join(usage_match.dropna().astype(str).unique())

            # 4️⃣ inventory update
            conn.execute(
                text("""
                    UPDATE reception
                    SET inventory_time = :ivt,
                        Emplacement = :emp
                    WHERE OP_lot = :oplot
                """),
                {   "ivt": dt.datetime.now(),
                    "emp": inv_emp,
                    "oplot": inv_lot
                }
            )



                # -------------------------
                # REFERENCE barcode generation
                # -------------------------
            buf_ref = BytesIO()
            Code128("P"+reference.upper(), writer=ImageWriter()).write(buf_ref, options)
            buf_ref.seek(0)
            ref_img = Image.open(buf_ref).convert("RGB")




                # -------------------------
                # Barcode
                # -------------------------




            ############ data matrix #############
            #RS = chr(30)
            #GS = chr(29)
            #EOT = chr(4)

            #data = "[)>" + RS+"06"+ GS + "12PGTL3"+ GS + f"V{vendor}"+ GS + f"Q{inv_qty}"+GS+f"P{reference.upper()}"+GS+ f"SI{inv_lot}" + RS + EOT


            #dm_barcode = treepoem.generate_barcode(barcode_type="datamatrix",data=data)

            #dm_img = dm_barcode.convert("RGB")
            #dm_img = dm_img.resize((160, 100), Image.NEAREST)
            ##########################################""




            #max_w = 430
            #total_h = 330

            #combined = Image.new("RGB", (max_w, total_h), "white")

            #text_sticker = ImageDraw.Draw(combined)
            #text_sticker.text(
            #    (55, 30),
            #    f"{dt.datetime.now().date()}  {usage}",
            #    fill="black",
            #    font=ffont
            #)
            #text_sticker.text(
            #    (35, 90),
            #    f"OPM lot : {inv_lot}",
            #    fill="black",
            #    font=ffont2
            #)
            #text_sticker.text(
            #    (35, ref_img.height+30),
            #    f"Reference : {reference}",
            #    fill="black",
            #    font=ffont2
            #)
            #text_sticker.text(
            #    (35, ref_img.height+60),
            #    f"Quantity : {inv_qty}",
            #    fill="black",
            #    font=ffont2
            #)




            #combined.paste(dm_img, (290, 200))



            #download_carton_buffer = BytesIO()
            #combined.save(download_carton_buffer, format="PNG")
            #download_carton_buffer.seek(0)

            # 모바일 표시용 resize
            #display_img = combined.copy()
            #display_img.thumbnail((800, 800))

            #st.image(display_img)

            #download_carton_buffer.seek(0)
            #st.session_state.reference = reference
            #st.session_state.qty = inv_qty
            #st.session_state.vendor = vendor
            #st.session_state.project = project
            #st.session_state.op_lot = inv_lot

            # -------------------------
            # Multiple Barcode
            # -------------------------


            if sup_sn_check is True:
                download_zip_buffer = BytesIO()

                with zipfile.ZipFile(download_zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr(f"barcode_{reference}.png", download_carton_buffer.read())
                    for i in range(1, qty + 1):
                        buf_lot = BytesIO()

                        Code128(f"{reference}_{OP_lot}_{i}", writer=ImageWriter()).write(buf_lot, options)
                        filename = f"{OP_lot}_{i}_{reference}_barcodes.png" 

                        buf_lot.seek(0)
                        lot_img = Image.open(buf_lot).convert("RGB")

                        # ✅ combined 캔버스 크기 계산
                        max_w = max(ref_img.width, lot_img.width) + 95
                        total_h = ref_img.height + lot_img.height + 20

                        combined = Image.new("RGB", (max_w - 15, total_h), "white")
                        combined.paste(lot_img, (50, ref_img.height+15))

                        text_sticker = ImageDraw.Draw(combined)
                        text_sticker.text(
                            (80, 0),
                            f"{dt.datetime.now().date()} {usage}",
                            fill="black",
                            font=ffont
                        )
                        text_sticker.text(
                            (105, 45),
                            f"{reference}",
                            fill="black",
                            font=ffont
                        )
                        text_sticker.text(
                            (200, ref_img.height+125),
                            f"{usage}",
                            fill="black",
                            font=ffont2
                        )

                        img_bytes = BytesIO()
                        combined.save(img_bytes, format="PNG")
                        img_bytes.seek(0)

                        zf.writestr(filename, img_bytes.read())




                #download_zip_buffer.seek(0)        
                #st.download_button(
                #label="📥 Download Barcode",
                #data=download_zip_buffer,
                #file_name=f"barcode_{reference}.zip" if sup_sn_check else f"barcode_{reference}.png",
                #mime="application/zip" if sup_sn_check else "image/png",
                #)
            #else: 
                #st.download_button(
                #label="📥 Download Barcode",
                #data=download_carton_buffer.getvalue(),
                #file_name=f"barcode_{reference}.zip" if sup_sn_check else f"barcode_{reference}.png",
                #mime="application/zip" if sup_sn_check else "image/png",
                #)
            st.success("DB updated")                        
    else: st.warning("Lot number missing")        








