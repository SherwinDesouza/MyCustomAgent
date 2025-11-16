import requests
import os
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("RAPID_API_KEY")


def SpeechToText(url: str) -> str:
    endpoint = "https://speech-to-text-ai.p.rapidapi.com/transcribe"
    querystring = {"url":url,"lang":"en","task":"transcribe"}
    headers = {
	"x-rapidapi-key": api_key,
	"x-rapidapi-host": "speech-to-text-ai.p.rapidapi.com"
    }
    response = requests.get(endpoint, headers=headers, params=querystring).json()
    return response['text']

# SpeechToText("https://www.youtube.com/watch?v=1htKBjuUWec")