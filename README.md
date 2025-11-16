# My Conversational Bot

A conversational AI agent built with LangGraph and Groq that can:
- Convert audio files to text
- Process YouTube videos (transcription and vision analysis)
- Execute Python code
- Perform calculations
- Answer questions using various tools

## Features

- **Audio Transcription**: Convert audio files to text using Groq's Whisper model
- **YouTube Video Processing**: 
  - Speech-to-text transcription for YouTube, TikTok, and Facebook videos
  - Vision analysis for YouTube videos using Gemini
- **Python Code Execution**: Execute Python code with proper output capture
- **File Management**: List and read files from the Files directory
- **Calculator**: Basic addition operations
- **Smart Tool Selection**: Automatically determines when to use tools vs. answering directly

## Prerequisites

- Python 3.11 or higher
- API keys for the following services (see API Setup section)

## Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd "My Conversational Bot"
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
```

3. Activate the virtual environment:
   - **Windows (PowerShell)**: `venv\Scripts\Activate.ps1`
   - **Windows (CMD)**: `venv\Scripts\activate.bat`
   - **Linux/Mac**: `source venv/bin/activate`

4. Install dependencies:
```bash
pip install -r requirements.txt
```

## API Setup

This project requires API keys from three different services:

### 1. Groq API (Required)

**What it's used for:**
- LLM inference (Llama 3.3 70B model)
- Audio transcription (Whisper Large V3 Turbo)

**How to get it:**
1. Go to [https://console.groq.com/](https://console.groq.com/)
2. Sign up for a free account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key

**Free tier:** Generous free tier available

### 2. Google Gemini API (Required)

**What it's used for:**
- Vision analysis of YouTube videos (Gemini 2.5 Flash model)

**How to get it:**
1. Go to [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Copy the key

**Free tier:** Free tier with usage limits available

### 3. RapidAPI - Speech-to-Text AI (Required)

**What it's used for:**
- Transcribing YouTube, TikTok, and Facebook videos

**How to get it:**
1. Go to [https://rapidapi.com/](https://rapidapi.com/)
2. Sign up for a free account
3. Search for "Speech-to-Text AI" in the marketplace
4. Navigate to: [Speech-to-Text AI API](https://rapidapi.com/hub)
5. Subscribe to the API (look for free tier if available)
6. Copy your RapidAPI key from your dashboard (not the API's specific key, but your general RapidAPI key)

**Note:** The specific endpoint used is: `speech-to-text-ai.p.rapidapi.com`

**Free tier:** Check the API's pricing page for free tier availability

## Configuration

1. Create a `.env` file in the project root directory:
```bash
cp .example_env .env
```

2. Edit the `.env` file and add your API keys:
```env
GROQ_API_KEY=your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
RAPID_API_KEY=your_rapidapi_key_here
```

**Important:** Never commit your `.env` file to version control. It's already included in `.gitignore`.

## Usage

1. Make sure your virtual environment is activated

2. Run the agent:
```bash
python main.py
```

3. Type your questions when prompted. The agent will:
   - Answer simple questions directly from its knowledge
   - Use appropriate tools when needed (file operations, calculations, code execution, etc.)
   - Provide concise one-word/one-number answers for direct questions

4. Type `exit` or `quit` to stop the agent

## Available Tools

1. **calculator** - Perform basic addition operations
2. **python_tool** - Execute Python code (supports classes, functions, and `if __name__ == "__main__"` blocks)
3. **convert_audio_to_text** - Transcribe audio files using Whisper
4. **list_attached_files** - List all files in the `Files` folder
5. **read_python_file** - Read Python file contents safely
6. **SpeechToText** - Transcribe YouTube, TikTok, or Facebook videos
7. **gemini_vision** - Perform vision analysis on YouTube videos

## Project Structure

```
My Conversational Bot/
├── main.py              # Main entry point and conversation loop
├── graph.py             # LangGraph workflow definition
├── tools.py             # Tool definitions and implementations
├── state.py             # Agent state management
├── requirements.txt     # Python dependencies
├── .env                 # API keys (create this file)
├── .example_env         # Example environment file
├── .gitignore          # Git ignore rules
├── Files/              # Directory for user files
│   ├── PythonCode.py
│   └── ...
└── TestFolder/         # Test scripts
    ├── TestGemini.py
    ├── TestPythonOnlyTools.py
    └── ...
```

## Example Interactions

**Simple question (no tools needed):**
```
You: What is the opposite of left?
Agent: right
```

**File operation:**
```
You: List the files in the Files folder
Agent: [Uses list_attached_files tool]
```

**Code execution:**
```
You: Run the PythonCode.py file
Agent: [Uses read_python_file, then python_tool]
```

## Troubleshooting

### "Error: tool_use_failed"
- This usually happens when the agent tries to use file paths with backslashes incorrectly
- The agent should automatically use `read_python_file` tool first, then pass code to `python_tool`
- If this persists, check that your API keys are correctly set in `.env`

### "FileNotFoundError"
- Always use `list_attached_files()` first to get the correct absolute path
- Make sure files are in the `Files` directory

### API Rate Limits
- Groq: Check your usage at [console.groq.com](https://console.groq.com/)
- Gemini: Check quotas at [Google AI Studio](https://aistudio.google.com/)
- RapidAPI: Check your subscription limits in your RapidAPI dashboard

## Dependencies

See `requirements.txt` for the complete list. Main dependencies include:
- `langchain` & `langchain-core` - LLM framework
- `langgraph` - Agent workflow management
- `langchain-groq` - Groq API integration
- `google-genai` - Gemini API integration
- `python-dotenv` - Environment variable management
- `requests` - HTTP requests for RapidAPI

