# Universal Management System (Project T06)

## Description

A highly configurable and adaptable command-line framework designed as a foundation for various data management applications. It provides core Create, Read, Update, Delete (CRUD) functionalities organized into distinct modules:

*   **Student Management:** Manage student records, grades, and attendance.
*   **Inventory Management:** Track inventory items, stock levels, prices, and suppliers.
*   **Records Management:** Store general-purpose records with metadata (category, tags).
*   **Custom Management:** A *basic* framework for storing user-defined record types with custom fields using JSON.

The system includes features for data analysis (averages), basic visualization (using Matplotlib to save plots), and data export (to CSV).

## Core Features

*   **Modular Design:** Separate managers for Students, Inventory, Records, and Custom data.
*   **CRUD Operations:** Standard Create, Read, Update, Delete functions for each module.
*   **Database Storage:** Uses SQLite (`management_system.db`) for persistent data storage.
*   **Data Export:** Export data from any module to CSV files (saved in `data_exports/`).
*   **Data Visualization:** Generate basic plots (e.g., student grade distribution, inventory stock levels) saved as PNG files in `plots/` (requires Matplotlib).
*   **Search & Filtering:** Basic search capabilities within modules.
*   **User-Friendly Interface:** Uses `PyInputPlus` for robust command-line interaction.
*   **Extensibility:** Designed conceptually to be extended with more modules or features.

## Modules Detailed

### Student Management
*   Add, view, update, delete student profiles (ID, name, grade, contact).
*   Track basic attendance status.
*   Manage multiple grades per student (subject, grade value).
*   Calculate average grade per student.
*   Visualize grades per student (bar chart saved to file).

### Inventory Management
*   Add, view, update, delete inventory items (SKU, name, description, quantity, price).
*   Track stock levels and adjust quantities.
*   Set reorder points and view low-stock items.
*   Store basic supplier information.
*   Visualize overall stock levels (bar chart saved to file).

### Records Management
*   Add, view, update, delete general records (title, snippet).
*   Categorize and tag records (simple comma-separated tags).
*   Search records by title, snippet, category, or tag.

### Custom Management (Simplified)
*   **Concept:** Allows storing records of user-defined types (e.g., 'Project', 'Recipe').
*   **Implementation:** Uses a generic table where custom fields for each record are stored as a single JSON string in the `custom_data` column.
*   **Functionality:** Add new custom records, view records filtered by type/name. *Update/Delete are not implemented in this basic version but could be added.* Export provides basic table data including the JSON string.

## Requirements

*   Python 3.7+
*   Libraries listed in `requirements.txt`:
    *   `matplotlib`: For generating plot visualizations.
    *   `pyinputplus`: For robust user input validation.
*   Standard libraries: `sqlite3`, `json`, `os`, `csv`, `datetime`.

## Setup

1.  **Clone or Download:** Get the project files. Ensure you have `universal_management_system.py` and `requirements.txt`.
2.  **Navigate to Directory:** Open your terminal or command prompt and change into the project directory (`universal_management_system/`).
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
    *(If you don't need visualization features, you could optionally skip installing `matplotlib`, but the visualization options in the menu will then show an error message).*

## Usage

1.  Make sure your virtual environment is activated (if you created one).
2.  Run the script from the terminal:
    ```bash
    python universal_management_system.py
    ```
3.  The script will:
    *   Automatically create the `management_system.db` database file if it doesn't exist.
    *   Create the `data_exports/` and `plots/` directories if they don't exist.
    *   Present the main menu to choose a management module (Students, Inventory, Records, Custom).
    *   Navigate through the sub-menus for each module to perform CRUD operations, view data, export, or visualize.
    *   Follow the on-screen prompts for input.
    *   Select 'Exit' from the main menu to quit the application.

## License

This project can be considered under the MIT License (or specify otherwise if needed).