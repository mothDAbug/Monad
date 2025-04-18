import os
# HACK, BECAUSE OF MAJOR REFACTORING ISSUES... Change the current working directory
os.chdir(r'C:\monad\monad-main')

import shutil

source_file = ".env.example"
dest_file = ".env"

# Check if the destination file (.env) ALREADY exists
if os.path.exists(dest_file):
    pass
else:
    # If .env DOES NOT exist, proceed to create it
    print(f"'{dest_file}' not found. Attempting to create from '{source_file}'...")

    # Check if the source file (.env.example) exists before trying to copy
    if os.path.exists(source_file):
        try:
            # Copy the source file to the destination file
            shutil.copy2(source_file, dest_file)
            print(f"Successfully created '{dest_file}' from '{source_file}'.")
        except Exception as e:
            print(f"Error copying '{source_file}' to '{dest_file}': {e}")
    else:
        # Handle the case where the template file itself is missing
        print(f"Error: Source file '{source_file}' not found. Cannot create '{dest_file}'.")

import subprocess
import sys
import time

# --- Configuration ---
REQUIREMENTS_FILE = 'requirements.txt'
CHROMA_DB_FOLDER = 'chroma_db'
SETUP_SCRIPT = 'setup_chroma.py'
ENV_FILE = '.env'
AGENT_SCRIPT = 'run_agent.py'
VENV_DIR = 'venv'
WAIT_TIME = 2
# ---------------------

# --- Color & Text Config ---
RED_COLOR_ANSI = "\033[91m" # Bright Red ANSI code
RESET_COLOR_ANSI = "\033[0m" # Reset ANSI code

FOOTER_TEXT = "(this our project scope try to develop projects under these verbatim)"
FOOTER_START_COLOR = (0, 255, 0) # Green
FOOTER_END_COLOR = (0, 128, 255)   # Light Blue
# -----------------------------

# --- Gradient ASCII Function (Needed for Footer and Banner) ---
def rgb_gradient_ascii(ascii_lines, start_rgb, end_rgb):
    # --- [ This function remains the same as before ] ---
    if isinstance(ascii_lines, str):
        ascii_lines = [ascii_lines]
    try:
        max_length = max(len(line) for line in ascii_lines if line)
        if max_length == 0: return "\n".join(ascii_lines)
    except ValueError: return ""
    gradient_lines = []
    num_lines = len(ascii_lines)
    for idx, line in enumerate(ascii_lines):
        gradient_line = ""
        line_length = len(line.rstrip())
        denominator = max(1, line_length - 1)
        for i, char in enumerate(line):
            if i < line_length and char != ' ':
                r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * i / denominator)
                g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * i / denominator)
                b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * i / denominator)
                r, g, b = max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))
                gradient_line += f"\033[38;2;{r};{g};{b}m{char}\033[0m"
            else:
                gradient_line += char
        gradient_lines.append(gradient_line)
    # Return single string if single line input, otherwise joined lines
    return gradient_lines[0] if len(gradient_lines) == 1 and isinstance(ascii_lines, list) and len(ascii_lines) == 1 and isinstance(ascii_lines[0], str) else "\n".join(gradient_lines)

# --- Hardcoded Scope Text (Modified for Solid Red and Prefix) ---
# Apply gradient ONLY to the footer text
colored_footer = rgb_gradient_ascii(FOOTER_TEXT, FOOTER_START_COLOR, FOOTER_END_COLOR)

# Build the list of echo commands with solid red for the tree
# Note: Using f-strings to embed the color codes makes it readable
SCOPE_TEXT_LINES = [
    "@echo off", # Turn off command echoing
    # Add the prefix - Use echo without color for this line
    f"echo {RED_COLOR_ANSI} docs/projectScope/",
    # Add the tree structure, applying red color to each line
    f"echo {RED_COLOR_ANSI}├─ Conversion Tools{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}│   ├─ Unit Converter{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}│   ├─ Currency Converter{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}│   └─ Text Case Converter{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}├─ Basic Generators{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}│   ├─ Random Name Generator{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}│   └─ Lorem Ipsum Generator{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}├─ Data Management System{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}│   └─ Student / Inventory / Records System{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}├─ File Management System{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}│   ├─ Local File Organizer{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}│   └─ Duplicate Finder{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}├─ Task Manager{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}│   ├─ To-Do List{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}│   ├─ Task Scheduler{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}│   ├─ Habit Tracker{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}│   └─ Reminder System{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}├─ Tracking-Based Apps{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}│   ├─ Expense Tracker{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}│   ├─ Time Tracker{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}│   └─ Goal Tracker{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}├─ Notes App{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}│   └─ Notes App{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}├─ Secure Storage System{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}│   ├─ Password Manager{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}│   ├─ Digital Vault{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}│   └─ API Key Manager{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}├─ Sentiment Analyzer{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}│   └─ Sentiment Analyzer{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}├─ Text Summarizer{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}│   └─ Text Summarizer{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}└─ Number Guessing Game{RESET_COLOR_ANSI}",
    f"echo {RED_COLOR_ANSI}    └─ Number Guessing Game{RESET_COLOR_ANSI}",
    "echo.", # Blank line before footer
    # Echo the pre-colored gradient footer text
    "echo." + colored_footer,
    # Pause without the "Press any key..." message
    "pause > nul"
]
# Combine lines into a single command string separated by '&'
SCOPE_CMD_STRING = " & ".join(SCOPE_TEXT_LINES)
# ---------------------------------------------

