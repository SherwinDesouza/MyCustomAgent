from dotenv import load_dotenv
import requests
import os
from google import genai
from google.genai import types
load_dotenv()
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def gemini_vision(youtube_url:str,user_query:str) -> str:
    response = gemini_client.models.generate_content(
    model='models/gemini-2.5-flash',
    contents=types.Content(
        parts=[
            types.Part(
                file_data=types.FileData(file_uri=youtube_url)
            ),
            types.Part(text=user_query)
        ]
    )
)
    return response.text

print(gemini_vision("https://www.youtube.com/watch?v=L1vXCYZAYYM","In the video, what is the highest number of bird species to be on camera simultaneously?"))