import pyinputplus as pyip
import re
import requests
import json

# --- Case Conversion Functions ---

def to_uppercase(text):
    """Converts text to UPPERCASE."""
    return text.upper()

def to_lowercase(text):
    """Converts text to lowercase."""
    return text.lower()

def to_title_case(text):
    """Converts text to Title Case."""
    return text.title()

def to_sentence_case(text):
    """Converts text to Sentence case (first letter capitalized)."""
    if not text:
        return ""
    return text[0].upper() + text[1:].lower()

def to_camel_case(text):
    """Converts text to camelCase."""
    # Remove non-alphanumeric, replace spaces/hyphens/underscores
    s = re.sub(r"[^a-zA-Z0-9]+", " ", text).strip()
    if not s:
        return ""
    parts = s.split()
    # Lowercase the first word, Title Case the rest
    return parts[0].lower() + "".join(word.title() for word in parts[1:])

def to_pascal_case(text):
    """Converts text to PascalCase (aka UpperCamelCase)."""
    # Remove non-alphanumeric, replace spaces/hyphens/underscores
    s = re.sub(r"[^a-zA-Z0-9]+", " ", text).strip()
    if not s:
        return ""
    parts = s.split()
    # Title Case all words and join
    return "".join(word.title() for word in parts)

def to_snake_case(text, validate_words=False):
    """Converts text to snake_case."""
    # Find sequences of letters/numbers
    words = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+', text)
    if not words:
        return ""

    processed_words = [word.lower() for word in words]

    if validate_words:
        valid_words = [word for word in processed_words if is_valid_english_word(word)]
        if len(valid_words) < len(processed_words):
             print(f"Warning: Some parts might not be valid words: {set(processed_words) - set(valid_words)}")
             # Optionally, use only valid words or keep all? Let's keep all for now.
             # processed_words = valid_words # Uncomment to only use validated words

    return "_".join(processed_words)


def to_kebab_case(text, validate_words=False):
    """Converts text to kebab-case."""
     # Find sequences of letters/numbers
    words = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+', text)
    if not words:
        return ""

    processed_words = [word.lower() for word in words]

    if validate_words:
        valid_words = [word for word in processed_words if is_valid_english_word(word)]
        if len(valid_words) < len(processed_words):
            print(f"Warning: Some parts might not be valid words: {set(processed_words) - set(valid_words)}")
            # Optionally, use only valid words or keep all? Let's keep all for now.
            # processed_words = valid_words # Uncomment to only use validated words

    return "-".join(processed_words)


# --- Optional: Dictionary API Integration ---
DICTIONARY_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/"
WORD_VALIDATION_CACHE = {} # Simple in-memory cache

def is_valid_english_word(word):
    """Checks if a word is likely a valid English word using the Free Dictionary API."""
    if not word or not word.isalpha(): # Skip numbers or empty strings
        return False
    if word in WORD_VALIDATION_CACHE:
        return WORD_VALIDATION_CACHE[word]

    print(f"Checking dictionary for '{word}'...")
    try:
        response = requests.get(f"{DICTIONARY_API_URL}{word}", timeout=5)
        if response.status_code == 200:
            # API returns a list if word is found, or an object with 'title' if not found
            is_valid = isinstance(response.json(), list)
            WORD_VALIDATION_CACHE[word] = is_valid
            return is_valid
        elif response.status_code == 404:
             WORD_VALIDATION_CACHE[word] = False
             return False
        else:
            print(f"Warning: Dictionary API returned status {response.status_code} for '{word}'")
            # Assume valid if API fails? Or invalid? Let's assume invalid on API error.
            WORD_VALIDATION_CACHE[word] = False
            return False
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not connect to Dictionary API: {e}")
        # Assume valid if API is unreachable? Or invalid? Let's assume valid to avoid blocking.
        return True # Fail open - assume it's valid if we can't check


# --- Main Application ---

def main():
    print("-" * 30)
    print("   Text Case Converter")
    print("-" * 30)

    case_options = {
        "UPPERCASE": to_uppercase,
        "lowercase": to_lowercase,
        "Title Case": to_title_case,
        "Sentence case": to_sentence_case,
        "camelCase": to_camel_case,
        "PascalCase": to_pascal_case,
        "snake_case": to_snake_case,
        "kebab-case": to_kebab_case,
    }
    option_list = list(case_options.keys())

    validate_words_option = False # Default for validation

    while True:
        text_input = pyip.inputStr("\nEnter the text to convert (or type 'quit'): \n> ")
        if text_input.lower() == 'quit':
            break

        print("\nChoose the target case:")
        chosen_case = pyip.inputMenu(option_list, numbered=True)

        conversion_func = case_options[chosen_case]
        result = ""

        # Ask for validation only for snake/kebab case
        if chosen_case in ["snake_case", "kebab-case"]:
            validate_input = pyip.inputYesNo(f"Attempt to validate parts of '{chosen_case}' against an English dictionary? (Requires internet) (yes/no): ", default='no')
            validate_words_option = (validate_input == 'yes')
            result = conversion_func(text_input, validate_words=validate_words_option)
        else:
            result = conversion_func(text_input)


        print("-" * 30)
        print(f"Original:  {text_input}")
        print(f"Converted ({chosen_case}): {result}")
        print("-" * 30)

        another = pyip.inputYesNo("\nConvert another text? (yes/no): ", default='yes')
        if another == 'no':
            break

    print("\nThank you for using the Text Case Converter!")

if __name__ == "__main__":
    main()
