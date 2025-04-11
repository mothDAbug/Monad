# duplicate_finder.py

import os
import hashlib
import json
import pyinputplus as pyip
import sys
from collections import defaultdict
import datetime
import shutil

# --- Configuration ---
DEFAULT_HASH_ALGORITHM = 'sha256' # More secure than md5
CHUNK_SIZE = 65536  # Read files in 64kb chunks

# --- Hashing Function ---

def calculate_hash(filepath, algorithm=DEFAULT_HASH_ALGORITHM):
    """Calculates the hash of a file."""
    hasher = hashlib.new(algorithm)
    try:
        with open(filepath, 'rb') as file:
            while True:
                chunk = file.read(CHUNK_SIZE)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()
    except FileNotFoundError:
        print(f"Warning: File not found during hashing: {filepath}")
        return None
    except PermissionError:
        print(f"Warning: Permission denied accessing file: {filepath}")
        return None
    except Exception as e:
        print(f"Warning: Error hashing file {filepath}: {e}")
        return None

# --- Duplicate Finding Logic ---

def find_duplicates(directory_to_scan):
    """
    Scans a directory recursively and finds duplicate files based on content hash.

    Returns:
        A dictionary where keys are hashes and values are lists of file paths
        sharing that hash (only includes hashes with more than one file).
        Also returns a dictionary mapping file size to lists of files, for initial filtering.
    """
    hashes_by_size = defaultdict(list)
    files_by_hash = defaultdict(list)
    duplicates_found = defaultdict(list)
    file_count = 0
    skipped_count = 0

    print(f"\nScanning directory: '{os.path.abspath(directory_to_scan)}'...")

    # Phase 1: Group files by size
    for root, _, filenames in os.walk(directory_to_scan):
        for filename in filenames:
            filepath = os.path.join(root, filename)
            try:
                # Skip symlinks to avoid potential loops or redundant checks
                if os.path.islink(filepath):
                    # print(f"Skipping symlink: {filepath}")
                    skipped_count += 1
                    continue

                file_size = os.path.getsize(filepath)
                # Ignore empty files as they often hash the same
                if file_size > 0:
                    hashes_by_size[file_size].append(filepath)
                    file_count += 1
                else:
                     skipped_count += 1 # Count empty files as skipped

            except FileNotFoundError:
                print(f"Warning: File vanished during scan: {filepath}")
                skipped_count += 1
            except OSError as e:
                print(f"Warning: Cannot access file stats {filepath}: {e}")
                skipped_count += 1

    print(f"Phase 1 Complete: Scanned {file_count} non-empty files, skipped {skipped_count}.")

    # Phase 2: Hash files only where sizes match
    print("Phase 2: Calculating hashes for potential duplicates...")
    potential_duplicates_count = 0
    hashed_count = 0
    for size, filepaths in hashes_by_size.items():
        if len(filepaths) > 1:
            potential_duplicates_count += len(filepaths)
            for filepath in filepaths:
                file_hash = calculate_hash(filepath)
                if file_hash:
                    files_by_hash[file_hash].append(filepath)
                    hashed_count += 1
                else:
                    skipped_count += 1 # Count files skipped due to hashing errors

    print(f"Phase 2 Complete: Hashed {hashed_count} potential duplicates.")

    # Phase 3: Identify actual duplicates (hashes with more than one file)
    for file_hash, filepaths in files_by_hash.items():
        if len(filepaths) > 1:
            duplicates_found[file_hash] = sorted(filepaths) # Sort for consistent output

    print(f"Phase 3 Complete: Found {len(duplicates_found)} sets of duplicate files.")
    return duplicates_found


# --- Duplicate Management Functions ---

def list_duplicates(duplicate_sets):
    """Prints the sets of duplicate files found."""
    if not duplicate_sets:
        print("\nNo duplicate files found.")
        return

    print("\n--- Duplicate File Sets ---")
    set_count = 0
    total_files = 0
    for i, (file_hash, filepaths) in enumerate(duplicate_sets.items()):
        set_count += 1
        total_files += len(filepaths)
        print(f"\nSet {i + 1} (Hash: {file_hash[:10]}...):") # Show partial hash
        for filepath in filepaths:
            try:
                 size_kb = os.path.getsize(filepath) / 1024
                 print(f"  - {filepath} ({size_kb:.2f} KB)")
            except OSError:
                 print(f"  - {filepath} (Size unavailable)")
    print("-" * 27)
    print(f"Found {set_count} sets of duplicates involving {total_files} files.")
    print("---------------------------")

