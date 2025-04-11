# password_manager.py

import sqlite3
import os
import datetime
import pyinputplus as pyip
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import sys
import json
import hashlib
import hmac # For compare_digest
import random
import string
import re
import requests
import time

# --- Configuration ---
DB_NAME = "passwords.db"
DATA_DIR = "data"
AUTH_STORE_FILE = os.path.join(DATA_DIR, "auth_store_pm.json") # Unique name
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# --- Security Constants ---
PW_HASH_ITERATIONS = 390000 # Iterations for password hashing (PBKDF2)
ENC_KEY_ITERATIONS = 390000 # Iterations for deriving encryption key (PBKDF2)
AES_NONCE_BYTES = 12        # Standard nonce size for AES-GCM

# --- HIBP API ---
HIBP_API_URL = "https://api.pwnedpasswords.com/range/"
# Rate limiting recommended for HIBP - basic delay implemented
HIBP_REQUEST_DELAY = 1.6 # Seconds between HIBP requests

# --- Database Setup ---
def initialize_database():
    """Creates the database and necessary tables if they don't exist."""
    os.makedirs(DATA_DIR, exist_ok=True) # Ensure data directory exists

    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cursor = conn.cursor()

    # Passwords Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS passwords (
        entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_name TEXT NOT NULL, -- Website, App name etc.
        username TEXT,
        url TEXT,
        encrypted_password BLOB NOT NULL, -- Store encrypted password as bytes
        nonce BLOB NOT NULL,         -- Nonce used for AES-GCM encryption
        notes TEXT,
        tags TEXT,                   -- Comma-separated tags
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Trigger to update 'updated_at'
    cursor.execute('''
    CREATE TRIGGER IF NOT EXISTS update_pwd_timestamp
    AFTER UPDATE ON passwords FOR EACH ROW
    BEGIN
        UPDATE passwords SET updated_at = CURRENT_TIMESTAMP WHERE entry_id = OLD.entry_id;
    END;
    ''')

    conn.commit()
    conn.close()
    print(f"Database '{DB_NAME}' initialized/checked successfully.")


# --- Cryptography Helper Functions ---
# (derive_key, encrypt_text, decrypt_text, hash_password are reused from T12)
def derive_key(password: str, salt: bytes, iterations: int, length: int = 32) -> bytes:
    if not password: raise ValueError("Password cannot be empty.")
    if not salt: raise ValueError("Salt cannot be empty.")
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(),length=length,salt=salt,iterations=iterations,)
    return kdf.derive(password.encode())

def encrypt_text(plain_text: str, password: str, enc_salt: bytes) -> tuple[bytes, bytes] | None:
    try:
        key = derive_key(password, enc_salt, ENC_KEY_ITERATIONS)
        aesgcm = AESGCM(key)
        nonce = os.urandom(AES_NONCE_BYTES)
        encrypted_data = aesgcm.encrypt(nonce, plain_text.encode(), None)
        return nonce, encrypted_data
    except Exception as e: print(f"Encryption failed: {e}"); return None

def decrypt_text(nonce: bytes, encrypted_data: bytes, password: str, enc_salt: bytes) -> str | None:
    try:
        key = derive_key(password, enc_salt, ENC_KEY_ITERATIONS)
        aesgcm = AESGCM(key)
        decrypted_bytes = aesgcm.decrypt(nonce, encrypted_data, None)
        return decrypted_bytes.decode()
    except Exception as e: print(f"Decryption failed: {e}"); return None

def hash_password(password: str, salt: bytes) -> bytes:
    return derive_key(password, salt, PW_HASH_ITERATIONS)

