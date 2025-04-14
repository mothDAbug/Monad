# utils.py
import sys
import time
import itertools
import os
import traceback # Import traceback for logging

# --- ANSI Color Codes ---
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"
COLOR_DIM = "\033[2m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_GREY = "\033[90m"
COLOR_BLUE = "\033[94m"
COLOR_MAGENTA = "\033[95m"
COLOR_CYAN = "\033[96m"
COLOR_RED = "\033[91m"  # *** ADDED MISSING COLOR_RED ***

# This will be set by run_agent.py after saving the original stdout
original_stdout = sys.stdout
log_file_path = "agent_log.txt" # Default log file path relative to project root

def print_ui(message="", end="\n", flush=False):
    """Prints exclusively to the original standard output."""
    try:
        original_stdout.write(str(message) + end)
        if flush:
            original_stdout.flush()
    except Exception as e:
        sys.__stdout__.write(f"[print_ui Error] Failed to write to original stdout: {e}\n")
        sys.__stdout__.write(f"[print_ui Fallback] Message: {message}\n")

def clear_line_ui():
    """Clears the current line on the original standard output."""
    print_ui("\r" + " " * 80 + "\r", end="", flush=True)

def animate_ui(base_message, duration=2.0, interval=0.15):
    """Displays a simple animation (dots) on the original stdout for a set duration."""
    animation_chars = itertools.cycle(['.', '..', '...'])
    print_ui(f"{base_message}", end="", flush=True)
    start_time = time.time()
    last_char = ""
    while time.time() - start_time < duration:
        char = next(animation_chars)
        print_ui(f"\r{base_message}{char.ljust(3)}", end="", flush=True)
        last_char = char
        time.sleep(interval)
    clear_line_ui()
    print_ui(COLOR_RESET, end="", flush=True)

def log_context_switch(from_agent: str, to_agent: str):
    """Prints a formatted context switch message to the UI."""
    print_ui(f"\n{COLOR_BOLD}{COLOR_BLUE}~$ {from_agent} 🔗 {to_agent}{COLOR_RESET}", flush=True)

# --- Logger Class to handle redirection ---
class Logger:
    """Redirects stdout/stderr to a log file."""
    def __init__(self, filename=log_file_path):
        self.terminal = sys.stdout
        self.logfile = None
        self.filename = filename
        try:
            log_dir = os.path.dirname(self.filename)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            self.logfile = open(self.filename, "a", encoding='utf-8')
            # *** CHANGED: Write init success message directly to the log file ***
            init_msg = f"[Logger Class Init] Successfully opened log file: {self.filename}\n"
            self.logfile.write(init_msg)
            self.logfile.flush()
            # Removed: print(init_msg, file=original_stdout)
            # ******************************************************************
        except Exception as e:
            # Still print FATAL errors to original stdout if logger init fails
            print(f"FATAL: Could not open log file {self.filename}: {e}", file=original_stdout)
            traceback.print_exc(file=original_stdout)
            self.logfile = None

    def write(self, message):
        """Writes message to the log file."""
        if self.logfile:
            try:
                self.logfile.write(str(message))
                self.logfile.flush()
            except Exception as e:
                sys.__stderr__.write(f"[Logger Write Error] Failed to write to log: {e}\n")
                pass

    def flush(self):
        """Flushes the log file buffer."""
        if self.logfile:
            try:
                self.logfile.flush()
            except Exception:
                pass

    def close(self):
        """Closes the log file."""
        if self.logfile:
            try:
                self.flush()
                self.logfile.write(f"--- Log End ({time.strftime('%Y-%m-%d %H:%M:%S')}) ---\n")
                self.logfile.flush()
                self.logfile.close()
                # Removed print statement about closing from here
                # print(f"[Logger Class Close] Closed log file: {self.filename}", file=original_stdout)
                self.logfile = None
            except Exception as e:
                 print(f"[Logger Class Close Error] Error closing log file: {e}", file=original_stdout)
                 self.logfile = None

    def __del__(self):
        """Ensures file is closed when logger object is garbage collected."""
        self.close()