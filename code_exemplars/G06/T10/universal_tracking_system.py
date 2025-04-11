# universal_tracking_system.py (Corrected Currency Default & Total)

import sqlite3
import datetime
import csv
import os
import json
import pyinputplus as pyip
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import sys
from collections import defaultdict

# --- Configuration ---
DB_NAME = "tracker_system.db"
EXPORT_DIR = "data_exports"
PLOT_DIR = "plots"
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# --- Database Setup ---
def initialize_database():
    """Creates the database and necessary tables if they don't exist."""
    os.makedirs(EXPORT_DIR, exist_ok=True)
    os.makedirs(PLOT_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cursor = conn.cursor()

    # Expense Tracker Table - Make sure DEFAULT works as expected
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS expenses (
        expense_id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL,
        currency TEXT DEFAULT 'USD' NOT NULL, -- Ensure NOT NULL and Default works
        category TEXT NOT NULL,
        expense_date DATE NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Time Tracker Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS time_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        activity_name TEXT NOT NULL,
        start_time TIMESTAMP,
        end_time TIMESTAMP,
        duration_minutes INTEGER,
        log_date DATE NOT NULL,
        category TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Goal Tracker Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS goals (
        goal_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        metric_type TEXT,
        target_value REAL,
        current_value REAL DEFAULT 0,
        unit TEXT,
        deadline DATE,
        status TEXT DEFAULT 'Active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Custom Metric Definition Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS custom_metrics (
        metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        unit TEXT,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Custom Metric Log Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS metric_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        metric_id INTEGER NOT NULL,
        value REAL NOT NULL,
        log_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        notes TEXT,
        FOREIGN KEY (metric_id) REFERENCES custom_metrics (metric_id) ON DELETE CASCADE
    )''')

    # Habit Definition Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS habits (
        habit_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        frequency TEXT DEFAULT 'Daily',
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Habit Log Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS habit_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        habit_id INTEGER NOT NULL,
        log_date DATE NOT NULL,
        completed INTEGER NOT NULL DEFAULT 0,
        notes TEXT,
        current_streak INTEGER DEFAULT 0,
        UNIQUE (habit_id, log_date),
        FOREIGN KEY (habit_id) REFERENCES habits (habit_id) ON DELETE CASCADE
    )''')

    conn.commit()
    conn.close()
    print(f"Database '{DB_NAME}' initialized/checked successfully.")


# --- Helper Functions ---
def get_date_input(prompt_text):
    """Gets a valid date input from the user."""
    while True:
        date_str = pyip.inputStr(f"{prompt_text} ({DATE_FORMAT}, today, yesterday, blank for today): ", blank=True).lower()
        today = datetime.date.today()
        if not date_str or date_str == 'today':
            return today
        if date_str == 'yesterday':
            return today - datetime.timedelta(days=1)
        try:
            # Return date object directly
            return datetime.datetime.strptime(date_str, DATE_FORMAT).date()
        except ValueError:
            print(f"Invalid format. Please use {DATE_FORMAT}, today, or yesterday.")

def format_date_display(date_obj):
    """Formats date object for display."""
    if isinstance(date_obj, (datetime.date, datetime.datetime)):
        return date_obj.strftime(DATE_FORMAT)
    elif isinstance(date_obj, str):
        try:
            # Try parsing common formats before displaying
            parsed_dt = None
            try: parsed_dt = datetime.datetime.strptime(date_obj, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try: parsed_dt = datetime.datetime.strptime(date_obj, '%Y-%m-%d')
                except ValueError: pass # Keep original if unparseable

            if parsed_dt: return parsed_dt.strftime(DATE_FORMAT)
            else: return date_obj # Return original string
        except: return date_obj
    return "N/A"

# --- Base Manager (for connection & common export) ---
class BaseManager:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name

    def _connect(self):
        """Connects to the database with type detection."""
        return sqlite3.connect(self.db_name, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)

    def export_table_to_csv(self, table_name, filename_prefix):
        """Exports data from a specified table to a CSV file."""
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            if not rows:
                print(f"No data found in '{table_name}' to export.")
                return

            headers = list(rows[0].keys())
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(EXPORT_DIR, f"{filename_prefix}_{timestamp}.csv")

            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)
                for row in rows:
                     formatted_row = []
                     for value in row:
                         if isinstance(value, datetime.datetime):
                             formatted_row.append(value.strftime(DATETIME_FORMAT))
                         elif isinstance(value, datetime.date):
                             formatted_row.append(value.strftime(DATE_FORMAT))
                         else:
                             formatted_row.append(value)
                     writer.writerow(formatted_row)

            print(f"Data from '{table_name}' exported successfully to '{filepath}'")

        except IndexError:
             print(f"No data found in '{table_name}' to export.")
        except sqlite3.Error as e:
            print(f"Database error during export from '{table_name}': {e}")
        except IOError as e:
            print(f"File error during export: {e}")
        finally:
            if conn: conn.close()


# --- Expense Tracker Module ---
class ExpenseTracker(BaseManager):
    def add_expense(self):
        print("\n-- Log New Expense --")
        amount = pyip.inputFloat("Amount: ", min=0)
        # --- FIX: Ensure currency default is handled ---
        currency_input = pyip.inputStr("Currency (e.g., USD, EUR, leave blank for USD): ", blank=True).strip().upper()
        currency = currency_input if currency_input else "USD" # Explicitly set to USD if blank
        # --- END FIX ---
        category = pyip.inputStr("Category (e.g., Food, Transport, Bills): ")
        expense_date = get_date_input("Date of expense")
        notes = pyip.inputStr("Notes (optional): ", blank=True)

        conn = self._connect()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO expenses (amount, currency, category, expense_date, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (amount, currency, category, expense_date, notes)) # Pass the validated currency
            conn.commit()
            print("Expense logged successfully.")
        except sqlite3.Error as e:
            print(f"Database error logging expense: {e}")
        finally:
            conn.close()

    def view_expenses(self, limit=20, category_filter=None, date_filter=None):
        print("\n-- View Expenses --")
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            query = "SELECT expense_id, amount, currency, category, expense_date, notes FROM expenses"
            params = []
            conditions = []
            if category_filter:
                 conditions.append("category LIKE ?")
                 params.append(f"%{category_filter}%")
            if date_filter:
                 conditions.append("expense_date = ?")
                 params.append(date_filter)

            if conditions:
                 query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY expense_date DESC, created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            expenses = cursor.fetchall()

            if not expenses:
                print("No expenses found" + (" matching criteria." if (category_filter or date_filter) else "."))
                return

            print("\n{:<5} {:<12} {:<5} {:<20} {:<12} {:<30}".format("ID", "Amount", "Cur", "Category", "Date", "Notes"))
            print("-" * 90)
            total_shown = 0.0
            for exp in expenses:
                date_str = format_date_display(exp['expense_date'])
                # --- FIX: Correctly sum USD totals ---
                if exp['currency'] == 'USD':
                     total_shown += exp['amount']
                # --- END FIX ---
                print("{:<5} {:<12.2f} {:<5} {:<20} {:<12} {:<30}".format(
                    exp['expense_id'], exp['amount'], exp['currency'], exp['category'], date_str, exp['notes'] or ""))
            print("-" * 90)
            print(f"Total amount shown (USD only): {total_shown:.2f}") # This total should now be correct


        except sqlite3.Error as e:
            print(f"Database error viewing expenses: {e}")
        finally:
            conn.close()

    def view_summary(self):
        """Shows spending summary by category for the current month."""
        print("\n-- Monthly Spending Summary (by Category) --")
        conn = self._connect()
        conn.row_factory = sqlite3.Row # Use Row factory for summary too
        cursor = conn.cursor()
        try:
            today = datetime.date.today()
            start_of_month = today.replace(day=1)
            # Find next month's start, then subtract one day
            next_month_start_year = start_of_month.year if start_of_month.month < 12 else start_of_month.year + 1
            next_month_start_month = start_of_month.month + 1 if start_of_month.month < 12 else 1
            next_month_start = datetime.date(next_month_start_year, next_month_start_month, 1)
            end_of_month = next_month_start - datetime.timedelta(days=1)

            # Query for sums by category within the date range (explicitly filter for USD)
            cursor.execute("""
                SELECT category, SUM(amount) as total
                FROM expenses
                WHERE expense_date BETWEEN ? AND ? AND currency = 'USD'
                GROUP BY category
                ORDER BY total DESC
            """, (start_of_month, end_of_month))

            summary = cursor.fetchall()
            if not summary:
                print(f"No USD expenses found for {today.strftime('%B %Y')}.")
                return

            print(f"\nSummary for {today.strftime('%B %Y')} (USD Only):")
            print("{:<25} {:>15}".format("Category", "Total Amount"))
            print("-" * 45)
            grand_total = 0.0
            categories = []
            totals = []
            for row in summary:
                category = row['category'] # Access by name
                total = row['total']       # Access by name
                print("{:<25} {:>15.2f}".format(category, total))
                grand_total += total
                categories.append(category)
                totals.append(total)
            print("-" * 45)
            print("{:<25} {:>15.2f}".format("Grand Total", grand_total))
            print("-" * 45)

            if categories:
                 visualize = pyip.inputYesNo("Generate spending pie chart? (yes/no): ", default='no')
                 if visualize == 'yes':
                     self.visualize_spending(categories, totals, today.strftime('%B %Y'))

        except sqlite3.Error as e:
            print(f"Database error generating summary: {e}")
        finally:
            conn.close()

    # visualize_spending and menu remain the same as previous correct version

    def visualize_spending(self, categories, totals, time_period):
        """Generates a pie chart for spending."""
        print("Generating pie chart...")
        try:
            plt.figure(figsize=(10, 8))
            colors = plt.cm.viridis([i/float(len(categories)) for i in range(len(categories))])

            threshold_percent = 3
            total_spending = sum(totals)
            if total_spending == 0: total_spending = 1
            small_slice_threshold = (threshold_percent / 100.0) * total_spending

            main_categories = []
            main_totals = []
            other_total = 0.0
            sorted_data = sorted(zip(categories, totals), key=lambda item: item[1], reverse=True)

            for cat, tot in sorted_data:
                if tot >= small_slice_threshold:
                    main_categories.append(cat)
                    main_totals.append(tot)
                else:
                    other_total += tot

            if other_total > 0:
                 main_categories.append('Other (<{:.0f}%)'.format(threshold_percent))
                 main_totals.append(other_total)
                 colors = plt.cm.viridis([i/float(len(main_categories)) for i in range(len(main_categories))])

            plt.pie(main_totals, labels=main_categories, colors=colors, autopct='%1.1f%%', startangle=140, pctdistance=0.85)
            plt.title(f"Spending Distribution by Category - {time_period} (USD Only)")
            plt.axis('equal')
            plt.tight_layout()

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(PLOT_DIR, f"expense_summary_{timestamp}.png")
            plt.savefig(filename)
            plt.close()
            print(f"Spending visualization saved to '{filename}'")

        except ImportError:
             print("Matplotlib is required for visualization. Please install it (`pip install matplotlib`).")
        except Exception as e:
             print(f"Error during visualization: {e}")


    def menu(self):
         while True:
            print("\n--- Expense Tracker Menu ---")
            action = pyip.inputMenu([
                'Log Expense',
                'View Recent Expenses',
                'View Monthly Summary',
                'Export Expenses to CSV',
                'Back to Main Menu'
            ], numbered=True)

            if action == 'Log Expense':
                self.add_expense()
            elif action == 'View Recent Expenses':
                 limit = pyip.inputInt("How many recent expenses to show? ", default=20, min=1, max=200)
                 cat_filter = pyip.inputStr("Filter by category (blank for all): ", blank=True)
                 date_str = pyip.inputStr(f"Filter by specific date ({DATE_FORMAT}, blank for all): ", blank=True)
                 date_filter = None
                 if date_str:
                     try: date_filter = datetime.datetime.strptime(date_str, DATE_FORMAT).date()
                     except ValueError: print("Invalid date format for filter.")
                 self.view_expenses(limit=limit,
                                    category_filter=cat_filter if cat_filter else None,
                                    date_filter=date_filter)
            elif action == 'View Monthly Summary':
                 self.view_summary()
            elif action == 'Export Expenses to CSV':
                 self.export_table_to_csv('expenses', 'expenses_export')
            elif action == 'Back to Main Menu':
                break


# --- Time Tracker Module --- (Code remains the same as previous correct version)
class TimeTracker(BaseManager):
    def log_time(self):
        print("\n-- Log Time Entry --")
        activity = pyip.inputStr("Activity/Project/Task/Client: ")
        log_date = get_date_input("Date work was done")
        category = pyip.inputStr("Category (optional): ", blank=True)
        notes = pyip.inputStr("Notes (optional): ", blank=True)

        input_method = pyip.inputChoice(['duration', 'times'], prompt="Log by duration or start/end times? (duration/times): ")

        start_time, end_time, duration_minutes = None, None, None
        if input_method == 'duration':
             duration_minutes = pyip.inputInt("Duration (in minutes): ", min=1)
        else: # start/end times
             while True:
                 start_str = pyip.inputStr("Start Time (HH:MM): ")
                 end_str = pyip.inputStr("End Time (HH:MM): ")
                 try:
                     start_dt = datetime.datetime.strptime(f"{log_date.strftime(DATE_FORMAT)} {start_str}", f"{DATE_FORMAT} %H:%M")
                     end_dt = datetime.datetime.strptime(f"{log_date.strftime(DATE_FORMAT)} {end_str}", f"{DATE_FORMAT} %H:%M")
                     if end_dt <= start_dt:
                         print("End time must be after start time.")
                         continue
                     start_time = start_dt
                     end_time = end_dt
                     duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
                     print(f"Calculated duration: {duration_minutes} minutes.")
                     break
                 except ValueError:
                     print("Invalid time format. Please use HH:MM (24-hour).")


        conn = self._connect()
        cursor = conn.cursor()
        try:
             cursor.execute("""
                 INSERT INTO time_logs (activity_name, start_time, end_time, duration_minutes, log_date, category, notes)
                 VALUES (?, ?, ?, ?, ?, ?, ?)
             """, (activity, start_time, end_time, duration_minutes, log_date, category, notes))
             conn.commit()
             print("Time entry logged successfully.")
        except sqlite3.Error as e:
             print(f"Database error logging time: {e}")
        finally:
             conn.close()

    def view_time_logs(self, limit=20, activity_filter=None, date_filter=None):
        print("\n-- View Time Logs --")
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            query = "SELECT log_id, activity_name, duration_minutes, log_date, category, notes, start_time, end_time FROM time_logs"
            params = []
            conditions = []
            if activity_filter:
                 conditions.append("activity_name LIKE ?")
                 params.append(f"%{activity_filter}%")
            if date_filter:
                 conditions.append("log_date = ?")
                 params.append(date_filter)

            if conditions:
                 query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY log_date DESC, created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            logs = cursor.fetchall()

            if not logs:
                print("No time logs found" + (" matching criteria." if (activity_filter or date_filter) else "."))
                return

            print("\n{:<5} {:<12} {:<30} {:<8} {:<15} {:<25}".format(
                "ID", "Date", "Activity", "Mins", "Category", "Notes"))
            print("-" * 100)
            total_minutes = 0
            for log in logs:
                date_str = format_date_display(log['log_date'])
                print("{:<5} {:<12} {:<30} {:<8} {:<15} {:<25}".format(
                    log['log_id'], date_str, log['activity_name'], log['duration_minutes'] or 0,
                    log['category'] or "", log['notes'] or ""))
                total_minutes += log['duration_minutes'] or 0
            print("-" * 100)
            print(f"Total time shown: {total_minutes // 60} hours, {total_minutes % 60} minutes")


        except sqlite3.Error as e:
            print(f"Database error viewing time logs: {e}")
        finally:
            conn.close()

    def view_time_summary(self):
        """Shows time summary by activity for the current week."""
        print("\n-- Weekly Time Summary (by Activity) --")
        conn = self._connect()
        conn.row_factory = sqlite3.Row # Use Row factory
        cursor = conn.cursor()
        try:
            today = datetime.date.today()
            start_of_week = today - datetime.timedelta(days=today.weekday())
            end_of_week = start_of_week + datetime.timedelta(days=6)

            cursor.execute("""
                SELECT activity_name, SUM(duration_minutes) as total_minutes
                FROM time_logs
                WHERE log_date BETWEEN ? AND ?
                GROUP BY activity_name
                ORDER BY total_minutes DESC
            """, (start_of_week, end_of_week))

            summary = cursor.fetchall()
            if not summary:
                print(f"No time logs found for the week starting {format_date_display(start_of_week)}.")
                return

            print(f"\nSummary for Week of {format_date_display(start_of_week)}:")
            print("{:<35} {:>15}".format("Activity", "Total Time"))
            print("-" * 55)
            grand_total_minutes = 0
            activities = []
            totals = []
            for row in summary:
                activity = row['activity_name'] # Access by name
                total_minutes = row['total_minutes'] or 0 # Handle potential NULL
                hours = total_minutes // 60
                minutes = total_minutes % 60
                time_str = f"{hours}h {minutes}m"
                print("{:<35} {:>15}".format(activity, time_str))
                grand_total_minutes += total_minutes
                activities.append(activity)
                totals.append(total_minutes)
            print("-" * 55)
            grand_hours = grand_total_minutes // 60
            grand_minutes = grand_total_minutes % 60
            print("{:<35} {:>15}".format("Grand Total", f"{grand_hours}h {grand_minutes}m"))
            print("-" * 55)

            if activities:
                 visualize = pyip.inputYesNo("Generate time allocation bar chart? (yes/no): ", default='no')
                 if visualize == 'yes':
                     self.visualize_time(activities, totals, f"Week of {format_date_display(start_of_week)}")

        except sqlite3.Error as e:
            print(f"Database error generating time summary: {e}")
        finally:
            conn.close()


    def visualize_time(self, activities, totals_minutes, time_period):
        """Generates a bar chart for time allocation."""
        print("Generating bar chart...")
        try:
            totals_hours = [m / 60.0 for m in totals_minutes]
            max_bars = 15
            if len(activities) > max_bars:
                 sorted_data = sorted(zip(activities, totals_hours), key=lambda item: item[1], reverse=True)
                 activities = [d[0] for d in sorted_data[:max_bars]]
                 totals_hours = [d[1] for d in sorted_data[:max_bars]]

            plt.figure(figsize=(12, 7))
            colors = plt.cm.Paired([i/float(len(activities)) for i in range(len(activities))])
            bars = plt.barh(activities, totals_hours, color=colors)

            plt.bar_label(bars, fmt='%.1f h', padding=3)

            plt.ylabel("Activity")
            plt.xlabel("Total Time (Hours)")
            plt.title(f"Time Allocation by Activity - {time_period}")
            plt.gca().invert_yaxis()
            plt.tight_layout()

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(PLOT_DIR, f"time_summary_{timestamp}.png")
            plt.savefig(filename)
            plt.close()
            print(f"Time allocation visualization saved to '{filename}'")

        except ImportError:
             print("Matplotlib is required for visualization. Please install it (`pip install matplotlib`).")
        except Exception as e:
             print(f"Error during visualization: {e}")


    def menu(self):
         while True:
            print("\n--- Time Tracker Menu ---")
            action = pyip.inputMenu([
                'Log Time Entry',
                'View Recent Time Logs',
                'View Weekly Summary',
                'Export Time Logs to CSV',
                'Back to Main Menu'
            ], numbered=True)

            if action == 'Log Time Entry':
                self.log_time()
            elif action == 'View Recent Time Logs':
                limit = pyip.inputInt("How many recent logs to show? ", default=20, min=1, max=200)
                act_filter = pyip.inputStr("Filter by activity (blank for all): ", blank=True)
                date_str = pyip.inputStr(f"Filter by specific date ({DATE_FORMAT}, blank for all): ", blank=True)
                date_filter = None
                if date_str:
                    try: date_filter = datetime.datetime.strptime(date_str, DATE_FORMAT).date()
                    except ValueError: print("Invalid date format for filter.")
                self.view_time_logs(limit=limit,
                                    activity_filter=act_filter if act_filter else None,
                                    date_filter=date_filter)
            elif action == 'View Weekly Summary':
                self.view_time_summary()
            elif action == 'Export Time Logs to CSV':
                self.export_table_to_csv('time_logs', 'time_logs_export')
            elif action == 'Back to Main Menu':
                break


# --- Goal Tracker Module --- (Code remains the same as previous correct version)
class GoalTracker(BaseManager):
    def add_goal(self):
        print("\n-- Define New Goal --")
        name = pyip.inputStr("Goal Name: ")
        desc = pyip.inputStr("Description (optional): ", blank=True)
        deadline = get_date_input("Target Deadline (optional)")

        metric = pyip.inputStr("Metric/Unit to track (e.g., kg, km, books, tasks, leave blank if binary): ", blank=True)
        target = 0.0
        if metric:
             target = pyip.inputFloat("Target Value: ")
             metric_type = 'Numeric'
             unit = metric
        else:
             metric_type = 'Binary' # Simple completion goal
             unit = None
             target = 1 # Target is completion

        conn = self._connect()
        cursor = conn.cursor()
        try:
             cursor.execute("""
                 INSERT INTO goals (name, description, metric_type, target_value, unit, deadline, status)
                 VALUES (?, ?, ?, ?, ?, ?, 'Active')
             """, (name, desc, metric_type, target, unit, deadline))
             conn.commit()
             print(f"Goal '{name}' defined successfully (ID: {cursor.lastrowid}).")
        except sqlite3.Error as e:
             print(f"Database error defining goal: {e}")
        finally:
             conn.close()


    def update_goal_progress(self):
        print("\n-- Update Goal Progress --")
        goal_id = pyip.inputInt("Enter Goal ID to update: ", min=1)
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM goals WHERE goal_id = ?", (goal_id,))
            goal = cursor.fetchone()
            if not goal:
                 print(f"Goal ID {goal_id} not found.")
                 return

            print(f"Updating: {goal['name']} (Target: {goal['target_value']} {goal['unit'] or ''}, Current: {goal['current_value']})")

            if goal['metric_type'] == 'Binary':
                completed = pyip.inputYesNo("Mark goal as completed? (yes/no): ")
                new_value = 1.0 if completed == 'yes' else 0.0
                new_status = 'Achieved' if completed == 'yes' else 'Active'
            else: # Numeric
                 update_val = pyip.inputFloat(f"Enter new CURRENT value (or change amount +/-): ")
                 new_value = update_val
                 new_status = 'Achieved' if new_value >= goal['target_value'] else 'Active' # Basic check

            if goal['deadline'] and isinstance(goal['deadline'], datetime.date) and datetime.date.today() > goal['deadline'] and new_status != 'Achieved':
                 print("Note: Deadline has passed.")

            cursor.execute("UPDATE goals SET current_value = ?, status = ? WHERE goal_id = ?", (new_value, new_status, goal_id))
            conn.commit()
            print(f"Goal {goal_id} progress updated. New value: {new_value}, Status: {new_status}")

        except sqlite3.Error as e:
            print(f"Database error updating goal: {e}")
        finally:
            conn.close()


    def view_goals(self, status_filter='Active'):
        print("\n-- View Goals --")
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            query = "SELECT * FROM goals" # Select all columns
            params = []
            if status_filter and status_filter != 'All':
                 query += " WHERE status = ?"
                 params.append(status_filter)
            query += " ORDER BY deadline IS NULL, deadline ASC, name ASC"

            cursor.execute(query, params)
            goals = cursor.fetchall()

            if not goals:
                print(f"No goals found" + (f" with status '{status_filter}'." if status_filter!='All' else "."))
                return

            print("\n{:<5} {:<30} {:<15} {:<15} {:<12} {:<10}".format("ID", "Name", "Target", "Current", "Deadline", "Status"))
            print("-" * 95)
            for goal in goals:
                 target_str = f"{goal['target_value']:.1f} {goal['unit'] or ''}" if goal['metric_type'] != 'Binary' else "Complete"
                 current_str = f"{goal['current_value']:.1f} {goal['unit'] or ''}" if goal['metric_type'] != 'Binary' else ("Yes" if goal['current_value']>=1 else "No")
                 deadline_str = format_date_display(goal['deadline']) # Use helper
                 print("{:<5} {:<30} {:<15} {:<15} {:<12} {:<10}".format(
                     goal['goal_id'], goal['name'], target_str, current_str, deadline_str, goal['status']))
            print("-" * 95)

        except sqlite3.Error as e:
             print(f"Database error viewing goals: {e}")
        finally:
             conn.close()

    def menu(self):
         while True:
            print("\n--- Goal Tracker Menu ---")
            action = pyip.inputMenu([
                'Define New Goal',
                'Update Goal Progress',
                'View Goals (Active)',
                'View Goals (All Statuses)',
                'Export Goals to CSV',
                'Back to Main Menu'
            ], numbered=True)

            if action == 'Define New Goal':
                self.add_goal()
            elif action == 'Update Goal Progress':
                self.update_goal_progress()
            elif action == 'View Goals (Active)':
                self.view_goals(status_filter='Active')
            elif action == 'View Goals (All Statuses)':
                self.view_goals(status_filter='All')
            elif action == 'Export Goals to CSV':
                self.export_table_to_csv('goals', 'goals_export')
            elif action == 'Back to Main Menu':
                break


# --- Custom Metric Tracker Module --- (Code remains the same as previous correct version)
class CustomMetricTracker(BaseManager):
    def define_metric(self):
        print("\n-- Define Custom Metric --")
        name = pyip.inputStr("Metric Name (unique): ")
        unit = pyip.inputStr("Unit (e.g., kg, count, rating, blank if dimensionless): ", blank=True)
        desc = pyip.inputStr("Description (optional): ", blank=True)

        conn = self._connect()
        cursor = conn.cursor()
        try:
             cursor.execute("INSERT INTO custom_metrics (name, unit, description) VALUES (?, ?, ?)", (name, unit, desc))
             conn.commit()
             print(f"Metric '{name}' defined successfully (ID: {cursor.lastrowid}).")
        except sqlite3.IntegrityError:
            print(f"Error: Metric name '{name}' already exists.")
        except sqlite3.Error as e:
             print(f"Database error defining metric: {e}")
        finally:
             conn.close()

    def list_metrics(self):
        print("\n-- Defined Custom Metrics --")
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT metric_id, name, unit, description FROM custom_metrics ORDER BY name")
            metrics = cursor.fetchall()
            if not metrics:
                 print("No custom metrics defined yet.")
                 return [] # Return empty list

            print("\n{:<5} {:<25} {:<15} {}".format("ID", "Name", "Unit", "Description"))
            print("-" * 80)
            for m in metrics:
                print("{:<5} {:<25} {:<15} {}".format(m['metric_id'], m['name'], m['unit'] or "N/A", m['description'] or ""))
            print("-" * 80)
            return metrics # Return list for selection
        except sqlite3.Error as e:
             print(f"Database error listing metrics: {e}")
             return []
        finally:
             conn.close()


    def log_metric_value(self):
        print("\n-- Log Metric Value --")
        defined_metrics = self.list_metrics()
        if not defined_metrics:
            return

        metric_choices = {str(m['metric_id']): f"{m['name']} ({m['unit'] or 'N/A'})" for m in defined_metrics}
        # Find metric ID from chosen description string
        chosen_desc = pyip.inputMenu(list(metric_choices.values()), prompt="Select metric to log for:\n", numbered=True)
        metric_id = None
        for id_key, desc_val in metric_choices.items():
            if desc_val == chosen_desc:
                metric_id = int(id_key)
                break
        if metric_id is None:
             print("Invalid selection.")
             return

        value = pyip.inputFloat("Value to log: ")
        log_time_choice = pyip.inputYesNo("Log for current time? (yes/no, no=enter specific time): ", default='yes')
        log_timestamp = datetime.datetime.now()
        if log_time_choice == 'no':
             log_date = get_date_input("Date for log entry")
             # Simple: use start of the entered day
             log_timestamp = datetime.datetime.combine(log_date, datetime.datetime.min.time())
             # Could add HH:MM input here if needed

        notes = pyip.inputStr("Notes (optional): ", blank=True)

        conn = self._connect()
        cursor = conn.cursor()
        try:
             cursor.execute("INSERT INTO metric_logs (metric_id, value, log_timestamp, notes) VALUES (?, ?, ?, ?)",
                            (metric_id, value, log_timestamp, notes))
             conn.commit()
             print("Metric value logged successfully.")
        except sqlite3.Error as e:
             print(f"Database error logging metric value: {e}")
        finally:
             conn.close()


    def view_metric_logs(self, metric_id, limit=30):
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT name, unit FROM custom_metrics WHERE metric_id = ?", (metric_id,))
            metric_info = cursor.fetchone()
            if not metric_info:
                 print(f"Metric ID {metric_id} not found.")
                 return

            print(f"\n-- Logs for Metric: {metric_info['name']} ({metric_info['unit'] or 'N/A'}) --")

            cursor.execute("""
                SELECT log_id, value, log_timestamp, notes FROM metric_logs
                WHERE metric_id = ?
                ORDER BY log_timestamp DESC LIMIT ?
            """, (metric_id, limit))
            logs = cursor.fetchall()

            if not logs:
                 print("No logs found for this metric.")
                 return

            print("\n{:<5} {:<20} {:<15} {}".format("LogID", "Timestamp", "Value", "Notes"))
            print("-" * 70)
            timestamps = []
            values = []
            for log in logs:
                 # log_timestamp should be datetime if detect_types worked
                 ts_str = format_datetime_for_display(log['log_timestamp']) if isinstance(log['log_timestamp'], datetime.datetime) else str(log['log_timestamp'])
                 print("{:<5} {:<20} {:<15.2f} {}".format(log['log_id'], ts_str, log['value'], log['notes'] or ""))
                 if isinstance(log['log_timestamp'], datetime.datetime):
                      timestamps.append(log['log_timestamp'])
                      values.append(log['value'])
            print("-" * 70)

            if timestamps and values:
                visualize = pyip.inputYesNo("Generate trend chart for these logs? (yes/no): ", default='no')
                if visualize == 'yes':
                    self.visualize_metric_trend(metric_info['name'], metric_info['unit'], timestamps[::-1], values[::-1])

        except sqlite3.Error as e:
             print(f"Database error viewing metric logs: {e}")
        finally:
             conn.close()

    def visualize_metric_trend(self, metric_name, unit, timestamps, values):
        """Generates a line chart showing metric trend over time."""
        print("Generating trend chart...")
        try:
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(timestamps, values, marker='o', linestyle='-', color='dodgerblue')
            ax.set_xlabel("Time")
            ax.set_ylabel(f"Value ({unit or 'N/A'})")
            ax.set_title(f"Trend for Metric: {metric_name}")
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=10))
            fig.autofmt_xdate()
            plt.grid(True, linestyle='--', alpha=0.6)
            plt.tight_layout()

            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_metric_name = "".join(c if c.isalnum() else "_" for c in metric_name)
            filename = os.path.join(PLOT_DIR, f"metric_{safe_metric_name}_trend_{timestamp_str}.png")
            plt.savefig(filename)
            plt.close()
            print(f"Metric trend visualization saved to '{filename}'")

        except ImportError:
             print("Matplotlib and mdates are required for visualization. Please install it (`pip install matplotlib`).")
        except Exception as e:
             print(f"Error during visualization: {e}")


    def menu(self):
         while True:
            print("\n--- Custom Metric Tracker Menu ---")
            action = pyip.inputMenu([
                'Define New Metric',
                'List Defined Metrics',
                'Log Metric Value',
                'View Metric Logs (& Visualize)',
                'Export Metric Logs to CSV',
                'Export Metric Definitions to CSV',
                'Back to Main Menu'
            ], numbered=True)

            if action == 'Define New Metric':
                self.define_metric()
            elif action == 'List Defined Metrics':
                self.list_metrics()
            elif action == 'Log Metric Value':
                self.log_metric_value()
            elif action == 'View Metric Logs (& Visualize)':
                 metrics = self.list_metrics()
                 if metrics:
                     # Ask user to enter ID based on the list
                     metric_id_input = pyip.inputInt("Enter Metric ID to view logs for: ", min=1)
                     # Validate if ID exists? Optional, view_metric_logs handles not found
                     limit = pyip.inputInt("How many recent logs to show? ", default=30, min=1)
                     self.view_metric_logs(metric_id_input, limit)

            elif action == 'Export Metric Logs to CSV':
                 self.export_table_to_csv('metric_logs', 'metric_logs_export')
            elif action == 'Export Metric Definitions to CSV':
                 self.export_table_to_csv('custom_metrics', 'custom_metrics_def_export')
            elif action == 'Back to Main Menu':
                break


