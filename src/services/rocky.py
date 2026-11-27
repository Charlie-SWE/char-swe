import time

import requests
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, trim_messages
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from src.components.Env import ROCKY_API_KEY
from src.services.game_details import get_games

BASE_URL = "https://rocky.cs.kent.edu/v1"

# True if the user has a rocky API key
HAS_KEY = ROCKY_API_KEY != ""

HEADERS = {"Authorization": f"Bearer {ROCKY_API_KEY}"}

# Max reply tokens 
MAX_OUTPUT_TOKENS = 2048

# Token budget
HISTORY_TOKEN_BUDGET = 6000

# Buffer zone to re-use context before refetching
CONTEXT_TTL = 60 * 60 * 4

# Giving rocky basic context
def build_context(limit=10):
    games = get_games(games=limit)
    message = f"We are Kent State University. Our {limit} most recent games are:\n"

    for g in games:

        # Builds the message
        message += f"We played "

        # Home or away
        if g["home"]:
            message += "a home "
        else:
            message += "an away "
        message += "game on "

        # Handles the date part
        if g["date"]:
            day = g["date"].day
            month = g["date"].month
            year = g["date"].year
            message += f"{month}/{day}/{year}."
        else:
            message += "an unknown date."

        # Gets the score
        our_score, their_score = g["score"]
        if not g["home"]:
            # If not home, it flips the order
            our_score = g["score"][1]
            their_score = g["score"][0]

        # Win lose or draw
        message += " We"
        if our_score > their_score:
            message += " won"
        elif our_score < their_score:
            message += " lost"
        else:
            message += " drew"

        # Who we played against
        message += " against"
        if g["opponent"]:
            message += f" {g["opponent"]}."
        else:
            message += " an unknown team."

        # Score
        message += f" Us {our_score} to their {their_score}."

        message += "\n"

    return message


# Game data is the same for every user, so it is shared and cached
_context = {"text": None, "fetched_at": 0.0}


def get_context():
    now = time.monotonic()
    if _context["text"] is None or now - _context["fetched_at"] > CONTEXT_TTL:
        _context["text"] = build_context()
        _context["fetched_at"] = now
    return _context["text"]


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
        ("system", "{context}"),
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


def ask_rocky(prompt: str, history: list[dict]):
    chain = PROMPT | get_llm()
    reply = chain.invoke(
        {
            "context": get_context(),
            "history": trim_history(to_messages(history)),
            "prompt": prompt,
        }
    )
    return reply.text or "(empty response)"
