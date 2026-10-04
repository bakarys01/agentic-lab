"""Generate a short conversation label after the first completed answer."""

import os

from openai import OpenAI
from pydantic import BaseModel

from agents.config_loader import load_model_config
from prompts.loader import load_prompt


class TitleResult(BaseModel):
    title: str


def generate_title(question: str, answer: str) -> str:
    settings = load_model_config("title")
    if settings["provider"] != "openai":
        raise ValueError("The title model must use OpenAI.")
    api_key = os.getenv(settings["api_key_env"])
    if not api_key:
        raise ValueError("The title model credential is missing.")

    client = OpenAI(api_key=api_key, timeout=8.0, max_retries=0)
    response = client.responses.parse(
        model=settings["model_id"],
        instructions=load_prompt("title"),
        input=f"User question:\n{question[:1000]}\n\nAssistant answer:\n{answer[:1000]}",
        text_format=TitleResult,
        max_output_tokens=80,
        store=False,
    )
    if response.output_parsed is None:
        raise ValueError("The title model returned no title.")
    title = " ".join(response.output_parsed.title.split())
    if not title or len(title) > 80:
        raise ValueError("The title model returned an invalid title.")
    return title
