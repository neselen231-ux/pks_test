import streamlit as st
import pandas as pd
from barcode.codex import Code128
from barcode.writer import ImageWriter
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import create_engine, text
from streamlit_autorefresh import st_autorefresh
import datetime as dt

engine = create_engine(
    f"mysql+pymysql://{st.secrets['DB_USER']}:{st.secrets['DB_PASS']}@{st.secrets['DB_HOST']}:{st.secrets['DB_PORT']}/{st.secrets['DB_NAME']}",
    connect_args={
        "ssl": {"ca": "ca.pem"}
    }
)

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
st_autorefresh(interval=500000, key="refresh")
st.title("PFE Reception")


st.subheader("lot to be inspected")
df = pd.read_sql("SELECT * FROM reception", con=engine)
st.table(df[(df["Quantity"]!=0)&(df["Ok_qty"].isnull())].iloc[:,[-1,0,1,2]])


lot_number = st.number_input("OP Lot number",min_value=0)
ok_qty = st.number_input("Compliant Quantity",min_value=0,step=1)


if "changed_lots" not in st.session_state:
    st.session_state["changed_lots"] = []        





### Input button

if st.button("QI input"):
    if int(lot_number) in df["Lot_number"].values :
        with engine.begin() as con:
            total_quantity = con.execute(
                text("SELECT Quantity FROM reception WHERE Lot_number = :lot"),
                {"lot": int(lot_number)}
            ).scalar()
            st.session_state["changed_lots"].append(lot_number)


            serached_ref = con.execute(
                text("SELECT Reference FROM reception WHERE Lot_number = :lot"),
                {"lot": int(lot_number)}
            ).scalar()

            serached_dev = con.execute(
                text("SELECT delivery_note FROM reception WHERE Lot_number = :lot"),
                {"lot": int(lot_number)}
            ).scalar()            
                # reference barcode
            buf_lot = BytesIO()
            Code128(str(serached_ref), writer=ImageWriter()).write(buf_lot)
            buf_lot.seek(0)
            ref_img = Image.open(buf_lot).convert("RGB")
            ref_img.load()


            ## if QI QTY is 100percont of total QTY
            if total_quantity == int(ok_qty):
                con.execute(
                    text("UPDATE reception SET Ok_qty = :qty WHERE Lot_number = :lot"),
                    {"qty": int(ok_qty), "lot": int(lot_number)}
                    )
                con.execute(
                    text("UPDATE reception SET QI_time = :qit WHERE Lot_number = :lot"),
                    {"qit": dt.datetime.now(), "lot": int(lot_number)}
                    )               
                st.success("QI Updated on the same lot")

            elif (total_quantity)*-1 == int(ok_qty):
                con.execute(
                    text("UPDATE reception SET Ok_qty = 0, Quantity = :qty WHERE Lot_number = :lot"),
                    {"qty": int(total_quantity), "lot": int(lot_number)}
                    )
                con.execute(
                    text("UPDATE reception SET QI_time = :qit WHERE Lot_number = :lot"),
                    {"qit": dt.datetime.now(), "lot": int(lot_number)}
                    )        

                st.success("QI Updated on the same lot")




            else: 
                #### Creation of 2 different lots
                # put 0 on previous lot
                con.execute(
                    text("UPDATE reception SET Quantity = 0,QI_time = :qit, Ok_qty = 0, Status = :rem WHERE Lot_number = :lot"),
                    {"lot": int(lot_number), "rem":"New lots created", "qit": dt.datetime.now()}) 
                
                # creating new lot for compliant qty
                con.execute(
                    text("INSERT INTO reception  (Reference, Quantity, Ok_qty, Status, delivery_note,QI_time) VALUES (:ref, :qty, :oqty, :rem, :dev, :qit)"),
                    {"ref": serached_ref,"qty":int(ok_qty),"oqty":int(ok_qty), "rem":f"Ok_qty of {lot_number}","dev": serached_dev, "qit": dt.datetime.now()}) 
                ok_lot = con.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                st.session_state["changed_lots"].append(ok_lot)



                # compliant lot barcode
                buf_lot = BytesIO()
                Code128(str(ok_lot), writer=ImageWriter()).write(buf_lot)
                buf_lot.seek(0)
                lot_img = Image.open(buf_lot).convert("RGB")
                lot_img.load()

                total_width = max(ref_img.width , lot_img.width)
                max_height = ref_img.height + lot_img.height

                combined = Image.new("RGB", (total_width, max_height), "white")
                combined.paste(ref_img, (0, 0))
                combined.paste(lot_img, (0, ref_img.height))

                combined_file = BytesIO()
                combined.save(combined_file, format="PNG")
                combined_file_bytes = combined_file.getvalue()
                st.session_state["ok_barcode"] = combined_file_bytes
                st.session_state["ok_filename"] = f"barcode_{ok_lot}_{serached_ref}.png"





                # creating lot for non_compliant qty
                con.execute(
                    text("INSERT INTO reception  (Reference, Quantity, Status, Ok_qty, delivery_note, Emplacement,QI_time ) VALUES (:ref, :qty, :rem, :oqty, :dev, :emp , :qit)"),
                    {"ref": serached_ref,"qty":(int(total_quantity) - int(ok_qty)), "rem":f"NoK_qty of {lot_number}","oqty": 0,"dev": serached_dev,"emp":"Prison","qit": dt.datetime.now()})
                st.success("Prison lot & confirmed lot created")

                # NOK lot barcode
                Nok_lot = con.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                st.session_state["changed_lots"].append(Nok_lot)


                N_buf_lot = BytesIO()
                Code128(str(Nok_lot), writer=ImageWriter()).write( N_buf_lot)
                N_buf_lot.seek(0)
                N_lot_img = Image.open(N_buf_lot).convert("RGB")
                N_lot_img.load()

                total_width = max(ref_img.width , N_lot_img.width)
                max_height = ref_img.height + N_lot_img.height

                combined = Image.new("RGB", (total_width, max_height), "white")
                combined.paste(ref_img, (0, 0))
                combined.paste(N_lot_img, (0, ref_img.height))


                combined_file = BytesIO()
                combined.save(combined_file, format="PNG")
                combined_file_bytes2 = combined_file.getvalue()
                st.session_state["nok_barcode"] = combined_file_bytes2
                st.session_state["nok_filename"] = f"barcode_{Nok_lot}_{serached_ref}.png"
    else: st.warning("No lot")   


