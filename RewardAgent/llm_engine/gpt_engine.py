import requests
import json
import base64
import http.client
from openai import AzureOpenAI, OpenAI
import os 
from smolagents import Tool
from smolagents import CodeAgent,OpenAIServerModel
from dotenv import load_dotenv


def DeerapiEngine(api_key, model_id):
    """
    Create an OpenAIServerModel client for DeerAPI.
    api_key can be passed directly or will be read from env var 'IRA_API_KEY' (or legacy 'deerapi_key').
    """
    key = api_key or os.getenv("IRA_API_KEY") or os.getenv("deerapi_key")
    api_base = os.getenv("IRA_BASE_URL") or os.getenv("deerapi_base") or "https://api.cometapi.com/v1/"
    if not key:
        raise ValueError("Missing API key. Set IRA_API_KEY (or legacy deerapi_key) in environment or pass api_key.")
    return OpenAIServerModel(
            api_base=api_base,
            api_key=key,
            model_id=model_id
        )

if __name__ == "__main__":
    # Load environment variables and read DeerAPI key
    load_dotenv()
    api_key = os.getenv("IRA_API_KEY") or os.getenv("deerapi_key")

    model = DeerapiEngine(api_key, "gpt-5")
    agent = CodeAgent(
        model=model,
        tools=[],
        max_steps=5,
    )

    print(agent.run("Create a React component that shows 'Hello from SmolAgent!'"))
