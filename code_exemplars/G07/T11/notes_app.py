# notes_app.py (Corrected - Added format_datetime_for_display)

import sqlite3
import os
import datetime
import pyinputplus as pyip
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import sys
import json

# --- Configuration ---
DB_NAME = "notes.db"
EXPORT_DIR = "data_exports"
IMPORT_DIR = "data_imports"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S" # Use a format that includes time

# --- Security Warning ---
# (Warnings remain the same)
SALT_FILE = "app_salt.bin"

# --- Database Setup ---
def initialize_database():
    """Creates the database and necessary tables if they don't exist."""
    os.makedirs(EXPORT_DIR, exist_ok=True)
    os.makedirs(IMPORT_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notes (
        note_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        tags TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_encrypted INTEGER DEFAULT 0
    )''')

    cursor.execute('''
    CREATE TRIGGER IF NOT EXISTS update_note_timestamp
    AFTER UPDATE ON notes
    FOR EACH ROW
    BEGIN
        UPDATE notes SET updated_at = CURRENT_TIMESTAMP WHERE note_id = OLD.note_id;
    END;
    ''')

    conn.commit()
    conn.close()
    print(f"Database '{DB_NAME}' initialized/checked successfully.")
    generate_salt()

# --- Cryptography Utilities ---
# (generate_salt, load_salt, derive_key, encrypt_content, decrypt_content remain the same)
def generate_salt():
    """Generates and saves a salt if it doesn't exist."""
    if not os.path.exists(SALT_FILE):
        print("Generating new salt for key derivation...")
        salt = os.urandom(16)
        try:
            with open(SALT_FILE, 'wb') as f:
                f.write(salt)
            print(f"Salt saved to '{SALT_FILE}'. IMPORTANT: Keep this file safe!")
        except IOError as e:
            print(f"FATAL ERROR: Could not write salt file: {e}")
            sys.exit(1)

def load_salt():
    """Loads the salt from the file."""
    if not os.path.exists(SALT_FILE):
         print("FATAL ERROR: Salt file not found. Cannot perform encryption/decryption.")
         print("Try running the script once to generate it, or restore it from backup.")
         sys.exit(1)
    try:
        with open(SALT_FILE, 'rb') as f:
            return f.read()
    except IOError as e:
        print(f"FATAL ERROR: Could not read salt file: {e}")
        sys.exit(1)

def derive_key(password: str, salt: bytes) -> bytes:
    """Derives a cryptographic key from a password using PBKDF2."""
    if not password:
        raise ValueError("Password cannot be empty for key derivation.")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390000, # Adjust iterations as needed
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key

def encrypt_content(content: str, password: str) -> bytes:
    """Encrypts text content using Fernet symmetric encryption."""
    if not password:
        print("Encryption cancelled: Password required.")
        return None
    try:
        salt = load_salt()
        key = derive_key(password, salt)
        f = Fernet(key)
        encrypted_data = f.encrypt(content.encode())
        return encrypted_data
    except Exception as e:
        print(f"Encryption failed: {e}")
        return None

def decrypt_content(encrypted_data: bytes, password: str) -> str:
    """Decrypts Fernet encrypted data."""
    if not password:
        print("Decryption failed: Password required.")
        return None
    try:
        salt = load_salt()
        key = derive_key(password, salt)
        f = Fernet(key)
        decrypted_data = f.decrypt(encrypted_data)
        return decrypted_data.decode()
    except InvalidToken:
        print("Decryption failed: Invalid password or corrupted data.")
        return None
    except Exception as e:
        print(f"Decryption failed: {e}")
        return None

# --- ADDED HELPER FUNCTION ---
def format_datetime_for_display(dt_obj):
    """Formats a datetime object for display, handling None."""
    if isinstance(dt_obj, datetime.datetime):
        return dt_obj.strftime(DATE_FORMAT) # Use the defined format
    elif isinstance(dt_obj, str): # Fallback if it's somehow stored as string
        try:
             # Attempt to parse known formats
             parsed_dt = None
             try: parsed_dt = datetime.datetime.strptime(dt_obj, '%Y-%m-%d %H:%M:%S.%f') # With microseconds
             except ValueError:
                 try: parsed_dt = datetime.datetime.strptime(dt_obj, '%Y-%m-%d %H:%M:%S') # Without microseconds
                 except ValueError: pass # Keep original string if unparseable
             if parsed_dt: return parsed_dt.strftime(DATE_FORMAT)
             else: return dt_obj
        except: return dt_obj # Return original on any error
    return "N/A"
# --- END ADDED HELPER FUNCTION ---


# --- Note Manager Class ---
class NoteManager:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self.master_password_cache = None

    def _connect(self):
        """Connects to the database."""
        return sqlite3.connect(self.db_name, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)

    def _get_master_password(self, force_new=False):
        """Gets master password (insecurely caches for session)."""
        if self.master_password_cache and not force_new:
            return self.master_password_cache
        password = pyip.inputPassword("Enter Master Password (for encryption/decryption): ")
        if password:
            self.master_password_cache = password
            return password
        else:
            print("Password cannot be empty.")
            return None

    def _clear_password_cache(self):
        self.master_password_cache = None

    # --- add_note --- (Remains the same)
    def add_note(self):
        """Adds a new note, with optional encryption."""
        print("\n-- Add New Note --")
        title = pyip.inputStr("Note Title: ")
        print("Enter Note Content (Press Ctrl+Z or Ctrl+D on a new line when done):")
        content_lines = []
        while True:
            try:
                line = input()
                content_lines.append(line)
            except EOFError:
                break
        content = "\n".join(content_lines)
        if not content.strip():
            print("Note content cannot be empty. Aborting.")
            return

        tags_input = pyip.inputStr("Tags (comma-separated, optional): ", blank=True)
        tags = ','.join(tag.strip() for tag in tags_input.split(',') if tag.strip())

        encrypt_choice = pyip.inputYesNo("Encrypt this note? (yes/no): ", default='no')
        is_encrypted = 1 if encrypt_choice == 'yes' else 0
        content_to_store = content

        if is_encrypted:
            password = self._get_master_password()
            if not password: return
            encrypted_content = encrypt_content(content, password)
            if encrypted_content is None:
                print("Failed to encrypt note. Saving as plain text instead.")
                is_encrypted = 0
            else:
                content_to_store = encrypted_content
                print("Note content encrypted.")

        conn = self._connect()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO notes (title, content, tags, is_encrypted)
                VALUES (?, ?, ?, ?)
            """, (title, content_to_store, tags, is_encrypted))
            conn.commit()
            print(f"Note '{title}' added successfully (ID: {cursor.lastrowid}).")
        except sqlite3.Error as e:
            print(f"Database error adding note: {e}")
        finally:
            conn.close()

    # --- view_notes --- (Remains the same, uses inline formatting)
    def view_notes(self, search_term=None, tag_filter=None):
        """Lists notes, optionally filtering by search term or tag."""
        print("\n-- View Notes --")
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            query = "SELECT note_id, title, tags, is_encrypted, updated_at FROM notes"
            params = []
            conditions = []

            if search_term:
                conditions.append("(title LIKE ? OR (is_encrypted = 0 AND content LIKE ?))")
                params.extend([f"%{search_term}%", f"%{search_term}%"])
            if tag_filter:
                conditions.append("tags LIKE ?")
                params.append(f"%{tag_filter}%")

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY updated_at DESC"

            cursor.execute(query, params)
            notes = cursor.fetchall()

            if not notes:
                print("No notes found" + (" matching criteria." if (search_term or tag_filter) else "."))
                return

            print("\n{:<5} {:<40} {:<25} {:<10} {}".format("ID", "Title", "Tags", "Encrypted", "Last Updated"))
            print("-" * 95)
            for note in notes:
                 # Use the helper function here too for consistency
                 updated_at_str = format_datetime_for_display(note['updated_at'])
                 encrypted_str = "Yes" if note['is_encrypted'] == 1 else "No"
                 print("{:<5} {:<40} {:<25} {:<10} {}".format(
                     note['note_id'], note['title'], note['tags'] or "", encrypted_str, updated_at_str))
            print("-" * 95)

        except sqlite3.Error as e:
            print(f"Database error viewing notes: {e}")
        finally:
            conn.close()


    # --- read_note --- (Now uses the helper function correctly)
    def read_note(self):
        """Reads the full content of a selected note, decrypting if necessary."""
        print("\n-- Read Note --")
        note_id = pyip.inputInt("Enter Note ID to read: ", min=1)
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM notes WHERE note_id = ?", (note_id,))
            note = cursor.fetchone()
            if not note:
                print(f"Note ID {note_id} not found.")
                return

            title = note['title']
            content_stored = note['content']
            is_encrypted = note['is_encrypted']
            tags = note['tags']
            updated_at = note['updated_at'] # This should be a datetime object

            content_display = None
            if is_encrypted:
                print("This note is encrypted.")
                password = self._get_master_password()
                if not password: return # Abort if no password
                content_display = decrypt_content(content_stored, password)
                if content_display is None:
                    print("Could not decrypt note content.")
                    return
            else:
                content_display = content_stored

            print("\n" + "="*50)
            print(f"Note ID: {note_id}")
            print(f"Title: {title}")
            print(f"Tags: {tags or 'None'}")
            # --- FIXED: Use the helper function ---
            print(f"Last Updated: {format_datetime_for_display(updated_at)}")
            # --- END FIX ---
            print(f"Encrypted: {'Yes' if is_encrypted else 'No'}")
            print("-"*50)
            print(content_display)
            print("="*50)

        except sqlite3.Error as e:
             print(f"Database error reading note: {e}")
        finally:
             conn.close()

    # --- update_note --- (Remains the same)
    def update_note(self):
        """Updates an existing note."""
        print("\n-- Update Note --")
        note_id = pyip.inputInt("Enter Note ID to update: ", min=1)
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM notes WHERE note_id = ?", (note_id,))
            note = cursor.fetchone()
            if not note:
                print(f"Note ID {note_id} not found.")
                return

            print(f"Current Title: {note['title']}")
            print(f"Current Tags: {note['tags']}")
            print(f"Currently Encrypted: {'Yes' if note['is_encrypted'] else 'No'}")

            current_content = note['content']
            decrypted_content = ""
            password_needed = False
            if note['is_encrypted']:
                 print("Note is encrypted. Password needed to view/edit content.")
                 password = self._get_master_password()
                 if not password: return
                 password_needed = True
                 decrypted_content = decrypt_content(current_content, password)
                 if decrypted_content is None:
                     print("Decryption failed. Cannot update content.")
                     return
                 print("\nCurrent Content (Decrypted):\n" + "-"*20 + f"\n{decrypted_content}\n" + "-"*20)
            else:
                 decrypted_content = current_content
                 print("\nCurrent Content:\n" + "-"*20 + f"\n{decrypted_content}\n" + "-"*20)

            new_title = pyip.inputStr(f"New Title (keep '{note['title']}'): ", blank=True) or note['title']

            edit_content = pyip.inputYesNo("Edit content? (yes/no): ", default='no')
            new_content = decrypted_content
            if edit_content == 'yes':
                 print("Enter New Content (Ctrl+Z or Ctrl+D on new line when done):")
                 content_lines = []
                 while True:
                    try: line = input()
                    except EOFError: break
                    content_lines.append(line)
                 new_content_input = "\n".join(content_lines)
                 if new_content_input.strip():
                     new_content = new_content_input
                 else:
                     print("New content is empty, keeping original content.")

            new_tags_input = pyip.inputStr(f"New Tags (comma-sep, keep '{note['tags']}'): ", blank=True)
            new_tags = ','.join(tag.strip() for tag in new_tags_input.split(',') if tag.strip()) if new_tags_input else note['tags']

            new_encrypted_status = note['is_encrypted']
            change_encryption = pyip.inputYesNo(f"Change encryption status (currently {'Encrypted' if note['is_encrypted'] else 'Plain Text'})? (yes/no): ", default='no')
            if change_encryption == 'yes':
                 new_encrypted_status = 1 - note['is_encrypted']
                 print(f"Encryption status will be changed to: {'Encrypted' if new_encrypted_status else 'Plain Text'}")
                 if not password_needed and new_encrypted_status == 1:
                      password = self._get_master_password()
                      if not password:
                           print("Password required to encrypt. Aborting encryption change.")
                           new_encrypted_status = 0
                 elif password_needed and new_encrypted_status == 0:
                      print("Note will be saved as plain text.")

            content_to_store = new_content
            if new_encrypted_status == 1:
                if not password_needed: # May need password if changing status
                    password = self._get_master_password()
                    if not password:
                        print("Password required to save as encrypted. Aborting update.")
                        return
                # Ensure password var is set if originally encrypted and status didn't change
                if password_needed and not 'password' in locals(): password = self._get_master_password()
                if not password: # Final check if password somehow not obtained
                     print("Password error during encryption. Aborting update.")
                     return

                encrypted_final = encrypt_content(new_content, password)
                if encrypted_final is None:
                    print("Encryption failed during update. Aborting.")
                    return
                content_to_store = encrypted_final

            cursor.execute("""
                UPDATE notes
                SET title = ?, content = ?, tags = ?, is_encrypted = ?
                WHERE note_id = ?
            """, (new_title, content_to_store, new_tags, new_encrypted_status, note_id))
            conn.commit()
            print(f"Note ID {note_id} updated successfully.")

        except sqlite3.Error as e:
             print(f"Database error updating note: {e}")
             conn.rollback()
        finally:
             conn.close()

    # --- delete_note --- (Remains the same)
    def delete_note(self):
        """Deletes a note."""
        print("\n-- Delete Note --")
        note_id = pyip.inputInt("Enter Note ID to delete: ", min=1)
        confirm = pyip.inputYesNo(f"Are you sure you want to permanently delete note ID {note_id}? (yes/no): ", default='no')

        if confirm == 'yes':
            conn = self._connect()
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM notes WHERE note_id = ?", (note_id,))
                if cursor.rowcount > 0:
                    conn.commit()
                    print(f"Note ID {note_id} deleted successfully.")
                else:
                    print(f"Note ID {note_id} not found.")
            except sqlite3.Error as e:
                print(f"Database error deleting note: {e}")
                conn.rollback()
            finally:
                conn.close()
        else:
            print("Deletion cancelled.")

    # --- export_note_to_file --- (Remains the same)
    def export_note_to_file(self, note_id, note_data=None):
        """Exports a single note to a text file."""
        if not note_data:
             conn = self._connect()
             conn.row_factory = sqlite3.Row
             cursor = conn.cursor()
             cursor.execute("SELECT * FROM notes WHERE note_id = ?", (note_id,))
             note_data = cursor.fetchone()
             conn.close()

        if not note_data:
             print(f"Cannot export: Note ID {note_id} not found.")
             return False

        title = note_data['title']
        content_stored = note_data['content']
        is_encrypted = note_data['is_encrypted']
        tags = note_data['tags']
        content_to_write = ""

        # Handle potential password need without relying on instance cache
        local_password = None
        if is_encrypted:
             print(f"Note '{title}' (ID: {note_id}) is encrypted.")
             # Use a local prompt, don't rely on session cache for export safety
             local_password = pyip.inputPassword("Enter Master Password to decrypt for export: ")
             if not local_password:
                 print("Skipping export: Password needed.")
                 return False
             decrypted = decrypt_content(content_stored, local_password)
             if decrypted is None:
                 print("Skipping export: Decryption failed.")
                 return False
             content_to_write = decrypted
        else:
             content_to_write = content_stored

        safe_title = "".join(c if c.isalnum() or c in (' ', '-') else '_' for c in title).rstrip()
        filename = f"note_{note_id}_{safe_title}.txt"
        filepath = os.path.join(EXPORT_DIR, filename)

        try:
             with open(filepath, 'w', encoding='utf-8') as f:
                 f.write(f"Title: {title}\n")
                 f.write(f"Tags: {tags or 'None'}\n")
                 f.write(f"Encrypted: {'Yes' if is_encrypted else 'No'}\n")
                 f.write("="*20 + "\n\n")
                 f.write(content_to_write)
             print(f"Note {note_id} exported successfully to '{filepath}'.")
             return True
        except IOError as e:
             print(f"Error exporting note {note_id} to file: {e}")
             return False

    # --- export_all_notes --- (Remains the same)
    def export_all_notes(self):
        """Exports all notes to individual text files."""
        print("\n-- Export All Notes --")
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notes ORDER BY note_id")
        notes = cursor.fetchall()
        conn.close()

        if not notes:
             print("No notes found to export.")
             return

        exported_count = 0
        failed_count = 0
        password = None # Ask once only if needed

        needs_password = any(note['is_encrypted'] for note in notes)
        if needs_password:
             print("Some notes are encrypted. You will need the master password.")
             # Get password once for the bulk operation for convenience
             password = pyip.inputPassword("Enter Master Password for encrypted notes: ")
             if not password:
                  print("Cannot export encrypted notes without password. Aborting export.")
                  return

        print(f"Exporting {len(notes)} notes to '{EXPORT_DIR}'...")
        for note in notes:
            # Re-prompting logic within export_note_to_file is tricky here.
            # Simplification: Pass the bulk password if obtained.
            # Note: export_note_to_file was modified to ask locally,
            # let's revert that or pass the password explicitly.
            # Passing explicitly is cleaner.

             content_to_write = ""
             if note['is_encrypted']:
                  if not password: # Should have been caught above, but double-check
                      print(f"Skipping encrypted note {note['note_id']}: No password provided.")
                      failed_count += 1
                      continue
                  decrypted = decrypt_content(note['content'], password)
                  if decrypted is None:
                      print(f"Skipping encrypted note {note['note_id']}: Decryption failed.")
                      failed_count += 1
                      continue
                  content_to_write = decrypted
             else:
                  content_to_write = note['content']

             # --- Inline export logic from export_note_to_file ---
             safe_title = "".join(c if c.isalnum() or c in (' ', '-') else '_' for c in note['title']).rstrip()
             filename = f"note_{note['note_id']}_{safe_title}.txt"
             filepath = os.path.join(EXPORT_DIR, filename)
             try:
                 with open(filepath, 'w', encoding='utf-8') as f:
                     f.write(f"Title: {note['title']}\n")
                     f.write(f"Tags: {note['tags'] or 'None'}\n")
                     f.write(f"Encrypted: {'Yes' if note['is_encrypted'] else 'No'}\n")
                     f.write("="*20 + "\n\n")
                     f.write(content_to_write)
                 # print(f"Note {note['note_id']} exported successfully.") # Verbose logging
                 exported_count += 1
             except IOError as e:
                 print(f"Error exporting note {note['note_id']} to file: {e}")
                 failed_count += 1
             # --- End inline export logic ---


        print(f"\nExport complete. Successfully exported: {exported_count}. Failed/Skipped: {failed_count}.")
        # No password cache to clear here as we asked once locally

    # --- import_notes_from_files --- (Remains the same)
    def import_notes_from_files(self):
        """Imports notes from text files in the import directory."""
        print(f"\n-- Import Notes from '{IMPORT_DIR}' --")
        print("Place plain text (.txt) files in the import directory.")
        print("The filename (without .txt) will be used as the note title.")
        print("The file content will be the note content.")

        if not os.path.isdir(IMPORT_DIR):
            print(f"Error: Import directory '{IMPORT_DIR}' not found.")
            return

        files_to_import = [f for f in os.listdir(IMPORT_DIR) if f.lower().endswith('.txt') and os.path.isfile(os.path.join(IMPORT_DIR, f))]

        if not files_to_import:
             print("No .txt files found in the import directory.")
             return

        imported_count = 0
        failed_count = 0
        conn = self._connect()
        cursor = conn.cursor()

        print(f"Found {len(files_to_import)} .txt files to import.")
        confirm = pyip.inputYesNo("Proceed with import? (yes/no): ", default='no')
        if confirm != 'yes':
             print("Import cancelled.")
             conn.close()
             return

        for filename in files_to_import:
            filepath = os.path.join(IMPORT_DIR, filename)
            title = os.path.splitext(filename)[0]
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                if not content.strip():
                     print(f"Skipping '{filename}': File is empty.")
                     failed_count += 1
                     continue

                cursor.execute("INSERT INTO notes (title, content, is_encrypted) VALUES (?, ?, 0)", (title, content))
                conn.commit()
                print(f"Successfully imported '{filename}' as note ID {cursor.lastrowid}.")
                imported_count += 1

            except IOError as e:
                print(f"Error reading file '{filename}': {e}")
                failed_count += 1
            except sqlite3.Error as e:
                 print(f"Database error importing '{filename}': {e}")
                 failed_count += 1
                 conn.rollback()
            except Exception as e:
                 print(f"Unexpected error importing '{filename}': {e}")
                 failed_count += 1

        conn.close()
        print(f"\nImport process finished. Imported: {imported_count}. Failed/Skipped: {failed_count}.")

    # --- main_menu --- (Remains the same)
    def main_menu(self):
        """Displays the main menu and handles user actions."""
        while True:
            self._clear_password_cache() # Clear at start of loop
            print("\n======= Notes App Menu =======")
            action = pyip.inputMenu([
                'Add Note',
                'View/Search Notes',
                'Read Note',
                'Update Note',
                'Delete Note',
                'Export Note(s)',
                'Import Notes from Files',
                'Exit'
            ], numbered=True)

            if action == 'Add Note':
                self.add_note()
            elif action == 'View/Search Notes':
                 search = pyip.inputStr("Search term (title/content - blank for all): ", blank=True)
                 tag = pyip.inputStr("Filter by Tag (blank for all): ", blank=True)
                 self.view_notes(search_term=search if search else None,
                                 tag_filter=tag if tag else None)
            elif action == 'Read Note':
                 self.read_note()
            elif action == 'Update Note':
                 self.update_note()
            elif action == 'Delete Note':
                 self.delete_note()
            elif action == 'Export Note(s)':
                 export_choice = pyip.inputChoice(['Single', 'All'], prompt="Export a single note or all notes? (Single/All): ")
                 if export_choice == 'Single':
                     note_id = pyip.inputInt("Enter Note ID to export: ", min=1)
                     self.export_note_to_file(note_id)
                 else:
                     self.export_all_notes()
            elif action == 'Import Notes from Files':
                 self.import_notes_from_files()
            elif action == 'Exit':
                print("Exiting Notes App. Goodbye!")
                sys.exit(0)


# --- Main Execution ---
if __name__ == "__main__":
    try:
        initialize_database()
        manager = NoteManager()
        manager.main_menu()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user. Exiting.")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected critical error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
