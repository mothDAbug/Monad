# Lorem Ipsum Generator (Project T05)

## Description

Creates placeholder text ('Lorem Ipsum') for use in design mockups, website layouts, and application development before final content is ready. Allows customization of text length (by words, sentences, or paragraphs) and output format (plain text, basic HTML, Markdown).

## Features

*   Generates specified number of paragraphs, sentences, or words of classic Lorem Ipsum text.
*   Customizable length parameters for generated content.
*   Output formats include:
    *   Plain Text (`.txt`)
    *   Basic HTML (paragraphs wrapped in `<p>` tags, saved as `.html`)
    *   Basic Markdown (paragraphs separated by newlines, saved as `.md`)
*   Interactive command-line interface using `PyInputPlus` for easy generation choices.
*   Option to save the generated dummy text directly to a file with a suggested extension based on format.
*   Uses a standard internal block of Lorem Ipsum text as the source.

## Requirements

*   Python 3.7+
*   Libraries listed in `requirements.txt`:
    *   `pyinputplus`: For robust user input validation.

## Setup

1.  **Clone or Download:** Get the project files (`lorem_ipsum_factory.py`, `requirements.txt`).
2.  **Navigate to Directory:** Open your terminal or command prompt and change into the project directory (`lorem_ipsum_generator/`).
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
    python lorem_ipsum_factory.py
    ```
3.  The script will:
    *   Prompt you to choose the generation unit (Paragraphs, Sentences, Words).
    *   Ask for the quantity of the chosen unit to generate.
    *   Prompt you to choose the output format (Plain Text, HTML, Markdown).
    *   Generate the text and display a preview.
    *   Ask if you want to save the output to a file. If yes, it will suggest a default filename (e.g., `lorem.txt`, `lorem.html`) and allow you to specify a different one.
    *   Ask if you want to generate more text.

## Customization

*   The source Lorem Ipsum text is hardcoded in the `LOREM_IPSUM_WORDS` list within the script. You could potentially modify this list or load text from an external file if desired.
*   The sentence and paragraph length ranges (`min_words`, `max_words`, `min_sentences`, `max_sentences`) can be adjusted within the `generate_sentence` and `generate_paragraph` functions.

## License

This project can be considered under the MIT License (or specify otherwise if needed).