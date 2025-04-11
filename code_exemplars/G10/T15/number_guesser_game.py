# number_guesser_game.py (Corrected visualize_guess_distribution)

import random
import json
import os
import datetime
import sys
# Make sure pyinputplus and matplotlib are installed:
# pip install pyinputplus matplotlib
try:
    import pyinputplus as pyip
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError as import_error:
    # Handle specific missing libraries
    if 'pyinputplus' in str(import_error):
        print("Error: pyinputplus library not found. Please install it: pip install pyinputplus")
    elif 'matplotlib' in str(import_error):
        print("Warning: matplotlib library not found. Visualization will be disabled.")
        print("To enable visualization, install it: pip install matplotlib")
        MATPLOTLIB_AVAILABLE = False
    else:
        print(f"An unexpected import error occurred: {import_error}")
    # Decide if the program should exit or continue with limited functionality
    # For this game, matplotlib is optional for core gameplay. pyinputplus is required.
    if 'pyinputplus' in str(import_error):
       sys.exit("Exiting due to missing required library.")
    # If only matplotlib is missing, we can continue without visualization.


# --- Configuration ---
DATA_DIR = "data"
SCORES_FILE = os.path.join(DATA_DIR, "high_scores.json")
STATS_FILE = os.path.join(DATA_DIR, "game_stats.json")
PLOT_DIR = "plots"
MAX_HIGH_SCORES = 10

DIFFICULTY_LEVELS = {
    "Easy": {"range": (1, 50), "attempts": 10},
    "Medium": {"range": (1, 100), "attempts": 7},
    "Hard": {"range": (1, 200), "attempts": 7}
}
# Define format constants globally
DATE_FORMAT_DISPLAY = "%Y-%m-%d %H:%M" # For displaying high score dates
FILENAME_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S" # For unique filenames (filesystem safe)

# --- Data Handling ---
def load_json_data(filepath, default_data):
    """Loads JSON data from a file, creating it with defaults if necessary."""
    # Ensure the directory exists
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
    except OSError as e:
        print(f"Error: Could not create directory for '{filepath}': {e}. Using defaults.")
        return default_data

    # Check if file exists, create if not
    if not os.path.exists(filepath):
        print(f"Info: Data file '{os.path.basename(filepath)}' not found. Creating with defaults.")
        save_json_data(filepath, default_data) # Try to save defaults
        return default_data # Return defaults regardless of save success

    # Try to load existing file
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Failed to load or parse '{os.path.basename(filepath)}': {e}. Using default data.")
        return default_data
    except Exception as e:
        print(f"Warning: An unexpected error occurred loading '{os.path.basename(filepath)}': {e}. Using defaults.")
        return default_data

def save_json_data(filepath, data):
    """Saves data to a JSON file."""
    try:
        # Ensure the directory exists before saving
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
    except (IOError, OSError) as e:
        print(f"Error: Failed to save data to '{os.path.basename(filepath)}': {e}")
    except Exception as e:
        print(f"Error: An unexpected error occurred saving '{os.path.basename(filepath)}': {e}")


# --- High Score Management ---
def update_high_scores(difficulty, player_name, guesses):
    """Updates the high score list for a given difficulty."""
    scores_data = load_json_data(SCORES_FILE, {"Easy": [], "Medium": [], "Hard": []})

    # Ensure the difficulty key exists
    if difficulty not in scores_data:
        scores_data[difficulty] = []

    level_scores = scores_data[difficulty]
    now = datetime.datetime.now().strftime(DATE_FORMAT_DISPLAY) # Use display format

    # Add the new score
    level_scores.append({"name": player_name, "guesses": guesses, "date": now})

    # Sort scores by the number of guesses (ascending)
    level_scores.sort(key=lambda x: x["guesses"])

    # Keep only the top N scores
    scores_data[difficulty] = level_scores[:MAX_HIGH_SCORES]

    save_json_data(SCORES_FILE, scores_data)

def display_high_scores():
    """Displays the high scores for all difficulties."""
    print("\n--- High Scores ---")
    scores_data = load_json_data(SCORES_FILE, {"Easy": [], "Medium": [], "Hard": []})
    found_any_scores = False

    for diff, scores in scores_data.items():
        print(f"\n--- {diff} ---")
        if not scores:
            print("No scores yet.")
            continue # Skip to the next difficulty

        found_any_scores = True
        # Print header
        print("{:<5} {:<20} {:<8} {}".format("Rank", "Name", "Guesses", "Date"))
        print("-" * 60)
        # Print scores
        for i, score_entry in enumerate(scores):
            # Use .get() for robustness in case a key is missing unexpectedly
            name = score_entry.get("name", "N/A")
            guesses = score_entry.get("guesses", "?")
            date = score_entry.get("date", "N/A")
            print("{:<5} {:<20} {:<8} {}".format(i + 1, name, guesses, date))
        print("-" * 60)

    if not found_any_scores:
        print("\nNo high scores recorded yet for any difficulty.")


