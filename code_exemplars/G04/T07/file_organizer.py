# file_organizer.py

import os
import shutil
import json
import datetime
import pyinputplus as pyip
import sys

# --- Configuration ---
CONFIG_DIR = "config"
RULES_FILE = os.path.join(CONFIG_DIR, "organizer_rules.json")
DEFAULT_TARGET_DIR = "." # Default to current directory

# --- Helper Functions ---

def load_rules(filepath):
    """Loads organization rules from a JSON file."""
    if not os.path.exists(filepath):
        print(f"Error: Rules file not found at '{filepath}'.")
        print("Please ensure the 'config' folder and 'organizer_rules.json' exist.")
        return None # Return None to indicate failure
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            rules = json.load(f)
        # Basic validation
        if "rules_by_extension" not in rules:
             print(f"Error: 'rules_by_extension' key missing in '{filepath}'.")
             return None
        print(f"Rules loaded successfully from '{filepath}'.")
        return rules
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{filepath}'. Check the file format.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading rules: {e}")
        return None

def get_file_extension(filename):
    """Extracts the file extension in lowercase."""
    # Handle filenames starting with '.' (like .bashrc) - treat them as having no extension for sorting
    if filename.startswith('.') and '.' not in filename[1:]:
        return ""
    # Get the part after the last dot
    parts = filename.rsplit('.', 1)
    if len(parts) > 1 and parts[0] != '': # Ensure there's a name before the dot
        return parts[1].lower()
    return "" # No extension found

def get_destination_folder(extension, rules_config):
    """Determines the destination folder name based on the extension and rules."""
    rules_map = rules_config.get("rules_by_extension", {})
    for folder_name, extensions_list in rules_map.items():
        if extension in extensions_list:
            return folder_name

    # Handle files not matching any rule
    if rules_config.get("use_other_folder", False):
        return rules_config.get("other_folder_name", "Miscellaneous")
    else:
        return None # Indicate that this file should not be moved

# --- Core Logic ---

def organize_directory(target_dir, rules_config, dry_run=False):
    """Scans the target directory and organizes files based on the rules."""
    if not os.path.isdir(target_dir):
        print(f"Error: Target directory '{target_dir}' not found or is not a directory.")
        return 0, 0 # Return counts of moved and skipped

    print(f"\nScanning directory: '{os.path.abspath(target_dir)}'")
    if dry_run:
        print("--- DRY RUN MODE: No files will be moved. ---")

    moved_count = 0
    skipped_count = 0
    created_folders = set() # Keep track of folders checked/created in this run

    try:
        for filename in os.listdir(target_dir):
            source_path = os.path.join(target_dir, filename)

            # Skip directories and the script itself
            if os.path.isdir(source_path):
                # print(f"Skipping directory: {filename}")
                skipped_count += 1
                continue
            if filename == os.path.basename(__file__) or filename == RULES_FILE or filename.endswith('.pyc'):
                 # print(f"Skipping script/config file: {filename}")
                 skipped_count += 1
                 continue

            extension = get_file_extension(filename)
            dest_folder_name = get_destination_folder(extension, rules_config)

            if dest_folder_name:
                dest_dir = os.path.join(target_dir, dest_folder_name)
                dest_path = os.path.join(dest_dir, filename)

                print(f"Processing '{filename}' (Ext: '{extension}') -> Target Folder: '{dest_folder_name}'")

                if dry_run:
                    if not os.path.exists(dest_dir):
                         print(f"  [Dry Run] Would create directory: '{dest_dir}'")
                    print(f"  [Dry Run] Would move '{filename}' to '{dest_dir}'")
                    moved_count += 1 # Count potential moves in dry run
                else:
                    # Create destination directory if it doesn't exist
                    if dest_folder_name not in created_folders and not os.path.exists(dest_dir):
                        try:
                            os.makedirs(dest_dir)
                            print(f"  Created directory: '{dest_dir}'")
                            created_folders.add(dest_folder_name)
                        except OSError as e:
                            print(f"  Error creating directory '{dest_dir}': {e}. Skipping file '{filename}'.")
                            skipped_count += 1
                            continue # Skip this file if folder creation fails

                    # Move the file
                    try:
                        # Prevent overwriting - check if file exists at destination
                        if os.path.exists(dest_path):
                             # Add a timestamp or counter to the filename to avoid collision
                             base, ext = os.path.splitext(filename)
                             timestamp = datetime.datetime.now().strftime("_%Y%m%d%H%M%S")
                             new_filename = f"{base}{timestamp}{ext}"
                             dest_path = os.path.join(dest_dir, new_filename)
                             print(f"  Warning: File '{filename}' already exists in '{dest_folder_name}'. Renaming to '{new_filename}'.")

                        shutil.move(source_path, dest_path)
                        print(f"  Moved '{filename}' to '{dest_dir}'")
                        moved_count += 1
                    except Exception as e:
                        print(f"  Error moving file '{filename}': {e}. Skipping.")
                        skipped_count += 1

            else:
                # print(f"Skipping '{filename}' (No matching rule and 'Other' folder disabled or no extension)")
                skipped_count += 1

    except FileNotFoundError:
         print(f"Error: Target directory '{target_dir}' was removed during scan.")
         return moved_count, skipped_count
    except Exception as e:
         print(f"An unexpected error occurred during scanning: {e}")
         # Potentially log the error traceback here
         return moved_count, skipped_count


    print("\n--- Organization Summary ---")
    if dry_run:
        print(f"Dry run complete. Would have moved {moved_count} files.")
    else:
        print(f"Organization complete. Moved {moved_count} files.")
    print(f"Skipped {skipped_count} items (directories, script, config, or no matching rule).")
    print("--------------------------")
    return moved_count, skipped_count


