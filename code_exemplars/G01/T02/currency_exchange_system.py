import requests
import json
import pyinputplus as pyip
import os
import datetime
from dotenv import load_dotenv

# --- Configuration ---
CACHE_FILE = "rates_cache.json"
CACHE_DURATION_HOURS = 6  # How long the cache is valid in hours
BASE_CURRENCY = "USD"  # Base currency for API requests

# --- Load API Key ---
load_dotenv()
API_KEY = os.getenv("EXCHANGE_RATE_API_KEY")

if not API_KEY:
    print("Error: EXCHANGE_RATE_API_KEY not found in .env file.")
    print("Please create a .env file with your API key.")
    print("Example: EXCHANGE_RATE_API_KEY=\"YOUR_KEY_HERE\"")
    exit()

API_URL = f"https://v6.exchangerate-api.com/v6/{API_KEY}/latest/{BASE_CURRENCY}"

# --- Cache Functions ---

def load_cache():
    """Loads exchange rates from the cache file if it exists and is valid."""
    if not os.path.exists(CACHE_FILE):
        return None

    try:
        # Check cache file age
        cache_mod_time = os.path.getmtime(CACHE_FILE)
        now = datetime.datetime.now().timestamp()
        max_age_seconds = CACHE_DURATION_HOURS * 3600

        if (now - cache_mod_time) > max_age_seconds:
            print("Cache is outdated.")
            return None

        with open(CACHE_FILE, 'r') as f:
            cache_data = json.load(f)
            # Basic validation: check if it has the expected structure
            if "rates" in cache_data and "last_updated_utc" in cache_data:
                 print("Using cached rates.")
                 return cache_data["rates"]
            else:
                print("Cache file format is invalid.")
                return None
    except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
        print(f"Error loading cache: {e}")
        return None

def save_cache(rates_data):
    """Saves fetched exchange rates to the cache file."""
    try:
        # API provides 'time_last_update_utc', use it if available for accuracy
        timestamp = rates_data.get('time_last_update_utc', datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000"))
        cache_content = {
            "last_updated_utc": timestamp,
            "base_code": rates_data.get('base_code', BASE_CURRENCY),
            "rates": rates_data.get('conversion_rates', {})
        }
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_content, f, indent=4)
        print("Rates saved to cache.")
    except (IOError, TypeError) as e:
        print(f"Error saving cache: {e}")

# --- API Fetch Function ---

def fetch_exchange_rates():
    """Fetches the latest exchange rates from the API."""
    print(f"Fetching latest exchange rates from API (Base: {BASE_CURRENCY})...")
    try:
        response = requests.get(API_URL, timeout=10) # Added timeout
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        data = response.json()

        # Check API response structure and status
        if data.get("result") == "success" and "conversion_rates" in data:
            print("Successfully fetched rates from API.")
            save_cache(data)
            return data["conversion_rates"]
        else:
            error_type = data.get("error-type", "Unknown API Error")
            print(f"Error fetching rates from API: {error_type}")
            # Provide specific feedback for common errors
            if "invalid-key" in error_type:
                print("-> Your API Key might be invalid or inactive.")
            elif "inactive-account" in error_type:
                 print("-> Your API Key is associated with an inactive account.")
            elif "quota-reached" in error_type:
                 print("-> You have exceeded your API request quota.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Network error fetching rates: {e}")
        return None
    except json.JSONDecodeError:
        print("Error: Failed to decode API response.")
        return None

# --- Core Conversion Logic ---

def get_rates():
    """Gets exchange rates, trying cache first, then API."""
    rates = load_cache()
    if rates:
        return rates
    else:
        return fetch_exchange_rates()

def convert_currency(amount, from_currency, to_currency, rates):
    """Performs the currency conversion."""
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if from_currency not in rates:
        print(f"Error: Currency code '{from_currency}' not found in rates.")
        return None
    if to_currency not in rates:
        print(f"Error: Currency code '{to_currency}' not found in rates.")
        return None

    # Conversion formula: Amount * (ToRate / FromRate)
    # Since rates are relative to BASE_CURRENCY (e.g., USD):
    # AmountInUSD = Amount / rates[from_currency]
    # AmountInTarget = AmountInUSD * rates[to_currency]
    # Simplified: Amount * (rates[to_currency] / rates[from_currency])

    if from_currency == BASE_CURRENCY:
        converted_amount = amount * rates[to_currency]
    elif to_currency == BASE_CURRENCY:
         converted_amount = amount / rates[from_currency]
    else:
        converted_amount = amount * (rates[to_currency] / rates[from_currency])

    return converted_amount

# --- Main Application ---

def main():
    """Main function to run the currency converter."""
    print("-" * 30)
    print("   Real-Time Currency Converter")
    print("-" * 30)

    rates = get_rates()

    if not rates:
        print("\nCould not obtain exchange rates. Exiting.")
        print(f"(Check your API key in .env, internet connection, and API service status)")
        return

    available_currencies = sorted(list(rates.keys()))
    print(f"\nAvailable currencies ({len(available_currencies)}):")
    # Print currencies in columns for better readability
    col_width = 10
    cols = 6
    for i in range(0, len(available_currencies), cols):
        print(" ".join(f"{cur:<{col_width}}" for cur in available_currencies[i:i+cols]))

    while True:
        print("\nEnter conversion details:")

        # Get amount using pyinputplus for validation
        amount = pyip.inputFloat("Amount: ", min=0)

        # Get 'from' currency using pyinputplus menu for validation
        from_currency = pyip.inputMenu(available_currencies,
                                       prompt="Convert FROM currency (e.g., USD): \n",
                                       numbered=False, blank=False, caseSensitive=False)

        # Get 'to' currency using pyinputplus menu for validation
        to_currency = pyip.inputMenu(available_currencies,
                                     prompt="Convert TO currency (e.g., EUR): \n",
                                     numbered=False, blank=False, caseSensitive=False)

        # Perform conversion
        converted_amount = convert_currency(amount, from_currency, to_currency, rates)

        if converted_amount is not None:
            print("-" * 30)
            print(f"Result: {amount:.2f} {from_currency.upper()} = {converted_amount:,.2f} {to_currency.upper()}")
            print("-" * 30)
        else:
            print("Conversion failed.")

        # Ask to continue
        another = pyip.inputYesNo("\nPerform another conversion? (yes/no): ")
        if another == 'no':
            break

    print("\nThank you for using the Currency Converter!")

if __name__ == "__main__":
    main()