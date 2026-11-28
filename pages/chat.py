import openai
import requests
from nicegui import ui, app

from src.components.Colors import (
    PrimaryDarkHex,
    PrimaryLightHex,
    SecondaryDarkHex,
    SecondaryLightHex,
)
from src.components.Layout import frame, page_body, page_header
from src.components.Auth import create_session, log_message, fetch_session_names, fetch_messages_from_session, delete_session
from src.services.rocky import HAS_KEY, ask_rocky


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


def tool_used_row(name: str):
    with ui.row().classes("tool-used items-center gap-1 no-wrap"):
        ui.icon("code").classes("tool-used-icon")
        ui.label("Used LangChain tool")
        ui.label(name).classes("tool-used-name")


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

        # Don't create a session until a message is sent.
        session_id = None

        def scroll_down():
            ui.run_javascript(
                "window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'})"
            )

        def new_chat():
            history.clear()
            messages.clear()
            empty.set_visibility(True)
            nonlocal session_id
            session_id = None

        def on_delete_session(delete_session_id):
            delete_session(delete_session_id)
            new_chat()

        def populate_from_session(populate_session_id):
            new_chat()
            session_messages = fetch_messages_from_session(populate_session_id)
            for message in session_messages:
                with messages:
                    if (message[0] == "ai"):
                        bot_bubble(message[1])
                        history.append({"role": "assistant", "content": message[1]})
                    else:
                        user_bubble(message[1])
                        history.append({"role": "user", "content": message[1]})
                
            nonlocal session_id
            session_id = populate_session_id

        def refresh_session_list():
            session_list.clear()
            session_names = fetch_session_names()
            with session_list:
                for session in session_names:
                    with ui.element("div").style("flex: column") as session_button:
                        ui.button(f"Unnamed Session {session[0]}", 
                            on_click=lambda s = session: populate_from_session(s[0])
                            ).props("outline no-caps").style(
                            f"color:{PrimaryDarkHex}; border-radius:10px; font-weight:600")
                        ui.button("x",
                                    on_click=lambda s = session, e = session_button: (
                                        on_delete_session(s[0]),
                                        e.remove(e)
                                    )
                                    ).props("flat")

        async def send():
            prompt = (box.value or "").strip()
            if not prompt or busy["on"]:
                return
            busy["on"] = True
            send_btn.disable()
            box.value = ""
            empty.set_visibility(False)

            # Create our session if it doesn't exist.
            nonlocal session_id
            if session_id == None:
                session_id = create_session()
                refresh_session_list()

            with messages:
                user_bubble(prompt)
                # Tool lines go here, above Rocky's icon and reply
                tools_box = ui.column().classes("gap-1")
                tools_box.set_visibility(False)
                pending = thinking_row()
            scroll_down()

            # Remember which chat this reply belongs to, in case the user
            # switches chats while Rocky is answering.
            reply_session = session_id

            def show_tool(name):
                if session_id != reply_session:
                    return
                tools_box.set_visibility(True)
                with tools_box:
                    tool_used_row(name)
                scroll_down()

            try:
                # Pass a copy of the earlier turns; the new prompt is sent
                # separately so it isn't duplicated.
                reply = await ask_rocky(prompt, list(history), on_tool=show_tool)
            except (openai.APIConnectionError, requests.exceptions.RequestException):
                ui.notify("Connection error.", type="negative")
            except openai.APIStatusError as e:
                ui.notify(f"Rocky returned an error: {e.message}", type="negative")
            else:
                # Only save the turn once Rocky has answered, so the database
                # and the in-memory history always match.
                log_message(reply_session, prompt, "user")
                log_message(reply_session, reply, "ai")
                if session_id == reply_session:
                    history.append({"role": "user", "content": prompt})
                    history.append({"role": "assistant", "content": reply})
                    with messages:
                        bot_bubble(reply)
            finally:
                pending.delete()
                busy["on"] = False
                send_btn.enable()
                scroll_down()

        with page_body():
            with ui.row().classes("w-full"):
                # Session history
                with ui.column().style("overflow-y: auto") as session_list:
                    refresh_session_list()
                            
                # Chat interface
                with ui.column().style("flex: 1"):
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
