# digital_vault_system.py (Revised and Simplified)

import sqlite3
import os
import datetime
import pyinputplus as pyip
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.exceptions import InvalidTag # Important for decryption error handling
import base64
import sys
import json
import hmac
import shutil
import uuid
import traceback

# --- Configuration ---
DB_NAME = "vault_storage.db"
VAULT_DATA_DIR = "vault_data"
VAULT_FILES_DIR = os.path.join(VAULT_DATA_DIR, "files")
VAULT_EXPORTS_DIR = "vault_exports"
AUTH_STORE_FILE = os.path.join(VAULT_DATA_DIR, "auth_store.json")
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# --- Security Constants ---
# NOTE: Reduce iterations for faster testing if needed, but increase for production
PW_HASH_ITERATIONS = 390000 # Lower for testing: 10000
ENC_KEY_ITERATIONS = 390000 # Lower for testing: 10000
AES_NONCE_BYTES = 12
SALT_BYTES = 16

# --- Helper Functions ---

def create_directories():
    """Creates necessary directories if they don't exist."""
    os.makedirs(VAULT_DATA_DIR, exist_ok=True)
    os.makedirs(VAULT_FILES_DIR, exist_ok=True)
    os.makedirs(VAULT_EXPORTS_DIR, exist_ok=True)

def derive_key(password: str, salt: bytes, iterations: int, length: int = 32) -> bytes:
    """Derives a key using PBKDF2HMACSHA256."""
    if not password: raise ValueError("Password cannot be empty.")
    if not salt or len(salt) != SALT_BYTES: raise ValueError("Invalid salt.")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=length,
        salt=salt,
        iterations=iterations,
    )
    return kdf.derive(password.encode('utf-8'))

def hash_password(password: str, salt: bytes) -> bytes:
    """Hashes a password for verification."""
    return derive_key(password, salt, PW_HASH_ITERATIONS)

def encrypt_text(plain_text: str, password: str, enc_salt: bytes) -> tuple[bytes, bytes] | None:
    """Encrypts text data using AES-GCM."""
    try:
        key = derive_key(password, enc_salt, ENC_KEY_ITERATIONS)
        aesgcm = AESGCM(key)
        nonce = os.urandom(AES_NONCE_BYTES)
        encrypted_data = aesgcm.encrypt(nonce, plain_text.encode('utf-8'), None)
        return nonce, encrypted_data # Return nonce and ciphertext
    except Exception as e:
        print(f"Encryption failed: {e}")
        return None

def decrypt_text(nonce: bytes, encrypted_data: bytes, password: str, enc_salt: bytes) -> str | None:
    """Decrypts text data using AES-GCM."""
    if not nonce or len(nonce) != AES_NONCE_BYTES:
        print("Decryption failed: Invalid nonce.")
        return None
    try:
        key = derive_key(password, enc_salt, ENC_KEY_ITERATIONS)
        aesgcm = AESGCM(key)
        decrypted_bytes = aesgcm.decrypt(nonce, encrypted_data, None)
        return decrypted_bytes.decode('utf-8')
    except InvalidTag:
        print("Decryption failed: Invalid password or corrupted data (InvalidTag).")
        return None
    except Exception as e:
        print(f"Decryption failed: {e}")
        return None

def encrypt_file(input_filepath: str, output_filepath: str, password: str, enc_salt: bytes) -> bool:
    """Encrypts a file using AES-GCM, writing nonce at the start."""
    try:
        key = derive_key(password, enc_salt, ENC_KEY_ITERATIONS)
        aesgcm = AESGCM(key)
        nonce = os.urandom(AES_NONCE_BYTES) # Generate ONE nonce for the entire file

        with open(input_filepath, 'rb') as infile, open(output_filepath, 'wb') as outfile:
            outfile.write(nonce) # Write nonce FIRST
            while True:
                chunk = infile.read(64 * 1024) # Read in chunks
                if not chunk:
                    break
                encrypted_chunk = aesgcm.encrypt(nonce, chunk, None)
                outfile.write(encrypted_chunk)
        return True
    except FileNotFoundError:
        print(f"File encryption failed: Input file not found '{input_filepath}'")
        return False
    except Exception as e:
        print(f"File encryption failed: {e}")
        # Clean up potentially incomplete output file
        if os.path.exists(output_filepath):
            try:
                os.remove(output_filepath)
            except OSError: pass # Ignore error if removal fails
        return False

