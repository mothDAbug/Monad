# File Organizer (Project T07)

## Description

An automated command-line tool for decluttering and structuring directories by sorting files into subfolders based on user-defined rules, primarily focused on file extensions. Helps maintain an organized file system, especially useful for folders like 'Downloads'.

## Features

*   **Rule-Based Sorting:** Organizes files based on their extensions defined in a configuration file (`config/organizer_rules.json`).
*   **Customizable Rules:** Easily modify the JSON configuration to add/remove extensions or change target folder names.
*   **'Other' Folder:** Option to move files that don't match any specific rule into a designated 'Miscellaneous' folder (configurable).
*   **Directory Creation:** Automatically creates necessary subfolders within the target directory if they don't exist.
*   **Collision Avoidance:** If a file with the same name already exists in the destination folder, the moved file will be renamed with a timestamp to prevent overwriting.
*   **Dry Run Mode:** Allows you to preview the changes (which files would be moved where) without actually moving any files.
*   **Confirmation Prompts:** Asks for confirmation before making changes to the file system (unless in dry run mode).
*   **Skips Directories:** Only processes files within the specified target directory, ignoring subdirectories.

## Requirements

*   Python 3.7+
*   Libraries listed in `requirements.txt`:
    *   `pyinputplus`: For robust user input validation.
*   Standard libraries: `os`, `shutil`, `json`, `datetime`.

## Setup

1.  **Clone or Download:** Get the project files. Ensure you have `file_organizer.py`, `requirements.txt`, and the `config` folder containing `organizer_rules.json`.
2.  **Navigate to Directory:** Open your terminal or command prompt and change into the project directory (`file_organizer/`).
3.  **Customize Rules (Optional):**
    *   Open `config/organizer_rules.json`.
    *   Modify the `rules_by_extension` object:
        *   Keys are the **names of the subfolders** to be created (e.g., "Images", "Documents").
        *   Values are **lists of file extensions** (lowercase, without the dot) that should go into that folder.
    *   Adjust `use_other_folder` (true/false) and `other_folder_name` if desired.
4.  **Create Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    ```
    *   Activate it:
        *   Windows: `.\venv\Scripts\activate`
        *   macOS/Linux: `source venv/bin/activate`
5.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1.  Make sure your virtual environment is activated (if you created one).
2.  Run the script from the terminal:
    ```bash
    python file_organizer.py
    ```
3.  The script will:
    *   Load the rules from `config/organizer_rules.json`.
    *   Prompt you to enter the path to the directory you want to organize (e.g., `~/Downloads`, `C:\Users\YourUser\Downloads`). You can leave it blank to organize the directory where the script is located.
    *   Ask if you want to perform a 'dry run' first. It's **highly recommended** to do a dry run (`yes`) the first time for a specific directory to see what will happen.
    *   If doing a dry run, it will list the planned actions and ask if you want to proceed with the actual organization.
    *   If *not* doing a dry run, it will ask for **final confirmation** before moving any files.
    *   Display a summary of how many files were moved and skipped.

## Important Considerations

*   **Backup:** It's always wise to **back up important files** before running any automated file organization tool, especially for the first time.
*   **Target Directory:** Be careful about the target directory you specify. Organizing system folders or application directories is generally not recommended. Use it primarily for personal folders like 'Downloads' or 'Desktop'.
*   **Permissions:** The script needs read and write permissions in the target directory and its subdirectories to move files and create folders.
*   **Limitations:** This basic version sorts based on file extension only. It doesn't analyze file content. It also doesn't handle subdirectories recursively within the target folder.

## License

This project can be considered under the MIT License (or specify otherwise if needed).