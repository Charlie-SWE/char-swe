import pandas as pd
import streamlit as st

def pull_roster_data():
    # Placeholder data, to be replaced with DB retrieval
    return {
        "2026 JV": [
            {"Name": "Jane Doe", "Position": "Forward"},
            {"Name": "Jan Do", "Position": "Mid"},
        ]
    }


def main():
    roster_data = pull_roster_data()

    selected_roster = st.selectbox(
        "Select a roster",
        options=list(roster_data.keys()),
    )

    st.title(selected_roster)

    edited_roster = st.data_editor(
        pd.DataFrame(roster_data[selected_roster]),
        num_rows="dynamic",
        use_container_width=True,
        key=f"roster_{selected_roster}",
    )

if __name__ == "__main__":
    main()