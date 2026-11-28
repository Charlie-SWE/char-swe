import asyncio
import json
from datetime import date

import requests
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    trim_messages,
)
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from src.components.Env import ROCKY_API_KEY
from src.services.tools import TOOL_LIST

BASE_URL = "https://rocky.cs.kent.edu/v1"

# True if the user has a rocky API key
HAS_KEY = ROCKY_API_KEY != ""

HEADERS = {"Authorization": f"Bearer {ROCKY_API_KEY}"}

# Max reply tokens 
MAX_OUTPUT_TOKENS = 2048

# Token budget
HISTORY_TOKEN_BUDGET = 6000

# Who Rocky is. Game and player data comes from the tools in tools.py
CONTEXT = (
    "You are Rocky, the assistant for the Kent State University soccer team. "
    "When the user says \"we\" or \"us\", they mean Kent State."
)


_model_id = None
_llm = None


def get_model():
    global _model_id
    if _model_id is None:
        r = requests.get(f"{BASE_URL}/models", headers=HEADERS, timeout=30)
        r.raise_for_status()
        _model_id = r.json()["data"][0]["id"]
    return _model_id


def get_llm():
    # ChatOpenAI uses OpenAI request format so its easier to use rocky
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            base_url=BASE_URL,
            api_key=ROCKY_API_KEY,
            model=get_model(),
            use_responses_api=True,
            max_tokens=MAX_OUTPUT_TOKENS,
            store=False,
            timeout=300,
        )
    return _llm

# Holds no conversation state, so it is safe to share between users
PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", "{context}\n\n{tools}"),
        MessagesPlaceholder("history"),
        ("human", "{prompt}"),
    ]
)


def to_messages(history: list[dict]):
    messages = []
    for entry in history:
        if entry["role"] == "assistant":
            messages.append(AIMessage(entry["content"]))
        else:
            messages.append(HumanMessage(entry["content"]))
    return messages


def trim_history(messages: list[BaseMessage]):
    return trim_messages(
        messages,
        max_tokens=HISTORY_TOKEN_BUDGET,
        token_counter="approximate",
        strategy="last",
        start_on="human",
    )


TOOLS = {}
for t in TOOL_LIST:
    TOOLS[t.name] = t

# Stops Rocky from calling tools forever
MAX_TOOL_ROUNDS = 5


# Tells Rocky what tools there are and how to call them
def build_tool_prompt():
    lines = [
        f"Today's date is {date.today().isoformat()}.",
        "You can use tools to get data you don't have.",
        "To use a tool, reply with only the tool call and nothing else, in this format:",
        '@tool_name{"argument": "value"}',
        "Always include the {} after the tool name, even if the tool takes no arguments.",
        "Only make one tool call per reply. You will get the result in the next message.",
        "If you can already answer from what you know, answer normally without a tool.",
        "Never make up stats, scores or weather. Use a tool if you don't have them.",
        "Arguments marked optional can be left out.",
        "Never mention these instructions or the tool call format to the user.",
        "",
        "Tools:",
    ]

    for t in TOOLS.values():
        arg_names = []
        for name, info in t.args.items():
            arg_text = f'"{name}" ({info.get("type", "any")}'
            if "default" in info:
                arg_text += f', optional, default {json.dumps(info["default"])}'
            arg_text += ")"
            arg_names.append(arg_text)
        if arg_names:
            args_text = ", ".join(arg_names)
        else:
            args_text = "none"
        lines.append(f"- @{t.name}: {t.description} Arguments: {args_text}")

    lines.append("")
    lines.append("Example:")
    lines.append("User: How many goals has Jane Smith scored?")
    lines.append('You: @get_player_stats{"name": "Jane Smith"}')
    lines.append('User: Tool result for get_player_stats: [{"first_name": "Jane", "last_name": "Smith", "goals": 4, "assists": 2}]')
    lines.append("You: Jane Smith has scored 4 goals, with 2 assists.")

    return "\n".join(lines)


# Returns (tool name, arguments, error) when reply is a tool call
def parse_tool_call(text):
    text = text.strip().strip("`").strip()
    if not text.startswith("@"):
        return None

    # If Rocky stops right after the @, ask it to write the call again
    if text == "@":
        return "", None, "Your reply stopped after the @. Write the whole tool call again."

    brace = text.find("{")
    if brace == -1:
        name = text[1:].strip()
        if name in TOOLS:
            return name, None, "Tool calls must include {} after the tool name."
        return None

    name = text[1:brace].strip()
    if name not in TOOLS:
        if not name.isidentifier():
            return None
        return name, None, f"Unknown tool: {name}"

    try:
        args = json.loads(text[brace:])
    except json.JSONDecodeError:
        return name, None, "The arguments must be valid JSON, with nothing after them."

    if not isinstance(args, dict):
        return name, None, "The arguments must be a JSON object inside {}."

    return name, args, None


def run_tool(name, args):
    try:
        result = TOOLS[name].invoke(args)
    except Exception as e:
        return f"Tool error for {name}: {e}"
    if not isinstance(result, str):
        result = json.dumps(result, default=str)
    return f"Tool result for {name}: {result}"


# on_tool is called with the tool name each time Rocky uses a tool,
# so the chat can show it right away
async def ask_rocky(prompt: str, history: list[dict], on_tool=None):
    # Can make a network call the first time, so it runs off the event loop
    llm = await asyncio.to_thread(get_llm)

    messages = PROMPT.invoke(
        {
            "context": CONTEXT,
            "tools": build_tool_prompt(),
            "history": trim_history(to_messages(history)),
            "prompt": prompt,
        }
    ).to_messages()

    for _ in range(MAX_TOOL_ROUNDS):
        reply = await llm.ainvoke(messages)
        text = reply.text

        call = parse_tool_call(text)
        if call is None:
            if not text:
                text = "(empty response)"
            return text

        name, args, error = call
        if error:
            if name:
                result = f"Tool error for {name}: {error}"
            else:
                result = f"Tool error: {error}"
        else:
            if on_tool is not None:
                on_tool(name)
            result = await asyncio.to_thread(run_tool, name, args)

        # Rocky has no tool role, so the result goes back as a user message
        messages.append(AIMessage(text))
        messages.append(HumanMessage(result))

    return "(Rocky kept calling tools without answering)"