# --- Statistics Management ---
DEFAULT_STATS = {
    "total_games_played": 0,
    "total_wins": 0,
    "total_losses": 0,
    "total_guesses_made": 0,
    "average_guesses_per_win": 0.0,
    "guess_distribution": {}, # Stores win counts per number of guesses { '3': 5, '4': 10, ... }
    "total_guesses_in_wins": 0 # Sum of guesses for all wins, used for average
}

def update_stats(win, guesses_taken, difficulty=None): # difficulty currently unused here, but could be added later
    """Updates game statistics."""
    stats_data = load_json_data(STATS_FILE, DEFAULT_STATS.copy()) # Use .copy()

    stats_data["total_games_played"] += 1
    stats_data["total_guesses_made"] += guesses_taken

    if win:
        stats_data["total_wins"] += 1
        stats_data["total_guesses_in_wins"] += guesses_taken

        # Update average guesses per win
        if stats_data["total_wins"] > 0:
            stats_data["average_guesses_per_win"] = round(
                stats_data["total_guesses_in_wins"] / stats_data["total_wins"], 2
            )
        else:
             stats_data["average_guesses_per_win"] = 0.0 # Avoid division by zero if somehow total_wins is 0

        # Update guess distribution (using string key for JSON compatibility)
        guesses_key = str(guesses_taken)
        stats_data["guess_distribution"][guesses_key] = stats_data.get("guess_distribution", {}).get(guesses_key, 0) + 1
    else:
        stats_data["total_losses"] += 1

    save_json_data(STATS_FILE, stats_data)


def display_stats():
    """Displays game statistics and offers visualization."""
    print("\n--- Game Statistics ---")
    stats = load_json_data(STATS_FILE, DEFAULT_STATS.copy()) # Use .copy()

    total_games = stats.get('total_games_played', 0)
    total_wins = stats.get('total_wins', 0)
    total_losses = stats.get('total_losses', 0)
    total_guesses = stats.get('total_guesses_made', 0)
    avg_guesses_win = stats.get('average_guesses_per_win', 0.0)
    guess_dist = stats.get('guess_distribution', {})

    print(f"Total Games Played: {total_games}")
    print(f"Total Wins:         {total_wins}")
    print(f"Total Losses:       {total_losses}")

    # Calculate win percentage safely
    win_percentage = (total_wins / total_games * 100) if total_games > 0 else 0
    print(f"Win Percentage:     {win_percentage:.1f}%")

    print(f"Total Guesses Made: {total_guesses}")
    print(f"Average Guesses/Win:{avg_guesses_win:.2f}")
    print("-" * 25) # Adjust width as needed

    # Offer visualization only if matplotlib is available and there's data
    if MATPLOTLIB_AVAILABLE and guess_dist:
         try:
             # Use yes/no prompt with default 'no'
             if pyip.inputYesNo("Visualize guess distribution? (y/N): ", default='no', blank=True) == 'yes':
                  visualize_guess_distribution(guess_dist)
         except pyip.PyInputPlusException as e:
             print(f"Input error: {e}") # Handle potential pyinputplus errors
    elif not MATPLOTLIB_AVAILABLE and guess_dist:
        print("Guess distribution data exists, but visualization requires matplotlib.")
        print("(Install with: pip install matplotlib)")
    elif not guess_dist:
        print("No guess distribution data available to visualize.")


# --- Visualization ---
def visualize_guess_distribution(distribution_data):
    """Creates and saves a bar chart of the guess distribution for winning games."""
    if not MATPLOTLIB_AVAILABLE:
        print("Cannot visualize: matplotlib library is not available.")
        return
    if not distribution_data:
        print("No guess distribution data available to visualize.")
        return

    try:
        # Sort items by the integer value of the guess count (key)
        # Example: {'3': 5, '10': 2, '2': 8} -> [('2', 8), ('3', 5), ('10', 2)]
        sorted_items = sorted(distribution_data.items(), key=lambda item: int(item[0]))

        # Extract sorted guesses (as strings for labels) and counts
        guesses = [item[0] for item in sorted_items]
        counts = [item[1] for item in sorted_items]

        plt.figure(figsize=(10, 6)) # Adjust figure size as needed
        bars = plt.bar(guesses, counts, color='skyblue')
        plt.xlabel("Number of Guesses Taken (Wins)")
        plt.ylabel("Frequency (Number of Wins)")
        plt.title("Guess Distribution for Winning Games")
        plt.xticks(rotation=45, ha='right') # Rotate x-axis labels if many categories
        plt.tight_layout() # Adjust layout to prevent labels overlapping

        # Add labels on top of bars
        plt.bar_label(bars, padding=3)

        # Ensure plot directory exists
        os.makedirs(PLOT_DIR, exist_ok=True)

        # Generate a unique filename using the safe timestamp format
        timestamp_str = datetime.datetime.now().strftime(FILENAME_TIMESTAMP_FORMAT)
        filename = os.path.join(PLOT_DIR, f"guess_distribution_{timestamp_str}.png")

        # Save the plot
        plt.savefig(filename)
        plt.close() # Close the plot figure to free memory
        print(f"Guess distribution plot saved to '{filename}'")

    # No need for specific ImportError here as MATPLOTLIB_AVAILABLE check handles it
    except (ValueError, TypeError) as e:
         print(f"Error during visualization: Invalid data format in distribution - {e}")
    except OSError as e:
         print(f"Error saving plot: Could not write to file '{filename}' - {e}")
    except Exception as e:
         # Catch any other unexpected errors during plotting/saving
         print(f"An unexpected error occurred during visualization: {e}")


