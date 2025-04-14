# run_agent.py
import sys
import os
import subprocess
import time
import traceback

# --- Keep path setup ---
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ----------------------

# --- Import Agents and Utils ---
try:
    from Agents.Lead import LeadAgent
    import utils
    from utils import (
        Logger, print_ui, animate_ui, clear_line_ui, log_context_switch,
        COLOR_GREY, COLOR_YELLOW, COLOR_RESET
    )
except ImportError as e:
     print(f"FATAL: Could not import required modules. Check Agents/Lead.py and utils.py.\nError: {e}", file=sys.stderr)
     traceback.print_exc(file=sys.stderr)
     sys.exit(1)
# -----------------------------

LOG_FILE = os.path.abspath(os.path.join(project_root, utils.log_file_path))

# --- Logger Process Function ---
# (start_logger_process remains the same as previous version)
def start_logger_process(log_file_path):
    """Tails the log file and prints its content to a separate window."""
    print(f"[Logger Process Activated - Tailing: {log_file_path}]")
    print("--- Waiting for logs ---")
    try:
        if not os.path.exists(log_file_path):
             print("[Logger] Log file not found, creating...")
             try:
                 log_dir = os.path.dirname(log_file_path)
                 if log_dir and not os.path.exists(log_dir): os.makedirs(log_dir)
                 with open(log_file_path, "w", encoding='utf-8') as f: f.write("--- Log Start (created by logger process) ---\n")
                 print("[Logger] Log file created.")
             except Exception as create_e: print(f"[Logger Error] Could not create log file: {create_e}"); time.sleep(10); return

        print("[Logger] Tailing log file...")
        while True:
            try:
                with open(log_file_path, "r", encoding='utf-8') as f:
                    f.seek(0, os.SEEK_END)
                    while True:
                        line = f.readline()
                        if not line:
                            current_pos = f.tell(); time.sleep(0.3)
                            try:
                                if not os.path.exists(log_file_path):
                                     print("[Logger] Log file disappeared. Waiting...");
                                     while not os.path.exists(log_file_path): time.sleep(2)
                                     print("[Logger] Log file reappeared. Re-opening..."); break
                                if os.path.getsize(log_file_path) < current_pos: print("[Logger] Log file truncated. Seeking to start..."); f.seek(0, os.SEEK_SET)
                                else: f.seek(current_pos)
                            except Exception as check_e: print(f"[Logger Error] Error checking log file state: {check_e}"); time.sleep(2)
                            continue
                        print(line, end='', flush=True)
            except FileNotFoundError: print(f"[Logger Error] Log file not found during tailing: {log_file_path}. Waiting..."); time.sleep(5); continue
            except Exception as read_e: print(f"[Logger Error] Error reading log file: {read_e}"); traceback.print_exc(); time.sleep(5); continue
    except KeyboardInterrupt: print("\n[Logger Process Exiting Gracefully]")
    except Exception as e: print(f"\n[Logger Error] An unexpected fatal error occurred:"); traceback.print_exc(); time.sleep(10)


