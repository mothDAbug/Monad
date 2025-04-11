# Duplicate File Finder (Project T08)

## Description

A command-line utility that scans a specified directory recursively to identify duplicate files based on their content hash (using SHA256 by default). It helps identify redundant files to potentially recover disk space. Includes options to list duplicates and interactively delete them.

## Features

*   **Recursive Scanning:** Scans the target directory and all its subdirectories using `os.walk`.
*   **Content-Based Detection:** Identifies duplicates by comparing file content hashes, ensuring accuracy. Uses SHA256 for hashing.
*   **Efficient Hashing:** Reads files in chunks to handle large files without consuming excessive memory.
*   **Size Pre-filtering:** Optimizes the process by only hashing files that have the same size.
*   **Interactive Deletion:** Provides a safe, interactive mode to delete duplicates, prompting the user to choose which file to keep from each set. Requires final confirmation before deletion.
*   **Clear Listing:** Displays identified duplicate sets with file paths and sizes.
*   **Symlink Skipping:** Skips symbolic links during the scan to avoid potential issues.
*   **Error Handling:** Includes basic handling for file access errors (permissions, file not found during scan).

## Requirements

*   Python 3.7+
*   Libraries listed in `requirements.txt`:
    *   `pyinputplus`: For robust user input validation.
*   Standard libraries: `os`, `hashlib`, `json`, `shutil`, `datetime`.

## Setup

1.  **Clone or Download:** Get the project files (`duplicate_finder.py`, `requirements.txt`).
2.  **Navigate to Directory:** Open your terminal or command prompt and change into the project directory (`duplicate_file_finder/`).
3.  **Create Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    ```
    *   Activate it:
        *   Windows: `.\venv\Scripts\activate`
        *   macOS/Linux: `source venv/bin/activate`
4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1.  Make sure your virtual environment is activated (if you created one).
2.  Run the script from the terminal:
    ```bash
    python duplicate_finder.py
    ```
3.  The script will:
    *   Prompt you to enter the path to the directory you want to scan.
    *   Perform the scan in phases (group by size, hash potential duplicates).
    *   Display a summary of the scan results.
    *   If duplicates are found, present an action menu:
        *   **List Duplicate Sets:** Shows all groups of identical files found.
        *   **Delete Duplicates Interactively:** Guides you through each duplicate set, asking which file to **KEEP**. All others in the set are marked for deletion. A final summary and confirmation prompt are shown before any files are actually removed.
        *   **Exit:** Quits the application.

## Important Warnings

*   **!!! DATA LOSS RISK !!!** Deleting files is permanent. Use the deletion feature with **EXTREME CAUTION**.
*   **Backup:** Always **BACK UP your important data** before running any tool that deletes files, especially if you are unsure.
*   **Verification:** Carefully review the files listed in the interactive deletion prompt before confirming. Ensure you are keeping the correct version.
*   **System Files:** Avoid scanning system directories or application folders unless you are absolutely certain about what you are doing. Deleting necessary system or application files can cause instability or data loss.
*   **Performance:** Scanning very large directories with many files can take a significant amount of time and CPU resources due to file I/O and hashing.

## Future Enhancements (Potential Ideas)

*   Add options to move duplicates to a specific folder instead of deleting.
*   Implement file comparison beyond exact hash matches (e.g., fuzzy hashing for similar images - more complex).
*   Add configuration file for excluding specific directories, file types, or sizes.
*   Implement hash caching to speed up subsequent scans (though cache validation is complex).
*   Add option to create symbolic links or hard links instead of deleting.

## License

This project can be considered under the MIT License (or specify otherwise if needed). Please use responsibly.