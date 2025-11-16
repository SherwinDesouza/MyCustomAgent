import os
from pathlib import Path
def list_attached_files() -> list[str]:
    """List all files in the Files folder. 
    
    Use this tool whenever the user mentions they have attached a file, 
    uploaded a file, provided a file, or refers to files they want you to process.
    This will return a list of all available file paths in the Files directory.
    """
    files_folder = Path(r"C:\Users\PAX\My Conversational Bot\Files")
    print(files_folder)
    
    # Get all files in the Files folder
    file_paths = []
    if files_folder.exists():
        for file_path in files_folder.iterdir():
            if file_path.is_file():
                # Return absolute path
                file_paths.append(str(file_path.absolute()))
    
    return file_paths

# print(list_attached_files())