def delete_duplicates_interactive(duplicate_sets):
    """Interactively prompts the user to delete duplicate files, keeping one original."""
    if not duplicate_sets:
        print("\nNo duplicate files found to delete.")
        return

    print("\n--- Interactive Duplicate Deletion ---")
    print("For each set, you will be asked which file to KEEP.")
    print("All other files in that set will be marked for deletion.")
    print("A final confirmation will be required before any files are deleted.")

    files_to_delete = []
    total_deleted_count = 0

    for i, (file_hash, filepaths) in enumerate(duplicate_sets.items()):
        print(f"\n--- Set {i + 1} ---")
        options = []
        for idx, filepath in enumerate(filepaths):
             try:
                 size_kb = os.path.getsize(filepath) / 1024
                 options.append(f"{filepath} ({size_kb:.2f} KB)")
             except OSError:
                 options.append(f"{filepath} (Size unavailable)")


        while True: # Loop until valid input or skip
            print("Which file do you want to KEEP? (Enter the number)")
            try:
                # Use inputMenu for robust selection
                choice_str = pyip.inputMenu(options, numbered=True, prompt="Keep file number: ", blank=True)

                if not choice_str: # User pressed Enter to skip
                    print("Skipping this set.")
                    files_to_delete_this_set = [] # Ensure it's empty if skipping
                    break

                # PyInputPlus returns the chosen string, find its index
                choice_index = options.index(choice_str)
                file_to_keep = filepaths[choice_index]
                files_to_delete_this_set = [fp for idx, fp in enumerate(filepaths) if idx != choice_index]
                print(f"Marked {len(files_to_delete_this_set)} files in this set for deletion.")
                break # Valid choice made

            except ValueError: # Should not happen with inputMenu unless list is empty
                 print("Invalid input. Please try again.")
            except pyip.RetryLimitException:
                 print("Too many invalid attempts. Skipping this set.")
                 files_to_delete_this_set = []
                 break

        files_to_delete.extend(files_to_delete_this_set)

    if not files_to_delete:
        print("\nNo files were marked for deletion.")
        return

    print("\n--- Deletion Summary ---")
    print(f"{len(files_to_delete)} files are marked for deletion:")
    for fp in files_to_delete:
        print(f"  - {fp}")
    print("-" * 24)

    confirm = pyip.inputYesNo(f"WARNING: Permanently delete these {len(files_to_delete)} files? (yes/no): ", default='no')

    if confirm == 'yes':
        print("Deleting files...")
        for filepath in files_to_delete:
            try:
                os.remove(filepath)
                print(f"  Deleted: {filepath}")
                total_deleted_count += 1
            except OSError as e:
                print(f"  Error deleting {filepath}: {e}")
        print(f"\nDeletion complete. {total_deleted_count} files deleted.")
    else:
        print("Deletion cancelled. No files were deleted.")


# --- Main Application ---
def main():
    print("-" * 30)
    print("   Duplicate File Finder")
    print("-" * 30)

    # Get directory to scan
    while True:
        scan_dir_input = pyip.inputStr("Enter the directory path to scan for duplicates: ", blank=False)
        scan_dir = os.path.abspath(scan_dir_input) # Get absolute path

        if os.path.isdir(scan_dir):
            print(f"Selected directory: '{scan_dir}'")
            break
        else:
            print(f"Error: '{scan_dir_input}' is not a valid directory. Please try again.")

    # Find duplicates
    duplicate_sets = find_duplicates(scan_dir)

    if not duplicate_sets:
        print("\nFinished scan. No duplicate files found in the specified directory.")
        sys.exit(0)

    # Present options
    while True:
        print("\n--- Actions ---")
        action = pyip.inputMenu([
            'List Duplicate Sets',
            'Delete Duplicates Interactively',
            # 'Move Duplicates (Not Implemented Yet)',
            'Exit'
        ], numbered=True)

        if action == 'List Duplicate Sets':
            list_duplicates(duplicate_sets)
        elif action == 'Delete Duplicates Interactively':
            list_duplicates(duplicate_sets) # Show them again before deleting
            delete_duplicates_interactive(duplicate_sets)
            # Re-scan or exit might be needed after deletion, as sets change
            print("\nDeletion process finished. It's recommended to re-scan or exit.")
            # For simplicity, we'll just break the action loop here.
            # A more advanced version might offer re-scanning.
            break
        elif action == 'Exit':
            break

    print("\nThank you for using the Duplicate File Finder!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
         print("\nOperation cancelled by user.")
         sys.exit(1)
    except Exception as e:
         print(f"\nAn unexpected critical error occurred: {e}")
         # Consider logging traceback here
         sys.exit(1)