# --- Authentication Manager ---
# (AuthManager class is reused from T12 simplified version)
class AuthManager:
    def __init__(self, store_path=AUTH_STORE_FILE):
        self.store_path = store_path
        self.auth_data = self._load_auth_data()
    def _load_auth_data(self):
        if os.path.exists(self.store_path):
            try:
                with open(self.store_path, 'r') as f:
                    data = json.load(f)
                    if not all(k in data for k in ["password_hash", "pw_salt", "enc_salt"]):
                        raise ValueError("Auth store missing keys.")
                    data["pw_salt_bytes"] = base64.urlsafe_b64decode(data["pw_salt"])
                    data["enc_salt_bytes"] = base64.urlsafe_b64decode(data["enc_salt"])
                    return data
            except Exception as e:
                print(f"ERROR: Auth store '{self.store_path}' invalid: {e}"); sys.exit(1)
        else: return None
    def _save_auth_data(self):
        if not self.auth_data: return
        data_to_save = {"password_hash": self.auth_data["password_hash"], "pw_salt": self.auth_data["pw_salt"], "enc_salt": self.auth_data["enc_salt"],}
        try:
             os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
             with open(self.store_path, 'w') as f: json.dump(data_to_save, f, indent=4)
             print(f"Auth data updated: '{self.store_path}'.")
        except IOError as e: print(f"FATAL: Could not save auth store: {e}"); sys.exit(1)
    def get_salts(self) -> tuple[bytes, bytes] | tuple[None, None]:
        if self.auth_data: return self.auth_data.get("pw_salt_bytes"), self.auth_data.get("enc_salt_bytes")
        return None, None
    def setup_master_password(self):
        print("\n--- Master Password Setup ---")
        print("Choose a strong password for your Password Manager.")
        while True:
            pwd = pyip.inputPassword("Enter Master Password: ")
            pwd_c = pyip.inputPassword("Confirm: ");
            if not pwd: print("Cannot be empty."); continue
            if pwd == pwd_c: break
            else: print("No match."); continue
        pw_salt = os.urandom(16); enc_salt = os.urandom(16)
        pw_hash = hash_password(pwd, pw_salt)
        self.auth_data = {
            "password_hash": base64.urlsafe_b64encode(pw_hash).decode('ascii'),
            "pw_salt": base64.urlsafe_b64encode(pw_salt).decode('ascii'),
            "enc_salt": base64.urlsafe_b64encode(enc_salt).decode('ascii'),
            "pw_salt_bytes": pw_salt, "enc_salt_bytes": enc_salt,}
        self._save_auth_data(); print("\nMaster Password set.")
    def verify_password(self, password: str) -> bool:
        if not self.auth_data: return False
        try:
            stored_hash = base64.urlsafe_b64decode(self.auth_data["password_hash"])
            pw_salt = self.auth_data["pw_salt_bytes"]
            entered_hash = hash_password(password, pw_salt)
            return hmac.compare_digest(entered_hash, stored_hash)
        except Exception as e: print(f"Verify error: {e}"); return False
    def change_master_password(self):
        print("\n--- Change Master Password ---")
        if not self.auth_data: print("Not set up yet."); return
        old_pwd = pyip.inputPassword("Current Password: ");
        if not self.verify_password(old_pwd): print("Incorrect pwd."); return
        print("\nEnter NEW Master Password.")
        while True:
            new_pwd = pyip.inputPassword("New Password: ")
            new_pwd_c = pyip.inputPassword("Confirm: ");
            if not new_pwd: print("Cannot be empty."); continue
            if new_pwd == new_pwd_c: break
            else: print("No match."); continue
        new_pw_salt = os.urandom(16); new_enc_salt = os.urandom(16)
        new_pw_hash = hash_password(new_pwd, new_pw_salt)
        self.auth_data["password_hash"] = base64.urlsafe_b64encode(new_pw_hash).decode('ascii')
        self.auth_data["pw_salt"] = base64.urlsafe_b64encode(new_pw_salt).decode('ascii')
        self.auth_data["enc_salt"] = base64.urlsafe_b64encode(new_enc_salt).decode('ascii')
        self.auth_data["pw_salt_bytes"] = new_pw_salt
        self.auth_data["enc_salt_bytes"] = new_enc_salt
        self._save_auth_data()
        print("\n" + "*"*60 + "\nIMPORTANT: Password updated. Existing entries NOT re-encrypted.\nManually update old entries if needed.\n" + "*"*60)


