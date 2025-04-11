# Number Guessing Game (Project T15)

## Description

A classic interactive command-line game where the computer thinks of a random number within a specified range, and the player attempts to guess it within a limited number of attempts. Includes difficulty levels, high score tracking, and game statistics.

## Features

*   **Random Number Generation:** Computer picks a secret number.
*   **User Input:** Player enters guesses via the command line using `PyInputPlus` for validation.
*   **Feedback:** Provides feedback ('Too high', 'Too low', 'Correct!').
*   **Difficulty Levels:**
    *   Easy (1-50, 10 attempts)
    *   Medium (1-100, 7 attempts)
    *   Hard (1-200, 7 attempts)
    *   (Ranges/attempts can be configured in the script).
*   **Attempt Tracking:** Limits the number of guesses based on difficulty.
*   **High Score List:** Records the top scores (lowest number of guesses) for each difficulty level, stored in `data/high_scores.json`.
*   **Game Statistics:** Tracks overall stats like games played, wins, losses, average guesses per win, stored in `data/game_stats.json`.
*   **Statistics Visualization:** Optionally generates a bar chart showing the distribution of guesses taken in winning games (requires Matplotlib), saved to `plots/`.

## Requirements

*   Python 3.7+
*   Libraries listed in `requirements.txt`:
    *   `pyinputplus`: For user input validation.
    *   `matplotlib`: For optional statistics visualization.
*   Standard libraries: `random`, `json`, `os`, `datetime`.

## Setup

1.  **Clone or Download:** Get the project files (`number_guesser_game.py`, `requirements.txt`).
2.  **Navigate to Directory:** Open terminal/cmd into the `number_guessing_game/` directory.
3.  **Create Virtual Environment (Recommended):** `python -m venv venv` then activate.
4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(If you don't need the statistics visualization feature, you could optionally skip installing `matplotlib`, but the visualization option will show an error message).*
5.  **(Optional) Initial Data Files:** The script will automatically create the `data` directory and empty `high_scores.json` and `game_stats.json` files if they don't exist on the first run.

## Usage

1.  Make sure your virtual environment is activated.
2.  Run the script:
    ```bash
    python number_guesser_game.py
    ```
3.  Use the main menu:
    *   **Play Game:** Starts a new round. You'll choose a difficulty, and then start guessing.
    *   **View High Scores:** Displays the top scores recorded for each difficulty level.
    *   **View Statistics:** Shows overall game statistics (wins, losses, averages). Optionally generates a plot of guess distribution for wins.
    *   **Exit:** Quits the game.

## Game Rules

1.  Select a difficulty level.
2.  The computer chooses a secret number within the range for that difficulty.
3.  Enter your guess when prompted.
4.  The computer tells you if your guess is too high or too low.
5.  Keep guessing until you find the number or run out of attempts.
6.  If you win, you can enter your name for the high score list!

## License

This project can be considered under the MIT License (or specify otherwise if needed). Have fun!