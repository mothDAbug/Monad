# lorem_ipsum_factory.py (Corrected)

import random
import pyinputplus as pyip
import os
import textwrap # For potentially wrapping long lines if needed

# --- Lorem Ipsum Source Text ---
# A standard Lorem Ipsum passage split into words
LOREM_IPSUM_WORDS = """
lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut labore et dolore magna aliqua ut enim ad minim veniam quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur excepteur sint occaecat cupidatat non proident sunt in culpa qui officia deserunt mollit anim id est laborum
""".lower().split()

# --- Generation Logic ---

def generate_words(count):
    """Generates a specified number of random Lorem Ipsum words."""
    if count <= 0:
        return ""
    # Ensure we don't request more words than available if count is huge, though unlikely here
    if count > len(LOREM_IPSUM_WORDS):
        # Simple repetition if needed, or just use choices which handles sampling with replacement
        pass # random.choices handles this naturally
    return " ".join(random.choices(LOREM_IPSUM_WORDS, k=count))

def generate_sentence(min_words=5, max_words=15):
    """Generates a single Lorem Ipsum sentence with random length."""
    num_words = random.randint(min_words, max_words)
    sentence = generate_words(num_words)
    # Capitalize first letter and add a period.
    return sentence.capitalize() + "."

def generate_paragraph(min_sentences=3, max_sentences=7):
    """Generates a paragraph composed of multiple random sentences."""
    num_sentences = random.randint(min_sentences, max_sentences)
    return " ".join(generate_sentence() for _ in range(num_sentences))

def generate_text(unit, count):
    """Generates text based on the specified unit (words, sentences, paragraphs)."""
    if unit == 'words':
        return generate_words(count)
    elif unit == 'sentences':
        return " ".join(generate_sentence() for _ in range(count))
    elif unit == 'paragraphs':
        # Add double newline between paragraphs for plain text readability
        return "\n\n".join(generate_paragraph() for _ in range(count))
    else:
        # This part should ideally not be reached with the corrected main logic
        print(f"Error: Unexpected unit '{unit}' received in generate_text.")
        return ""

# --- Formatting ---

def format_output(text, format_type):
    """Formats the generated text based on the chosen format."""
    if format_type == 'plain':
        return text
    elif format_type == 'html':
        # Simple HTML: wrap paragraphs in <p> tags
        # Split carefully, ensuring empty strings are handled if needed
        paragraphs = [p for p in text.split('\n\n') if p]
        return "\n".join(f"<p>{p}</p>" for p in paragraphs)
    elif format_type == 'markdown':
        # Basic Markdown: paragraphs are separated by blank lines (already done)
        return text
    else:
        print(f"Warning: Unknown format '{format_type}'. Defaulting to plain text.")
        return text

# --- File Output ---

def save_to_file(content, filename):
    """Saves the generated content to a specified file."""
    try:
        if not filename.lower().endswith(('.txt', '.html', '.md')) and '.' in os.path.basename(filename):
             print(f"Warning: Filename '{filename}' has an unexpected or non-standard extension for the chosen format. Saving anyway.")

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Successfully saved content to '{filename}'.")
    except IOError as e:
        print(f"Error: Could not write to file '{filename}'. Reason: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while saving the file: {e}")


# --- Main Application ---

def main():
    print("-" * 30)
    print("   Lorem Ipsum Generator")
    print("-" * 30)

    unit_options = ['Paragraphs', 'Sentences', 'Words']
    format_options = ['Plain Text', 'HTML', 'Markdown']
    default_filenames = {'Plain Text': 'lorem.txt', 'HTML': 'lorem.html', 'Markdown': 'lorem.md'}

    while True:
        print("\nChoose generation unit:")
        chosen_unit_display = pyip.inputMenu(unit_options, numbered=True)

        # --- FIX ---
        # Convert display choice to internal lower case key
        # REMOVED the incorrect `[:-1]` slicing
        chosen_unit = chosen_unit_display.lower() # Correct: 'paragraphs', 'sentences', 'words'
        # --- END FIX ---

        try:
            # Use the display name in the prompt for clarity
            count = pyip.inputInt(f"How many {chosen_unit_display.lower()} to generate? ", min=1, max=5000) # Increased max limit slightly
        except pyip.RetryLimitException:
            print("Too many invalid inputs for quantity.")
            continue

        print("\nChoose output format:")
        chosen_format_display = pyip.inputMenu(format_options, numbered=True)
        # Convert display choice to internal lower case key
        if chosen_format_display == 'Plain Text':
            chosen_format = 'plain'
        elif chosen_format_display == 'HTML':
            chosen_format = 'html'
        else: # Markdown
            chosen_format = 'markdown'

        # Generate text
        generated_text = generate_text(chosen_unit, count) # Pass the corrected chosen_unit

        if not generated_text and count > 0: # Check count > 0 as generating 0 is valid but produces empty text
            print("Failed to generate text (check console for errors).")
            continue
        elif count <=0:
            print("Generated empty text as requested count was zero or less.")

        # Format text
        formatted_output = format_output(generated_text, chosen_format)

        print("\n--- Generated Text ---")
        # Print a snippet if it's very long
        snippet_length = 500 # Increased snippet length
        if len(formatted_output) > snippet_length:
            print(textwrap.shorten(formatted_output, width=snippet_length, placeholder="..."))
        elif formatted_output:
             print(formatted_output)
        else:
             print("(Empty output generated)") # Handle case where 0 count resulted in empty string
        print("-" * 22)


        # Ask to save only if output is not empty
        if formatted_output:
            save_choice = pyip.inputYesNo("\nSave the generated text to a file? (yes/no): ", default='no')
            if save_choice == 'yes':
                 default_filename = default_filenames.get(chosen_format_display, 'generated_text.txt')
                 filename = pyip.inputFilepath(f"Enter filename to save (default: '{default_filename}'): ",
                                                blank=True, default=default_filename)
                 save_to_file(formatted_output, filename)

        another = pyip.inputYesNo("\nGenerate more Lorem Ipsum? (yes/no): ", default='yes')
        if another == 'no':
            break

    print("\nThank you for using the Lorem Ipsum Generator!")

if __name__ == "__main__":
    main()
