# Digital Vault & API Key Manager (Project T12)

## Description

A secure, command-line repository for storing confidential files and sensitive API keys or secrets. Employs AES-GCM authenticated encryption derived from a master password using PBKDF2.

**IMPORTANT:** This is a template project demonstrating concepts. Security is hard. Review the warnings below before using for real sensitive data.

## Features

*   **Master Password Authentication:** Requires a master password to unlock the vault. Password hash stored securely using PBKDF2 and salt.
*   **Digital Vault Module:**
    *   Add files: Encrypts and stores files securely in a dedicated vault directory (`vault_data/files/`).
    *   List files: View metadata (original name, tags, notes) of stored files.
    *   Retrieve files: Decrypts and saves files to an export directory (`vault_exports/`).
    *   Delete files: Securely removes file metadata and the corresponding encrypted file.
*   **API Key Manager Module:**
    *   Add keys: Securely stores service name, key name, key value (encrypted), notes, and optional expiry date.
    *   List keys: Displays key metadata (service, name, expiry, notes) - **does not show the key value**. Checks for expired keys.
    *   Retrieve key value: Decrypts and displays the API key value (use with caution!). Updates last accessed time.
    *   Delete keys: Removes API key entries from the database.
*   **Strong Encryption:** Uses AES-256-GCM for authenticated encryption of file contents and API key values. Keys derived using PBKDF2.
*   **Secure Key Derivation:** Uses PBKDF2 with unique salts for password hashing and encryption key derivation. Salts stored in `vault_data/auth_store.json`.
*   **Session Timeout:** Basic idle timeout (~10 minutes) requires re-entering the master password.
*   **Change Master Password:** Allows changing the master password, which re-encrypts all stored data (can take time).

## Requirements

*   Python 3.7+
*   Libraries listed in `requirements.txt`:
    *   `pyinputplus`: For user input validation.
    *   `cryptography`: For hashing and encryption functions (PBKDF2, AES-GCM).
*   Standard libraries: `sqlite3`, `os`, `datetime`, `json`, `base64`, `hashlib`, `shutil`, `time`.

## Setup

1.  **Clone or Download:** Get the project files (`digital_vault_system.py`, `requirements.txt`).
2.  **Navigate to Directory:** Open your terminal or command prompt and change into the project directory (`digital_vault_system/`).
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
5.  **Run for First Time (Setup):**
    ```bash
    python digital_vault_system.py
    ```
    *   The script will detect it's the first run.
    *   It will guide you to set up a **strong, unique Master Password**. **REMEMBER THIS PASSWORD!**
    *   It will create the `vault_storage.db` database.
    *   It will create the `vault_data/` directory and the `vault_data/auth_store.json` file containing crucial salts and the password hash. **BACK UP `auth_store.json` and `vault_storage.db` securely!**
    *   It will create `vault_data/files/` and `vault_exports/` directories.

## Usage

1.  Make sure your virtual environment is activated.
2.  Run the script: `python digital_vault_system.py`
3.  Enter your Master Password when prompted.
4.  Navigate the main menu:
    *   **Digital Vault:** Manage encrypted files (Add, List, Retrieve, Delete).
    *   **API Key Manager:** Manage encrypted API keys (Add, List, Retrieve Value, Delete).
    *   **Change Master Password:** Securely update your master password (requires current password and re-encrypts all data).
    *   **Lock Vault (Logout):** Clears the temporary session key, requiring password re-entry on the next action or after timeout.
    *   **Exit Application:** Securely closes the application.
5.  Follow the on-screen prompts within each module.

## SECURITY WARNINGS - READ CAREFULLY!

*   **Master Password is KEY:** If you forget your master password, **ALL YOUR ENCRYPTED DATA WILL BE PERMANENTLY LOST**. There is no recovery mechanism. Choose a strong password you can remember or store securely (e.g., in a separate, reputable password manager).
*   **Backup Regularly:** **BACK UP** your `vault_storage.db` file AND the `vault_data/auth_store.json` file to a secure, separate location frequently. Losing either can lead to data loss. Also back up the `vault_data/files/` directory.
*   **Session Key Caching:** This script caches the derived encryption key in memory for performance during a session. This is **inherently insecure** if someone gains access to your computer's memory while the application is running. Use the 'Lock Vault' option or exit the application when not actively using it. The session has a basic idle timeout.
*   **Clipboard Risk:** When retrieving API key values, they are displayed on screen and potentially copied to the clipboard. Be mindful of clipboard managers and clear your clipboard after use.
*   **Database Not Fully Encrypted:** Only the file contents (in separate files) and the API key *values* are encrypted. Metadata (filenames, service names, tags, notes, dates) in the `vault_storage.db` file is **NOT** encrypted. Use full disk encryption on your computer for better protection of the database file itself.
*   **No Audit Logs / MFA:** This template lacks advanced security features like detailed audit trails or multi-factor authentication found in commercial products.
*   **Template Code:** This is example code. While efforts were made to use secure libraries and practices (PBKDF2, AES-GCM), it has not undergone rigorous security auditing. **Use at your own risk.**

## License

This project can be considered under the MIT License (or specify otherwise if needed). Use responsibly and understand the security implications.