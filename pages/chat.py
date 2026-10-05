import streamlit as st
import requests
import os
import dotenv

dotenv.load_dotenv()

from src.components.Colors import (
    PrimaryDarkHex,
    PrimaryLightHex,
    SecondaryDarkHex,
    SecondaryLightHex,
    SecondaryYellowHex,
)


url = "https://rocky.cs.kent.edu/v1/responses"
headers = {
    "Authorization": f"Bearer {os.environ['ROCKY_API_KEY']}"
}

models_response = requests.get(
    "https://rocky.cs.kent.edu/v1/models",
    headers=headers,
    timeout=30,
)
models_response.raise_for_status()
model = models_response.json()["data"][0]["id"]

def generate_payload(text):
    return {
        "model": model,
        "input": text,
        "max_output_tokens": 300,
        "store": False
    }
        

class Message:
    def __init__(self, text, type):
        self.text = text
        self.type = type

    # Display the message
    def display(self):
        st.chat_message(self.type).markdown(self.text)

def main():
    st.title("Chat")

    # Establish session history
    if "history" not in st.session_state:
        st.session_state.history = []

    # Show prior messages
    for message in st.session_state.history:
        message.display()

    prompt = st.chat_input("Ask a question.")

    if prompt != None:
        # Create and display messages for the user's prompt
        mess_prompt = Message(prompt, "user")
        mess_prompt.display()

        # Record the prompt
        st.session_state.history.append(mess_prompt)

        # Send request to rocky
        response = requests.post(url, headers=headers, json=generate_payload(prompt), timeout=300)
        response.raise_for_status()

        mess_response = Message(response.json()["output_text"], "ai")
        mess_response.display()

        
        st.session_state.history.append(mess_response)



    


if __name__ == "__main__":
    main()