# task_manager.py (Corrected for DD/MM/YYYY, Keywords, IndexError)

import sqlite3
import datetime
import csv
import os
import pyinputplus as pyip
import matplotlib.pyplot as plt
import sys
import calendar

# --- Configuration ---
DB_NAME = "task_manager.db"
EXPORT_DIR = "data_exports"
PLOT_DIR = "plots"

# --- Constants ---
PRIORITY_LEVELS = {1: 'High', 2: 'Medium', 3: 'Low', 0: 'None'}
STATUS_LEVELS = {0: 'Pending', 1: 'In-Progress', 2: 'Completed'}
DATE_FORMAT = "%d/%m/%Y"
DATETIME_FORMAT = "%d/%m/%Y %H:%M"

# --- Database Setup ---
def initialize_database():
    """Creates the database and necessary tables if they don't exist."""
    os.makedirs(EXPORT_DIR, exist_ok=True)
    os.makedirs(PLOT_DIR, exist_ok=True)

    # Connect but don't rely solely on detect_types for custom formats/keywords
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cursor = conn.cursor()

    # Tasks Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        task_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        category TEXT,
        priority INTEGER DEFAULT 0,
        status INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        due_date TIMESTAMP,
        scheduled_time TIMESTAMP,
        parent_task_id INTEGER,
        FOREIGN KEY (parent_task_id) REFERENCES tasks (task_id) ON DELETE CASCADE
    )''')

    conn.commit()
    conn.close()
    print(f"Database '{DB_NAME}' initialized/checked successfully.")

# --- Helper Function to format dates consistently ---
def format_datetime_for_display(dt_obj):
    """Formats a datetime object for display, handling None."""
    if isinstance(dt_obj, datetime.datetime):
        # Check if it has time component other than midnight
        if dt_obj.hour == 0 and dt_obj.minute == 0:
             return dt_obj.strftime(DATE_FORMAT)
        else:
             return dt_obj.strftime(DATETIME_FORMAT)
    elif isinstance(dt_obj, datetime.date):
         return dt_obj.strftime(DATE_FORMAT)
    elif isinstance(dt_obj, str): # If it's still a string (fallback)
        try: # Attempt to parse known formats before display
            parsed_dt = None
            try:
                parsed_dt = datetime.datetime.strptime(dt_obj, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    parsed_dt = datetime.datetime.strptime(dt_obj, '%Y-%m-%d %H:%M')
                except ValueError:
                    try:
                        parsed_dt = datetime.datetime.strptime(dt_obj, '%Y-%m-%d')
                    except ValueError:
                        pass # Keep original string if unparseable
            if parsed_dt:
                if parsed_dt.hour == 0 and parsed_dt.minute == 0:
                    return parsed_dt.strftime(DATE_FORMAT)
                else:
                    return parsed_dt.strftime(DATETIME_FORMAT)
            else:
                return dt_obj # Return original string if parsing failed
        except: # Catch any other parsing errors
            return dt_obj # Fallback
    return "None"

# --- Task Manager Class ---
class TaskManager:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name

    def _connect(self):
        """Connects to the database."""
        # Still use detect_types for standard timestamps like created_at
        return sqlite3.connect(self.db_name, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)

    def _parse_datetime_input(self, prompt_text):
        """
        Helper to get datetime input from user, supporting DD/MM/YYYY format
        and keywords: today, tomorrow, yesterday.
        """
        today = datetime.date.today()
        while True:
            dt_str = pyip.inputStr(
                prompt=f"{prompt_text} ({DATE_FORMAT} or {DATETIME_FORMAT}, today, tomorrow, yesterday, blank for none): ",
                blank=True
            ).lower()

            if not dt_str:
                return None

            if dt_str == 'today':
                return datetime.datetime.combine(today, datetime.datetime.min.time()) # Return datetime obj (start of day)
            if dt_str == 'tomorrow':
                return datetime.datetime.combine(today + datetime.timedelta(days=1), datetime.datetime.min.time())
            if dt_str == 'yesterday':
                return datetime.datetime.combine(today - datetime.timedelta(days=1), datetime.datetime.min.time())

            try:
                # Try parsing with time first using the new format
                return datetime.datetime.strptime(dt_str, DATETIME_FORMAT)
            except ValueError:
                try:
                    # Try parsing date only using the new format
                    dt_obj = datetime.datetime.strptime(dt_str, DATE_FORMAT)
                    # Return datetime object (start of the day)
                    return dt_obj
                except ValueError:
                    print(f"Invalid format. Please use {DATE_FORMAT}, {DATETIME_FORMAT}, today, tomorrow, yesterday, or leave blank.")

    # --- Add Task ---
    def add_task(self, parent_task_id=None):
        """Adds a new task or subtask to the database."""
        print(f"\n-- Add New {'Subtask' if parent_task_id else 'Task'} --")
        if parent_task_id:
             print(f"(Adding as subtask to Task ID: {parent_task_id})")

        title = pyip.inputStr("Task Title: ")
        desc = pyip.inputStr("Description (optional): ", blank=True)
        category = pyip.inputStr("Category (optional): ", blank=True)

        priority_choices = [f"{k}: {v}" for k, v in PRIORITY_LEVELS.items()]
        priority_input = pyip.inputMenu(priority_choices, prompt="Priority:\n", numbered=True, default='0: None')
        priority = int(priority_input.split(':')[0])

        status = 0 # Default to Pending

        due_date = self._parse_datetime_input("Due Date")
        scheduled_time = self._parse_datetime_input("Scheduled Time (for specific event time)")

        conn = self._connect()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO tasks (title, description, category, priority, status, due_date, scheduled_time, parent_task_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (title, desc, category, priority, status, due_date, scheduled_time, parent_task_id))
            conn.commit()
            print(f"Task '{title}' added successfully (ID: {cursor.lastrowid}).")
        except sqlite3.Error as e:
            print(f"Database error adding task: {e}")
        finally:
            conn.close()

    # --- View Tasks ---
    def view_tasks(self, filters=None, sort_by='due_date', show_subtasks=True):
        """Views tasks with filtering and sorting."""
        print("\n-- View Tasks --")
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # --- FIX: Removed problematic aliases ---
        base_query = """
            SELECT t.task_id, t.title, t.category, t.priority, t.status,
                   t.due_date, t.created_at, -- Fetch original columns
                   t.parent_task_id,
                   (SELECT COUNT(*) FROM tasks sub WHERE sub.parent_task_id = t.task_id) as subtask_count
            FROM tasks t
        """
        # --- END FIX ---

        conditions = []
        params = []

        # Apply filters (logic remains mostly the same)
        if filters:
            status_filter = filters.get('status')
            if status_filter is not None:
                if isinstance(status_filter, list):
                    if status_filter:
                        placeholders = ','.join('?' * len(status_filter))
                        conditions.append(f"t.status IN ({placeholders})")
                        params.extend(status_filter)
                else:
                     conditions.append("t.status = ?")
                     params.append(status_filter)

            if filters.get('priority') is not None:
                conditions.append("t.priority = ?")
                params.append(filters['priority'])
            if filters.get('category'):
                conditions.append("t.category LIKE ?")
                params.append(f"%{filters['category']}%")

            # Handle 'due_today' filter using date('now', 'localtime')
            if filters.get('due_today'):
                 conditions.append("DATE(t.due_date) = DATE('now', 'localtime')")

            if filters.get('upcoming'):
                 conditions.append("DATE(t.due_date) >= DATE('now', 'localtime')")
                 conditions.append("t.status != ?")
                 params.append(2) # Status code for 'Completed'

            if filters.get('parent_id') is not None:
                 conditions.append("t.parent_task_id = ?")
                 params.append(filters['parent_id'])
            elif not show_subtasks:
                 conditions.append("t.parent_task_id IS NULL")

        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)

        # Apply sorting (logic remains the same)
        if sort_by == 'priority':
             base_query += " ORDER BY CASE t.priority WHEN 0 THEN 99 ELSE t.priority END ASC, t.due_date ASC"
        elif sort_by == 'created_at':
             base_query += " ORDER BY t.created_at DESC"
        elif sort_by == 'title':
             base_query += " ORDER BY t.title COLLATE NOCASE ASC"
        else: # Default sort by due date (nulls last)
            base_query += " ORDER BY t.due_date IS NULL, t.due_date ASC"

        try:
            cursor.execute(base_query, params)
            tasks = cursor.fetchall()

            if not tasks:
                print("No tasks found" + (" matching criteria." if filters else "."))
                return

            print("\n{:<5} {:<35} {:<15} {:<10} {:<12} {:<16} {:<5}".format(
                "ID", "Title", "Category", "Priority", "Status", "Due Date", "Subs"))
            print("-" * 105)

            for task in tasks:
                 priority_str = PRIORITY_LEVELS.get(task['priority'], 'Unknown')
                 status_str = STATUS_LEVELS.get(task['status'], 'Unknown')

                 # --- FIX: Access original column and format ---
                 due_date_obj = task['due_date'] # Access the original column
                 due_date_str = format_datetime_for_display(due_date_obj) # Use helper
                 # --- END FIX ---

                 sub_count_str = f"({task['subtask_count']})" if task['subtask_count'] > 0 else ""
                 indent = "  " if task['parent_task_id'] and show_subtasks else ""

                 print(f"{indent}{task['task_id']:<5} {task['title']:<35} {task['category'] or 'N/A':<15} "
                       f"{priority_str:<10} {status_str:<12} {due_date_str:<16} {sub_count_str:<5}")

            print("-" * 105)

        except sqlite3.Error as e:
            print(f"Database error viewing tasks: {e}")
        finally:
            conn.close()

    # --- Update Task ---
    def update_task(self):
        """Updates details of an existing task."""
        print("\n-- Update Task --")
        task_id = pyip.inputInt("Enter ID of task to update: ", min=1)
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            task = cursor.fetchone()
            if not task:
                print(f"Task with ID {task_id} not found.")
                return

            current_due_date_obj = task['due_date'] # Access original column
            current_due_date_str = format_datetime_for_display(current_due_date_obj)

            print(f"\nUpdating Task ID: {task_id} - '{task['title']}'")
            print(f"Current Status: {STATUS_LEVELS.get(task['status'])}, Priority: {PRIORITY_LEVELS.get(task['priority'])}")
            print(f"Current Due Date: {current_due_date_str}")

            # Get updated values
            title = pyip.inputStr(f"New Title (keep '{task['title']}'): ", blank=True) or task['title']
            desc = pyip.inputStr(f"New Description (keep existing): ", blank=True) or task['description']
            category = pyip.inputStr(f"New Category (keep '{task['category']}'): ", blank=True) or task['category']

            priority_choices = [f"{k}: {v}" for k, v in PRIORITY_LEVELS.items()]
            priority_input = pyip.inputMenu(priority_choices, prompt=f"New Priority (keep {PRIORITY_LEVELS.get(task['priority'])}):\n", numbered=True, blank=True)
            priority = int(priority_input.split(':')[0]) if priority_input else task['priority']

            status_choices = [f"{k}: {v}" for k, v in STATUS_LEVELS.items()]
            status_input = pyip.inputMenu(status_choices, prompt=f"New Status (keep {STATUS_LEVELS.get(task['status'])}):\n", numbered=True, blank=True)
            status = int(status_input.split(':')[0]) if status_input else task['status']

            # Handle due date update
            print(f"\nCurrent Due Date: {current_due_date_str}")
            # Use the updated parser function
            new_due_date = self._parse_datetime_input("New Due Date ('clear' to remove, blank to keep)")

            # Logic to decide final due date:
            # If user entered 'clear', it returns None implicitly via _parse_datetime_input logic if we modify it slightly or check here
            # If user entered blank, _parse_datetime_input returns None, so keep original.
            # If user entered valid date/keyword, _parse_datetime_input returns the datetime object.
            # Let's adjust _parse_datetime_input to return a special marker or handle 'clear' directly
            final_due_date = current_due_date_obj # Default to original
            if new_due_date is not None: # User entered something valid (date or keyword)
                 final_due_date = new_due_date
            # If user entered blank, new_due_date is None, so final_due_date remains the original.
            # We need to handle 'clear'. Let's modify the prompt/check:
            clear_input = pyip.inputStr("Type 'clear' to remove due date, otherwise press Enter: ", blank=True).lower()
            if clear_input == 'clear':
                 final_due_date = None
            elif new_due_date is not None: # Only update if it wasn't cleared and wasn't blank
                 final_due_date = new_due_date


            cursor.execute("""
                UPDATE tasks
                SET title = ?, description = ?, category = ?, priority = ?, status = ?, due_date = ?
                WHERE task_id = ?
            """, (title, desc, category, priority, status, final_due_date, task_id))
            conn.commit()
            print(f"Task ID {task_id} updated successfully.")

        except sqlite3.Error as e:
            print(f"Database error updating task: {e}")
            conn.rollback()
        finally:
            conn.close()

    # --- Delete Task ---
    def delete_task(self):
        """Deletes a task and its subtasks."""
        # (Code remains the same as before)
        print("\n-- Delete Task --")
        task_id = pyip.inputInt("Enter ID of task to delete: ", min=1)
        confirm = pyip.inputYesNo(f"WARNING: This will delete task ID {task_id} and ALL its subtasks. Are you sure? (yes/no): ", default='no')

        if confirm == 'yes':
            conn = self._connect()
            cursor = conn.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys = ON")
                cursor.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
                if cursor.rowcount > 0:
                    conn.commit()
                    print(f"Task ID {task_id} and its subtasks deleted successfully.")
                else:
                    print(f"Task ID {task_id} not found.")
            except sqlite3.Error as e:
                print(f"Database error deleting task: {e}")
                conn.rollback()
            finally:
                conn.close()
        else:
            print("Deletion cancelled.")


    # --- Manage Subtasks ---
    def manage_subtasks(self):
        """Menu to manage subtasks for a given parent task."""
        # (Code remains mostly the same, view_tasks call is now correct)
        print("\n-- Manage Subtasks --")
        parent_id = pyip.inputInt("Enter the ID of the parent task: ", min=1)

        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM tasks WHERE task_id = ?", (parent_id,))
        parent_task = cursor.fetchone()
        conn.close()

        if not parent_task:
            print(f"Parent task with ID {parent_id} not found.")
            return
        print(f"\nManaging subtasks for: '{parent_task[0]}' (ID: {parent_id})")

        while True:
            print("\nSubtask Actions:")
            action = pyip.inputMenu([
                'Add Subtask',
                'View Subtasks',
                'Update Subtask',
                'Delete Subtask',
                'Back to Main Menu'
            ], numbered=True)

            if action == 'Add Subtask':
                self.add_task(parent_task_id=parent_id)
            elif action == 'View Subtasks':
                 self.view_tasks(filters={'parent_id': parent_id}, sort_by='created_at', show_subtasks=True)
            elif action == 'Update Subtask':
                 print("To update a subtask, please use the main 'Update Task' option and enter the subtask's specific ID.")
            elif action == 'Delete Subtask':
                 print("To delete a subtask, please use the main 'Delete Task' option and enter the subtask's specific ID.")
            elif action == 'Back to Main Menu':
                break


    # --- Export to CSV ---
    def export_to_csv(self):
        """Exports all tasks (including subtasks) to CSV."""
        print("\n-- Export Tasks to CSV --")
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT task_id, title, description, category, priority, status,
                       created_at, due_date, scheduled_time, -- Fetch original columns
                       parent_task_id
                FROM tasks
                ORDER BY parent_task_id NULLS FIRST, created_at
            """)
            tasks = cursor.fetchall()
            if not tasks:
                print("No tasks found to export.")
                return

            headers = ["ID", "Title", "Description", "Category", "Priority", "Status", "Created At", "Due Date", "Scheduled Time", "Parent ID"]
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(EXPORT_DIR, f"tasks_export_{timestamp}.csv")

            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)
                for task in tasks:
                     # Format datetimes using helper
                     created_at_str = format_datetime_for_display(task['created_at'])
                     due_date_str = format_datetime_for_display(task['due_date'])
                     scheduled_time_str = format_datetime_for_display(task['scheduled_time'])

                     writer.writerow([
                        task['task_id'],
                        task['title'],
                        task['description'],
                        task['category'],
                        PRIORITY_LEVELS.get(task['priority']),
                        STATUS_LEVELS.get(task['status']),
                        created_at_str,
                        due_date_str,
                        scheduled_time_str,
                        task['parent_task_id'] or ""
                     ])
            print(f"Tasks exported successfully to '{filepath}'")

        except sqlite3.Error as e:
            print(f"Database error during export: {e}")
        except IOError as e:
            print(f"File error during export: {e}")
        finally:
            conn.close()

    # --- Visualize Tasks ---
    def visualize_tasks(self):
        """Generates visualizations (e.g., status pie chart)."""
        # (Code remains the same as before)
        print("\n-- Visualize Task Data --")
        conn = self._connect()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT status, COUNT(*) FROM tasks WHERE parent_task_id IS NULL GROUP BY status")
            status_counts = cursor.fetchall()

            if not status_counts:
                print("No task data (non-subtasks) to visualize by status.")
                return

            labels = [STATUS_LEVELS.get(s[0], 'Unknown') for s in status_counts]
            sizes = [s[1] for s in status_counts]
            status_color_map = {0: 'gold', 1: 'lightcoral', 2: 'lightskyblue'}
            colors = [status_color_map.get(s[0], 'grey') for s in status_counts]
            explode_tuple = tuple([0.1 if s[0] == 2 else 0 for s in status_counts])

            plt.figure(figsize=(8, 8))
            plt.pie(sizes, explode=explode_tuple if any(e > 0 for e in explode_tuple) else None,
                    labels=labels, colors=colors,
                    autopct='%1.1f%%', shadow=True, startangle=140)
            plt.axis('equal')
            plt.title("Task Status Distribution (Top-Level Tasks)")

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(PLOT_DIR, f"task_status_pie_{timestamp}.png")
            plt.savefig(filename)
            plt.close()
            print(f"Status visualization saved to '{filename}'")

        except sqlite3.Error as e:
            print(f"Database error fetching data for visualization: {e}")
        except ImportError:
            print("Matplotlib is required for visualization. Please install it (`pip install matplotlib`).")
        except Exception as e:
            print(f"Error during visualization: {e}")
        finally:
            conn.close()


    # --- View Calendar ---
    def view_calendar(self):
        """Displays a simple text-based monthly calendar highlighting task due dates."""
        print("\n-- Monthly Task Calendar --")
        try:
            current_year = datetime.datetime.now().year
            year = pyip.inputInt(f"Enter year (e.g., {current_year}): ", default=current_year, min=1900, max=2100)
            month = pyip.inputInt("Enter month (1-12): ", min=1, max=12)
        except pyip.RetryLimitException:
             print("Invalid input.")
             return

        conn = self._connect()
        cursor = conn.cursor()
        try:
            # Get distinct due dates within the selected month/year
            # We need to store dates as TEXT in YYYY-MM-DD format for reliable BETWEEN queries
            # Or convert the input year/month range to timestamps if storing as TIMESTAMP
            # Let's stick to comparing TEXT dates for simplicity here if possible
            start_date_str = f"{year}-{month:02d}-01"
            _, last_day = calendar.monthrange(year, month)
            end_date_str = f"{year}-{month:02d}-{last_day:02d}"

            # Query using DATE function which works on timestamps/iso8601 strings
            cursor.execute("""
                SELECT DISTINCT DATE(due_date)
                FROM tasks
                WHERE DATE(due_date) BETWEEN ? AND ?
            """, (start_date_str, end_date_str))

            due_dates_in_month = set()
            for row in cursor.fetchall():
                 if row[0]: # Ensure date string is not null
                    try:
                        # Extract day part
                        due_dates_in_month.add(int(row[0].split('-')[2]))
                    except (IndexError, ValueError):
                         print(f"Warning: Could not parse day from date string '{row[0]}'")

        except sqlite3.Error as e:
            print(f"Database error fetching due dates: {e}")
            due_dates_in_month = set()
        finally:
            conn.close()

        cal = calendar.TextCalendar(calendar.SUNDAY)
        month_calendar_str = cal.formatmonth(year, month)

        print(f"\n{calendar.month_name[month]} {year} (* indicates task due)")
        # (Highlighting logic remains the same)
        lines = month_calendar_str.split('\n')
        print(lines[0]) # Header
        print(lines[1]) # Separator
        for line in lines[2:]:
             highlighted_line = line
             for day in range(1, 32):
                 day_str_padded = f" {day:2d} "
                 day_str_start = f"{day:2d} "
                 day_str_end = f" {day:2d}"
                 if day in due_dates_in_month:
                     if day_str_padded in highlighted_line:
                         highlighted_line = highlighted_line.replace(day_str_padded, f" {day:2d}* ", 1)
                     elif highlighted_line.startswith(day_str_start):
                         highlighted_line = highlighted_line.replace(day_str_start, f"{day:2d}* ", 1)
                     elif highlighted_line.endswith(day_str_end):
                          highlighted_line = highlighted_line.replace(day_str_end, f" {day:2d}*", 1)
             print(highlighted_line)


# --- Main Application ---
def main():
    initialize_database()
    manager = TaskManager()

    print("--- Tasks Due Today ---")
    manager.view_tasks(filters={'due_today': True}, sort_by='priority')
    print("-" * 21)

    while True:
        print("\n======= Task Management System =======")
        action = pyip.inputMenu([
            'Add Task',
            'View Tasks (Filter/Sort)',
            'Update Task',
            'Delete Task',
            'Manage Subtasks',
            'View Calendar',
            'Visualize Task Data',
            'Export Tasks to CSV',
            'Exit'
        ], numbered=True)

        if action == 'Add Task':
            manager.add_task()
        elif action == 'View Tasks (Filter/Sort)':
             print("\n-- Filter & Sort Options --")
             filter_opts = {}
             sort_choice = 'due_date'

             status_choices = ['All', 'Pending', 'In-Progress', 'Completed']
             filter_status = pyip.inputChoice(status_choices, prompt=f"Filter by Status ({'/'.join(status_choices)}): ", default='All')
             if filter_status != 'All':
                 filter_opts['status'] = list(STATUS_LEVELS.keys())[list(STATUS_LEVELS.values()).index(filter_status)]

             priority_choices = ['All'] + [PRIORITY_LEVELS[k] for k in sorted(PRIORITY_LEVELS.keys())]
             filter_priority = pyip.inputChoice(priority_choices, prompt=f"Filter by Priority ({'/'.join(priority_choices)}): ", default='All')
             if filter_priority != 'All':
                  filter_opts['priority'] = list(PRIORITY_LEVELS.keys())[list(PRIORITY_LEVELS.values()).index(filter_priority)]

             filter_category = pyip.inputStr("Filter by Category (text contains, blank for none): ", blank=True)
             if filter_category:
                 filter_opts['category'] = filter_category

             filter_upcoming = pyip.inputYesNo("Show only Upcoming/Unfinished tasks due today or later? (yes/no): ", default='no')
             if filter_upcoming == 'yes':
                  filter_opts['upcoming'] = True

             sort_options = {'d': 'due_date', 'p': 'priority', 'c': 'created_at', 't': 'title'}
             sort_input = pyip.inputChoice(list(sort_options.keys()), prompt="Sort by (d=Due Date, p=Priority, c=Created, t=Title): ", default='d')
             sort_choice = sort_options.get(sort_input, 'due_date')

             manager.view_tasks(filters=filter_opts if filter_opts else None, sort_by=sort_choice)

        elif action == 'Update Task':
            manager.update_task()
        elif action == 'Delete Task':
            manager.delete_task()
        elif action == 'Manage Subtasks':
             manager.manage_subtasks()
        elif action == 'View Calendar':
             manager.view_calendar()
        elif action == 'Visualize Task Data':
             manager.visualize_tasks()
        elif action == 'Export Tasks to CSV':
             manager.export_to_csv()
        elif action == 'Exit':
            print("Exiting Task Management System. Goodbye!")
            sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user. Exiting.")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected critical error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
