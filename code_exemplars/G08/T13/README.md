# Password Manager (Project T13)

## Description

A command-line application specifically designed for storing, managing, and generating login credentials (usernames, passwords, URLs). Includes features for password generation, basic strength analysis, and checking passwords against the Have I Been Pwned (HIBP) database via their public API. Uses AES-GCM encryption derived from a master password.

**IMPORTANT:** This is a template project. Security is complex. Review the warnings carefully before use.

## Features

*   **Master Password Authentication:** Protects access using a master password hashed with PBKDF2.
*   **Secure Storage:** Encrypts passwords using AES-256-GCM. Stores service name, username, URL, notes, tags, and encrypted password metadata in an SQLite database (`passwords.db`).
*   **CRUD Operations:** Add, list (metadata only), retrieve (decrypt), update, and delete password entries.
*   **Password Generation:** Generates strong, random passwords with customizable length and character sets.
*   **Password Strength Check:** Provides a basic assessment of password complexity (length, character types).
*   **HIBP Integration:** Checks if a password (its SHA-1 hash) has appeared in known data breaches using the public Have I Been Pwned API (requires internet).
*   **Tagging:** Simple comma-separated tags for organizing entries.
*   **Search:** Basic search by service, username, URL, notes, or tag.
*   **Clipboard Integration:** Attempts to copy retrieved or generated passwords to the clipboard (requires `pyperclip`).
*   **Change Master Password (Simplified):** Updates the master password credentials but **does not re-encrypt existing passwords**.

## Requirements

*   Python 3.7+
*   Libraries listed in `requirements.txt`:
    *   `pyinputplus`: For user input validation.
    *   `cryptography`: For hashing and encryption.
    *   `requests`: For HIBP API calls.
*   Standard libraries: `sqlite3`, `os`, `datetime`, `json`, `base64`, `hashlib`, `hmac`, `random`, `string`, `re`, `time`.
*   Optional: `pyperclip` (for clipboard copy functionality). Install with `pip install pyperclip`.

## Setup

1.  **Clone or Download:** Get `password_manager.py`, `requirements.txt`.
2.  **Navigate to Directory:** Open terminal/cmd into the `password_manager/` directory.
3.  **Create Virtual Environment (Recommended):** `python -m venv venv` then activate.
4.  **Install Dependencies:** `pip install -r requirements.txt` (and optionally `pip install pyperclip`).
5.  **Run for First Time (Setup):**
    ```bash
    python password_manager.py
    ```
    *   Sets up your **Master Password**. **REMEMBER IT!** Losing it means losing access to all stored passwords.
    *   Creates `passwords.db` database.
    *   Creates `data/` directory and `data/auth_store_pm.json` (contains salts/hash). **BACK UP `auth_store_pm.json` and `passwords.db` securely!**

## Usage

1.  Activate virtual environment.
2.  Run: `python password_manager.py`
3.  Enter your Master Password.
4.  Use the menu:
    *   **Manage Entries:** Access submenu for Add, List, Get Password, Update, Delete, Generate, Strength Check, HIBP Check.
    *   **Change Master Password:** Updates login credentials (read warning about old data).
    *   **Exit:** Closes the application.
5.  Follow prompts. Password required for adding entries and retrieving/updating passwords.

## Security Warnings & Considerations

*   **Master Password:** **CRITICAL.** Forgotten = Data Loss. No recovery.
*   **Backup:** **BACK UP** `passwords.db` AND `data/auth_store_pm.json` securely and regularly.
*   **HIBP Check:** This feature sends the **SHA-1 hash** (not the password itself) of your password to an external API (`api.pwnedpasswords.com`). While designed to be safe, be aware you are interacting with an external service. User confirmation is requested before checking.
*   **Clipboard Risk:** Copying passwords to the clipboard can be risky if malware is present or clipboard history is not cleared.
*   **Database Not Fully Encrypted:** Only the password *value* is encrypted. Service names, usernames, URLs, notes, tags, and timestamps in `passwords.db` are **NOT** encrypted. Use full disk encryption.
*   **Password Change Behavior:** Changing the master password **DOES NOT** re-encrypt old passwords. Manually update old entries if needed.
*   **Template Code:** Example code, not audited. **Use at your own risk.**

## License

This project can be considered under the MIT License (or specify otherwise if needed). Use responsibly and understand the security implications.