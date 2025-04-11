# universal_management_system.py

import sqlite3
import json
import os
import csv
import datetime
import pyinputplus as pyip
import matplotlib.pyplot as plt
import sys

# --- Configuration ---
DB_NAME = "management_system.db"
EXPORT_DIR = "data_exports"
PLOT_DIR = "plots"

# --- Database Setup ---
def initialize_database():
    """Creates the database and necessary tables if they don't exist."""
    os.makedirs(EXPORT_DIR, exist_ok=True)
    os.makedirs(PLOT_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Student Management Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS students (
        student_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        grade INTEGER,
        contact_info TEXT,
        attendance_status TEXT DEFAULT 'Present', -- e.g., Present, Absent, Late
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Student Grades Table (separate for multiple grades per student)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS student_grades (
        grade_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        subject TEXT NOT NULL,
        grade_value REAL NOT NULL, -- Use REAL for potential decimal grades
        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students (student_id) ON DELETE CASCADE
    )''')

    # Inventory Management Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS inventory (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE, -- Stock Keeping Unit
        name TEXT NOT NULL,
        description TEXT,
        quantity INTEGER NOT NULL DEFAULT 0,
        price REAL, -- Use REAL for currency
        supplier_info TEXT, -- Simplified supplier info
        reorder_point INTEGER DEFAULT 0,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Records Management Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS records (
        record_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content_snippet TEXT,
        category TEXT,
        tags TEXT, -- Store as comma-separated string or JSON
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Custom Management Table (Generic - using JSON for flexibility)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS custom_records (
        custom_id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_type TEXT NOT NULL, -- User-defined type (e.g., 'Project', 'Recipe')
        name TEXT NOT NULL,
        custom_data TEXT, -- Store specific fields as JSON string
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()
    conn.close()
    print(f"Database '{DB_NAME}' initialized/checked successfully.")

# --- Base Manager Class (Optional - for common methods like export) ---
class BaseManager:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name

    def _connect(self):
        """Connects to the database."""
        return sqlite3.connect(self.db_name)

    def export_to_csv(self, table_name, filename_prefix):
        """Exports data from a specified table to a CSV file."""
        conn = self._connect()
        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            if not rows:
                print(f"No data found in '{table_name}' to export.")
                return

            headers = [description[0] for description in cursor.description]
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(EXPORT_DIR, f"{filename_prefix}_{timestamp}.csv")

            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)
                writer.writerows(rows)
            print(f"Data from '{table_name}' exported successfully to '{filepath}'")

        except sqlite3.Error as e:
            print(f"Database error during export from '{table_name}': {e}")
        except IOError as e:
            print(f"File error during export: {e}")
        finally:
            conn.close()

# --- Student Management ---
class StudentManager(BaseManager):
    def add_student(self):
        print("\n-- Add New Student --")
        name = pyip.inputStr("Student Name: ")
        grade = pyip.inputInt("Grade Level (e.g., 9, 10): ", min=1, max=12)
        contact = pyip.inputStr("Contact Info (optional): ", blank=True)

        conn = self._connect()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO students (name, grade, contact_info) VALUES (?, ?, ?)",
                           (name, grade, contact))
            conn.commit()
            print(f"Student '{name}' added successfully (ID: {cursor.lastrowid}).")
        except sqlite3.Error as e:
            print(f"Database error adding student: {e}")
        finally:
            conn.close()

    def view_students(self, search_term=None):
        print("\n-- View Students --")
        conn = self._connect()
        cursor = conn.cursor()
        try:
            query = "SELECT student_id, name, grade, contact_info, attendance_status FROM students"
            params = []
            if search_term:
                query += " WHERE name LIKE ? OR contact_info LIKE ?"
                params.extend([f"%{search_term}%", f"%{search_term}%"])
            query += " ORDER BY name"

            cursor.execute(query, params)
            students = cursor.fetchall()

            if not students:
                print("No students found." + (" Matching search." if search_term else ""))
                return

            print("\n{:<5} {:<25} {:<6} {:<20} {:<10}".format("ID", "Name", "Grade", "Contact", "Status"))
            print("-" * 70)
            for s in students:
                print("{:<5} {:<25} {:<6} {:<20} {:<10}".format(s[0], s[1], s[2], s[3] or "N/A", s[4]))
            print("-" * 70)

        except sqlite3.Error as e:
            print(f"Database error viewing students: {e}")
        finally:
            conn.close()

    def update_student(self):
        print("\n-- Update Student --")
        student_id = pyip.inputInt("Enter ID of student to update: ", min=1)
        conn = self._connect()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT name, grade, contact_info, attendance_status FROM students WHERE student_id = ?", (student_id,))
            student = cursor.fetchone()
            if not student:
                print(f"Student with ID {student_id} not found.")
                return

            print(f"Updating Student: {student[0]} (Grade: {student[1]}, Status: {student[3]})")
            name = pyip.inputStr(f"New Name (leave blank to keep '{student[0]}'): ", blank=True) or student[0]
            grade = pyip.inputInt(f"New Grade (leave blank to keep '{student[1]}'): ", blank=True, min=1, max=12) or student[1]
            contact = pyip.inputStr(f"New Contact Info (leave blank to keep '{student[2]}'): ", blank=True) or student[2]
            status = pyip.inputStr(f"New Attendance Status (leave blank to keep '{student[3]}'): ", blank=True) or student[3]

            cursor.execute("""
                UPDATE students
                SET name = ?, grade = ?, contact_info = ?, attendance_status = ?
                WHERE student_id = ?
            """, (name, grade, contact, status, student_id))
            conn.commit()
            print(f"Student ID {student_id} updated successfully.")

        except sqlite3.Error as e:
            print(f"Database error updating student: {e}")
        finally:
            conn.close()

    def delete_student(self):
        print("\n-- Delete Student --")
        student_id = pyip.inputInt("Enter ID of student to delete: ", min=1)
        confirm = pyip.inputYesNo(f"Are you sure you want to delete student ID {student_id} and all related grades? (yes/no): ", default='no')

        if confirm == 'yes':
            conn = self._connect()
            cursor = conn.cursor()
            try:
                # Ensure foreign key constraints are enabled (usually by default)
                cursor.execute("PRAGMA foreign_keys = ON")
                # Deleting student will cascade delete grades due to FOREIGN KEY constraint
                cursor.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
                if cursor.rowcount > 0:
                    conn.commit()
                    print(f"Student ID {student_id} and associated grades deleted successfully.")
                else:
                    print(f"Student ID {student_id} not found.")
            except sqlite3.Error as e:
                print(f"Database error deleting student: {e}")
                conn.rollback()
            finally:
                conn.close()
        else:
            print("Deletion cancelled.")

    def manage_grades(self):
        print("\n-- Manage Student Grades --")
        student_id = pyip.inputInt("Enter Student ID to manage grades for: ", min=1)

        # Verify student exists
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM students WHERE student_id = ?", (student_id,))
        student = cursor.fetchone()
        conn.close()

        if not student:
            print(f"Student with ID {student_id} not found.")
            return
        print(f"Managing grades for: {student[0]} (ID: {student_id})")

        while True:
            action = pyip.inputMenu(['Add Grade', 'View Grades', 'Calculate GPA/Average', 'Visualize Grades', 'Back'], numbered=True)

            if action == 'Add Grade':
                subject = pyip.inputStr("Subject: ")
                grade_value = pyip.inputFloat("Grade Value (e.g., 85.5): ", min=0, max=1000) # Allow flexible grading scales

                conn = self._connect()
                cursor = conn.cursor()
                try:
                    cursor.execute("INSERT INTO student_grades (student_id, subject, grade_value) VALUES (?, ?, ?)",
                                   (student_id, subject, grade_value))
                    conn.commit()
                    print(f"Grade for {subject} added successfully.")
                except sqlite3.Error as e:
                    print(f"Database error adding grade: {e}")
                finally:
                    conn.close()

            elif action == 'View Grades':
                conn = self._connect()
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                        SELECT grade_id, subject, grade_value, recorded_at
                        FROM student_grades WHERE student_id = ? ORDER BY subject, recorded_at
                    """, (student_id,))
                    grades = cursor.fetchall()
                    if not grades:
                        print("No grades recorded for this student.")
                    else:
                        print("\n{:<8} {:<20} {:<10} {:<20}".format("GradeID", "Subject", "Grade", "Recorded At"))
                        print("-" * 60)
                        for g in grades:
                            print("{:<8} {:<20} {:<10.2f} {:<20}".format(g[0], g[1], g[2], g[3]))
                        print("-" * 60)
                except sqlite3.Error as e:
                     print(f"Database error viewing grades: {e}")
                finally:
                     conn.close()

            elif action == 'Calculate GPA/Average':
                conn = self._connect()
                cursor = conn.cursor()
                try:
                    cursor.execute("SELECT AVG(grade_value) FROM student_grades WHERE student_id = ?", (student_id,))
                    result = cursor.fetchone()
                    average = result[0] if result else None
                    if average is not None:
                         print(f"\nAverage grade for student {student_id} ({student[0]}): {average:.2f}")
                         # GPA calculation depends heavily on the scale (e.g., 4.0 scale)
                         # This would require a mapping function based on grade values.
                         # print("GPA calculation requires a specific grading scale mapping (not implemented).")
                    else:
                        print("No grades recorded to calculate average.")
                except sqlite3.Error as e:
                    print(f"Database error calculating average: {e}")
                finally:
                    conn.close()

            elif action == 'Visualize Grades':
                self.visualize_student_grades(student_id, student[0])

            elif action == 'Back':
                break

    def visualize_student_grades(self, student_id, student_name):
        """Generates a bar chart of grades for a specific student."""
        conn = self._connect()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT subject, grade_value FROM student_grades WHERE student_id = ?", (student_id,))
            grades = cursor.fetchall()
            if not grades:
                print("No grades to visualize for this student.")
                return

            subjects = [g[0] for g in grades]
            values = [g[1] for g in grades]

            plt.figure(figsize=(10, 6))
            plt.bar(subjects, values, color='skyblue')
            plt.xlabel("Subject")
            plt.ylabel("Grade Value")
            plt.title(f"Grades for {student_name} (ID: {student_id})")
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(PLOT_DIR, f"grades_{student_id}_{student_name.replace(' ','_')}_{timestamp}.png")
            plt.savefig(filename)
            plt.close() # Close the plot to free memory
            print(f"Grade visualization saved to '{filename}'")

        except sqlite3.Error as e:
            print(f"Database error fetching grades for visualization: {e}")
        except ImportError:
            print("Matplotlib is required for visualization. Please install it (`pip install matplotlib`).")
        except Exception as e:
            print(f"Error during visualization: {e}")
        finally:
            conn.close()

    def menu(self):
        while True:
            print("\n--- Student Management Menu ---")
            action = pyip.inputMenu([
                'Add Student',
                'View/Search Students',
                'Update Student',
                'Delete Student',
                'Manage Grades',
                'Export Students to CSV',
                'Back to Main Menu'
            ], numbered=True)

            if action == 'Add Student':
                self.add_student()
            elif action == 'View/Search Students':
                search = pyip.inputStr("Enter search term (or leave blank to view all): ", blank=True)
                self.view_students(search_term=search if search else None)
            elif action == 'Update Student':
                self.update_student()
            elif action == 'Delete Student':
                self.delete_student()
            elif action == 'Manage Grades':
                self.manage_grades()
            elif action == 'Export Students to CSV':
                 self.export_to_csv('students', 'students_export')
                 self.export_to_csv('student_grades', 'student_grades_export')
            elif action == 'Back to Main Menu':
                break

# --- Inventory Management ---
class InventoryManager(BaseManager):
    def add_item(self):
        print("\n-- Add New Inventory Item --")
        name = pyip.inputStr("Item Name: ")
        sku = pyip.inputStr("SKU (unique identifier, optional): ", blank=True) or None
        desc = pyip.inputStr("Description (optional): ", blank=True)
        qty = pyip.inputInt("Initial Quantity: ", min=0)
        price = pyip.inputFloat("Price (optional, e.g., 19.99): ", min=0, blank=True)
        supplier = pyip.inputStr("Supplier Info (optional): ", blank=True)
        reorder = pyip.inputInt("Reorder Point (optional, e.g., 10): ", min=0, blank=True)

        conn = self._connect()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO inventory (name, sku, description, quantity, price, supplier_info, reorder_point, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (name, sku, desc, qty, price, supplier, reorder))
            conn.commit()
            print(f"Item '{name}' added successfully (ID: {cursor.lastrowid}).")
        except sqlite3.IntegrityError:
             print(f"Error: SKU '{sku}' already exists. Please use a unique SKU.")
        except sqlite3.Error as e:
            print(f"Database error adding item: {e}")
        finally:
            conn.close()

    def view_inventory(self, search_term=None, low_stock_only=False):
        print("\n-- View Inventory --")
        conn = self._connect()
        cursor = conn.cursor()
        try:
            query = """
                SELECT item_id, sku, name, quantity, price, reorder_point, supplier_info, last_updated
                FROM inventory
            """
            params = []
            conditions = []

            if search_term:
                conditions.append("(name LIKE ? OR sku LIKE ? OR description LIKE ?)")
                params.extend([f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"])
            if low_stock_only:
                conditions.append("(quantity <= reorder_point AND reorder_point > 0)")

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY name"

            cursor.execute(query, params)
            items = cursor.fetchall()

            if not items:
                print("No inventory items found." + (" Matching criteria." if (search_term or low_stock_only) else ""))
                return

            print("\n{:<5} {:<15} {:<25} {:<8} {:<10} {:<8} {:<20} {:<20}".format(
                "ID", "SKU", "Name", "Qty", "Price", "Reorder", "Supplier", "Last Update"))
            print("-" * 120)
            low_stock_alerts = []
            for item in items:
                # item_id, sku, name, quantity, price, reorder_point, supplier_info, last_updated
                print("{:<5} {:<15} {:<25} {:<8} {:<10.2f} {:<8} {:<20} {:<20}".format(
                    item[0], item[1] or "N/A", item[2], item[3], item[4] or 0.0,
                    item[5] or 0, item[6] or "N/A", item[7][:19])) # Truncate timestamp if needed
                if item[5] > 0 and item[3] <= item[5]: # If reorder point set and quantity is low
                     low_stock_alerts.append(f"  - Low Stock Alert: {item[2]} (ID: {item[0]}) - Qty: {item[3]}, Reorder at: {item[5]}")
            print("-" * 120)
            if low_stock_alerts and not low_stock_only: # Only show alerts if not already filtering for them
                print("\n--- Low Stock Alerts ---")
                for alert in low_stock_alerts:
                    print(alert)
                print("------------------------")


        except sqlite3.Error as e:
            print(f"Database error viewing inventory: {e}")
        finally:
            conn.close()


    def update_item(self):
        print("\n-- Update Inventory Item --")
        item_id = pyip.inputInt("Enter ID of item to update: ", min=1)
        conn = self._connect()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT name, sku, description, quantity, price, supplier_info, reorder_point FROM inventory WHERE item_id = ?", (item_id,))
            item = cursor.fetchone()
            if not item:
                print(f"Item with ID {item_id} not found.")
                return

            print(f"Updating Item: {item[0]} (SKU: {item[1]}, Qty: {item[3]})")
            # Allow updating all fields
            name = pyip.inputStr(f"New Name (keep '{item[0]}'): ", blank=True) or item[0]
            sku = pyip.inputStr(f"New SKU (keep '{item[1]}'): ", blank=True) or item[1]
            desc = pyip.inputStr(f"New Description (keep existing): ", blank=True) or item[2]
            # For quantity, offer adjustment instead of direct set?
            qty_change = pyip.inputInt(f"Adjust Quantity (current: {item[3]}, e.g., +10 or -5, 0 for no change): ", default=0)
            new_qty = item[3] + qty_change
            price = pyip.inputFloat(f"New Price (keep {item[4]}): ", blank=True, min=0) or item[4]
            supplier = pyip.inputStr(f"New Supplier (keep '{item[5]}'): ", blank=True) or item[5]
            reorder = pyip.inputInt(f"New Reorder Point (keep {item[6]}): ", blank=True, min=0) or item[6]


            cursor.execute("""
                UPDATE inventory
                SET name = ?, sku = ?, description = ?, quantity = ?, price = ?, supplier_info = ?, reorder_point = ?, last_updated = CURRENT_TIMESTAMP
                WHERE item_id = ?
            """, (name, sku, desc, new_qty, price, supplier, reorder, item_id))
            conn.commit()
            print(f"Item ID {item_id} updated successfully. New quantity: {new_qty}")

        except sqlite3.IntegrityError:
             print(f"Error: SKU '{sku}' might already exist for another item.")
        except sqlite3.Error as e:
            print(f"Database error updating item: {e}")
            conn.rollback()
        finally:
            conn.close()


    def delete_item(self):
        print("\n-- Delete Inventory Item --")
        item_id = pyip.inputInt("Enter ID of item to delete: ", min=1)
        confirm = pyip.inputYesNo(f"Are you sure you want to delete item ID {item_id}? (yes/no): ", default='no')

        if confirm == 'yes':
            conn = self._connect()
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM inventory WHERE item_id = ?", (item_id,))
                if cursor.rowcount > 0:
                    conn.commit()
                    print(f"Item ID {item_id} deleted successfully.")
                else:
                    print(f"Item ID {item_id} not found.")
            except sqlite3.Error as e:
                print(f"Database error deleting item: {e}")
                conn.rollback()
            finally:
                conn.close()
        else:
            print("Deletion cancelled.")

    def visualize_stock_levels(self):
        """Generates a bar chart of current stock levels."""
        conn = self._connect()
        cursor = conn.cursor()
        try:
            # Get top N items by quantity or name? Let's do by name for simplicity
            cursor.execute("SELECT name, quantity FROM inventory ORDER BY name LIMIT 20") # Limit for readability
            items = cursor.fetchall()
            if not items:
                print("No inventory items to visualize.")
                return

            names = [item[0] for item in items]
            quantities = [item[1] for item in items]

            plt.figure(figsize=(12, 7))
            plt.bar(names, quantities, color='lightcoral')
            plt.xlabel("Item Name")
            plt.ylabel("Quantity in Stock")
            plt.title("Inventory Stock Levels (Top 20 by Name)")
            plt.xticks(rotation=75, ha='right') # Rotate labels for long names
            plt.tight_layout() # Adjust layout

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(PLOT_DIR, f"inventory_stock_{timestamp}.png")
            plt.savefig(filename)
            plt.close()
            print(f"Stock level visualization saved to '{filename}'")

        except sqlite3.Error as e:
            print(f"Database error fetching inventory for visualization: {e}")
        except ImportError:
            print("Matplotlib is required for visualization. Please install it (`pip install matplotlib`).")
        except Exception as e:
            print(f"Error during visualization: {e}")
        finally:
            conn.close()

    def menu(self):
         while True:
            print("\n--- Inventory Management Menu ---")
            action = pyip.inputMenu([
                'Add Item',
                'View/Search Inventory',
                'View Low Stock Items',
                'Update Item (Incl. Adjust Stock)',
                'Delete Item',
                'Visualize Stock Levels',
                'Export Inventory to CSV',
                'Back to Main Menu'
            ], numbered=True)

            if action == 'Add Item':
                self.add_item()
            elif action == 'View/Search Inventory':
                search = pyip.inputStr("Enter search term (SKU, name, desc - blank for all): ", blank=True)
                self.view_inventory(search_term=search if search else None)
            elif action == 'View Low Stock Items':
                 self.view_inventory(low_stock_only=True)
            elif action == 'Update Item (Incl. Adjust Stock)':
                self.update_item()
            elif action == 'Delete Item':
                self.delete_item()
            elif action == 'Visualize Stock Levels':
                 self.visualize_stock_levels()
            elif action == 'Export Inventory to CSV':
                self.export_to_csv('inventory', 'inventory_export')
            elif action == 'Back to Main Menu':
                break

# --- Records Management ---
class RecordsManager(BaseManager):
    def add_record(self):
        print("\n-- Add New Record --")
        title = pyip.inputStr("Record Title: ")
        snippet = pyip.inputStr("Content Snippet/Summary (optional): ", blank=True)
        category = pyip.inputStr("Category (optional): ", blank=True)
        tags_input = pyip.inputStr("Tags (comma-separated, optional): ", blank=True)
        tags = ','.join(tag.strip() for tag in tags_input.split(',') if tag.strip()) # Cleaned tags

        conn = self._connect()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO records (title, content_snippet, category, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (title, snippet, category, tags))
            conn.commit()
            print(f"Record '{title}' added successfully (ID: {cursor.lastrowid}).")
        except sqlite3.Error as e:
            print(f"Database error adding record: {e}")
        finally:
            conn.close()

    def view_records(self, search_term=None, category_filter=None, tag_filter=None):
        print("\n-- View Records --")
        conn = self._connect()
        cursor = conn.cursor()
        try:
            query = "SELECT record_id, title, category, tags, updated_at FROM records"
            params = []
            conditions = []

            if search_term:
                conditions.append("(title LIKE ? OR content_snippet LIKE ?)")
                params.extend([f"%{search_term}%", f"%{search_term}%"])
            if category_filter:
                 conditions.append("category LIKE ?")
                 params.append(f"%{category_filter}%")
            if tag_filter:
                 conditions.append("tags LIKE ?")
                 params.append(f"%{tag_filter}%") # Simple LIKE search for tags

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY updated_at DESC"

            cursor.execute(query, params)
            records = cursor.fetchall()

            if not records:
                print("No records found." + (" Matching criteria." if any([search_term, category_filter, tag_filter]) else ""))
                return

            print("\n{:<5} {:<30} {:<20} {:<25} {:<20}".format("ID", "Title", "Category", "Tags", "Last Updated"))
            print("-" * 105)
            for r in records:
                print("{:<5} {:<30} {:<20} {:<25} {:<20}".format(
                    r[0], r[1], r[2] or "N/A", r[3] or "N/A", r[4][:19]))
            print("-" * 105)

        except sqlite3.Error as e:
            print(f"Database error viewing records: {e}")
        finally:
            conn.close()

    def update_record(self):
        print("\n-- Update Record --")
        record_id = pyip.inputInt("Enter ID of record to update: ", min=1)
        conn = self._connect()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT title, content_snippet, category, tags FROM records WHERE record_id = ?", (record_id,))
            record = cursor.fetchone()
            if not record:
                print(f"Record with ID {record_id} not found.")
                return

            print(f"Updating Record: {record[0]} (Category: {record[2]}, Tags: {record[3]})")
            title = pyip.inputStr(f"New Title (keep '{record[0]}'): ", blank=True) or record[0]
            snippet = pyip.inputStr(f"New Snippet (keep existing): ", blank=True) or record[1]
            category = pyip.inputStr(f"New Category (keep '{record[2]}'): ", blank=True) or record[2]
            tags_input = pyip.inputStr(f"New Tags (comma-sep, keep '{record[3]}'): ", blank=True)
            tags = ','.join(tag.strip() for tag in tags_input.split(',') if tag.strip()) if tags_input else record[3]

            cursor.execute("""
                UPDATE records
                SET title = ?, content_snippet = ?, category = ?, tags = ?, updated_at = CURRENT_TIMESTAMP
                WHERE record_id = ?
            """, (title, snippet, category, tags, record_id))
            conn.commit()
            print(f"Record ID {record_id} updated successfully.")

        except sqlite3.Error as e:
            print(f"Database error updating record: {e}")
            conn.rollback()
        finally:
            conn.close()


    def delete_record(self):
        print("\n-- Delete Record --")
        record_id = pyip.inputInt("Enter ID of record to delete: ", min=1)
        confirm = pyip.inputYesNo(f"Are you sure you want to delete record ID {record_id}? (yes/no): ", default='no')

        if confirm == 'yes':
            conn = self._connect()
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM records WHERE record_id = ?", (record_id,))
                if cursor.rowcount > 0:
                    conn.commit()
                    print(f"Record ID {record_id} deleted successfully.")
                else:
                    print(f"Record ID {record_id} not found.")
            except sqlite3.Error as e:
                print(f"Database error deleting record: {e}")
                conn.rollback()
            finally:
                conn.close()
        else:
            print("Deletion cancelled.")

    def menu(self):
        while True:
            print("\n--- Records Management Menu ---")
            action = pyip.inputMenu([
                'Add Record',
                'View/Search Records',
                'Update Record',
                'Delete Record',
                'Export Records to CSV',
                'Back to Main Menu'
            ], numbered=True)

            if action == 'Add Record':
                self.add_record()
            elif action == 'View/Search Records':
                search = pyip.inputStr("Search term (title/snippet, blank for none): ", blank=True)
                category = pyip.inputStr("Filter by Category (blank for none): ", blank=True)
                tag = pyip.inputStr("Filter by Tag (blank for none): ", blank=True)
                self.view_records(
                    search_term=search if search else None,
                    category_filter=category if category else None,
                    tag_filter=tag if tag else None
                )
            elif action == 'Update Record':
                self.update_record()
            elif action == 'Delete Record':
                self.delete_record()
            elif action == 'Export Records to CSV':
                self.export_to_csv('records', 'records_export')
            elif action == 'Back to Main Menu':
                break

# --- Custom Management (Simplified) ---
class CustomManager(BaseManager):
    def add_custom_record(self):
        print("\n-- Add Custom Record --")
        record_type = pyip.inputStr("Type of record (e.g., Project, Recipe, Contact): ")
        name = pyip.inputStr("Name/Identifier for this record: ")

        print("Enter custom fields (key-value pairs). Type 'done' for key when finished.")
        custom_data = {}
        while True:
            key = pyip.inputStr("Field Name (or 'done'): ")
            if key.lower() == 'done':
                break
            value = pyip.inputStr(f"Value for '{key}': ")
            custom_data[key] = value

        conn = self._connect()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO custom_records (record_type, name, custom_data, created_at, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (record_type, name, json.dumps(custom_data))) # Store data as JSON
            conn.commit()
            print(f"Custom record '{name}' (Type: {record_type}) added successfully (ID: {cursor.lastrowid}).")
        except sqlite3.Error as e:
            print(f"Database error adding custom record: {e}")
        finally:
            conn.close()

    def view_custom_records(self, type_filter=None, name_filter=None):
        print("\n-- View Custom Records --")
        conn = self._connect()
        cursor = conn.cursor()
        try:
            query = "SELECT custom_id, record_type, name, custom_data, updated_at FROM custom_records"
            params = []
            conditions = []

            if type_filter:
                conditions.append("record_type LIKE ?")
                params.append(f"%{type_filter}%")
            if name_filter:
                conditions.append("name LIKE ?")
                params.append(f"%{name_filter}%")

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY record_type, name"

            cursor.execute(query, params)
            records = cursor.fetchall()

            if not records:
                print("No custom records found." + (" Matching criteria." if (type_filter or name_filter) else ""))
                return

            print("\n-- Custom Records --")
            # Group by type for better readability
            current_type = None
            for r in records:
                # custom_id, record_type, name, custom_data, updated_at
                record_id, record_type, name, data_json, updated_at = r
                if record_type != current_type:
                    print(f"\n--- Type: {record_type} ---")
                    current_type = record_type
                print(f"  ID: {record_id}, Name: {name} (Updated: {updated_at[:19]})")
                try:
                    custom_data = json.loads(data_json)
                    for key, value in custom_data.items():
                        print(f"    - {key}: {value}")
                except json.JSONDecodeError:
                     print(f"    - Custom Data (Invalid JSON): {data_json}")
                print("-" * 20)


        except sqlite3.Error as e:
            print(f"Database error viewing custom records: {e}")
        finally:
            conn.close()

    # Update and Delete for CustomManager would be similar, needing to fetch, modify JSON, and save.
    # Let's keep it simple for this template and omit update/delete for custom.
    # Add placeholders if needed.

    def menu(self):
         while True:
            print("\n--- Custom Records Management Menu ---")
            print("(Note: This is a simplified module using JSON for custom fields.)")
            action = pyip.inputMenu([
                'Add Custom Record',
                'View Custom Records (by Type/Name)',
                'Export Custom Records to CSV', # Exporting JSON might be tricky in flat CSV
                'Back to Main Menu'
            ], numbered=True)

            if action == 'Add Custom Record':
                self.add_custom_record()
            elif action == 'View Custom Records (by Type/Name)':
                r_type = pyip.inputStr("Filter by Type (blank for none): ", blank=True)
                r_name = pyip.inputStr("Filter by Name (blank for none): ", blank=True)
                self.view_custom_records(
                    type_filter=r_type if r_type else None,
                    name_filter=r_name if r_name else None
                )
            elif action == 'Export Custom Records to CSV':
                 # Exporting JSON data to flat CSV can be complex.
                 # A simple export might just include ID, Type, Name, and the JSON string.
                 print("Exporting custom records to CSV (basic)...")
                 self.export_to_csv('custom_records', 'custom_records_export')

            elif action == 'Back to Main Menu':
                break


# --- Main Application ---
def main():
    initialize_database()

    student_manager = StudentManager()
    inventory_manager = InventoryManager()
    records_manager = RecordsManager()
    custom_manager = CustomManager()

    while True:
        print("\n======= Universal Management System =======")
        print("Select a module to manage:")
        main_choice = pyip.inputMenu([
            'Student Management',
            'Inventory Management',
            'Records Management',
            'Custom Records Management',
            'Exit'
        ], numbered=True)

        if main_choice == 'Student Management':
            student_manager.menu()
        elif main_choice == 'Inventory Management':
            inventory_manager.menu()
        elif main_choice == 'Records Management':
            records_manager.menu()
        elif main_choice == 'Custom Records Management':
            custom_manager.menu()
        elif main_choice == 'Exit':
            print("Exiting Universal Management System. Goodbye!")
            sys.exit(0) # Clean exit

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user. Exiting.")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected critical error occurred: {e}")
        # Consider logging the error traceback here for debugging
        sys.exit(1)