if "ok_barcode" in st.session_state:
    st.image(st.session_state["ok_barcode"], caption="Compliant pcs Barcode")
    st.download_button(
        "📥 Download OK lot Barcode",
        data=st.session_state["ok_barcode"],
        file_name=st.session_state["ok_filename"],
        mime="image/png",
        key="dl_ok_keep"
    )



if "nok_barcode" in st.session_state:
    st.image(st.session_state["nok_barcode"], caption="NON-compliant pcs Barcode")
    st.download_button(
        "📥 Download NoK lot Barcode",
        data=st.session_state["nok_barcode"],
        file_name=st.session_state["nok_filename"],
        mime="image/png",
        key="dl_nok_keep"
    )





### Rollback Button
with st.expander("Inspected lot roll back", expanded=False):

    col1, col2, col3 = st.columns([1,1,1])

    with col1:
        ol = st.number_input("Original Lot", step=1, format="%d")

    with col2:
        oq = st.number_input("Original Quantity", step=1, format="%d")

    with col3:
        st.write("") 
        if st.button("QI Input cancel", use_container_width=True):

            if ol == 0 or oq == 0:
                st.error("⚠️ Original Lot 과 Quantity 를 입력하세요.")
            else:
                with engine.begin() as cancel_con:
                    # 기존 LOT 원복
                    cancel_con.execute(
                        text("""
                            UPDATE reception
                            SET Quantity = :qty,
                                Status = '',
                                Ok_qty = 0
                            WHERE Lot_number = :lot
                        """),
                        {"qty": int(oq), "lot": int(ol)})
                st.success("✅ Rollback completed successfully")


with st.expander("🗑️ Delete specific lot", expanded=False):

    col1, col2 = st.columns([2,1])

    with col1:
        ld = st.number_input("Lot to delete", step=1, format="%d")

    with col2:
        st.write("")   # 버튼 정렬용 (한 줄 맞추기)
        if st.button("🗑️ Delete Lot", use_container_width=True):

            if ld == 0:
                st.error("⚠️ Lot number is required")
            else:
                try:
                    with engine.begin() as cancel_con:
                        cancel_con.execute(
                            text("""
                                DELETE FROM reception
                                WHERE Lot_number = :lot
                            """),
                            {"lot": int(ld)}
                        )

                    st.success(f"✅ Lot {int(ld)} deleted successfully")

                except Exception as e:
                    st.error(f"❌ Delete failed: {e}")

df = pd.read_sql("SELECT * FROM reception", con=engine)
new_rows = df[df["OP_lot"].isin(st.session_state["changed_lots"])]

st.subheader("Inspected lots")
st.dataframe(new_rows)

    
