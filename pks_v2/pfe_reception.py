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
st.title("Reception")

# 2 input boxes

with st.form("input_form"):
    reference = st.text_input("Reference number")
    qty_input = st.text_input("quantity", "1")
    delivery_note = st.text_input("Delivery note")
    #project = st.selectbox("Project", ["Als 525", "Als 105", "Als Common", "Hess 3P", "Hess 4P", "Hess common"])
    sup_lot = st.text_input("Supplier lot",max_chars=40)
    Comment = st.text_input("Comment",max_chars=20)
    sup_sn_check = st.checkbox("S/N mode", value = False )
    submit = st.form_submit_button("Input")




## vendorlist ##

vendor_list = pd.read_csv("vendorlist2.csv",sep=";")
usage_list = pd.read_csv("usage.csv",sep=";")
##


# Reference pattern
pattern = r"^\d{7}[A-Za-z]{2}$"

options = {
    "module_width": 0.15,     
    "module_height": 2,   
    "quiet_zone": 1.5,       
    "font_size": 5,          
    "text_distance": 2.5}



ffont = ImageFont.truetype("pks_v2/fonts/NanumGothic-Regular.ttf", 27)
ffont2 = ImageFont.truetype("pks_v2/fonts/NanumGothic-Regular.ttf", 22)

if submit:
    if delivery_note:
        if re.fullmatch(pattern, reference):
            try:
                qty = int(qty_input)
            except:
                st.error("Quantity must be a number")
                st.stop()
                            #----- Vendorcheck

            vendor_match = vendor_list.loc[vendor_list["Part number"] == reference, "Supplier"]
            usage_match = usage_list.loc[usage_list["reference"] == reference[:7], "usage"]
            usage = ','.join(usage_match.dropna().astype(str).unique())
            if vendor_match.empty:
                vendor = "VNUL"
            else:
                vendor = vendor_match.iloc[0]
            



            with engine.begin() as conn_2:
                conn_2.execute(
                    text("""INSERT INTO reception
                            (Reference, Quantity, delivery_note, Comment, reception_date, Status, sup_lot,program)
                            VALUES (:ref, :qty, :dev, :rem, :rep, :sta, :sup, :prog)"""),
                    {"ref": reference.upper(), "qty": qty, "dev": delivery_note,
                     "rem": Comment, "rep": dt.datetime.now(), "sta": "to insepct", "sup": sup_lot, "prog" : usage
}
                )
                OP_lot = conn_2.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                

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

                ############ data matrix #############
                RS = chr(30)
                GS = chr(29)
                EOT = chr(4)
                
                data = f"S{OP_lot}\rV{vendor}\rP{reference.upper()}\rQ{qty}\r"

                dm_barcode = treepoem.generate_barcode(barcode_type="datamatrix",data=data)
                
                dm_img = dm_barcode.convert("RGB")
                dm_img = dm_img.resize((200, 200), Image.NEAREST)
                ##########################################""

                

                                
                max_w = max(ref_img.width, lot_img.width, qty_img.width, vendor_img.width) + 250
                total_h = ref_img.height + lot_img.height + qty_img.height + vendor_img.height

                combined = Image.new("RGB", (max_w, total_h), "white")

                text_sticker = ImageDraw.Draw(combined)
                text_sticker.text(
                    (55, 30),
                    f"{dt.datetime.now().date()}  {usage}",
                    fill="black",
                    font=ffont
                )
                text_sticker.text(
                    (35, 90),
                    f"OPM lot : {OP_lot}",
                    fill="black",
                    font=ffont2
                )
                text_sticker.text(
                    (35, ref_img.height+30),
                    f"Reference : {reference}",
                    fill="black",
                    font=ffont2
                )
                text_sticker.text(
                    (35, ref_img.height+60),
                    f"Quantity : {qty}",
                    fill="black",
                    font=ffont2
                )



                #combined.paste(lot_img, (165, 28))
                #combined.paste(ref_img, (165, ref_img.height+18))
                combined.paste(dm_img, (290, qty_img.height))
                #combined.paste(vendor_img, (165, vendor_img.height+140))


                download_carton_buffer = BytesIO()
                combined.save(download_carton_buffer, format="PNG")
                download_carton_buffer.seek(0)

                # 모바일 표시용 resize
                display_img = combined.copy()
                display_img.thumbnail((800, 800))
                
                st.image(display_img)

                download_carton_buffer.seek(0)
                st.session_state.reference = reference
                st.session_state.qty = qty
                st.session_state.vendor = vendor
                #st.session_state.project = project
                st.session_state.op_lot = OP_lot

                # -------------------------
                # Multiple Barcode
                # -------------------------

                
                if sup_sn_check is True:
                    download_zip_buffer = BytesIO()

                    with zipfile.ZipFile(download_zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                        zf.writestr(f"barcode_{reference}.png", download_carton_buffer.read())
                        for i in range(1, qty + 1):
                            buf_lot = BytesIO()

                            Code128(f"{OP_lot}_{i}", writer=ImageWriter()).write(buf_lot, options)
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
                            


                        
                    download_zip_buffer.seek(0)        
                    st.download_button(
                    label="📥 Download Barcode",
                    data=download_zip_buffer,
                    file_name=f"barcode_{reference}.zip" if sup_sn_check else f"barcode_{reference}.png",
                    mime="application/zip" if sup_sn_check else "image/png",
                    )
                else: 

                    st.download_button(
                    label="📥 Download Barcode",
                    data=download_carton_buffer.getvalue(),
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

#if st.button("Print"):
#    print_label(
#    st.session_state.reference,
#    st.session_state.qty,
#    st.session_state.vendor,
#    st.session_state.project,
#    st.session_state.op_lot
#    )





df = pd.read_sql("SELECT * FROM reception", con=engine)



new_rows = df.iloc[-10:,[-2,0,1,2]]


with st.expander("last 10 receptions",expanded=False):
    st.table(new_rows)






















































































































































































































































