# --- Habit Tracker Module --- (Code remains the same as previous correct version)
class HabitTracker(BaseManager):
    def define_habit(self):
        print("\n-- Define New Habit --")
        name = pyip.inputStr("Habit Name (unique): ")
        frequency = 'Daily' # Keep simple for now
        desc = pyip.inputStr("Description (optional): ", blank=True)

        conn = self._connect()
        cursor = conn.cursor()
        try:
             cursor.execute("INSERT INTO habits (name, frequency, description) VALUES (?, ?, ?)", (name, frequency, desc))
             conn.commit()
             print(f"Habit '{name}' defined successfully (ID: {cursor.lastrowid}).")
        except sqlite3.IntegrityError:
            print(f"Error: Habit name '{name}' already exists.")
        except sqlite3.Error as e:
             print(f"Database error defining habit: {e}")
        finally:
             conn.close()

    def list_habits(self):
        print("\n-- Defined Habits --")
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT habit_id, name, frequency, description FROM habits ORDER BY name")
            habits = cursor.fetchall()
            if not habits:
                 print("No habits defined yet.")
                 return []
            print("\n{:<5} {:<25} {:<10} {}".format("ID", "Name", "Frequency", "Description"))
            print("-" * 80)
            for h in habits:
                print("{:<5} {:<25} {:<10} {}".format(h['habit_id'], h['name'], h['frequency'], h['description'] or ""))
            print("-" * 80)
            return habits
        except sqlite3.Error as e:
             print(f"Database error listing habits: {e}")
             return []
        finally:
             conn.close()

    def log_habit(self):
        print("\n-- Log Habit Completion --")
        defined_habits = self.list_habits()
        if not defined_habits:
            return

        habit_choices = {str(h['habit_id']): h['name'] for h in defined_habits}
        chosen_name = pyip.inputMenu(list(habit_choices.values()), prompt="Select habit to log for:\n", numbered=True)
        habit_id = None
        for id_key, name_val in habit_choices.items():
            if name_val == chosen_name:
                habit_id = int(id_key)
                break
        if habit_id is None:
             print("Invalid selection.")
             return

        log_date = get_date_input("Date for habit log")
        completed_input = pyip.inputYesNo(f"Did you complete '{chosen_name}' on {format_date_display(log_date)}? (yes/no): ")
        completed = 1 if completed_input == 'yes' else 0
        notes = pyip.inputStr("Notes (optional): ", blank=True)

        current_streak = 0
        if completed:
             conn_streak = self._connect()
             cursor_streak = conn_streak.cursor()
             try:
                 prev_day = log_date - datetime.timedelta(days=1)
                 cursor_streak.execute("SELECT completed, current_streak FROM habit_logs WHERE habit_id = ? AND log_date = ?", (habit_id, prev_day))
                 prev_log = cursor_streak.fetchone()
                 if prev_log and prev_log[0] == 1:
                     current_streak = (prev_log[1] or 0) + 1
                 else:
                     current_streak = 1
             except sqlite3.Error as e:
                 print(f"Warning: Error checking previous day's streak - {e}")
             finally:
                 conn_streak.close()

        conn = self._connect()
        cursor = conn.cursor()
        try:
             cursor.execute("""
                 INSERT OR REPLACE INTO habit_logs (habit_id, log_date, completed, notes, current_streak)
                 VALUES (?, ?, ?, ?, ?)
             """, (habit_id, log_date, completed, notes, current_streak))
             conn.commit()
             print(f"Habit log for {format_date_display(log_date)} saved.")
             if current_streak > 0:
                 print(f"Current streak: {current_streak} day(s)!")
        except sqlite3.Error as e:
             print(f"Database error logging habit: {e}")
        finally:
             conn.close()


    def view_habit_logs(self, habit_id, limit=30):
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT name FROM habits WHERE habit_id = ?", (habit_id,))
            habit_info = cursor.fetchone()
            if not habit_info:
                 print(f"Habit ID {habit_id} not found.")
                 return

            print(f"\n-- Recent Logs for Habit: {habit_info['name']} --")

            cursor.execute("""
                SELECT log_id, log_date, completed, current_streak, notes FROM habit_logs
                WHERE habit_id = ?
                ORDER BY log_date DESC LIMIT ?
            """, (habit_id, limit))
            logs = cursor.fetchall()

            if not logs:
                 print("No logs found for this habit.")
                 return

            print("\n{:<5} {:<12} {:<10} {:<8} {}".format("LogID", "Date", "Completed", "Streak", "Notes"))
            print("-" * 60)
            dates = []
            streaks = []
            completions = []
            for log in logs:
                 date_str = format_date_display(log['log_date'])
                 completed_str = "Yes" if log['completed'] == 1 else "No"
                 streak_str = str(log['current_streak']) if log['completed'] == 1 else "-"
                 print("{:<5} {:<12} {:<10} {:<8} {}".format(log['log_id'], date_str, completed_str, streak_str, log['notes'] or ""))
                 if isinstance(log['log_date'], datetime.date):
                      dates.append(log['log_date'])
                      # Use streak only if completed, otherwise 0 for plot continuity?
                      streaks.append(log['current_streak'] if log['completed'] == 1 else 0)
                      completions.append(log['completed'])
            print("-" * 60)

            if dates: # Check if there's data before asking to visualize
                 visualize = pyip.inputYesNo("Generate streak chart for these logs? (yes/no): ", default='no')
                 if visualize == 'yes':
                     self.visualize_habit_streak(habit_info['name'], dates[::-1], streaks[::-1], completions[::-1])

        except sqlite3.Error as e:
             print(f"Database error viewing habit logs: {e}")
        finally:
             conn.close()

    def visualize_habit_streak(self, habit_name, dates, streaks, completions):
        """Generates a chart showing habit completion and streak over time."""
        print("Generating habit chart...")
        if not dates: return
        try:
            fig, ax1 = plt.subplots(figsize=(14, 7))

            colors = ['limegreen' if c == 1 else 'lightcoral' for c in completions]
            ax1.scatter(dates, completions, color=colors, marker='o', s=50, label='Completion (1=Yes, 0=No)')
            ax1.set_xlabel("Date")
            ax1.set_ylabel("Completed Status", color='black')
            ax1.set_yticks([0, 1])
            ax1.set_yticklabels(['No', 'Yes'])
            ax1.tick_params(axis='y', labelcolor='black')
            ax1.grid(True, axis='y', linestyle=':', alpha=0.7)

            ax2 = ax1.twinx()
            ax2.plot(dates, streaks, color='deepskyblue', linestyle='-', marker='.', label='Streak Count')
            ax2.set_ylabel('Streak Count', color='deepskyblue')
            ax2.tick_params(axis='y', labelcolor='deepskyblue')
            ax2.set_ylim(bottom=0)

            plt.title(f"Habit Completion & Streak: {habit_name}")
            fig.autofmt_xdate()
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax1.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=15))

            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

            fig.tight_layout()

            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_habit_name = "".join(c if c.isalnum() else "_" for c in habit_name)
            filename = os.path.join(PLOT_DIR, f"habit_{safe_habit_name}_trend_{timestamp_str}.png")
            plt.savefig(filename)
            plt.close()
            print(f"Habit trend visualization saved to '{filename}'")

        except ImportError:
             print("Matplotlib and mdates are required for visualization. Please install it (`pip install matplotlib`).")
        except Exception as e:
             print(f"Error during visualization: {e}")


    def menu(self):
         while True:
            print("\n--- Habit Tracker Menu ---")
            action = pyip.inputMenu([
                'Define New Habit',
                'List Defined Habits',
                'Log Habit Completion',
                'View Habit Logs (& Visualize)',
                'Export Habit Logs to CSV',
                'Export Habit Definitions to CSV',
                'Back to Main Menu'
            ], numbered=True)

            if action == 'Define New Habit':
                self.define_habit()
            elif action == 'List Defined Habits':
                self.list_habits()
            elif action == 'Log Habit Completion':
                self.log_habit()
            elif action == 'View Habit Logs (& Visualize)':
                 habits = self.list_habits()
                 if habits:
                     # Ask user for ID based on list
                     habit_id_input = pyip.inputInt("Enter Habit ID to view logs for: ", min=1)
                     # Could add validation here
                     limit = pyip.inputInt("How many recent logs to show? ", default=30, min=1)
                     self.view_habit_logs(habit_id_input, limit)

            elif action == 'Export Habit Logs to CSV':
                 self.export_table_to_csv('habit_logs', 'habit_logs_export')
            elif action == 'Export Habit Definitions to CSV':
                 self.export_table_to_csv('habits', 'habits_def_export')
            elif action == 'Back to Main Menu':
                break


# --- Main Application --- (Code remains the same as previous correct version)
def main():
    initialize_database()

    expense_tracker = ExpenseTracker()
    time_tracker = TimeTracker()
    goal_tracker = GoalTracker()
    metric_tracker = CustomMetricTracker()
    habit_tracker = HabitTracker()

    while True:
        print("\n======= Universal Tracker System =======")
        print("Select a module to manage:")
        main_choice = pyip.inputMenu([
            'Expense Tracker',
            'Time Tracker',
            'Goal Tracker',
            'Custom Metric Tracker',
            'Habit Tracker',
            'Exit'
        ], numbered=True)

        if main_choice == 'Expense Tracker':
            expense_tracker.menu()
        elif main_choice == 'Time Tracker':
            time_tracker.menu()
        elif main_choice == 'Goal Tracker':
            goal_tracker.menu()
        elif main_choice == 'Custom Metric Tracker':
            metric_tracker.menu()
        elif main_choice == 'Habit Tracker':
            habit_tracker.menu()
        elif main_choice == 'Exit':
            print("Exiting Universal Tracker System. Goodbye!")
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
