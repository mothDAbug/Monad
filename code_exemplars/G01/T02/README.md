# Real-Time Currency Converter (Project T02)

## Description

A command-line real-time currency conversion tool that fetches up-to-date exchange rates from a reliable API (ExchangeRate-API). Allows users to quickly convert amounts between numerous world currencies. Essential for finance, travel planning, e-commerce, and international business applications.

## Features

*   Fetches real-time exchange rates via the ExchangeRate-API.
*   Supports conversion between a vast list of global currencies (USD, EUR, JPY, GBP, etc.).
*   Interactive command-line interface for easy amount and currency input using `PyInputPlus` for validation.
*   Implements local caching of exchange rates (using `rates_cache.json`) for offline use or to reduce API calls. Cache validity is configurable (default: 6 hours).
*   Handles API key management securely using a `.env` file.
*   Provides accurate and current foreign exchange (Forex) conversions.
*   Displays available currencies neatly.
*   Gracefully handles potential network errors and API issues.

## Requirements

*   Python 3.7+
*   Libraries listed in `requirements.txt`:
    *   `requests`: For making HTTP requests to the API.
    *   `pyinputplus`: For robust user input validation.
    *   `python-dotenv`: For loading environment variables from the `.env` file.

## Setup

1.  **Clone or Download:** Get the project files.
2.  **Navigate to Directory:** Open your terminal or command prompt and change into the project directory (`currency_converter/`).
3.  **API Key:**
    *   Sign up for a free API key at [https://www.exchangerate-api.com/](https://www.exchangerate-api.com/).
    *   Create a file named `.env` in the project directory.
    *   Add your API key to the `.env` file like this:
        ```dotenv
        EXCHANGE_RATE_API_KEY="YOUR_ACTUAL_API_KEY"
        ```
    *   **Important:** Replace `"YOUR_ACTUAL_API_KEY"` with the key you obtained.
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
    python currency_exchange_system.py
    ```
3.  The script will:
    *   Attempt to load cached rates.
    *   If the cache is missing or outdated, it will fetch fresh rates from the API using your key and update the cache (`rates_cache.json`).
    *   Display the list of available currencies.
    *   Prompt you to enter the amount, the source currency, and the target currency. Use the full currency codes (e.g., `USD`, `EUR`, `JPY`) or select from the numbered list provided by `PyInputPlus`.
    *   Display the conversion result.
    *   Ask if you want to perform another conversion. Type `yes` or `no`.
    *   You can type `quit` at any prompt to exit.

## Caching

*   To minimize API calls and allow for limited offline use, the script caches the fetched exchange rates in a `rates_cache.json` file.
*   The cache is considered valid for a specific duration (default is 6 hours, configurable via `CACHE_DURATION_HOURS` in the script).
*   If the cache file exists and is within the valid duration, the script uses the cached rates. Otherwise, it fetches new rates from the API.

## License

This project can be considered under the MIT License (or specify otherwise if needed).