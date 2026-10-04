import streamlit as st

@st.dialog("Settings")
def settings_modal():
    st.write("Profile")
    st.write("Account")
    st.write("Notifications")

    if st.button("Close"):
        st.rerun()


def settings_button():
    if st.sidebar.button("Settings", icon=":material/settings:"):
        settings_modal()