import streamlit as st

def main():

    # Builds left sidebar
    st.sidebar.write("Gaffer")
    st.sidebar.button("Home")
    st.sidebar.button("Statistics")
    st.sidebar.button("Matchups")

if __name__ == "__main__":
    main()