# --- Game Logic ---
def play_game():
    """Plays one round of the number guessing game."""
    print("\n--- New Game ---")

    # Select difficulty
    try:
        difficulty_choice = pyip.inputMenu(
            list(DIFFICULTY_LEVELS.keys()),
            prompt="Choose difficulty level:\n",
            numbered=True
        )
    except pyip.PyInputPlusException as e:
        print(f"Input error: {e}. Returning to main menu.")
        return

    settings = DIFFICULTY_LEVELS[difficulty_choice]
    min_num, max_num = settings["range"]
    max_attempts = settings["attempts"]

    # Generate secret number
    secret_number = random.randint(min_num, max_num)
    # print(f"[DEBUG] Secret number: {secret_number}") # Uncomment for debugging

    print(f"\nI'm thinking of a number between {min_num} and {max_num}.")
    print(f"You have {max_attempts} attempts to guess it.")

    guesses_taken = 0
    win = False

    # Game loop
    for attempt in range(1, max_attempts + 1):
        prompt_text = f"Attempt {attempt}/{max_attempts}. Your guess ({min_num}-{max_num}): "
        try:
            guess = pyip.inputInt(prompt_text, min=min_num, max=max_num, limit=3) # Limit retries for invalid input
        except pyip.RetryLimitException:
            print("Too many invalid inputs. Ending game.")
            break # Exit the loop if user fails to provide valid input
        except pyip.PyInputPlusException as e: # Catch other potential input errors
             print(f"Input error: {e}. Ending attempt.")
             continue # Skip to next attempt or end game if last attempt

        guesses_taken += 1 # Increment only on valid input attempt

        # Compare guess
        if guess < secret_number:
            print("Too low!")
        elif guess > secret_number:
            print("Too high!")
        else:
            print(f"\nCongratulations! You guessed the number {secret_number} correctly!")
            print(f"It took you {guesses_taken} guesses.")
            win = True
            break # Exit loop on correct guess

    # Game over message (if not won)
    if not win:
        print(f"\nSorry, you've run out of attempts. The number was {secret_number}.")

    # Update statistics (always update, win or lose)
    update_stats(win, guesses_taken, difficulty_choice)

    # Update high scores only if the player won
    if win:
         try:
            player_name = pyip.inputStr(
                "Enter your name for the high score list (max 20 chars): ",
                limit=3, # Allow a few tries
                blank=False, # Don't allow blank names
                blockRegexes=[(r'[<>{}"\'`]', "Invalid characters in name.")] # Basic filter
                ).strip()[:20] # Trim whitespace and limit length
            if not player_name: player_name = "Player" # Default if somehow still empty
            update_high_scores(difficulty_choice, player_name, guesses_taken)
         except pyip.RetryLimitException:
             print("Too many invalid name attempts. Not saving high score.")
         except pyip.PyInputPlusException as e:
             print(f"Input error for name: {e}. Not saving high score.")


# --- Main Menu ---
def main_menu():
    """Displays the main menu and handles user choices."""
    while True:
        print("\n======= Number Guessing Game =======")
        menu_options = ['Play Game', 'High Scores', 'Statistics', 'Exit']
        try:
            action = pyip.inputMenu(menu_options, numbered=True, prompt="Select an option:\n")

            if action == 'Play Game':
                play_game()
            elif action == 'High Scores':
                display_high_scores()
            elif action == 'Statistics':
                display_stats()
            elif action == 'Exit':
                print("\nThanks for playing! Goodbye.")
                sys.exit(0) # Clean exit

        except pyip.PyInputPlusException as e:
            print(f"Invalid menu choice: {e}. Please try again.")
        except Exception as e: # Catch unexpected errors in menu loop
            print(f"An unexpected error occurred in the main menu: {e}")
            # Optionally add more detailed logging or exit here
            # import traceback
            # traceback.print_exc()


# --- Main Execution ---
if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        print("\nOperation cancelled by user. Exiting.")
        sys.exit(1) # Indicate interruption exit status
    except Exception as e:
        # Catch any critical unexpected errors not handled elsewhere
        print(f"\nAn unexpected critical error occurred: {e}")
        import traceback
        traceback.print_exc() # Print detailed traceback for debugging
        sys.exit(1) # Indicate error exit status
