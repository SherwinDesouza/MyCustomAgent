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
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
from utilities import summarize_text
import pandas as pd
import numpy as np
import http.client


try:
    from ddgs import DDGS
except ImportError:
    DDGS = None
from Scraper import _fetch_html,_clean_text,_word_snippet,_find_nearby_urls,_extract_table_structure
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
RAPID_API_KEY = os.getenv("RAPID_API_KEY")
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


@tool
def calculator(a: float, b: float) -> float:
    """Add two numbers."""
    #print(f"Adding {a} and {b}")
    return a + b

# Directory for saving generated plots
PLOTS_DIR = Path(r"C:\Users\PAX\My Conversational Bot\frontend\public\plots")
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

# Python executor (safe) - with plot handling
def execute_python(code: str) -> Dict[str, Any]:
    """Execute Python code and capture output including plots."""
    import io
    import sys
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend for saving plots
    import matplotlib.pyplot as plt
    
    result = {
        "text_output": "",
        "image_path": None,
        "success": True
    }
    
    try:
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured_output = io.StringIO()
        
        # Create a namespace for the code to run in
        namespace = {
            '__name__': '__main__',
            'pd': pd,
            'plt': plt,
            'np': __import__('numpy')
        }
        exec(code, namespace)
        
        # Get captured output
        output = captured_output.getvalue()
        sys.stdout = old_stdout
        
        # Check if a plot was created
        if plt.get_fignums():
            import uuid
            plot_filename = f"plot_{uuid.uuid4().hex[:8]}.png"
            plot_path = PLOTS_DIR / plot_filename
            plt.savefig(plot_path, dpi=150, bbox_inches='tight')
            plt.close('all')
            result["image_path"] = f"/plots/{plot_filename}"
        
        # Return output if any, otherwise success message
        if output.strip():
            result["text_output"] = output.strip()
        else:
            result["text_output"] = "Code executed successfully (no output)"
            
        return result
        
    except Exception as e:
        sys.stdout = old_stdout if 'old_stdout' in locals() else sys.stdout
        plt.close('all')  # Clean up any partial plots
        result["success"] = False
        result["text_output"] = f"Error: {e}"
        return result

@tool
def run_python_code(code: str):
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
    """List all files in the Files folder for the current session. 
    
    ALWAYS call this tool FIRST when the user mentions they have attached a file, 
    uploaded a file, provided a file, or refers to files they want you to process.
    This will return a list of all available file paths (absolute paths) in the session's Files directory.
    
    After getting the file list, you can match the filename the user mentioned with 
    the actual absolute path from this list, then use that path with other tools like 
    convert_audio_to_text() or read_python_file().
    
    Returns:
        A list of absolute file paths (strings) of all files in the session's Files directory.
    """
    try:
        from session_context import get_session_id
        session_id = get_session_id()
        
        # Use session-specific directory
        files_folder = Path(r"C:\Users\PAX\My Conversational Bot\Files") / session_id
        print(f"Scanning folder for session {session_id}: {files_folder}")
        
        # Get all files in the session's Files folder
        file_paths = []
        if files_folder.exists():
            for file_path in files_folder.iterdir():
                if file_path.is_file():
                    # Return absolute path
                    file_paths.append(str(file_path.absolute()))
        
        if not file_paths:
            return f"No files found in the Files directory for session {session_id}."
        
        return file_paths
    except Exception as e:
        return f"ERROR: Failed to list files: {str(e)}"

