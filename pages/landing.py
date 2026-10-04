import streamlit as st
from src.components.Colors import PrimaryDarkHex, PrimaryLightHex

# Initial landing page the outlines our project
def main():
    st.title(f"Welcome to :color[Gaffer]{{foreground={PrimaryLightHex}}}")
    st.header(f"The :color[Team Charlie]{{foreground={PrimaryDarkHex}}} SWE project!")

    st.markdown('''
    Hello!\n
    We are creating an awesome app that takes data from previous soccer matches and uses it to predict future match outcomes to optimize for a win in the next game! The user and primary stakeholder is the Kent State women’s soccer coach Rob Marinaro. \n
    The project aims to support team and strategy management. The software will help the coach plan the team lineup for the next game and see historical data between the games that were previously played. If a player is sick or has scheduling conflicts, the coach will be able to adjust the lineup based on these conditions. \n
    Rob Marinaro will be able to input future game conditions and who the opposing team will be. There are also opportunities to input player schedules to filter what players and team compositions will be recommended. There will also be some capabilities to ask an AI assistant questions about player schedules, player statistics, and to make recommendations based on these statistics. He will also be able to set constraints and the application will generate possible lineups to use based on which is the most optimal. \n
    This project will use the NCAA API to pull historical data from previous soccer matches. It will also use data from kentstatesports.com. The project will be created with Streamlit using SQLite as the database. The backend will make requests to the Rocky API and use LangChain to allow the LLM to deterministically pull data and run an XGBoost model to make the best predictions and reconmmendations. \n
    Thank you!
    ''')

if __name__ == "__main__":
    main()
