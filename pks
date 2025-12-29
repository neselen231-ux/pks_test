import streamlit as st

st.title("PKS Reception")

# 입력란 2개
name = st.number_input("Reference number")
age = st.number_input("quantity", min_value=0, step=1)

# 버튼
if st.button("Input"):
    if name:
        st.success(f"REF : {name} & QTY : {age}")
    else:
        st.warning("Please input reference")
