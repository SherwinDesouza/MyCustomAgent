import os 
from groq import Groq
from dotenv import load_dotenv
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def convert_audio_to_text(audio_file: str) -> str:
    """Use this tool whenever there is an audio file provided by the user."""
    filename = audio_file
    with open(filename, "rb") as file:
        transcription = client.audio.transcriptions.create(
        file=file, # Required audio file
        model="whisper-large-v3-turbo", # Required model to use for transcription
        prompt="Specify context or spelling",  # Optional
        response_format="verbose_json",  # Optional
        language="en",  # Optional
        temperature=0.0  # Optional
        )
    # To print only the transcription text, you'd use print(transcription.text) (here we're printing the entire transcription object to access timestamps)
    return transcription.text

if __name__ == "__main__":
    convert_audio_to_text(r"C:\Users\PAX\My Conversational Bot\Files\GroceryList.mp3")