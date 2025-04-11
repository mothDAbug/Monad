# Text Case Converter (Project T03)

## Description

A flexible command-line utility for transforming text strings between various common casing conventions. Supports uppercase, lowercase, title case, sentence case, camelCase, PascalCase, snake_case, and kebab-case. Useful for programming, data cleaning, content editing, and text normalization tasks.

## Features

*   Converts input text to numerous target cases:
    *   `UPPERCASE`
    *   `lowercase`
    *   `Title Case`
    *   `Sentence case`
    *   `camelCase`
    *   `PascalCase` (UpperCamelCase)
    *   `snake_case`
    *   `kebab-case`
*   User-friendly command-line interface using `PyInputPlus` for selecting the target case.
*   Handles various edge cases and attempts intelligent word separation for snake\_case and kebab-case based on capital letters or existing separators.
*   **Optional Feature:** For `snake_case` and `kebab-case`, you can choose to validate the resulting word segments against the [Free Dictionary API](https://dictionaryapi.dev/) to check if they are likely valid English words (requires an internet connection).

## Requirements

*   Python 3.7+
*   Libraries listed in `requirements.txt`:
    *   `pyinputplus`: For robust user input validation.
    *   `requests`: Required *only* if you use the optional dictionary validation feature.

## Setup

1.  **Clone or Download:** Get the project files.
2.  **Navigate to Directory:** Open your terminal or command prompt and change into the project directory (`text_case_converter/`).
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

## Usage

1.  Make sure your virtual environment is activated (if you created one).
2.  Run the script from the terminal:
    ```bash
    python text_transformer.py
    ```
3.  The script will:
    *   Prompt you to enter the text you want to convert.
    *   Present a menu of available target cases.
    *   If you choose `snake_case` or `kebab-case`, it will ask if you want to perform optional dictionary validation for the segments (requires internet).
    *   Display the original text and the converted result.
    *   Ask if you want to perform another conversion. Type `yes` or `no`.
    *   You can type `quit` at the text input prompt to exit.

## Notes on Case Conversion Logic

*   **camelCase/PascalCase:** Non-alphanumeric characters are treated as separators. The first word is lowercased for camelCase.
*   **snake\_case/kebab-case:** The script attempts to identify word boundaries based on existing non-alphanumeric characters or changes in capitalization (e.g., `MyExampleText` becomes `my_example_text`). Dictionary validation is optional and uses an external API.
*   **Sentence case:** Capitalizes only the very first letter of the input string.

## License

This project can be considered under the MIT License (or specify otherwise if needed).