import os

import dotenv
import requests
from nicegui import run, ui
from datetime import date

from src.components.Colors import (
    PrimaryDarkHex,
    PrimaryLightHex,
    SecondaryDarkHex,
    SecondaryLightHex,
)
from src.components.Layout import frame, page_body, page_header
from src.services.game_details import get_games

dotenv.load_dotenv()

BASE_URL = "https://rocky.cs.kent.edu/v1"

ROCKY_API_KEY = os.environ.get("ROCKY_API_KEY", "")

# True if the user has a rocky API key
HAS_KEY = ROCKY_API_KEY != ""

HEADERS = {"Authorization": f"Bearer {ROCKY_API_KEY}"}


# Giving rocky basic context
def get_context(limit=10):

    games = get_games(games=limit)
    message = "Refer to me as Dr. Gaffer.\n"

    print("RUN!")
    for g in games:

        # Handles the date part
        message += f"We played a game on "
        if g["date"]:
            day = g["date"].day
            month = g["date"].month
            year = g["date"].year
            message += f"{month}/{day}/{year}."
        else:
            message += "an unknown date."

        message += "\n"

    print(f"MESSAGE:::::{message}")

    return message


context_test = get_context()

# ---------- Rocky API ----------

_model = None


def get_model() -> str:
    global _model
    if _model is None:
        r = requests.get(f"{BASE_URL}/models", headers=HEADERS, timeout=30)
        r.raise_for_status()
        _model = r.json()["data"][0]["id"]
    return _model


def extract_text(data: dict) -> str:
    if data.get("output_text"):
        return data["output_text"]
    parts = []
    for item in data.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    parts.append(c.get("text", ""))
    return "".join(parts)


def ask_rocky(history: list[dict]) -> str:
    payload = {
        "model": get_model(),
        "instructions": get_context(),
        "input": history,
        "max_output_tokens": 2048,
        "store": False,
    }
    r = requests.post(
        f"{BASE_URL}/responses", headers=HEADERS, json=payload, timeout=300
    )
    try:
        data = r.json()
    except ValueError:
        r.raise_for_status()
        raise RuntimeError("Rocky returned an invalid response.")
    err = data.get("error")
    if err or not r.ok:
        msg = err.get("message") if isinstance(err, dict) else err
        raise RuntimeError(msg or f"HTTP {r.status_code}")
    return extract_text(data) or "(empty response)"


# ---------- UI pieces ----------


def user_bubble(text: str):
    with ui.row().classes("w-full justify-end"):
        ui.label(text).classes(
            "bubble-me px-4 py-3 text-[15px] leading-relaxed max-w-[75%]"
        ).style("white-space:pre-wrap")


def bot_row():
    with ui.row().classes("w-full gap-3 no-wrap items-start"):
        with (
            ui.element("div")
            .classes("w-8 h-8 shrink-0 rounded-lg flex items-center justify-center")
            .style(f"background:{PrimaryLightHex}")
        ):
            ui.icon("smart_toy").style(f"color:{SecondaryDarkHex}; font-size:20px")
        col = ui.column().classes("gap-1 max-w-[80%]")
        with col:
            ui.label("ROCKY").classes("font-mono-label").style(
                f"color:{SecondaryLightHex}"
            )
    return col


def bot_bubble(text: str):
    with bot_row():
        with ui.element("div").classes(
            "bubble-bot px-4 py-3 text-[15px] leading-relaxed"
        ):
            ui.markdown(text)


def thinking_row():
    with ui.row().classes("w-full") as row:
        with bot_row():
            with ui.element("div").classes("bubble-bot px-4 py-2"):
                ui.spinner("dots", size="28px").style(f"color:{PrimaryDarkHex}")
    return row


# ---------- Page ----------


def init():
    @ui.page("/chat")
    def chat_page():
        frame("chat")

        history: list[dict] = []
        busy = {"on": False}

        def scroll_down():
            ui.run_javascript(
                "window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'})"
            )

        def new_chat():
            history.clear()
            messages.clear()
            empty.set_visibility(True)

        async def send():
            prompt = (box.value or "").strip()
            if not prompt or busy["on"]:
                return
            busy["on"] = True
            send_btn.disable()
            box.value = ""
            empty.set_visibility(False)

            with messages:
                user_bubble(prompt)
                pending = thinking_row()
            history.append({"role": "user", "content": prompt})
            scroll_down()

            try:
                reply = await run.io_bound(ask_rocky, list(history))
            except requests.exceptions.RequestException:
                history.pop()
                ui.notify("Connection error.", type="negative")
            except RuntimeError as e:
                history.pop()
                ui.notify(f"Rocky returned an error: {e}", type="negative")
            else:
                history.append({"role": "assistant", "content": reply})
                with messages:
                    bot_bubble(reply)
            finally:
                pending.delete()
                busy["on"] = False
                send_btn.enable()
                scroll_down()

        with page_body():
            with ui.row().classes("w-full items-end justify-between no-wrap"):
                page_header(
                    "Chat",
                    "Ask about schedules, stats and recommendations.",
                )
                ui.button("New chat", icon="add_comment", on_click=new_chat).props(
                    "outline no-caps"
                ).style(f"color:{PrimaryDarkHex}; border-radius:10px; font-weight:600")

            with ui.column().classes("card w-full gap-0").style("min-height:540px"):
                # Empty state
                with ui.column().classes(
                    "w-full flex-grow items-center justify-center gap-3 p-10"
                ) as empty:
                    with (
                        ui.element("div")
                        .classes(
                            "w-12 h-12 rounded-xl flex items-center justify-center"
                        )
                        .style(f"background:{PrimaryLightHex}")
                    ):
                        ui.icon("smart_toy").style(
                            f"color:{SecondaryDarkHex}; font-size:28px"
                        )
                    ui.label("Ask Rocky about your team").classes(
                        "chat-heading font-display text-xl font-bold"
                    ).style(f"color:{SecondaryDarkHex}")
                    ui.label(
                        "Player schedules, match statistics and lineup recommendations."
                    ).classes("chat-description text-sm").style("color:#55607A")

                # Messages
                messages = ui.column().classes("w-full gap-5 p-6")

                with (
                    ui.column()
                    .classes("chat-composer w-full gap-1 px-4 pt-3 pb-2")
                    .style(
                        "position:sticky; bottom:0; background:#fff; border-top:1px solid #E3E6EC;"
                        "border-radius:0 0 14px 14px; margin-top:auto"
                    )
                ):
                    with ui.row().classes(
                        "composer-box w-full items-center gap-2 no-wrap pl-4 pr-2 py-1"
                    ):
                        box = (
                            ui.input(placeholder="Ask a question...")
                            .props("borderless dense")
                            .classes("chat-input flex-grow text-[15px]")
                        )
                        box.on("keydown.enter", lambda: send())
                        send_btn = (
                            ui.button(icon="arrow_upward", on_click=lambda: send())
                            .props("unelevated round dense")
                            .style(
                                f"background:{PrimaryLightHex} !important; color:{SecondaryDarkHex}"
                            )
                        )

                        # If the user doesn't have an API key it disables the button and the typing box
                        if not HAS_KEY:
                            send_btn.disable()
                            box.disable()

                            # Tooltip when you hover over send without a rocky API key
                            with send_btn:
                                ui.tooltip("No Rocky API key in the .env file")

                    ui.label("Rocky can make mistakes.").classes(
                        "text-xs self-center"
                    ).style("color:#7A849A")
