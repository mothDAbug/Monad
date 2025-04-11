# Task Management System (Project T09)

## Description

A comprehensive personal productivity application combining a to-do list, basic task scheduling, and status tracking into one integrated command-line package. Designed to help users manage daily tasks, track progress, set priorities, and stay organized.

## Features

*   **Task Management (CRUD):** Create, view, update, and delete tasks with titles, descriptions, categories, priorities, and statuses.
*   **Database Storage:** Uses SQLite (`task_manager.db`) for persistent storage of tasks.
*   **Filtering & Sorting:** View tasks filtered by status, priority, category, or upcoming due dates. Sort tasks by due date, priority, creation date, or title.
*   **Priorities & Status:** Assign priority levels (High, Medium, Low, None) and track status (Pending, In-Progress, Completed).
*   **Due Dates & Scheduling:** Assign optional due dates (YYYY-MM-DD) or specific scheduled times (YYYY-MM-DD HH:MM).
*   **Subtasks:** Basic support for adding subtasks linked to a parent task (deletion cascades).
*   **Text Calendar View:** Display a simple monthly calendar highlighting days with task due dates.
*   **Data Visualization:** Generate basic plots (e.g., pie chart of task statuses) saved as PNG files in `plots/` (requires Matplotlib).
*   **CSV Export:** Export task lists to CSV format (saved in `data_exports/`).
*   **User-Friendly Interface:** Uses `PyInputPlus` for robust command-line interaction and input validation.

## Requirements

*   Python 3.7+
*   Libraries listed in `requirements.txt`:
    *   `matplotlib`: For generating plot visualizations.
    *   `pyinputplus`: For robust user input validation.
*   Standard libraries: `sqlite3`, `datetime`, `csv`, `os`, `calendar`.

## Setup

1.  **Clone or Download:** Get the project files (`task_manager.py`, `requirements.txt`).
2.  **Navigate to Directory:** Open your terminal or command prompt and change into the project directory (`task_management_system/`).
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
    *(If you don't need visualization features, you could optionally skip installing `matplotlib`, but the visualization option in the menu will then show an error message).*

## Usage

1.  Make sure your virtual environment is activated (if you created one).
2.  Run the script from the terminal:
    ```bash
    python task_manager.py
    ```
3.  The script will:
    *   Automatically create the `task_manager.db` database file if it doesn't exist.
    *   Create the `data_exports/` and `plots/` directories if they don't exist.
    *   Optionally display tasks due today upon startup.
    *   Present the main menu with available actions (Add, View, Update, Delete, Subtasks, Calendar, Visualize, Export, Exit).
    *   Follow the on-screen prompts for input. Dates should generally be entered as `YYYY-MM-DD`, times as `HH:MM`.
    *   When viewing tasks, you'll be prompted for filtering and sorting preferences.
    *   Select 'Exit' from the main menu to quit the application.

## Database Schema (`tasks` table)

*   `task_id`: INTEGER, Primary Key, Auto-increment
*   `title`: TEXT, Not Null
*   `description`: TEXT
*   `category`: TEXT
*   `priority`: INTEGER (0: None, 1: High, 2: Medium, 3: Low)
*   `status`: INTEGER (0: Pending, 1: In-Progress, 2: Completed)
*   `created_at`: TIMESTAMP (Defaults to current time)
*   `due_date`: TIMESTAMP (Optional)
*   `scheduled_time`: TIMESTAMP (Optional, for specific event times)
*   `parent_task_id`: INTEGER (Foreign Key to `tasks.task_id`, allows NULL)

## Limitations

*   **Reminders:** This CLI version does not provide active system notifications or pop-up reminders. "Reminders" are primarily handled by viewing upcoming/due tasks.
*   **Recurring Tasks:** Does not have built-in support for automatically creating recurring tasks.
*   **Tags:** Tagging functionality (many-to-many) is commented out in the schema setup but could be implemented as an extension.
*   **Complex Scheduling:** Scheduling features are basic (setting a date/time). No advanced calendar integration or conflict detection.

## License

This project can be considered under the MIT License (or specify otherwise if needed).