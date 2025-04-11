# Unit Converter (Project T01)

## Description

A comprehensive and user-friendly command-line tool for accurately converting between a wide array of measurement units. Supports length (meters, feet, miles), weight/mass (kg, pounds, ounces), temperature (Celsius, Fahrenheit, Kelvin), volume (liters, gallons), speed, pressure, energy, and more. Ideal for students, engineers, scientists, and everyday use requiring precise unit translation across metric, imperial, and other systems.

## Features

*   Converts between dozens of units across multiple categories (length, mass, temperature, volume, speed, pressure, energy, etc.).
*   Supports standard metric (SI) and imperial systems, plus potentially specialized units.
*   Performs high-precision calculations using appropriate conversion factors.
*   Utilizes an intuitive command-line interface with robust input validation via `PyInputPlus`.
*   Handles common and scientific unit conversions.
*   **Optional:** Tracks history of recent conversions via simple JSON storage (`conversion_history.json`).
*   Can potentially be integrated as a backend module for larger applications (core logic is self-contained).

## Requirements

*   Python 3.7+
*   Libraries listed in `requirements.txt`:
    *   `pyinputplus`: For robust user input validation.
*   Standard libraries: `json`, `math`.

## Setup

1.  **Clone or Download:** Get the project files (`unit_converter_core.py`, `requirements.txt`).
2.  **Navigate to Directory:** Open your terminal or command prompt and change into the project directory.
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
    python unit_converter_core.py
    ```
3.  The script will:
    *   Present a menu to choose the category of conversion (e.g., Length, Temperature).
    *   Prompt you to select the unit you are converting *from*.
    *   Prompt you to select the unit you are converting *to*.
    *   Ask for the value (amount) you want to convert.
    *   Display the conversion result.
    *   Optionally save the conversion to the history file.
    *   Ask if you want to perform another conversion.

## Optional History

*   If enabled or implemented in the code, the script may save recent conversions to a `conversion_history.json` file in the same directory.
*   This allows reviewing past conversions but is a basic implementation.

## License

This project can be considered under the MIT License (or specify otherwise if needed).