# --- Main Application Function ---
def start_main_application():
    """Sets up logging, runs agents, and handles main UI."""
    global original_stdout, original_stderr

    original_stdout = sys.stdout
    original_stderr = sys.stderr
    utils.original_stdout = original_stdout

    # 1. Clear/Create Log File (print_ui for errors only)
    log_cleared_successfully = False
    try:
        log_dir = os.path.dirname(LOG_FILE)
        if log_dir and not os.path.exists(log_dir): os.makedirs(log_dir)
        with open(LOG_FILE, "w", encoding='utf-8') as f:
            f.write(f"--- Log Start ({time.strftime('%Y-%m-%d %H:%M:%S')}) ---\n")
        log_cleared_successfully = True
    except Exception as e:
        print_ui(f"{COLOR_YELLOW}Warning: Could not clear/create log file '{LOG_FILE}': {e}{COLOR_RESET}\n")

    # --- Write initial messages directly to log file ---
    launch_msg = "Launching logger window...\n"
    debug_cmd = "" # We'll build this shortly
    if log_cleared_successfully:
        try:
            with open(LOG_FILE, "a", encoding='utf-8') as log_f:
                log_f.write(launch_msg)
                # The debug command needs to be constructed before writing it
        except Exception as write_e:
             print_ui(f"{COLOR_YELLOW}Warning: Could not write initial messages to log file: {write_e}{COLOR_RESET}\n")
    # -------------------------------------------------

    # 2. Start Logger Window Process
    try:
        # Removed: print_ui("Launching logger window...", flush=True)
        script_path = os.path.abspath(sys.argv[0])
        python_exe = sys.executable
        cmd = f'start "{os.path.basename(LOG_FILE)} Logger" /min cmd /c ""{python_exe}" "{script_path}" logger"'
        # *** Write the debug command to log BEFORE executing Popen ***
        debug_cmd = f"[RunAgent Debug] Launching logger command: {cmd}\n"
        if log_cleared_successfully:
             try:
                 with open(LOG_FILE, "a", encoding='utf-8') as log_f: log_f.write(debug_cmd)
             except Exception as write_e: print_ui(f"{COLOR_YELLOW}Warning: Could not write debug command to log: {write_e}{COLOR_RESET}\n")
        # Removed: print(f"[RunAgent Debug] Launching logger command: {cmd}")
        # *************************************************************

        subprocess.Popen(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        time.sleep(1.5)
        # Removed: clear_line_ui() # No message to clear from UI
    except Exception as popen_e:
        print_ui(f"{COLOR_YELLOW}Warning: Failed to launch logger window: {popen_e}{COLOR_RESET}\n")
        # Also write this error to the log if possible
        if log_cleared_successfully:
            try:
                 with open(LOG_FILE, "a", encoding='utf-8') as log_f:
                      log_f.write(f"[RunAgent Error] Popen exception: {popen_e}\n")
                      traceback.print_exc(file=log_f)
            except Exception: pass # Ignore if log write fails here

    # 3. Initial Startup Animation (Remains on main UI)
    animate_ui(f"{COLOR_GREY}Serializing Agents{COLOR_RESET}", duration=1.5, interval=0.3)

    # 4. Initialize Logger Class and Redirect stdout/stderr
    # The Logger __init__ will now write its success message to the log file itself
    logger_instance = Logger(LOG_FILE)
    if logger_instance.logfile is None:
        print_ui(f"{COLOR_YELLOW}FATAL: Logger could not be initialized. Check permissions and path ('{LOG_FILE}'). Exiting.{COLOR_RESET}\n")
        sys.exit(1)

    # --- Redirection ---
    # (This part remains the same)
    sys.stdout = logger_instance
    sys.stderr = logger_instance
    print("--- Main Process: stdout/stderr redirected to log file ---")
    print(f"Python executable: {sys.executable}")
    print(f"Project root: {project_root}")
    print(f"Log file path: {LOG_FILE}")
    print(f"Arguments: {sys.argv}")
    # -----------------

    # 5. Run Lead Agent
    # (This part remains the same)
    lead_agent = None
    try:
        print("(RunAgent Log): Initializing LeadAgent...")
        lead_agent = LeadAgent(original_stdout_handle=original_stdout)
        print("(RunAgent Log): Starting LeadAgent run loop...")
        lead_agent.run()
        print("(RunAgent Log): LeadAgent run loop finished.")
    except ImportError as e:
        print(f"\n--- FATAL ERROR during Agent Initialization ---"); print(f"Error: {e}"); traceback.print_exc()
        print_ui(f"\n{COLOR_YELLOW}FATAL ERROR: Import failed. Check logs ('{LOG_FILE}').\nError: {e}{COLOR_RESET}")
    except Exception as e:
        print(f"\n--- FATAL ERROR in Main Application Run ---"); print(f"Error Type: {type(e).__name__}"); print(f"Error Details: {e}"); traceback.print_exc()
        print_ui(f"\n{COLOR_YELLOW}FATAL ERROR: Unexpected error. Check logs ('{LOG_FILE}').\nError: {e}{COLOR_RESET}")
    finally:
        # 6. Restore stdout/stderr
        # (This part remains the same)
        print("(RunAgent Log): Restoring standard output streams...")
        if isinstance(sys.stdout, Logger): sys.stdout = original_stdout
        if isinstance(sys.stderr, Logger): sys.stderr = original_stderr
        print_ui("\nApplication finished.")

# --- Entry Point ---
# (This part remains the same)
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "logger":
        if 'LOG_FILE' not in globals():
             project_root_logger = os.path.dirname(os.path.abspath(__file__))
             default_log_path = "agent_log.txt"
             LOG_FILE = os.path.abspath(os.path.join(project_root_logger, default_log_path))
             print(f"[Logger Arg] LOG_FILE re-defined for logger process: {LOG_FILE}")
        start_logger_process(LOG_FILE)
    else:
        start_main_application()