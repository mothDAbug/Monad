# Universal Tracker System (Project T10)

## Description

A highly flexible and adaptable command-line framework for tracking diverse personal or professional metrics. It integrates multiple tracking modules into a single system with database storage, reporting, visualization, and data export capabilities.

## Modules

*   **Expense Tracker:** Log expenses with amount, category, date, and notes. View recent expenses and monthly summaries by category. Generate spending pie charts.
*   **Time Tracker:** Log time spent on activities (projects, tasks, clients). Log by duration or start/end times. View recent logs and weekly summaries by activity. Generate time allocation bar charts.
*   **Goal Tracker:** Define goals (numeric or binary completion) with targets and optional deadlines. Update progress and view goal status.
*   **Custom Metric Tracker:** Define your own metrics to track (e.g., mood, weight, pages read). Log numerical values against these metrics with timestamps. View recent logs and visualize trends over time.
*   **Habit Tracker:** Define daily habits. Log daily completion status and automatically track streaks. View recent logs and visualize completion/streak trends.

## Core Features

*   **Modular Design:** Separate manager classes for each tracking module.
*   **Database Storage:** Uses SQLite (`tracker_system.db`) for persistent data storage across all modules.
*   **Data Logging:** User-friendly interfaces using `PyInputPlus` for logging data in each module. Supports date keywords (`today`, `yesterday`).
*   **Reporting & Summaries:** View recent entries and generate summaries (e.g., monthly expenses, weekly time).
*   **Data Visualization:** Generate plots (pie charts, bar charts, line charts) for relevant data using Matplotlib, saved as PNG files in `plots/`.
*   **CSV Export:** Export data from any module's primary table to CSV files (saved in `data_exports/`).
*   **Streak Tracking:** Automatic calculation and tracking of consecutive completion days for habits.

## Requirements

*   Python 3.7+
*   Libraries listed in `requirements.txt`:
    *   `matplotlib`: For generating plot visualizations.
    *   `pyinputplus`: For robust user input validation.
*   Standard libraries: `sqlite3`, `datetime`, `csv`, `os`, `json`.

## Setup

1.  **Clone or Download:** Get the project files (`universal_tracking_system.py`, `requirements.txt`).
2.  **Navigate to Directory:** Open your terminal or command prompt and change into the project directory (`universal_tracker_system/`).
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
    *(If you don't need visualization features, you could optionally skip installing `matplotlib`, but visualization options in the menus will then show an error message).*

## Usage

1.  Make sure your virtual environment is activated (if you created one).
2.  Run the script from the terminal:
    ```bash
    python universal_tracking_system.py
    ```
3.  The script will:
    *   Automatically create the `tracker_system.db` database file if it doesn't exist.
    *   Create the `data_exports/` and `plots/` directories if they don't exist.
    *   Present the main menu to choose a tracking module (Expense, Time, Goal, Custom Metric, Habit).
    *   Navigate through the sub-menus for each module to log data, view entries/summaries, visualize, or export.
    *   Follow the on-screen prompts for input. Dates should generally be entered as `YYYY-MM-DD` or using keywords `today`, `yesterday`.
    *   Select 'Exit' from the main menu to quit the application.

## Database Schema (Primary Tables)

*   `expenses`: (expense\_id, amount, currency, category, expense\_date, notes, created\_at)
*   `time_logs`: (log\_id, activity\_name, start\_time, end\_time, duration\_minutes, log\_date, category, notes, created\_at)
*   `goals`: (goal\_id, name, description, metric\_type, target\_value, current\_value, unit, deadline, status, created\_at)
*   `custom_metrics`: (metric\_id, name, unit, description, created\_at)
*   `metric_logs`: (log\_id, metric\_id, value, log\_timestamp, notes)
*   `habits`: (habit\_id, name, frequency, description, created\_at)
*   `habit_logs`: (log\_id, habit\_id, log\_date, completed, notes, current\_streak)

## License

This project can be considered under the MIT License (or specify otherwise if needed).