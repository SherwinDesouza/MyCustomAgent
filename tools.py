# tools.py
from langchain_core.tools import tool
import json
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv
import requests
import os
import google.genai as genai
from google.genai import types
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
RAPID_API_KEY = os.getenv("RAPID_API_KEY")
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


@tool
def calculator(a: float, b: float) -> float:
    """Add two numbers."""
    #print(f"Adding {a} and {b}")
    return a + b

# Python executor (safe)
def execute_python(code: str):
    """Execute Python code (including statements, classes, functions)."""
    import io
    import sys
    try:
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured_output = io.StringIO()
        
        # Create a namespace for the code to run in
        namespace = {'__name__': '__main__'}  # Set __name__ to '__main__' so if __name__ blocks execute
        exec(code, namespace)
        
        # Get captured output
        output = captured_output.getvalue()
        sys.stdout = old_stdout
        
        # Return output if any, otherwise success message
        if output.strip():
            return output.strip()
        else:
            return "Code executed successfully (no output)"
    except Exception as e:
        sys.stdout = old_stdout if 'old_stdout' in locals() else sys.stdout
        return f"Error: {e}"

@tool
def python_tool(code: str):
    """Execute Python code. 
    
    IMPORTANT: 
    - Pass the Python code directly as a string. Do NOT try to read files inside the code parameter.
    - If you need to execute code from a file, first use list_attached_files() to get the file path, then read the file content and pass ONLY the code content (not file reading code).
    - For Windows file paths in code, use raw strings (r'C:\\path') or forward slashes ('C:/path').
    - The code parameter should contain ONLY the Python code to execute, not file I/O operations.
    
    Example: If you want to run code from a file, read the file first, then pass just the code content.
    """
    answer = execute_python(code)
    return answer


@tool
def convert_audio_to_text(audio_file: str) -> str:
    """Transcribe an audio file to text. 
    
    IMPORTANT: This tool requires the FULL ABSOLUTE PATH to the audio file. 
    If you only have a filename (like "Strawberrypie.mp3"), you MUST first call 
    list_attached_files() to get the complete file path, then use that path here.
    
    Args:
        audio_file: The absolute path to the audio file (e.g., "C:\\Users\\...\\Files\\Strawberrypie.mp3")
    
    Returns:
        The transcribed text from the audio file, or an error message if the file is not found.
    """
    try:
        filename = audio_file
        print(f"Attempting to transcribe: {filename}")
        
        # Check if file exists first
        if not os.path.exists(filename):
            available_files = list_attached_files()
            return f"ERROR: File not found at path '{filename}'. The file does not exist at this location. Please use list_attached_files() first to get the correct absolute path. Available files: {available_files}"
        
        with open(filename, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=file, # Required audio file
                model="whisper-large-v3-turbo", # Required model to use for transcription
                prompt="Specify context or spelling",  # Optional
                response_format="verbose_json",  # Optional
                language="en",  # Optional
                temperature=0.0  # Optional
            )
        return transcription.text
    except FileNotFoundError as e:
        available_files = list_attached_files()
        return f"ERROR: FileNotFoundError - The file '{audio_file}' was not found. This usually means you need to use list_attached_files() first to get the correct absolute path. Available files: {available_files}"
    except Exception as e:
        return f"ERROR: An error occurred while transcribing the audio file '{audio_file}': {str(e)}. Please check the file path and try again, or use list_attached_files() to see available files."
    
@tool
def list_attached_files() -> list[str]:
    """List all files in the Files folder. 
    
    ALWAYS call this tool FIRST when the user mentions they have attached a file, 
    uploaded a file, provided a file, or refers to files they want you to process.
    This will return a list of all available file paths (absolute paths) in the Files directory.
    
    After getting the file list, you can match the filename the user mentioned with 
    the actual absolute path from this list, then use that path with other tools like 
    convert_audio_to_text() or read_python_file().
    
    Returns:
        A list of absolute file paths (strings) of all files in the Files directory.
    """
    try:
        files_folder = Path(r"C:\Users\PAX\My Conversational Bot\Files")
        print(f"Scanning folder: {files_folder}")
        
        # Get all files in the Files folder
        file_paths = []
        if files_folder.exists():
            for file_path in files_folder.iterdir():
                if file_path.is_file():
                    # Return absolute path
                    file_paths.append(str(file_path.absolute()))
        
        if not file_paths:
            return "No files found in the Files directory."
        
        return file_paths
    except Exception as e:
        return f"ERROR: Failed to list files: {str(e)}"

@tool
def read_python_file(file_path: str) -> str:
    """Read the contents of a Python file.
    
    Use this tool to read Python code from a file before executing it with python_tool.
    This avoids path escaping issues when passing file paths in code strings.
    
    Args:
        file_path: The absolute path to the Python file (get this from list_attached_files())
    
    Returns:
        The contents of the Python file as a string, or an error message if the file cannot be read.
    """
    try:
        if not os.path.exists(file_path):
            available_files = list_attached_files()
            return f"ERROR: File not found at '{file_path}'. Available files: {available_files}"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return content
    except Exception as e:
        return f"ERROR: Failed to read file '{file_path}': {str(e)}"

@tool
def SpeechToText(url: str) -> str:
    """Trancribe the input URL
    Args: 
    url: could be a youtube, facebook or tiktok URL

    Returns:
    transcription: transcription of the input video in string format

    IMPORTANT: DO NOT CALL THIS TOOL IF USER IS INTERESTED IN THE VISION ANALYSIS. THIS IS ONLY FOR SPEECH RELATED TASKS
    
    """
    endpoint = "https://speech-to-text-ai.p.rapidapi.com/transcribe"
    querystring = {"url":url,"lang":"en","task":"transcribe"}
    headers = {
	"x-rapidapi-key": RAPID_API_KEY,
	"x-rapidapi-host": "speech-to-text-ai.p.rapidapi.com"
    }
    response = requests.get(endpoint, headers=headers, params=querystring).json()
    return response['text']

@tool 
def gemini_vision(youtube_url:str,user_query:str) -> str:
    """
    Explain the youtube video
    Args:
    youtube_url: the youtube_url provided by the user
    user_query: the question asked by the user

    IMPORTANT: ALWAYS CALL THIS TOOL FOR VISION RELATED TASKS
    returns:
    response: generate by the gemini model in form of string
    """
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

@tool
def reverse_string(text:str) -> str:
    """
    Tool to reverse a string

    Args:
    text: A string that needs to be reversed

    returns: the reversed text
    """
    return text[::-1]
TOOLS = [calculator, python_tool, convert_audio_to_text, list_attached_files, read_python_file, SpeechToText, gemini_vision,reverse_string]