def decrypt_file(input_filepath: str, output_filepath: str, password: str, enc_salt: bytes) -> bool:
    """Decrypts a file using AES-GCM, reading nonce from the start."""
    try:
        key = derive_key(password, enc_salt, ENC_KEY_ITERATIONS)
        aesgcm = AESGCM(key)

        with open(input_filepath, 'rb') as infile, open(output_filepath, 'wb') as outfile:
            nonce = infile.read(AES_NONCE_BYTES) # Read nonce FIRST
            if len(nonce) != AES_NONCE_BYTES:
                raise ValueError("Invalid encrypted file format (nonce missing or wrong size).")

            while True:
                chunk = infile.read(64 * 1024 + 16) # Read chunk + potential tag
                if not chunk:
                    break
                decrypted_chunk = aesgcm.decrypt(nonce, chunk, None)
                outfile.write(decrypted_chunk)
        return True
    except FileNotFoundError:
        print(f"File decryption failed: Input file not found '{input_filepath}'")
        return False
    except InvalidTag:
        print("File decryption failed: Invalid password or corrupted data (InvalidTag).")
        if os.path.exists(output_filepath):
            try:
                os.remove(output_filepath)
            except OSError: pass
        return False
    except ValueError as e: # Catch specific nonce error
         print(f"File decryption failed: {e}")
         if os.path.exists(output_filepath):
            try: os.remove(output_filepath)
            except OSError: pass
         return False
    except Exception as e:
        print(f"File decryption failed: {e}")
        if os.path.exists(output_filepath):
            try: os.remove(output_filepath)
            except OSError: pass
        return False

# --- Database Management ---