@tool
def read_python_file(file_path: str) -> str:
    """Read the contents of a Python file.
    
    Use this tool to read Python code from a file before executing it with run_python_code.
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

@tool
def web_search(user_query: str) -> str:
    """
    This tool is to perform a web search using DuckDuckGo and return top results as a JSON string.

    Args:
        user_query (str): The search query.

    Returns:
        str: JSON string containing a list of search results.
             Each result is a dictionary with keys: "title", "href", "body".
             "body" is truncated to the first ~20 words.
    """
    if DDGS is None:
        error_msg = {
            "status": "error",
            "message": "DuckDuckGo search library not installed. Install with: pip install duckduckgo-search"
        }
        return json.dumps(error_msg)
    
    try:
        results = DDGS().text(user_query, max_results=4, region="us-en")
        truncated = []

        for item in results:
            body = item.get("body", "")
            short_body = " ".join(body.split()[:20])

            truncated.append({
                "title": item.get("title", ""),
                "href": item.get("href", ""),
                "body": short_body
            })

        return json.dumps(truncated)

    except Exception as e:
        error_msg = {
            "status": "error",
            "message": f"Web search failed: {str(e)}"
        }
        return json.dumps(error_msg)

@tool
def scrape_data(url: str,
                selector: Optional[str] = None,
                keyword: Optional[str] = None,
                js: bool = False,
                max_snippets: int = 5,
                window_words: int = 20,
                user_query: Optional[str] = None) -> Dict[str, Any]:
    """
    Scrape a webpage and extract content based on different modes.
    
    This tool can operate in three modes:
    1. Initial exploration: Returns page headings and available selectors (when both selector and keyword are None)
    2. Keyword search: Finds text snippets containing the keyword with context (when keyword is provided)
    3. CSS selector extraction: Extracts content matching a CSS selector (when selector is provided)
    
    Args:
        url (str): The URL of the webpage to scrape.
        selector (Optional[str]): CSS selector to extract specific elements (e.g., "article", "table", ".class-name").
                                  If None and keyword is also None, returns page structure info.
        keyword (Optional[str]): Search for a specific keyword in the page text. Returns snippets with context.
        js (bool): Whether to render JavaScript (requires Playwright). Default is False.
        max_snippets (int): Maximum number of snippets to return. Default is 5.
        window_words (int): Number of words before and after keyword match to include in snippet. Default is 20.
        user_query (Optional[str]): The user's original query for query-aware compression. Used internally for summarization.
    
    Returns:
        Dict[str, Any]: A dictionary with the following structure:
            - status: "ok", "error", "not_found"
            - snippets: List of keyword-based text snippets with nearby URLs (if keyword search)
            - selector_results: List of extracted content from CSS selectors (if selector used)
            - headings: List of page headings h1, h2, h3 (if initial exploration)
            - selectors_hint: List of available selectors found on page (if initial exploration)
            - meta: Dictionary with fetched_url and final_url
            - error/note: Error message or note if something went wrong
    
    Usage Notes (for the agent):
        - First call with only url to explore page structure (get headings and selector hints)
        - Use keyword parameter to search for specific text content
        - Use selector parameter to extract structured content (tables, articles, lists, etc.)
        - Set js=True if the page requires JavaScript rendering
        - Combine with web_search() to find relevant URLs first, then scrape them
    """

    fetched = _fetch_html(url, js=js)
    if "error" in fetched:
        return {"status": "error", "error": fetched["error"], "meta": {"fetched_url": url}}

    html = fetched["html"]
    final_url = fetched.get("final_url", url)
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()

    page_text = _clean_text(soup.get_text(" ", strip=True))

    result = {
        "status": "ok",
        "snippets": [],
        "selector_results": [],
        "headings": [],
        "meta": {"fetched_url": url, "final_url": final_url}
    }

    # CASE 1 ------------------ Initial call (no keyword + no selector)
    if not selector and not keyword:
        headings = [h.get_text(" ", strip=True) for h in soup.select("h1, h2, h3")][:40]
        selectors_found = []

        for sel in ["table", "article", "main", "ul", "ol"]:
            if soup.select_one(sel):
                selectors_found.append(sel)

        result["headings"] = headings
        result["selectors_hint"] = selectors_found
        return result

    # CASE 2 ------------------ Keyword search
    if keyword:
        low = page_text.lower()
        kw = keyword.lower()

        matches = []
        start = 0
        while len(matches) < max_snippets:
            idx = low.find(kw, start)
            if idx == -1:
                break
            matches.append((idx, idx + len(kw)))
            start = idx + len(kw)


        if matches:
            for i, span in enumerate(matches):
               
                snippet, _, _ = _word_snippet(page_text, span, window_words=window_words)
          

                # Find the most specific (smallest) element containing the keyword
                element = None
                elements_checked = 0
                candidate_elements = []
                
                # Skip these large container elements
                skip_tags = {'html', 'body', 'main', 'div', 'section', 'article'}
                
                for el in soup.find_all():
                    elements_checked += 1
                    try:
                        el_text = el.get_text(" ", strip=True).lower()
                        if kw in el_text:
                            # Skip very large elements (likely page containers)
                            if len(el_text) > 500:
                                continue
                            # Prefer smaller, more specific elements
                            candidate_elements.append((el, len(el_text)))
                    except:
                        continue
                
                if candidate_elements:
                    # Sort by text length (smallest first) and take the most specific
                    candidate_elements.sort(key=lambda x: x[1])
                    element = candidate_elements[-1][0]
                   

                urls = _find_nearby_urls(soup, element) if element else []
                
                # Compress the snippet text to reduce token usage
                try:
                    compressed_snippet = summarize_text(snippet, query=user_query)
                except Exception as e:
                    # If summarization fails, use original snippet
                    print(f"Summarization failed for snippet: {e}")
                    compressed_snippet = snippet
                
                snippet_entry = {
                    "text": compressed_snippet,
                    "urls": urls
                }

                result["snippets"].append(snippet_entry)

            return result

        else:
            if not selector:
                return {
                    "status": "not_found",
                    "note": f"Keyword '{keyword}' not found on page.",
                    "meta": result["meta"]
                }

    # CASE 3 ------------------ CSS Selector extraction
    if selector:
        elems = soup.select(selector)
        if not elems:
            return {
                "status": "not_found",
                "note": f"Selector '{selector}' not found on page.",
                "meta": result["meta"]
            }

        for el in elems[:max_snippets]:
            # Check if this is a table element
            if el.name == 'table':
                urls = [a.get("href") for a in el.select("a[href]")]
                table_text = _clean_text(el.get_text(" ", strip=True))

                # Use pandas to extract a clean table representation
                try:
                    dfs = pd.read_html(str(el))
                    if dfs:
                        df = dfs[0]
                        table_data = {
                            "columns": [str(col) for col in df.columns],
                            "rows": df.to_dict(orient="records"),
                            "row_count": len(df)
                        }
                    else:
                        table_data = {
                            "columns": None,
                            "rows": [],
                            "row_count": 0
                        }
                except Exception as e:
                    print(f"Pandas failed to parse table: {e}")
                    table_data = _extract_table_structure(el)

                # Compress table text while preserving structured data
                try:
                    compressed_text = summarize_text(table_text, query=user_query)
                except Exception as e:
                    print(f"Summarization failed for table: {e}")
                    compressed_text = table_text

                result["selector_results"].append({
                    "selector": selector,
                    "type": "table",
                    "table_data": table_data,
                    "text": compressed_text,
                    "urls": urls[:5]
                })
            else:
                # For non-table elements, use existing text extraction
                text = _clean_text(el.get_text(" ", strip=True))
                urls = [a.get("href") for a in el.select("a[href]")]
                
                # Compress the extracted text
                try:
                    compressed_text = summarize_text(text, query=user_query)
                except Exception as e:
                    print(f"Summarization failed for text: {e}")
                    compressed_text = text
                
                result["selector_results"].append({
                    "selector": selector,
                    "type": "text",
                    "text": compressed_text,  # Use compressed version
                    "urls": urls[:5]
                })
        
        return result

    return {"status": "not_found", "note": "No matches found", "meta": result["meta"]}


def summarize_dataframe(
    df: pd.DataFrame,
    sample_values: int = 5,
    categorical_threshold: float = 0.05
) -> Dict[str, Any]:
    print("DEBUG: Inside summarize_dataframe")
    """
    Generate a robust, LLM-friendly summary of a pandas DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe
    sample_values : int
        Number of unique example values to capture per column
    categorical_threshold : float
        Max ratio of unique values to rows for categorical inference

    Returns
    -------
    Dict[str, Any]
        JSON-serializable dataset summary
    """

    def infer_semantic_type(values: list[str], col_name: str) -> str:
        lower_vals = {str(v).lower() for v in values}

        if lower_vals <= {"male", "female"}:
            return "gender"
        if lower_vals <= {"yes", "no"}:
            return "boolean"
        if "date" in col_name.lower():
            return "date"
        if "id" in col_name.lower():
            return "identifier"
        if "location" in col_name.lower():
            return "location"

        return "category"

    def infer_role(series: pd.Series) -> str:
        if pd.api.types.is_bool_dtype(series):
            return "boolean"

        if pd.api.types.is_datetime64_any_dtype(series):
            return "datetime"

        if pd.api.types.is_numeric_dtype(series):
            return "numeric"

        unique_count = series.nunique(dropna=True)
        total_count = len(series)

        if unique_count <= categorical_threshold * total_count:
            return "categorical"

        return "text"

    summary = {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "duplicate_rows": int(df.duplicated().sum()),
        "memory_usage_mb": round(df.memory_usage(deep=True).sum() / 1e6, 2),
        "columns": []
    }

    for col in df.columns:
        series = df[col]
        non_null = series.dropna()

        unique_values = non_null.unique()
        example_values = [
            v.item() if isinstance(v, np.generic) else v
            for v in unique_values[:sample_values]
        ]

        role = infer_role(series)

        column_info = {
            "name": col,
            "dtype": str(series.dtype),
            "role": role,
            "missing_count": int(series.isna().sum()),
            "missing_percent": round(series.isna().mean() * 100, 2),
            "unique_count": int(series.nunique(dropna=True)),
            "example_values": example_values
        }

        if role == "categorical":
            column_info["semantic_type"] = infer_semantic_type(
                example_values, col
            )

        summary["columns"].append(column_info)

    print(f"DEBUG: Summary generated with {len(summary['columns'])} columns")
    return summary


@tool
def get_weather(location: str) -> Dict[str, Any]:
    """Get current weather data for a location using the WeatherAPI.
    
    Args:
        location: The location to get weather data for
        
    Returns:
        Dict containing:
        - success: Whether the weather data was retrieved successfully
        - weather_data: Weather data from the API
        - error: Error message if the weather data could not be retrieved
    """
    try:
        conn = http.client.HTTPSConnection("weatherapi230.p.rapidapi.com")
        headers = {
            'x-rapidapi-key': os.getenv("RAPID_API_KEY"),
            'x-rapidapi-host': "weatherapi230.p.rapidapi.com"
        }
        conn.request("GET", f"/current?units=metric&location={location}", headers=headers)
        res = conn.getresponse()
        data = res.read()
        return {"success": True, "weather_data": data.decode("utf-8")}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def load_dataset(file_path: str) -> Dict[str, Any]:
    """Load a CSV or Excel file into a pandas DataFrame and return its summary.
    
    Args:
        file_path: Absolute path to the CSV or Excel file
        
    Returns:
        Dict containing:
        - success: Whether the file was loaded successfully
        - summary: Dataset summary from summarize_dataframe
        - error: Error message if loading failed
    """
    from session_context import get_session_id
    
    try:
        path = Path(file_path)
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        
        # Determine file type and load
        ext = path.suffix.lower()
        if ext == '.csv':
            df = pd.read_csv(file_path)
        elif ext in ['.xls', '.xlsx']:
            df = pd.read_excel(file_path)
        else:
            return {"success": False, "error": f"Unsupported file type: {ext}. Use .csv, .xls, or .xlsx"}
        
        # Store the dataframe in session-specific storage
        session_id = get_session_id()
        _session_datasets[session_id] = df
        
        # Generate summary
        summary = summarize_dataframe(df)
        print("DEBUG: Summary generation complete")
        print(f"DEBUG: Summary keys: {summary.keys()}")
        
        return {
            "success": True,
            "summary": summary,
            "file_path": file_path,
            "session_id": session_id
        }
    except Exception as e:
        print(f"DEBUG: load_dataset failed with error: {e}")
        return {"success": False, "error": str(e)}


# Global dictionary to store datasets per session
# Key: session_id, Value: pandas DataFrame
_session_datasets = {}


@tool
def generate_analysis_code(user_query: str, dataset_summary: str) -> str:
    """Generate executable Python code for data analysis using Gemini 2.5 Flash.
    
    This tool creates Python code that analyzes a dataset based on the user's query.
    The generated code uses pandas, matplotlib, and can answer questions or create visualizations.
    
    Args:
        user_query: The user's question or request about the data
        dataset_summary: JSON string containing the dataset summary from load_dataset
        
    Returns:
        Executable Python code string that can be passed to run_python_code
    """
    code_gen_prompt = f'''You are a data analysis code generator. Generate ONLY executable Python code.

DATASET SUMMARY:
{dataset_summary}

USER REQUEST: {user_query}

RULES:
1. The dataframe is already loaded as `df` - do NOT load it again
2. Use pandas for data manipulation
3. Use matplotlib.pyplot (as plt) for visualizations
4. If creating a plot, do NOT call plt.show() - the system saves plots automatically
5. Print any numerical answers or insights clearly
6. Handle potential errors gracefully (e.g., missing columns)
7. Return ONLY the Python code, no explanations or markdown

Generate the Python code:'''

    try:
        response = gemini_client.models.generate_content(
            model='models/gemini-2.5-flash',
            contents=code_gen_prompt
        )
        
        # Clean the response - remove markdown code blocks if present
        code = response.text.strip()
        if code.startswith('```python'):
            code = code[9:]
        if code.startswith('```'):
            code = code[3:]
        if code.endswith('```'):
            code = code[:-3]
        
        return code.strip()
    except Exception as e:
        return f"# Error generating code: {e}"


@tool
def analyze_data(user_query: str) -> Dict[str, Any]:
    """Analyze the currently loaded dataset based on user's query.
    
    This is a high-level tool that combines code generation and execution.
    First loads the dataset (if not loaded), generates analysis code using Gemini 2.5 Flash,
    then executes it and returns results including any generated plots.
    
    Args:
        user_query: The user's question about the data (e.g., "How many students have CGPA > 3?")
        
    Returns:
        Dict containing:
        - text_output: Text results from the analysis
        - image_path: Path to generated plot (if any)
        - code: The generated Python code
        - success: Whether the analysis succeeded
    """
    from session_context import get_session_id
    session_id = get_session_id()
    
    current_df = _session_datasets.get(session_id)
    
    if current_df is None:
        return {
            "success": False,
            "text_output": "No dataset loaded for this session. Please upload a CSV or Excel file first.",
            "image_path": None,
            "code": None
        }
    
    # Get summary of current dataset
    import numpy as np
    summary = summarize_dataframe(current_df)
    summary_str = json.dumps(summary, indent=2, default=str)
    
    # Generate code
    code = generate_analysis_code.func(user_query, summary_str)
    
    # Prepare execution environment with the dataset
    exec_code = f'''df = _current_dataset
{code}'''
    
    # Execute the code
    import io
    import sys
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    
    result = {
        "text_output": "",
        "image_path": None,
        "code": code,
        "success": True
    }
    
    try:
        old_stdout = sys.stdout
        sys.stdout = captured_output = io.StringIO()
        
        namespace = {
            '__name__': '__main__',
            'pd': pd,
            'plt': plt,
            'np': np,
            '_current_dataset': current_df,
            'df': current_df
        }
        exec(exec_code, namespace)
        
        output = captured_output.getvalue()
        sys.stdout = old_stdout
        
        # Check for plots
        if plt.get_fignums():
            import uuid
            plot_filename = f"plot_{uuid.uuid4().hex[:8]}.png"
            plot_path = PLOTS_DIR / plot_filename
            plt.savefig(plot_path, dpi=150, bbox_inches='tight')
            plt.close('all')
            result["image_path"] = f"/plots/{plot_filename}"
        
        result["text_output"] = output.strip() if output.strip() else "Analysis complete."
        
    except Exception as e:
        sys.stdout = old_stdout if 'old_stdout' in locals() else sys.stdout
        plt.close('all')
        result["success"] = False
        result["text_output"] = f"Error executing analysis: {e}"
    
    return result


TOOLS = [get_weather, analyze_data, load_dataset, generate_analysis_code, calculator, run_python_code, convert_audio_to_text, list_attached_files, read_python_file, SpeechToText, gemini_vision, reverse_string, web_search, scrape_data]

