import streamlit as st

# Pages for navbar directory
# Note that within the current structure, the first page listed
# will always be executed first.
#
# Format: "Category Title": 
# [st.Page("pages/[insert file name"), title="[insert title]"]
pages = {
    "Home": [
    st.Page("pages/landing.py", title="Welcome")
    ],

    "Pages": [ # placeholder name, will be changed when we wireframe
    st.Page("pages/calendar.py", title="Calendar")
    ]
}

# Navigates to pages in /pages/ as outlined in pages global
def main():
    global pages

    pg = st.navigation(pages)
    pg.run()

if __name__ == "__main__":
    main()
