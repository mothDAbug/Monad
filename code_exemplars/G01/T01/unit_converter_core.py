# beginner_projects/G01_Conversion_Tools/unit_converter_core.py
import math
import json
import os
import pyinputplus as pyip
from datetime import datetime

# --- Configuration ---
HISTORY_FILE = 'unit_converter_history.json'
MAX_HISTORY = 20 # Max number of recent conversions to store

# --- Conversion Factors (Example subset, expand as needed) ---
# Base units: meter (m), kilogram (kg), Celsius (C), liter (L)
CONVERSION_FACTORS = {
    "length": {
        "m": 1.0, "km": 1000.0, "cm": 0.01, "mm": 0.001,
        "ft": 0.3048, "in": 0.0254, "mi": 1609.34, "yd": 0.9144
    },
    "mass": {
        "kg": 1.0, "g": 0.001, "mg": 0.000001, "lb": 0.453592,
        "oz": 0.0283495, "t": 1000.0 # metric tonne
    },
    "volume": {
        "l": 1.0, "ml": 0.001, "m3": 1000.0, # cubic meter
        "gal": 3.78541, # US gallon
        "qt": 0.946353, # US quart
        "pt": 0.473176, # US pint
        "cup": 0.236588 # US cup
    }
    # Temperature requires specific functions, not just factors
}

# --- Helper Functions ---
def load_history():
    """Loads conversion history from the JSON file."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load history file ({e}). Starting fresh.")
            return []
    return []

def save_history(history, new_entry):
    """Adds a new entry to history and saves it, keeping it within MAX_HISTORY."""
    history.insert(0, new_entry) # Add to the beginning
    history = history[:MAX_HISTORY] # Trim old entries
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=4)
    except IOError as e:
        print(f"Warning: Could not save history file ({e}).")

def get_unit_category(unit):
    """Finds the category (length, mass, etc.) a unit belongs to."""
    for category, units in CONVERSION_FACTORS.items():
        if unit.lower() in units:
            return category
    if unit.lower() in ['c', 'f', 'k']:
        return "temperature"
    return None

def convert_temperature(value, from_unit, to_unit):
    """Handles temperature conversions."""
    from_unit = from_unit.lower()
    to_unit = to_unit.lower()

    if from_unit == to_unit:
        return value

    # Convert input to Celsius first
    celsius_value = 0
    if from_unit == 'c':
        celsius_value = value
    elif from_unit == 'f':
        celsius_value = (value - 32) * 5 / 9
    elif from_unit == 'k':
        celsius_value = value - 273.15
    else:
        raise ValueError("Invalid 'from' temperature unit.")

    # Convert from Celsius to the target unit
    if to_unit == 'c':
        return celsius_value
    elif to_unit == 'f':
        return (celsius_value * 9 / 5) + 32
    elif to_unit == 'k':
        return celsius_value + 273.15
    else:
        raise ValueError("Invalid 'to' temperature unit.")

def convert_standard_unit(value, from_unit, to_unit, category):
    """Handles standard conversions using factors."""
    from_unit = from_unit.lower()
    to_unit = to_unit.lower()

    factors = CONVERSION_FACTORS.get(category)
    if not factors or from_unit not in factors or to_unit not in factors:
        raise ValueError(f"Unsupported units in category '{category}': {from_unit}, {to_unit}")

    # Convert 'from_unit' value to base unit value
    base_value = value * factors[from_unit]

    # Convert base unit value to 'to_unit' value
    result = base_value / factors[to_unit]
    return result

# --- Main Conversion Logic ---
def perform_conversion():
    """Guides the user through a unit conversion process."""
    print("\n--- Unit Converter ---")
    print("Supported categories: length, mass, volume, temperature")
    print("Example units:")
    print("  Length: m, km, cm, mm, ft, in, mi, yd")
    print("  Mass:   kg, g, mg, lb, oz, t")
    print("  Volume: l, ml, m3, gal, qt, pt, cup")
    print("  Temp:   C, F, K")
    print("-" * 20)

    while True:
        try:
            value_str = pyip.inputStr("Enter the value to convert (or 'q' to quit): ",
                                      blockRegexes=[r'[^\d.\-]', r'\..*\.']) # Allow digits, decimal, minus
            if value_str.lower() == 'q':
                return None # Signal to quit

            value = float(value_str)

            from_unit = pyip.inputStr("Enter the unit to convert FROM (e.g., 'kg', 'ft', 'C'): ").strip()
            to_unit = pyip.inputStr("Enter the unit to convert TO (e.g., 'lb', 'm', 'F'): ").strip()

            category_from = get_unit_category(from_unit)
            category_to = get_unit_category(to_unit)

            if not category_from or category_from != category_to:
                print("Error: Units must belong to the same category and be supported.")
                print(f"'{from_unit}' category: {category_from}, '{to_unit}' category: {category_to}")
                continue

            if category_from == "temperature":
                result = convert_temperature(value, from_unit, to_unit)
            else:
                result = convert_standard_unit(value, from_unit, to_unit, category_from)

            print("-" * 20)
            print(f"Result: {value} {from_unit} = {result:.6f} {to_unit}") # Format to 6 decimal places
            print("-" * 20)
            return {
                "timestamp": datetime.now().isoformat(),
                "value": value,
                "from_unit": from_unit,
                "to_unit": to_unit,
                "result": result,
                "category": category_from
            }

        except ValueError as ve:
            print(f"Input Error: {ve}")
        except pyip.RetryLimitException:
            print("Error: Too many invalid attempts.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        print("Please try again.")


# --- Main Application Loop ---
if __name__ == "__main__":
    history = load_history()
    print("Welcome to the Unit Converter!")

    while True:
        print("\nOptions:")
        print("1. Perform a new conversion")
        print("2. View history")
        print("3. Quit")
        choice = pyip.inputChoice(['1', '2', '3'], prompt="Enter your choice: ")

        if choice == '1':
            conversion_result = perform_conversion()
            if conversion_result:
                save_history(history, conversion_result)
            elif conversion_result is None: # User chose to quit from conversion prompt
                break
        elif choice == '2':
            print("\n--- Conversion History (Most Recent First) ---")
            if not history:
                print("No history yet.")
            else:
                for i, entry in enumerate(history):
                    print(f"{i+1}. [{entry.get('timestamp', 'N/A')}] {entry.get('value', '?')} {entry.get('from_unit', '?')} -> {entry.get('result', '?'):.4f} {entry.get('to_unit', '?')}")
            print("-" * 20)
        elif choice == '3':
            break

    print("Goodbye!")