# --- Password Generation & Checking ---
def generate_password(length=16, use_uppercase=True, use_digits=True, use_symbols=True) -> str:
    """Generates a random password with specified complexity."""
    characters = string.ascii_lowercase
    if use_uppercase: characters += string.ascii_uppercase
    if use_digits: characters += string.digits
    if use_symbols: characters += string.punctuation # Adjust symbols as needed

    if not characters: return "(No character sets selected)"

    # Ensure minimum length
    length = max(8, length)

    # Ensure password includes at least one of each selected type (basic enforcement)
    password = []
    if use_uppercase: password.append(random.choice(string.ascii_uppercase))
    if use_digits: password.append(random.choice(string.digits))
    if use_symbols: password.append(random.choice(string.punctuation))
    # Fill remaining length
    remaining_length = length - len(password)
    password.extend(random.choices(characters, k=remaining_length))
    # Shuffle to mix character types
    random.shuffle(password)

    return "".join(password)

def check_password_strength(password: str) -> str:
    """Provides a basic assessment of password strength."""
    score = 0
    if not password: return "Very Weak (Empty)"

    # Length
    if len(password) >= 16: score += 3
    elif len(password) >= 12: score += 2
    elif len(password) >= 8: score += 1

    # Character types
    if re.search(r"[a-z]", password): score += 1
    if re.search(r"[A-Z]", password): score += 1
    if re.search(r"[0-9]", password): score += 1
    if re.search(r"[!\"#$%&'()*+,-./:;<=>?@[\\\]^_`{|}~]", password): score += 1 # Common symbols

    # Deductions (simple checks)
    if password.lower() in ["password", "123456", "qwerty", "admin"]: score -= 2
    # Could add checks for common words, sequences etc. (more complex)

    if score >= 7: return "Very Strong"
    elif score >= 5: return "Strong"
    elif score >= 3: return "Moderate"
    elif score >= 1: return "Weak"
    else: return "Very Weak"

def check_hibp(password: str) -> tuple[bool | None, str]:
    """
    Checks if a password hash appears in the HIBP Pwned Passwords database.
    Returns (is_pwned, message). is_pwned is None if check fails.
    """
    if not password: return None, "Password is empty."

    # 1. Hash the password using SHA-1 (required by HIBP API)
    sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
    prefix = sha1_hash[:5]
    suffix = sha1_hash[5:]

    print(f"Checking HIBP for password hash prefix: {prefix}...")
    try:
        # 2. Query the HIBP API with the prefix
        time.sleep(HIBP_REQUEST_DELAY) # Basic rate limiting
        response = requests.get(HIBP_API_URL + prefix, timeout=10)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        # 3. Check the response for the suffix
        hashes = (line.split(':') for line in response.text.splitlines())
        for h, count in hashes:
            if h == suffix:
                return True, f"Warning: Password pwned! Found {count} times in breaches."

        return False, "Good news: Password not found in HIBP breaches."

    except requests.exceptions.Timeout:
        return None, "Error: HIBP request timed out."
    except requests.exceptions.HTTPError as e:
        return None, f"Error: HIBP API request failed (Status {e.response.status_code})."
    except requests.exceptions.RequestException as e:
        return None, f"Error: Could not connect to HIBP API: {e}"
    except Exception as e:
        return None, f"Error during HIBP check: {e}"