# --- Main Banner ASCII Art Definition ---
banner_ascii_art_lines = [
    "     e    e        ,88~-_   888b    |      e      888~-_   ",
    "    d8b  d8b      d888   \\  |Y88b   |     d8b     888   \\  ",
    "   d888bdY88b    88888    | | Y88b  |    /Y88b    888    | ",
    "  / Y88Y Y888b   88888    | |  Y88b |   /  Y88b   888    | ",
    " /   YY   Y888b   Y888   /  |   Y88b|  /____Y88b  888   /  ",
    "/          Y888b   `88_-~   |    Y888 /      Y88b 888_-~   ",
    "                                                            "
]
banner_start_color = (0, 0, 255)     # Blue
banner_end_color = (255, 255, 255)   # White
# ---------------------------------------

# --- Helper Functions (Windows Only - Venv, Requirements, Run Script, etc.) ---
# --- [ These functions remain the same as the previous version ] ---
def find_or_create_venv(venv_path):
    if not os.path.isdir(venv_path):
        print(f"--- Virtual environment '{venv_path}' not found. Creating... ---")
        try:
            process = subprocess.run([sys.executable, '-m', 'venv', venv_path], check=True, capture_output=True, text=True, encoding='utf-8')
            print(f"Virtual environment created successfully in '{venv_path}'.")
            if process.stdout: print(f"Output:\n{process.stdout}")
            if process.stderr: print(f"Error Output:\n{process.stderr}", file=sys.stderr)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error: Failed to create venv '{venv_path}'. Code: {e.returncode}", file=sys.stderr)
            print(f"Stderr:\n{e.stderr}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"An unexpected error during venv creation: {e}", file=sys.stderr)
            return False
    else:
        print(f"--- Using existing virtual environment in '{venv_path}' ---")
        return True

def get_venv_python_executable_windows(venv_path):
    py_path = os.path.join(venv_path, 'Scripts', 'python.exe')
    if not os.path.isfile(py_path):
        print(f"Error: Venv Python executable not found: {py_path}", file=sys.stderr)
        return None
    return py_path

def ensure_requirements_installed(venv_python_exec, req_file):
    print(f"--- Ensuring requirements from {req_file} are installed... ---")
    if not os.path.isfile(req_file):
        print(f"Error: {req_file} not found.", file=sys.stderr)
        return False
    try:
        command = [venv_python_exec, '-m', 'pip', 'install', '-r', req_file]
        print(f"Running: {' '.join(command)}")
        process = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
        if process.stdout.strip(): print(f"pip output:\n{process.stdout}")
        if process.stderr.strip(): print(f"pip error output:\n{process.stderr}", file=sys.stderr)
        print("--- Requirements installation/check completed. ---")
        return True
    except FileNotFoundError:
        print(f"Error: Could not find '{venv_python_exec}' or pip.", file=sys.stderr)
        return False
    except subprocess.CalledProcessError as e:
        print(f"Error: 'pip install' failed. Code: {e.returncode}", file=sys.stderr)
        print(f"Stderr:\n{e.stderr}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"An unexpected error installing requirements: {e}", file=sys.stderr)
        return False

def run_script_in_venv_windows(venv_python_exec, script_path, wait=True, *args):
    print(f"--- Running script: {script_path} using {venv_python_exec} ---")
    if not os.path.isfile(script_path):
        print(f"Error: Script '{script_path}' not found.", file=sys.stderr)
        return False
    command = [venv_python_exec, script_path] + list(args)
    try:
        is_setup = script_path == SETUP_SCRIPT
        process = subprocess.run(command, check=is_setup, text=True, encoding='utf-8')
        if is_setup: print(f"--- Script {script_path} finished. ---")
        else: print(f"\n--- Script '{script_path}' finished or exited. ---")
        return True
    except FileNotFoundError:
         print(f"Error: Interpreter '{venv_python_exec}' or script '{script_path}' not found.", file=sys.stderr)
         return False
    except subprocess.CalledProcessError as e:
        print(f"Error: Script '{script_path}' failed. Code: {e.returncode}", file=sys.stderr)
        if e.stdout: print(f"Stdout:\n{e.stdout}", file=sys.stderr)
        if e.stderr: print(f"Stderr:\n{e.stderr}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"An unexpected error running {script_path}: {e}", file=sys.stderr)
        return False

def open_notepad(filepath):
    print(f"Opening '{filepath}' in Notepad...")
    try:
        os.startfile(filepath)
        return True
    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found.", file=sys.stderr)
        print("Please create it manually if needed and edit.")
        return False
    except Exception as e:
        print(f"Error opening '{filepath}' in Notepad: {e}", file=sys.stderr)
        print(f"Please manually open and edit '{filepath}'.")
        return False

def run_animation(duration_secs=2, message=""):
    if message: print(message, end="")
    sys.stdout.flush()
    animation_chars = [".  ", ".. ", "..."]
    start_time = time.time()
    while time.time() - start_time < duration_secs:
        for char_frame in animation_chars:
            print(f"\r{message}{char_frame}", end="")
            sys.stdout.flush()
            time.sleep(0.33)
            if time.time() - start_time >= duration_secs: break
    print(f"\r{message}... Done!   ")

def clear_screen_windows():
    os.system('cls')
# -----------------------------------------------------------------------------

# --- Function to launch scope display window (Windows Only - Hardcoded Echo) ---
def launch_scope_display_window_windows_hardcoded():
    """Launches a new CMD window that echoes the hardcoded scope and pauses silently."""
    print("--- Launching project scope display window... ---")

    try:
        # Command uses the pre-built SCOPE_CMD_STRING which includes colored footer
        # and 'pause > nul'
        full_command = ['cmd', '/K', SCOPE_CMD_STRING]

        # Launch the new window
        subprocess.Popen(full_command,
                         shell=False,
                         creationflags=subprocess.CREATE_NEW_CONSOLE)
        time.sleep(1.5) # Give window time to open

    except Exception as e:
        print(f"An error occurred launching the scope display window: {e}", file=sys.stderr)
        # Attempt fallback (optional, can be removed if primary method is reliable)
        print("Attempting fallback using 'start'...")
        try:
             # Need to be careful with quotes for the command string within start
             # Replacing internal quotes might be needed if the command string had them.
             # For this simple case, just quoting the whole thing might work.
             start_command = f'start "Project Scope" cmd /K "{SCOPE_CMD_STRING}"'
             subprocess.Popen(start_command, shell=True)
        except Exception as e2:
             print(f"Fallback using 'start' also failed: {e2}", file=sys.stderr)


# --- Main Execution Logic (Windows Only) ---
if __name__ == "__main__":

    # Enable ANSI processing in the main console if needed (for banner)
    os.system('') # Simple way to try and enable VT100 on Windows

    title = "Application Launcher (Windows)"; print(title); print("-" * len(title)); print()

    # 1. Venv Setup
    if not find_or_create_venv(VENV_DIR): sys.exit(1)
    venv_python = get_venv_python_executable_windows(VENV_DIR)
    if not venv_python: sys.exit(1)
    print(f"Using Venv Python: {venv_python}\n")

    # 2. Requirements
    if not ensure_requirements_installed(venv_python, REQUIREMENTS_FILE): sys.exit(1)
    print("\n")

    # 3. ChromaDB Check / Setup
    print(f"--- Checking for {CHROMA_DB_FOLDER} directory ---")
    if os.path.isdir(CHROMA_DB_FOLDER):
        print("Found. Skipping setup.")
    else:
        print("Not found.")
        if not run_script_in_venv_windows(venv_python, SETUP_SCRIPT, wait=True):
             sys.exit(1)
        if not os.path.isdir(CHROMA_DB_FOLDER):
             print(f"Warning: '{CHROMA_DB_FOLDER}' still not found after setup.", file=sys.stderr)
    print("\n")

    # 5. Env File Setup
    print("--- Environment Variable Setup ---")
    print(f"Please ensure your variables are set in '{ENV_FILE}'.")
    print(f"Opening {ENV_FILE} in Notepad in {WAIT_TIME}s...")
    time.sleep(WAIT_TIME)
    if not os.path.exists(ENV_FILE): print(f"Note: '{ENV_FILE}' not found, might be created by Notepad.")
    if open_notepad(ENV_FILE):
        input(f"\n>>> Press Enter after configuring '{ENV_FILE}' and closing Notepad... <<<")
    else:
        input(f"\n>>> Please manually edit '{ENV_FILE}', save, then press Enter here... <<<")

    # 6. Confirmation and Animation
    run_animation(duration_secs=WAIT_TIME, message="Okay, let's go")
    time.sleep(0.5)

    # ***** Launch Scope Display Window (Hardcoded Echo Method - Updated) *****
    launch_scope_display_window_windows_hardcoded()
    # ************************************************************************

    # 7. Clear screen, show gradient art, and run agent
    print("\nClearing main screen and preparing to start the agent...")
    time.sleep(WAIT_TIME + 1)
    clear_screen_windows()

    # Print Gradient ASCII Art Banner in *this* terminal
    try:
        gradient_art_output = rgb_gradient_ascii(banner_ascii_art_lines, banner_start_color, banner_end_color)
        print(gradient_art_output)
    except Exception as e:
        print("Error generating gradient banner art:", e, file=sys.stderr)
        print("\n".join(banner_ascii_art_lines)) # Fallback

    print("\n")
    time.sleep(1.5) # Pause to show art

    # Run the main agent script (waits for it to finish)
    if not run_script_in_venv_windows(venv_python, AGENT_SCRIPT, wait=True):
        print("\nFailed to launch or run the agent script.", file=sys.stderr)
        sys.exit(1)

    print("\nLauncher finished.")
