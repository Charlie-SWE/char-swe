import streamlit as st

from src.components.Colors import (
    PrimaryDarkHex,
    PrimaryLightHex,
    SecondaryDarkHex,
    SecondaryLightHex,
    SecondaryYellowHex,
)

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
        # Create and display messages for both prompt and response
        mess_prompt = Message(prompt, "user")
        mess_prompt.display()

        mess_response = Message(f"Echoed: {prompt}", "ai")
        mess_response.display()

        # Record the prompt and response
        st.session_state.history.append(mess_prompt)
        st.session_state.history.append(mess_response)



    


if __name__ == "__main__":
    main()