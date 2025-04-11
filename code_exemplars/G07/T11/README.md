# Notes App (Project T11)

## Description

A command-line digital notebook application for creating, organizing, searching, and optionally securing personal or professional notes using AES encryption.

## Features

*   **CRUD Operations:** Create, read, view, update, and delete notes.
*   **Tagging:** Organize notes using simple comma-separated tags.
*   **Search:** Search notes by title, content (unencrypted only), or tags.
*   **Optional Encryption:** Encrypt individual notes using AES (via Fernet) derived from a master password.
    *   **Security Note:** Master password handling is basic for this template. See warnings below.
*   **Text Import/Export:**
    *   Export individual notes or all notes to plain text files (decrypts if needed, requires password). Exports saved in `data_exports/`.
    *   Import notes from `.txt` files placed in the `data_imports/` directory (filename becomes title, content becomes note body, imported as plain text).
*   **Database Storage:** Uses SQLite (`notes.db`) for persistent storage.
*   **User Interface:** Uses `PyInputPlus` for robust command-line interaction.

## Requirements

*   Python 3.7+
*   Libraries listed in `requirements.txt`:
    *   `pyinputplus`: For user input validation.
    *   `cryptography`: For AES encryption/decryption.
*   Standard libraries: `sqlite3`, `os`, `datetime`, `base64`, `hashlib`.

## Setup

1.  **Clone or Download:** Get the project files (`notes_app.py`, `requirements.txt`).
2.  **Navigate to Directory:** Open your terminal or command prompt and change into the project directory (`notes_app/`).
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
5.  **Run Once (Initial Setup):**
    *   Run the script for the first time: `python notes_app.py`
    *   This will:
        *   Create the `notes.db` database file.
        *   Create the `data_exports/` and `data_imports/` directories.
        *   Generate a crucial `app_salt.bin` file needed for deriving the encryption key. **KEEP THIS FILE SAFE!** If you lose it, you cannot decrypt your encrypted notes. Back it up along with your `notes.db`.

## Usage

1.  Make sure your virtual environment is activated (if you created one).
2.  Run the script from the terminal:
    ```bash
    python notes_app.py
    ```
3.  The script will present the main menu:
    *   **Add Note:** Prompts for title, content (multi-line input, end with Ctrl+Z/D), tags. Asks if the note should be encrypted. If yes, prompts for the master password.
    *   **View/Search Notes:** Lists notes. Prompts for optional search term (searches title/unencrypted content) and tag filter.
    *   **Read Note:** Prompts for the Note ID to display. If the note is encrypted, prompts for the master password to decrypt and display.
    *   **Update Note:** Prompts for Note ID. Shows current details. If encrypted, asks for password to decrypt for editing. Prompts for new title, content (optional), tags. Asks if encryption status should be changed. Requires password if encrypting or re-encrypting.
    *   **Delete Note:** Prompts for Note ID and confirmation before deleting.
    *   **Export Note(s):** Choose to export a single note (by ID) or all notes. Encrypted notes require the master password for decryption before export. Files saved to `data_exports/`.
    *   **Import Notes from Files:** Looks for `.txt` files in `data_imports/`. Imports each file as a new plain text note.
    *   **Exit:** Quits the application.

## Security Warnings & Considerations

*   **Master Password Handling:** This template uses a **basic and insecure** method for handling the master password. It's requested repeatedly and briefly cached in memory during some operations. **In a real application, never store passwords directly or cache them insecurely.** Use secure methods like OS keyrings or more advanced key management.
*   **Salt File:** The `app_salt.bin` file is essential for decrypting notes. **Back it up securely along with your `notes.db` file.** Losing the salt means losing access to encrypted notes, even with the correct password.
*   **Database Encryption:** The SQLite database file (`notes.db`) itself is **not encrypted** by this script. Only the `content` field of notes marked as `is_encrypted=1` is encrypted. Someone with access to the `notes.db` file could still see note titles, tags, timestamps, and unencrypted content. Consider full disk encryption or encrypted database solutions (like SQLCipher) for higher security needs.
*   **Content Search:** Searching works fully only on unencrypted note content due to the nature of encryption.

## Database Schema (`notes` table)

*   `note_id`: INTEGER, Primary Key
*   `title`: TEXT, Not Null
*   `content`: TEXT (Stores plain text or base64-encoded encrypted bytes)
*   `tags`: TEXT (Comma-separated string)
*   `created_at`: TIMESTAMP
*   `updated_at`: TIMESTAMP
*   `is_encrypted`: INTEGER (0 = False, 1 = True)

## License

This project can be considered under the MIT License (or specify otherwise if needed). Use with caution regarding the security limitations mentioned above.