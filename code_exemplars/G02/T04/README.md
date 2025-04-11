# Random Name Generator (Project T04)

## Description

Generates realistic-sounding random names (first, last, or full) based on lists provided in JSON files. Ideal for creating test user data, character names in games or stories, or anonymizing datasets.

## Features

*   Generate random first names, last names, or full names.
*   Pulls names from customizable JSON data files (`data/first_names.json`, `data/last_names.json`). Easily add more names or create files for different cultural origins.
*   Specify the quantity of names to generate.
*   Simple, interactive command-line interface using `PyInputPlus` for clear prompts.
*   Option to save the generated list of names to a text file.
*   Basic error handling for missing or invalid data files.

## Requirements

*   Python 3.7+
*   Libraries listed in `requirements.txt`:
    *   `pyinputplus`: For robust user input validation.

## Setup

1.  **Clone or Download:** Get the project files. Ensure you have the `name_generator_engine.py` script, the `requirements.txt` file, and the `data` folder containing `first_names.json` and `last_names.json`.
2.  **Navigate to Directory:** Open your terminal or command prompt and change into the project directory (`random_name_generator/`).
3.  **(Optional) Customize Names:** Edit the `first_names.json` and `last_names.json` files in the `data` directory to add, remove, or change the names used for generation. Ensure they remain valid JSON lists of strings. You can create more files (e.g., `middle_names.json`) and modify the script if needed.
4.  **Create Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    ```
    *   Activate it:
        *   Windows: `.\venv\Scripts\activate`
        *   macOS/Linux: `source venv/bin/activate`
5.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1.  Make sure your virtual environment is activated (if you created one).
2.  Run the script from the terminal:
    ```bash
    python name_generator_engine.py
    ```
3.  The script will:
    *   Load names from the JSON files in the `data` directory.
    *   Prompt you to choose the type of name to generate (Full, First Only, Last Only).
    *   Ask for the number of names you want.
    *   Generate and display the names (or a sample if the list is long).
    *   Ask if you want to save the list to a file. If yes, it will prompt for a filename (defaulting to `generated_names.txt`).
    *   Ask if you want to generate more names.

## Data Files

*   The core name lists are stored in simple JSON files within the `data/` subdirectory.
*   `first_names.json`: Contains a list of first names.
*   `last_names.json`: Contains a list of last names.
*   You can modify these files or add new ones (e.g., for different languages/cultures) and update the `load_names_from_json` calls in the script if needed.

## License

This project can be considered under the MIT License (or specify otherwise if needed).