import os

from agents.config_loader import load_model_config


def create_model(name: str, runtime: str):
    settings = load_model_config(name)
    provider = settings["provider"]

    supported = {
        ("smolagents", "openai"),
        ("langchain", "openai"),
        ("langchain", "huggingface"),
    }

    if (runtime, provider) not in supported:
        raise ValueError(
            f"Unsupported model combination: {runtime}/{provider}"
        )

    variable = settings["api_key_env"]
    api_key = os.getenv(variable)

    if not api_key or not api_key.strip():
        raise ValueError(
            f"Missing environment variable: {variable}"
        )

    if runtime == "smolagents":
        from smolagents import OpenAIServerModel

        return OpenAIServerModel(
            model_id=settings["model_id"],
            api_key=api_key,
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=settings["model_id"], api_key=api_key, temperature=0)

    from langchain_huggingface import (
        ChatHuggingFace,
        HuggingFaceEndpoint,
    )

    endpoint = HuggingFaceEndpoint(
        repo_id=settings["model_id"],
        task="text-generation",
        huggingfacehub_api_token=api_key,
        max_new_tokens=1024,
        temperature=0.1,
    )

    return ChatHuggingFace(llm=endpoint)
