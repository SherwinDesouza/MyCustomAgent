from langchain_core.tools import tool
import json
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv
import requests
import os
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
from ddgs import DDGS


def test_search(user_query:str) -> str:
    results = DDGS().text(user_query, max_results=4,region="us-en")
    truncated = []
    for item in results:
        body = item.get("body", "")
        words = body.split()
        short_body = " ".join(words[:20])

        # build new dict
        truncated.append({
            "title": item.get("title"),
            "href": item.get("href"),
            "body": short_body
        })
    return truncated

answer = test_search("What is the first name of the only Malko Competition recipient from the 20th Century (after 1977) whose nationality on record is a country that no longer exists?")
print(answer)