import random
import json
import pyinputplus as pyip
import os
import sys

# --- Configuration ---
DATA_DIR = "data"
FIRST_NAMES_FILE = os.path.join(DATA_DIR, "first_names.json")
LAST_NAMES_FILE = os.path.join(DATA_DIR, "last_names.json")
DEFAULT_OUTPUT_FILE = "generated_names.txt"

# --- Data Loading ---

def load_names_from_json(filepath):
    """Loads a list of names from a JSON file."""
    if not os.path.exists(filepath):
        print(f"Error: Data file not found at '{filepath}'.")
        print("Please ensure the 'data' folder exists and contains the necessary JSON files.")
        sys.exit(1) # Exit if essential data is missing
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            names = json.load(f)
            if isinstance(names, list) and len(names) > 0:
                return names
            else:
                print(f"Warning: Data file '{filepath}' is empty or not a valid list.")
                return []
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{filepath}'. Check the file format.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while loading '{filepath}': {e}")
        sys.exit(1)

# --- Name Generation ---

def generate_name(first_names, last_names, name_type="full"):
    """Generates a single random name based on the specified type."""
    first = random.choice(first_names) if first_names else "UnknownFirst"
    last = random.choice(last_names) if last_names else "UnknownLast"

    if name_type == "first":
        return first
    elif name_type == "last":
        return last
    elif name_type == "full":
        return f"{first} {last}"
    else:
        print(f"Warning: Unknown name type '{name_type}'. Defaulting to full name.")
        return f"{first} {last}"

def generate_multiple_names(first_names, last_names, name_type="full", quantity=1):
    """Generates a list of random names."""
    if quantity <= 0:
        return []

    # Validate data lists
    if name_type in ["first", "full"] and not first_names:
        print("Warning: First name list is empty. Cannot generate requested names.")
        return []
    if name_type in ["last", "full"] and not last_names:
        print("Warning: Last name list is empty. Cannot generate requested names.")
        return []

    generated_names = [generate_name(first_names, last_names, name_type) for _ in range(quantity)]
    return generated_names

# --- File Output ---

def save_names_to_file(names_list, filename):
    """Saves a list of names to a text file, one name per line."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            for name in names_list:
                f.write(name + "\n")
        print(f"Successfully saved {len(names_list)} names to '{filename}'.")
    except IOError as e:
        print(f"Error: Could not write to file '{filename}'. Reason: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while saving the file: {e}")


# --- Main Application ---

def main():
    print("-" * 30)
    print("   Random Name Generator")
    print("-" * 30)

    # Load name data
    print("Loading name data...")
    first_names = load_names_from_json(FIRST_NAMES_FILE)
    last_names = load_names_from_json(LAST_NAMES_FILE)
    print(f"Loaded {len(first_names)} first names and {len(last_names)} last names.")

    if not first_names and not last_names:
        print("\nError: Both first and last name lists are empty or failed to load.")
        print("Cannot generate names. Exiting.")
        return # Exit gracefully

    while True:
        print("\nSelect name type:")
        name_type_options = ["Full Name", "First Name Only", "Last Name Only"]
        name_type_choice = pyip.inputMenu(name_type_options, numbered=True)

        # Map choice to internal type string
        if name_type_choice == "Full Name":
            name_type = "full"
            if not first_names or not last_names:
                 print("Warning: Cannot generate full names without both first and last name lists.")
                 continue
        elif name_type_choice == "First Name Only":
            name_type = "first"
            if not first_names:
                print("Warning: First name list is empty.")
                continue
        else: # Last Name Only
            name_type = "last"
            if not last_names:
                print("Warning: Last name list is empty.")
                continue

        try:
            quantity = pyip.inputInt("How many names to generate? ", min=1, max=10000) # Added max limit
        except pyip.RetryLimitException:
            print("Too many invalid inputs for quantity.")
            continue

        # Generate names
        generated_names = generate_multiple_names(first_names, last_names, name_type, quantity)

        if not generated_names:
            print("Failed to generate names (likely due to empty data lists for the selected type).")
        else:
            print("\n--- Generated Names ---")
            # Print a sample if too many
            limit_print = 15
            for i, name in enumerate(generated_names):
                 if i < limit_print:
                     print(f"{i+1}. {name}")
                 elif i == limit_print:
                     print(f"... (and {len(generated_names) - limit_print} more)")
                     break
            print("-" * 21)


            # Ask to save
            save_choice = pyip.inputYesNo("\nSave the generated list to a file? (yes/no): ", default='no')
            if save_choice == 'yes':
                filename = pyip.inputFilepath(f"Enter filename to save (default: '{DEFAULT_OUTPUT_FILE}'): ",
                                              blank=True, default=DEFAULT_OUTPUT_FILE)
                save_names_to_file(generated_names, filename)

        another = pyip.inputYesNo("\nGenerate more names? (yes/no): ", default='yes')
        if another == 'no':
            break

    print("\nThank you for using the Random Name Generator!")

if __name__ == "__main__":
    main()
