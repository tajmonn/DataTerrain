import streamlit as st

pg = st.navigation(
    [
        st.Page("test.py", title="Tester for testing code"),
        st.Page("map-uploader.py", title="Upload the map"),
        st.Page("ai-test.py", title="Test the AI"),
    ]
)
pg.run()
