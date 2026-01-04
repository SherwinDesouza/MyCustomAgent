from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv
load_dotenv()
client = ChatGroq(
    model="qwen/qwen3-32b",
    api_key=os.getenv("GROQ_API_KEY"),)

def summarize_text(text, query=None):
    """
    Summaries text using Qwen2.5-0.5B with a query-aware compression.
    """
    prompt = f"""
You are a fast, concise summarizer.
Your job: compress the webpage text while keeping only the information 
relevant to this user query: "{query or 'N/A'}".

Rules:
- Remove menus, ads, headers, unrelated links.
- Keep all **facts, statistics, dates, percentages, prices, quantities, and any numerical data**. 
- Keep meaningful content and key points.
- Do NOT invent or add new information.
- Output a short, clean summary that **never drops numbers**. 
- You may paraphrase text, but all numerical information must remain accurate.

TEXT TO SUMMARIZE:
{text}
"""

    

    response = client.invoke(prompt)
    return response