def initialize_database():
    """Creates the database and necessary tables if they don't exist."""
    create_directories() # Ensure directories are created first
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS vault_files (
            file_id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_name TEXT NOT NULL,
            encrypted_filename TEXT UNIQUE NOT NULL,
            tags TEXT,
            notes TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            key_id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name TEXT NOT NULL,
            key_name TEXT,
            encrypted_key_value BLOB NOT NULL,
            nonce BLOB NOT NULL,
            notes TEXT,
            expiry_date DATE,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP
        )''')
        conn.commit()
        print(f"Database '{DB_NAME}' initialized/checked successfully.")
    except sqlite3.Error as e:
        print(f"Database initialization error: {e}")
        sys.exit(1) # Critical error
    finally:
        if conn:
            conn.close()

# --- Authentication Manager ---

class AuthManager:
    def __init__(self, store_path=AUTH_STORE_FILE):
        self.store_path = store_path
        self.auth_data = self._load_auth_data() # Holds {'password_hash': str, 'pw_salt': bytes, 'enc_salt': bytes}

    def _load_auth_data(self):
        """Loads auth data, decodes salts from Base64."""
        if not os.path.exists(self.store_path):
            return None
        try:
            with open(self.store_path, 'r') as f:
                data_stored = json.load(f)
                # Validate keys exist
                if not all(k in data_stored for k in ["password_hash", "pw_salt", "enc_salt"]):
                    raise ValueError("Auth store file is missing required keys.")
                # Decode salts from base64 strings back to bytes
                pw_salt_bytes = base64.urlsafe_b64decode(data_stored["pw_salt"])
                enc_salt_bytes = base64.urlsafe_b64decode(data_stored["enc_salt"])
                return {
                    "password_hash": data_stored["password_hash"], # Keep hash as string
                    "pw_salt": pw_salt_bytes,
                    "enc_salt": enc_salt_bytes
                }
        except (FileNotFoundError, json.JSONDecodeError, ValueError, TypeError, base64.binascii.Error) as e:
            print(f"ERROR: Auth store '{self.store_path}' invalid or corrupt: {e}")
            print("You may need to delete the auth store file and set up a new password.")
            sys.exit(1) # Critical error

    def _save_auth_data(self):
        """Saves auth data, encodes salts to Base64."""
        if not self.auth_data: return
        try:
            data_to_save = {
                "password_hash": self.auth_data["password_hash"],
                # Encode salts from bytes to base64 strings for JSON storage
                "pw_salt": base64.urlsafe_b64encode(self.auth_data["pw_salt"]).decode('ascii'),
                "enc_salt": base64.urlsafe_b64encode(self.auth_data["enc_salt"]).decode('ascii'),
            }
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
            with open(self.store_path, 'w') as f:
                 json.dump(data_to_save, f, indent=4)
            print(f"Authentication data updated in '{self.store_path}'.")
        except (IOError, OSError) as e:
             print(f"FATAL ERROR: Could not save auth store: {e}")
             sys.exit(1) # Critical error

    def setup_master_password(self):
        """Guides user to set up the initial master password."""
        print("\n--- Master Password Setup ---")
        print("Choose a strong, unique password. FORGETTING IT MEANS LOSING ACCESS.")
        while True:
            password = pyip.inputPassword("Enter new Master Password: ")
            if not password:
                print("Password cannot be empty.")
                continue
            password_confirm = pyip.inputPassword("Confirm Master Password: ")
            if password == password_confirm:
                break
            else:
                print("Passwords do not match. Please try again.")

        # Generate new salts (bytes)
        pw_salt_bytes = os.urandom(SALT_BYTES)
        enc_salt_bytes = os.urandom(SALT_BYTES)

        # Hash the password (bytes)
        pw_hash_bytes = hash_password(password, pw_salt_bytes)

        # Store hash as b64 string, salts as bytes
        self.auth_data = {
            "password_hash": base64.urlsafe_b64encode(pw_hash_bytes).decode('ascii'),
            "pw_salt": pw_salt_bytes,
            "enc_salt": enc_salt_bytes,
        }
        self._save_auth_data()
        print("\nMaster Password set successfully.")

    def verify_password(self, password: str) -> bool:
        """Verifies the entered password against the stored hash using stored salt."""
        if not self.auth_data:
            print("Error: Authentication data not loaded.")
            return False
        try:
            stored_hash_bytes = base64.urlsafe_b64decode(self.auth_data["password_hash"])
            pw_salt_bytes = self.auth_data["pw_salt"] # Get the stored salt (bytes)

            # Hash the entered password using the *stored* salt
            entered_hash_bytes = hash_password(password, pw_salt_bytes)

            # Compare hashes securely
            return hmac.compare_digest(entered_hash_bytes, stored_hash_bytes)
        except (KeyError, TypeError, base64.binascii.Error) as e:
            print(f"Error during password verification (data corrupt?): {e}")
            return False

    def get_enc_salt(self) -> bytes | None:
        """Returns the encryption salt (bytes)."""
        if self.auth_data:
            return self.auth_data.get("enc_salt")
        return None

    def change_master_password(self):
        """Changes the master password and salts. Old data is NOT re-encrypted."""
        print("\n--- Change Master Password ---")
        if not self.auth_data:
             print("Error: Master password not set up yet.")
             return

        # 1. Verify current password
        current_password = pyip.inputPassword("Enter CURRENT Master Password: ")
        if not self.verify_password(current_password):
            print("Incorrect current password.")
            return

        # 2. Get and confirm new password
        print("\nEnter NEW Master Password.")
        while True:
            new_password = pyip.inputPassword("Enter new Master Password: ")
            if not new_password:
                print("New password cannot be empty.")
                continue
            new_password_confirm = pyip.inputPassword("Confirm new Master Password: ")
            if new_password == new_password_confirm:
                break
            else:
                print("New passwords do not match. Please try again.")

        # 3. Generate NEW salts
        new_pw_salt_bytes = os.urandom(SALT_BYTES)
        new_enc_salt_bytes = os.urandom(SALT_BYTES)

        # 4. Hash NEW password with NEW salt
        new_pw_hash_bytes = hash_password(new_password, new_pw_salt_bytes)

        # 5. Update auth_data with new hash and salts
        self.auth_data = {
            "password_hash": base64.urlsafe_b64encode(new_pw_hash_bytes).decode('ascii'),
            "pw_salt": new_pw_salt_bytes,
            "enc_salt": new_enc_salt_bytes,
        }

        # 6. Save the updated auth data
        self._save_auth_data()

        # 7. Warn user about implications
        print("\n" + "*"*60 + "\nIMPORTANT: Master Password updated successfully.")
        print("Existing encrypted data was *NOT* re-encrypted with the new parameters.")
        print("To protect old items with the new password/salts, you must:")
        print("  1. Retrieve/Export them using the OLD password (if possible).")
        print("  2. Delete them from the vault.")
        print("  3. Re-add them using the NEW password.")
        print("*"*60)

# --- Vault Manager ---

class VaultManager:
    def __init__(self, auth_manager: AuthManager):
        self.db_name = DB_NAME
        self.auth_manager = auth_manager

    def _connect(self):
        """Creates a database connection."""
        try:
            # Ensure types are detected for DATE/TIMESTAMP
            conn = sqlite3.connect(self.db_name, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
            conn.row_factory = sqlite3.Row # Access columns by name
            return conn
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            return None # Indicate failure

    def _execute_db(self, query, params=(), fetch_one=False, fetch_all=False, commit=False):
        """Helper to execute DB queries with error handling and connection management."""
        conn = self._connect()
        if not conn: return None # Connection failed
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            if commit:
                conn.commit()
                return cursor.lastrowid if "INSERT" in query.upper() else cursor.rowcount
            elif fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                 return cursor # Should not happen often
        except sqlite3.Error as e:
            print(f"Database error: {e}\nQuery: {query}\nParams: {params}")
            conn.rollback() # Rollback on error
            return None # Indicate failure
        finally:
            conn.close()

    def add_file(self):
        print("\n-- Add File to Vault --")
        source_path = pyip.inputFilepath("Enter the full path to the file: ")
        if not os.path.isfile(source_path):
            print(f"Error: File not found at '{source_path}'")
            return

        password = pyip.inputPassword("Enter Master Password to encrypt: ")
        if not self.auth_manager.verify_password(password):
            print("Incorrect password.")
            return

        enc_salt = self.auth_manager.get_enc_salt()
        if not enc_salt:
            print("Error: Cannot retrieve encryption salt. Auth data missing?")
            return

        original_name = os.path.basename(source_path)
        notes = pyip.inputStr("Enter notes (optional): ", blank=True)
        tags_in = pyip.inputStr("Enter tags (optional, comma-separated): ", blank=True)
        tags = ','.join(t.strip() for t in tags_in.split(',') if t.strip()) # Clean tags

        # Generate unique filename for encrypted storage
        encrypted_filename = f"{uuid.uuid4()}.enc"
        encrypted_filepath = os.path.join(VAULT_FILES_DIR, encrypted_filename)

        print(f"Encrypting '{original_name}'...")
        if encrypt_file(source_path, encrypted_filepath, password, enc_salt):
            # If encryption succeeds, add metadata to DB
            result = self._execute_db(
                "INSERT INTO vault_files (original_name, encrypted_filename, tags, notes) VALUES (?, ?, ?, ?)",
                (original_name, encrypted_filename, tags, notes),
                commit=True
            )
            if result is not None:
                print(f"File '{original_name}' added successfully (ID: {result}).")
            else:
                print("Database error occurred after encryption. Attempting cleanup.")
                # Cleanup encrypted file if DB insert failed
                if os.path.exists(encrypted_filepath):
                    try: os.remove(encrypted_filepath)
                    except OSError: print("Warning: Could not remove partially added encrypted file.")
        else:
            print("File encryption failed. Aborting add.")

    def list_files(self):
        print("\n-- Vault Files --")
        search = pyip.inputStr("Search term (in name/notes, leave blank for all): ", blank=True)
        tag = pyip.inputStr("Filter by tag (leave blank for all): ", blank=True)

        query = "SELECT file_id, original_name, tags, notes, added_at FROM vault_files"
        conditions = []
        params = []

        if search:
            conditions.append("(original_name LIKE ? OR notes LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        if tag:
            # Ensure tag search is robust (e.g., handles start, middle, end of tag list)
            conditions.append("(',' || tags || ',' LIKE ?)")
            params.append(f"%,{tag},%") # Search for tag surrounded by commas

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY added_at DESC"

        files = self._execute_db(query, params, fetch_all=True)

        if files is None:
            print("Error retrieving file list from database.")
            return
        if not files:
            print("No files found matching criteria.")
            return

        print("\n{:<5} {:<40} {:<25} {:<19} {}".format("ID", "Original Name", "Tags", "Added At", "Notes"))
        print("-" * 110)
        for f in files:
            added_time_str = f['added_at'].strftime(DATETIME_FORMAT) if f['added_at'] else "N/A"
            print("{:<5} {:<40} {:<25} {:<19} {}".format(
                f['file_id'],
                f['original_name'][:38] + ('..' if len(f['original_name']) > 38 else ''), # Truncate long names
                f['tags'] or "",
                added_time_str,
                f['notes'] or ""
            ))
        print("-" * 110)

    def retrieve_file(self):
        print("\n-- Retrieve File --")
        try:
            file_id = pyip.inputInt("Enter the File ID to retrieve: ", min=1)
        except (pyip.RetryLimitException, ValueError):
            print("Invalid ID entered.")
            return

        password = pyip.inputPassword("Enter Master Password to decrypt: ")
        if not self.auth_manager.verify_password(password):
            print("Incorrect password.")
            return

        enc_salt = self.auth_manager.get_enc_salt()
        if not enc_salt:
            print("Error: Cannot retrieve encryption salt.")
            return

        # Get file info from DB
        file_info = self._execute_db("SELECT original_name, encrypted_filename FROM vault_files WHERE file_id=?", (file_id,), fetch_one=True)

        if file_info is None: # Handles DB error or not found
            print(f"Error retrieving info or File ID {file_id} not found.")
            return

        original_name = file_info['original_name']
        encrypted_filename = file_info['encrypted_filename']
        encrypted_filepath = os.path.join(VAULT_FILES_DIR, encrypted_filename)

        if not os.path.exists(encrypted_filepath):
            print(f"Error: Encrypted file '{encrypted_filename}' is missing from the vault data directory!")
            print("Database record exists, but the file is gone.")
            return

        # Determine output path
        default_output_path = os.path.join(VAULT_EXPORTS_DIR, original_name)
        output_path = pyip.inputFilepath(f"Enter path to save decrypted file as [{default_output_path}]: ", default=default_output_path, blank=True)
        output_path = output_path or default_output_path # Use default if blank

        # Check for overwrite
        if os.path.exists(output_path):
            if pyip.inputYesNo(f"File '{output_path}' already exists. Overwrite? (yes/no): ", default='no') == 'no':
                print("Retrieval cancelled.")
                return

        # Ensure output directory exists
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        except OSError as e:
            print(f"Error creating output directory '{os.path.dirname(output_path)}': {e}")
            return

        print(f"Decrypting to '{output_path}'...")
        if decrypt_file(encrypted_filepath, output_path, password, enc_salt):
            print("File retrieved successfully.")
        else:
            print("File decryption failed. The output file (if created) may be incomplete or corrupt.")

    def delete_file(self):
        print("\n-- Delete File --")
        try:
            file_id = pyip.inputInt("Enter the File ID to delete: ", min=1)
        except (pyip.RetryLimitException, ValueError):
            print("Invalid ID entered.")
            return

        # Get file info first to confirm and get encrypted filename
        file_info = self._execute_db("SELECT original_name, encrypted_filename FROM vault_files WHERE file_id=?", (file_id,), fetch_one=True)

        if file_info is None: # Handles DB error or not found
            print(f"Error retrieving info or File ID {file_id} not found.")
            return

        original_name = file_info['original_name']
        encrypted_filename = file_info['encrypted_filename']
        encrypted_filepath = os.path.join(VAULT_FILES_DIR, encrypted_filename)

        # Confirm deletion
        if pyip.inputYesNo(f"Are you sure you want to permanently delete '{original_name}' (ID: {file_id})? (yes/no): ", default='no') == 'no':
            print("Deletion cancelled.")
            return

        # Delete from database first
        rows_deleted = self._execute_db("DELETE FROM vault_files WHERE file_id=?", (file_id,), commit=True)

        if rows_deleted is None:
            print("Database error occurred during deletion. Aborting.")
            return
        elif rows_deleted == 0:
             print("File ID not found in database during deletion attempt (maybe deleted already?).")
             # Still check if the file exists and try to delete it
        else:
            print("Database record deleted successfully.")

        # Then delete the actual encrypted file
        if os.path.exists(encrypted_filepath):
            try:
                os.remove(encrypted_filepath)
                print(f"Encrypted file '{encrypted_filename}' deleted successfully.")
            except OSError as e:
                print(f"Error deleting encrypted file '{encrypted_filepath}': {e}")
                print("Database record was deleted, but the file may still exist.")
        else:
            print(f"Warning: Encrypted file '{encrypted_filename}' was not found for deletion (already deleted?).")

    def menu(self):
         """Displays the Vault menu and handles user actions."""
         while True:
            print("\n--- Vault Menu ---")
            action = pyip.inputMenu(['Add File', 'List Files', 'Retrieve File', 'Delete File', 'Back'], numbered=True)
            if action == 'Add File':
                self.add_file()
            elif action == 'List Files':
                self.list_files()
            elif action == 'Retrieve File':
                self.retrieve_file()
            elif action == 'Delete File':
                self.delete_file()
            elif action == 'Back':
                break

# --- API Key Manager ---

class ApiKeyManager:
    def __init__(self, auth_manager: AuthManager):
        self.db_name = DB_NAME
        self.auth_manager = auth_manager
        # Re-use the _connect and _execute_db from VaultManager for consistency
        # (or duplicate them if you prefer strict separation)
        vm = VaultManager(auth_manager)
        self._connect = vm._connect
        self._execute_db = vm._execute_db

    def add_key(self):
        print("\n-- Add API Key --")
        service = pyip.inputStr("Service Name: ")
        key_name = pyip.inputStr("Key Name/Identifier (optional): ", blank=True)
        key_value = pyip.inputStr("API Key Value: ") # Consider inputPassword if very sensitive
        notes = pyip.inputStr("Notes (optional): ", blank=True)
        expiry_s = pyip.inputStr(f"Expiry Date ({DATE_FORMAT}, optional, e.g., 2025-12-31): ", blank=True)

        expiry_d = None
        if expiry_s:
            try:
                expiry_d = datetime.datetime.strptime(expiry_s, DATE_FORMAT).date()
            except ValueError:
                print(f"Invalid date format. Please use {DATE_FORMAT}. Key not added.")
                return

        password = pyip.inputPassword("Enter Master Password to encrypt: ")
        if not self.auth_manager.verify_password(password):
            print("Incorrect password.")
            return

        enc_salt = self.auth_manager.get_enc_salt()
        if not enc_salt:
            print("Error: Cannot retrieve encryption salt.")
            return

        print("Encrypting API key...")
        encryption_result = encrypt_text(key_value, password, enc_salt)

        if not encryption_result:
            print("Encryption failed. Key not added.")
            return

        nonce, encrypted_val = encryption_result

        # Add to database
        result = self._execute_db(
            "INSERT INTO api_keys (service_name, key_name, encrypted_key_value, nonce, notes, expiry_date) VALUES (?, ?, ?, ?, ?, ?)",
            (service, key_name or None, encrypted_val, nonce, notes or None, expiry_d),
            commit=True
        )

        if result is not None:
            print(f"API Key for '{service}' added successfully (ID: {result}).")
        else:
            print("Database error occurred. Key not added.")

    def list_keys(self, check_expiry=False):
        print("\n-- API Keys --")
        keys = self._execute_db("SELECT key_id, service_name, key_name, notes, expiry_date FROM api_keys ORDER BY service_name, key_name", fetch_all=True)

        if keys is None:
            print("Error retrieving keys from database.")
            return
        if not keys:
            print("No API keys found.")
            return

        print("\n{:<5} {:<25} {:<20} {:<12} {}".format("ID", "Service", "Key Name", "Expires", "Notes"))
        print("-" * 80)
        today = datetime.date.today()
        expired_count = 0
        expiring_soon_count = 0
        for k in keys:
            expiry_d = k['expiry_date'] # Already parsed as date by sqlite3 connector
            expiry_s = expiry_d.strftime(DATE_FORMAT) if isinstance(expiry_d, datetime.date) else "None"
            expiry_stat = ""
            if isinstance(expiry_d, datetime.date):
                 days_until_expiry = (expiry_d - today).days
                 if days_until_expiry < 0:
                     expiry_stat = " (EXPIRED!)"
                     expired_count += 1
                 elif days_until_expiry <= 30:
                     expiry_stat = f" (in {days_until_expiry}d)"
                     expiring_soon_count += 1

            print("{:<5} {:<25} {:<20} {:<12}{} {}".format(
                k['key_id'],
                k['service_name'],
                k['key_name'] or "",
                expiry_s,
                expiry_stat,
                k['notes'] or ""
            ))
        print("-" * 80)
        if check_expiry:
             if expired_count > 0: print(f"Found {expired_count} expired key(s).")
             if expiring_soon_count > 0: print(f"Found {expiring_soon_count} key(s) expiring within 30 days.")


    def get_key_value(self):
        print("\n-- Get API Key Value --")
        try:
            key_id = pyip.inputInt("Enter the API Key ID to retrieve: ", min=1)
        except (pyip.RetryLimitException, ValueError):
            print("Invalid ID entered.")
            return

        password = pyip.inputPassword("Enter Master Password to decrypt: ")
        if not self.auth_manager.verify_password(password):
            print("Incorrect password.")
            return

        enc_salt = self.auth_manager.get_enc_salt()
        if not enc_salt:
            print("Error: Cannot retrieve encryption salt.")
            return

        # Get key info (needs nonce)
        key_info = self._execute_db(
            "SELECT service_name, key_name, encrypted_key_value, nonce FROM api_keys WHERE key_id=?",
            (key_id,),
            fetch_one=True
        )

        if key_info is None: # Handles DB error or not found
            print(f"Error retrieving info or API Key ID {key_id} not found.")
            return

        print(f"Decrypting key for '{key_info['service_name']}'...")
        decrypted_value = decrypt_text(
            key_info['nonce'],
            key_info['encrypted_key_value'],
            password,
            enc_salt
        )

        if decrypted_value is not None:
            print("\n" + "="*20 + " DECRYPTED VALUE " + "="*20)
            print(f" Service: {key_info['service_name']}")
            if key_info['key_name']: print(f" Key Name: {key_info['key_name']}")
            print(f"\n {decrypted_value}")
            print("="*57)
            # Update last accessed time
            self._execute_db("UPDATE api_keys SET last_accessed = CURRENT_TIMESTAMP WHERE key_id=?", (key_id,), commit=True)
        else:
            print("Decryption failed.")

    def delete_key(self):
        print("\n-- Delete API Key --")
        try:
            key_id = pyip.inputInt("Enter the API Key ID to delete: ", min=1)
        except (pyip.RetryLimitException, ValueError):
            print("Invalid ID entered.")
            return

        # Get info first for confirmation
        key_info = self._execute_db("SELECT service_name FROM api_keys WHERE key_id=?", (key_id,), fetch_one=True)

        if key_info is None: # Handles DB error or not found
            print(f"Error retrieving info or API Key ID {key_id} not found.")
            return

        service_name = key_info['service_name']

        if pyip.inputYesNo(f"Are you sure you want to permanently delete the key for '{service_name}' (ID: {key_id})? (yes/no): ", default='no') == 'no':
            print("Deletion cancelled.")
            return

        # Delete from database
        rows_deleted = self._execute_db("DELETE FROM api_keys WHERE key_id=?", (key_id,), commit=True)

        if rows_deleted is None:
            print("Database error occurred during deletion.")
        elif rows_deleted > 0:
            print(f"API Key for '{service_name}' deleted successfully.")
        else:
            print("API Key ID not found in database during deletion attempt (maybe deleted already?).")

    def menu(self):
         """Displays the API Key menu and handles user actions."""
         while True:
            print("\n--- API Key Manager Menu ---")
            action = pyip.inputMenu(['Add Key', 'List Keys', 'List (Check Expiry)', 'Get Key Value', 'Delete Key', 'Back'], numbered=True)
            if action == 'Add Key':
                self.add_key()
            elif action == 'List Keys':
                self.list_keys(check_expiry=False)
            elif action == 'List (Check Expiry)':
                self.list_keys(check_expiry=True)
            elif action == 'Get Key Value':
                self.get_key_value()
            elif action == 'Delete Key':
                self.delete_key()
            elif action == 'Back':
                break

# --- Main Application Flow ---

def main():
    """Main function to run the application."""
    initialize_database()
    auth_manager = AuthManager()

    # --- Authentication ---
    if auth_manager.auth_data is None:
        print("No existing authentication data found.")
        auth_manager.setup_master_password()
        # Re-instantiate to load the newly created data
        auth_manager = AuthManager()
        if auth_manager.auth_data is None: # Check if setup failed
             print("Failed to set up master password. Exiting.")
             sys.exit(1)
    else:
        print("Existing vault detected.")
        attempts = 0
        max_attempts = 3
        while attempts < max_attempts:
             password = pyip.inputPassword("Enter Master Password: ")
             if auth_manager.verify_password(password):
                 print("Vault unlocked.")
                 break
             else:
                 attempts += 1
                 print(f"Incorrect password. ({max_attempts - attempts} attempts left)")
                 if attempts >= max_attempts:
                     print("Maximum login attempts reached. Exiting.")
                     sys.exit(1)

    # --- Initialized Managers ---
    vault_manager = VaultManager(auth_manager)
    apikey_manager = ApiKeyManager(auth_manager)

    # --- Main Menu Loop ---
    while True:
        print("\n======= Digital Vault & Key Manager =======")
        choice = pyip.inputMenu(['Manage Vault Files', 'Manage API Keys', 'Change Master Password', 'Exit'], numbered=True)

        if choice == 'Manage Vault Files':
            vault_manager.menu()
        elif choice == 'Manage API Keys':
            apikey_manager.menu()
        elif choice == 'Change Master Password':
            auth_manager.change_master_password()
            # Optional: force re-authentication after password change?
            # print("Password changed. Please re-authenticate.")
            # break # or sys.exit(0)
        elif choice == 'Exit':
            print("Locking vault and exiting.")
            sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user. Exiting.")
        sys.exit(1)
    except Exception as e:
        print("\n" + "="*20 + " CRITICAL ERROR " + "="*20)
        print(f"An unexpected error occurred: {e}")
        print("\n--- Traceback ---")
        traceback.print_exc()
        print("="*56)
        sys.exit(1)