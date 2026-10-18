# !!!!!!!
# NEEDS CONVERTED TO NICEGUI
# Once implemented, need to update __init__.py, src/components/layout.py, and app.py
# !!!!!!!


from nicegui import ui, run
import requests
import os
import dotenv
from src.components.Layout import frame
from src.components.Colors import (
    PrimaryDarkHex,
    PrimaryLightHex,
    SecondaryDarkHex,
    SecondaryLightHex,
    SecondaryYellowHex,
)

dotenv.load_dotenv()




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

#Change both values if you modify max, was having compiler issues with unitialized array -Brendan
previous_messages = [None] * 10
max = 10
current = 0

def generate_payload(text):
    global previous_messages, max, current
    if (max == None or current == None):
        max = 10
        current = 0
        previous_messages[0] = text
    else: 
        print(previous_messages, max, current, type(max), type(current))
        previous_messages[current] = text
        current = (current + 1) % max

    append_str = "\n**Context from previous messages:**\n"
    for i,v in enumerate(previous_messages):
        append_str += f"{i+1}. {v}\n"

    text = text + append_str
    payload = {
        "model": model,
        "input": text,
        "max_output_tokens": 2048,
        "store": False
    }

    print(text)
    return payload


def init():
    @ui.page('/chat')
    def chat_page():
        frame()
        ui.label("Chat").classes("text-4xl font-bold")

        chat_area = ui.column().classes('w-full max-w-3xl mx-auto flex-grow items stretch')
        
        async def send_message():
            prompt = text_input.value
            text_input.value = ''

            with chat_area:
                ui.chat_message(prompt,name='you',sent=True)

            try:
                response = await run.io_bound(
                    requests.post,
                    url,
                    headers=headers,
                    json=generate_payload(prompt),
                    timeout=300
                )
                response.raise_for_status()
                response_json = response.json()

                if "error" in response_json:
                    # Error on Rocky's end 
                    ui.notify(f"An error occurred when generate a response:\n\n{response_json.error['message']}")
                else:
                    output_text = response_json["output_text"]
                    with chat_area:
                        ui.chat_message(output_text, name='Rocky', sent=False)

            except requests.exceptions.RequestException:
                ui.notify("Connection Error")

        with ui.footer():
            text_input = ui.input(placeholder='Ask a question...').classes('w-full max-w-3xl mx-auto').on('keydown.enter', send_message)
            with text_input.add_slot('append'):
                ui.button(icon='send', on_click=send_message).props('flat')