# --- Main Application ---
def main():
    print("-" * 30)
    print("   File Organizer")
    print("-" * 30)

    # Load rules first
    rules_config = load_rules(RULES_FILE)
    if rules_config is None:
        print("\nExiting due to rule loading error.")
        sys.exit(1)

    # Get target directory
    while True:
        target_dir_input = pyip.inputStr(f"Enter the directory path to organize (leave blank for current '{os.path.abspath(DEFAULT_TARGET_DIR)}'): ",
                                        blank=True)
        target_dir = target_dir_input if target_dir_input else DEFAULT_TARGET_DIR

        if os.path.isdir(target_dir):
            print(f"Selected directory: '{os.path.abspath(target_dir)}'")
            break
        else:
            print(f"Error: '{target_dir}' is not a valid directory. Please try again.")

    # Confirm before proceeding
    print("\nBased on the loaded rules, files in the target directory will be moved into subfolders:")
    # Display planned folder structure briefly
    folders_to_create = set(rules_config["rules_by_extension"].keys())
    if rules_config.get("use_other_folder"):
        folders_to_create.add(rules_config.get("other_folder_name", "Miscellaneous"))
    print(f"Potential folders: {', '.join(sorted(list(folders_to_create)))}")

    # Ask for Dry Run
    dry_run_choice = pyip.inputYesNo("\nPerform a 'dry run' first (show what would happen without moving files)? (yes/no): ", default='yes')

    if dry_run_choice == 'yes':
        organize_directory(target_dir, rules_config, dry_run=True)
        # Ask if they want to proceed with the actual organization
        proceed = pyip.inputYesNo("\nDo you want to proceed with the actual organization now? (yes/no): ", default='no')
        if proceed == 'yes':
            organize_directory(target_dir, rules_config, dry_run=False)
        else:
            print("Organization cancelled.")
    else:
        # If not doing a dry run, ask for final confirmation
        confirm = pyip.inputYesNo(f"\nWARNING: This will move files in '{os.path.abspath(target_dir)}'.\nAre you absolutely sure you want to proceed? (yes/no): ", default='no')
        if confirm == 'yes':
            organize_directory(target_dir, rules_config, dry_run=False)
        else:
            print("Organization cancelled.")

    print("\nThank you for using the File Organizer!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
         print("\nOperation cancelled by user.")
         sys.exit(1)
    except Exception as e:
         print(f"\nAn unexpected critical error occurred: {e}")
         sys.exit(1)
