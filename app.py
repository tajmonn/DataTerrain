import streamlit as st

pg = st.navigation(
    [
        st.Page("test.py", title="Tester for testing code"),
    ]
)
pg.run()