# --- Password Manager Class ---
class PasswordManager:
    def __init__(self, auth_manager: AuthManager, db_name=DB_NAME):
        self.db_name = db_name
        self.auth_manager = auth_manager

    def _connect(self):
        return sqlite3.connect(self.db_name, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)

    def add_entry(self):
        """Adds a new password entry."""
        print("\n-- Add New Password Entry --")
        service = pyip.inputStr("Service/Website/App Name: ")
        username = pyip.inputStr("Username/Email (optional): ", blank=True)
        url = pyip.inputStr("URL (optional): ", blank=True)
        notes = pyip.inputStr("Notes (optional): ", blank=True)
        tags_input = pyip.inputStr("Tags (comma-sep, optional): ", blank=True)
        tags = ','.join(tag.strip() for tag in tags_input.split(',') if tag.strip())

        # Password input / generation
        use_generated = pyip.inputYesNo("Generate a strong password? (yes/no): ", default='yes')
        password_to_save = ""
        if use_generated == 'yes':
             length = pyip.inputInt("Password length (min 12): ", default=18, min=12)
             inc_upper = pyip.inputYesNo("Include uppercase? (Y/n): ", default='yes')
             inc_digits = pyip.inputYesNo("Include digits? (Y/n): ", default='yes')
             inc_symbols = pyip.inputYesNo("Include symbols? (Y/n): ", default='yes')
             password_to_save = generate_password(length, inc_upper=='yes', inc_digits=='yes', inc_symbols=='yes')
             print(f"Generated Password: {password_to_save}")
             # Optionally offer to check strength/HIBP here?
        else:
             password_to_save = pyip.inputPassword("Enter Password: ")
             if not password_to_save: print("Password cannot be empty."); return

        # Check strength and HIBP (optional but recommended)
        strength = check_password_strength(password_to_save)
        print(f"Password Strength: {strength}")
        if strength in ["Weak", "Very Weak"]:
            if pyip.inputYesNo("Password seems weak. Continue anyway? (y/N): ", default='no') == 'no':
                print("Add entry cancelled."); return

        check_online = pyip.inputYesNo("Check password against Have I Been Pwned (HIBP)? (Requires internet) (y/N): ", default='no')
        if check_online == 'yes':
             is_pwned, message = check_hibp(password_to_save)
             print(message)
             if is_pwned is True:
                 if pyip.inputYesNo("Password found in breaches. Use anyway? (y/N): ", default='no') == 'no':
                      print("Add entry cancelled."); return
             elif is_pwned is None:
                  print("Could not complete HIBP check. Proceed with caution.")

        # Encrypt password
        master_pwd = pyip.inputPassword("Enter Master Password to save entry: ")
        if not self.auth_manager.verify_password(master_pwd): print("Incorrect pwd."); return
        _, enc_salt = self.auth_manager.get_salts();
        if not enc_salt: print("No enc salt."); return

        print("Encrypting password...")
        encrypted_result = encrypt_text(password_to_save, master_pwd, enc_salt)
        if not encrypted_result: print("Encryption failed."); return

        nonce, enc_pwd = encrypted_result
        conn = self._connect(); cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO passwords (service_name, username, url, encrypted_password, nonce, notes, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (service, username, url, enc_pwd, nonce, notes, tags))
            conn.commit(); print(f"Entry for '{service}' added (ID: {cursor.lastrowid}).")
        except sqlite3.Error as e: print(f"DB add error: {e}"); conn.rollback()
        finally: conn.close()


    def list_entries(self, search_term=None, tag_filter=None):
        """Lists password entries (metadata only)."""
        print("\n-- Password Entries --")
        conn = self._connect(); conn.row_factory = sqlite3.Row; cursor = conn.cursor()
        try:
            q = "SELECT entry_id, service_name, username, url, tags FROM passwords"
            p = []; c = []
            if search_term: c.append("(service_name LIKE ? OR username LIKE ? OR url LIKE ? OR notes LIKE ?)"); p.extend([f"%{search_term}%"]*4)
            if tag_filter: c.append("tags LIKE ?"); p.append(f"%{tag_filter}%")
            if c: q += " WHERE " + " AND ".join(c)
            q += " ORDER BY service_name COLLATE NOCASE ASC" # Case-insensitive sort
            cursor.execute(q, p); entries = cursor.fetchall()
            if not entries: print("No entries found" + (" matching criteria." if (search_term or tag_filter) else ".")); return

            print("\n{:<5} {:<30} {:<25} {:<30} {}".format("ID", "Service", "Username", "URL", "Tags"))
            print("-" * 110)
            for e in entries: print("{:<5} {:<30} {:<25} {:<30} {}".format(e['entry_id'], e['service_name'], e['username'] or "", e['url'] or "", e['tags'] or ""));
            print("-" * 110)
        except sqlite3.Error as e: print(f"DB list error: {e}")
        finally: conn.close()


    def get_password(self):
        """Retrieves and decrypts a password."""
        print("\n-- Retrieve Password --")
        entry_id = pyip.inputInt("Enter Entry ID to retrieve password for: ", min=1)

        master_pwd = pyip.inputPassword("Enter Master Password: ")
        if not self.auth_manager.verify_password(master_pwd): print("Incorrect pwd."); return
        _, enc_salt = self.auth_manager.get_salts();
        if not enc_salt: print("No enc salt."); return

        conn = self._connect(); conn.row_factory = sqlite3.Row; cursor = conn.cursor()
        try:
            cursor.execute("SELECT service_name, username, encrypted_password, nonce FROM passwords WHERE entry_id = ?", (entry_id,))
            entry = cursor.fetchone();
            if not entry: print(f"ID {entry_id} not found."); return

            print(f"Decrypting password for '{entry['service_name']}' ({entry['username'] or 'N/A'})...")
            dec_pwd = decrypt_text(entry['nonce'], entry['encrypted_password'], master_pwd, enc_salt)

            if dec_pwd is not None:
                 print("\n" + "="*20 + " PASSWORD RETRIEVED " + "="*20)
                 print(f"Service: {entry['service_name']}")
                 print(f"Username: {entry['username'] or ''}")
                 print(f"\nPassword: {dec_pwd}")
                 print("="*60)
                 print("WARNING: Avoid leaving passwords visible. Consider copying.")
                 # Add to clipboard? Use pyperclip if installed.
                 try:
                     import pyperclip
                     pyperclip.copy(dec_pwd)
                     print("(Password copied to clipboard)")
                 except ImportError:
                     pass # pyperclip not installed, do nothing
            else: print("Failed to decrypt password.")
        except sqlite3.Error as e: print(f"DB get error: {e}")
        finally: conn.close()


    def update_entry(self):
        """Updates an existing password entry."""
        print("\n-- Update Password Entry --")
        entry_id = pyip.inputInt("Enter Entry ID to update: ", min=1)

        master_pwd = pyip.inputPassword("Enter Master Password: ")
        if not self.auth_manager.verify_password(master_pwd): print("Incorrect pwd."); return
        _, enc_salt = self.auth_manager.get_salts();
        if not enc_salt: print("No enc salt."); return

        conn = self._connect(); conn.row_factory = sqlite3.Row; cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM passwords WHERE entry_id = ?", (entry_id,))
            entry = cursor.fetchone();
            if not entry: print(f"ID {entry_id} not found."); return

            print(f"\nCurrent Service: {entry['service_name']}")
            print(f"Current Username: {entry['username']}")
            print(f"Current URL: {entry['url']}")
            # Don't show current password unless asked

            new_service = pyip.inputStr("New Service (keep current): ", blank=True) or entry['service_name']
            new_username = pyip.inputStr("New Username (keep current): ", blank=True) or entry['username']
            new_url = pyip.inputStr("New URL (keep current): ", blank=True) or entry['url']
            new_notes = pyip.inputStr("New Notes (keep current): ", blank=True) or entry['notes']
            new_tags_in = pyip.inputStr("New Tags (CSV, keep current): ", blank=True)
            new_tags = ','.join(t.strip() for t in new_tags_in.split(',') if t.strip()) if new_tags_in else entry['tags']

            new_password_str = None
            nonce = entry['nonce'] # Keep old nonce unless password changes
            enc_pwd = entry['encrypted_password'] # Keep old encrypted pwd unless password changes

            change_pwd = pyip.inputYesNo("Change password for this entry? (yes/no): ", default='no')
            if change_pwd == 'yes':
                 # Input/Generate new password logic (similar to add_entry)
                 use_gen = pyip.inputYesNo("Generate new password? ", default='yes')
                 if use_gen == 'yes':
                     l = pyip.inputInt("Length: ", default=18, min=12)
                     new_password_str = generate_password(l) # Simplify options for update
                     print(f"Generated: {new_password_str}")
                 else:
                     new_password_str = pyip.inputPassword("Enter new password: ")
                     if not new_password_str: print("Empty password invalid."); return

                 # Optional checks (strength, HIBP)
                 strength = check_password_strength(new_password_str)
                 print(f"Strength: {strength}")
                 check_online = pyip.inputYesNo("Check new password on HIBP? ", default='no')
                 if check_online == 'yes':
                     is_pwned, msg = check_hibp(new_password_str); print(msg)
                     if is_pwned: print("Consider using a different password.")

                 # Re-encrypt with new password
                 print("Encrypting new password...")
                 enc_res = encrypt_text(new_password_str, master_pwd, enc_salt)
                 if not enc_res: print("Encryption failed."); return
                 nonce, enc_pwd = enc_res # Update nonce and encrypted value

            # Update database
            cursor.execute("""
                UPDATE passwords SET service_name=?, username=?, url=?, encrypted_password=?,
                nonce=?, notes=?, tags=? WHERE entry_id=?
            """, (new_service, new_username, new_url, enc_pwd, nonce, new_notes, new_tags, entry_id))
            conn.commit(); print(f"Entry ID {entry_id} updated.")

        except sqlite3.Error as e: print(f"DB update error: {e}"); conn.rollback()
        finally: conn.close()


    def delete_entry(self):
        """Deletes a password entry."""
        print("\n-- Delete Password Entry --")
        entry_id = pyip.inputInt("Enter Entry ID to delete: ", min=1)
        conn = self._connect(); conn.row_factory = sqlite3.Row; cursor = conn.cursor()
        try:
            cursor.execute("SELECT service_name FROM passwords WHERE entry_id=?", (entry_id,))
            info = cursor.fetchone();
            if not info: print("ID not found."); return
            if pyip.inputYesNo(f"Delete entry for '{info['service_name']}' (ID:{entry_id})? ", default='no') != 'yes': print("Cancelled."); return
            cursor.execute("DELETE FROM passwords WHERE entry_id=?", (entry_id,))
            if cursor.rowcount > 0: conn.commit(); print("Deleted.")
            else: print("Delete failed."); conn.rollback()
        except sqlite3.Error as e: print(f"DB delete error: {e}"); conn.rollback()
        finally: conn.close()


    def menu(self):
        """Displays the Password Manager menu."""
        while True:
            print("\n--- Password Manager Menu ---")
            action = pyip.inputMenu([
                'Add Entry', 'List Entries', 'Get Password',
                'Update Entry', 'Delete Entry', 'Generate Password',
                'Check Password Strength', 'Check HIBP', 'Back'
            ], numbered=True)

            if action == 'Add Entry': self.add_entry()
            elif action == 'List Entries':
                 s = pyip.inputStr("Search: ", blank=True); t = pyip.inputStr("Tag: ", blank=True)
                 self.list_entries(s or None, t or None)
            elif action == 'Get Password': self.get_password()
            elif action == 'Update Entry': self.update_entry()
            elif action == 'Delete Entry': self.delete_entry()
            elif action == 'Generate Password':
                 l = pyip.inputInt("Length (min 12): ", default=18, min=12)
                 pwd = generate_password(l); print(f"Generated: {pwd}")
                 try: import pyperclip; pyperclip.copy(pwd); print("(Copied)")
                 except ImportError: pass
            elif action == 'Check Password Strength':
                 pwd = pyip.inputPassword("Password to check: "); print(f"Strength: {check_password_strength(pwd)}")
            elif action == 'Check HIBP':
                 pwd = pyip.inputPassword("Password to check on HIBP: "); _, msg = check_hibp(pwd); print(msg)
            elif action == 'Back': break


# --- Main Application Flow ---
def main():
    initialize_database()
    auth_manager = AuthManager()

    if auth_manager.auth_data is None:
        auth_manager.setup_master_password()
    else:
        attempts = 0; max_attempts = 3
        while attempts < max_attempts:
             password = pyip.inputPassword("Enter Master Password: ")
             if auth_manager.verify_password(password): print("Unlocked."); break
             else: attempts += 1; print(f"Incorrect. ({max_attempts - attempts} left)")
             if attempts >= max_attempts: print("Max attempts. Exiting."); sys.exit(1)

    password_manager = PasswordManager(auth_manager=auth_manager)

    while True:
        print("\n======= Password Manager =======")
        choice = pyip.inputMenu(['Manage Entries', 'Change Master Password', 'Exit'], numbered=True)
        if choice == 'Manage Entries': password_manager.menu()
        elif choice == 'Change Master Password': auth_manager.change_master_password()
        elif choice == 'Exit': print("Exiting."); sys.exit(0)


if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\nCancelled."); sys.exit(1)
    except Exception as e: print(f"\nCritical error: {e}"); import traceback; traceback.print_exc(); sys.exit(1)
