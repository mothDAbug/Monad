# Agents/Tester.py
import sys
import os
import json
import re
import subprocess # For running tests
import time
import traceback
from dotenv import load_dotenv
import google.generativeai as genai

# --- Import Utils (Essential) ---
try:
    project_root_dir_utils = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root_dir_utils not in sys.path:
        sys.path.insert(0, project_root_dir_utils)

    import utils
    from utils import print_ui, animate_ui, clear_line_ui
    from utils import COLOR_RESET, COLOR_DIM, COLOR_YELLOW, COLOR_GREEN, COLOR_RED, COLOR_CYAN

    # Reuse Developer's NativeCodeGenerator
    from Agents.Developer import NativeCodeGenerator

    # Try to get the artifacts directory name consistently
    try:
        from Agents.Analyst import OUTPUT_DIR as ARTIFACTS_DIR_NAME
    except (ImportError, AttributeError):
        ARTIFACTS_DIR_NAME = "artifacts"
        print(f"Warning (TesterAgent): Could not determine artifacts dir from Analyst. Defaulting to '{ARTIFACTS_DIR_NAME}'.")

except ImportError:
     print("FATAL Error (TesterAgent): Could not import utils or Developer Agent components. UI and logging might fail.")
     def print_ui(message="", end="\n", flush=False): print(message, end=end, flush=flush)
     def animate_ui(base_message, duration=2.0, interval=0.15): print(f"{base_message}...")
     def clear_line_ui(): pass
     COLOR_RESET=COLOR_DIM=COLOR_YELLOW=COLOR_GREEN=COLOR_RED=COLOR_CYAN=""; ARTIFACTS_DIR_NAME = "artifacts"
     # Define a placeholder NativeCodeGenerator if import fails
     class NativeCodeGenerator:
         def __init__(self): self.model = None
         def generate_code_native(self, p): print("Error: NativeCodeGenerator not loaded"); return None
         def extract_code(self, t): print("Error: NativeCodeGenerator not loaded"); return None
# --------------------------------------------------------

# --- Helper function to load prompts ---
def load_prompt_template(file_path_relative: str) -> str | None:
    """Loads a prompt template string from a file relative to the project root."""
    try:
        _project_root = project_root_dir_utils # Use the defined project root
        full_path = os.path.normpath(os.path.join(_project_root, file_path_relative))
        if os.path.exists(full_path) and os.path.isfile(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            print(f"Error (Tester Prompt Loader): Prompt file not found or is not a file: {full_path}")
            return None
    except NameError:
        print(f"Error (Tester Prompt Loader): Project root directory not defined. Cannot load prompt '{file_path_relative}'.")
        return None
    except Exception as e:
        print(f"Error reading prompt '{file_path_relative}': {e}"); traceback.print_exc(); return None
# --------------------------------------------------------

# --- Configuration ---
PROMPTS_DIR = ".sysprompts"
TESTER_GENERATOR_PROMPT_FILE = os.path.join(PROMPTS_DIR, "tester_generator.prompt")
# TESTER_REFINER_PROMPT_FILE = os.path.join(PROMPTS_DIR, "tester_refiner.prompt") # Add if refinement needed
DEFAULT_USER_STORIES_FILENAME = "user_stories_output.json"
MAX_TEST_GENERATION_RETRIES = 3
UNITTEST_DIR_NAME = "unittest" # Subdirectory for test files

# --- Marker Definitions ---
TEST_CODE_START_MARKER_PATTERN = r"\[\[\[BEGIN_TEST_FILE:.*?\]\]\]" # Regex pattern
TEST_CODE_END_MARKER_PATTERN = r"\[\[\[END_TEST_FILE:.*?\]\]\]"     # Regex pattern

class TesterAgent:
    """
    Generates, saves, and runs Python unittest tests for code created by the Developer Agent.
    """
    def __init__(self, original_stdout_handle=None):
        print("(TesterAgent Log): Initializing Test Agent...")
        if original_stdout_handle: utils.original_stdout = original_stdout_handle
        load_dotenv()
        self.project_root = project_root_dir_utils # Store project root
        self.code_generator = NativeCodeGenerator() # Reuse from Developer
        if not self.code_generator.model:
            print("CRITICAL Warning (TesterAgent): Native Generator model failed init.")

        # Load prompts
        self.generator_template_str = load_prompt_template(TESTER_GENERATOR_PROMPT_FILE)
        # self.refiner_template_str = load_prompt_template(TESTER_REFINER_PROMPT_FILE) # Load if needed

        if not self.generator_template_str: print(f"FATAL Error: Missing TESTER GENERATOR prompt ({TESTER_GENERATOR_PROMPT_FILE}).")
        # if not self.refiner_template_str: print(f"Warning: Missing TESTER REFINER prompt.")

        print("(TesterAgent Log): Test Agent Init complete.")

    def _save_test_code(self, code_content: str, test_script_path: str) -> bool:
        """Saves the generated test code to the specified path, creating directories."""
        if not test_script_path or code_content is None:
            print(f"Error (Save Test): Invalid path or content provided.")
            return False
        try:
            test_script_dir = os.path.dirname(test_script_path)
            if test_script_dir: # Ensure directory exists
                os.makedirs(test_script_dir, exist_ok=True)
                print(f"(TesterAgent Log): Ensured test directory exists: {test_script_dir}")

            # Add __init__.py to the unittest directory if it doesn't exist
            init_py_path = os.path.join(test_script_dir, "__init__.py")
            if not os.path.exists(init_py_path):
                try:
                    with open(init_py_path, 'w', encoding='utf-8') as f_init:
                        f_init.write("# Required for test discovery\n")
                    print(f"(TesterAgent Log): Created __init__.py in {test_script_dir}")
                except Exception as init_e:
                     print(f"Warning (Save Test): Failed to create __init__.py: {init_e}")


            with open(test_script_path, 'w', encoding='utf-8') as f:
                f.write(code_content)
            print(f"(TesterAgent Log): Test code saved successfully to {test_script_path}.")
            return True
        except Exception as e:
            print(f"Error (Save Test): Failed to save test code to {test_script_path}: {e}"); traceback.print_exc()
            return False

    def _read_developer_code(self, developer_script_path: str) -> str | None:
        """Reads the content of the script generated by the Developer Agent."""
        if not developer_script_path or not os.path.isfile(developer_script_path):
            print(f"Error (Read Dev Code): Developer script not found or invalid path: {developer_script_path}")
            return None
        try:
            with open(developer_script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"(TesterAgent Log): Successfully read developer code from: {developer_script_path}")
            return content
        except Exception as e:
            print(f"Error (Read Dev Code): Failed to read {developer_script_path}: {e}")
            traceback.print_exc()
            return None

    def _load_tester_stories(self, user_stories_json_path: str | None) -> str:
        """Loads user stories from JSON and filters for the 'Tester' role."""
        if not user_stories_json_path:
            default_path = os.path.join(self.project_root, ARTIFACTS_DIR_NAME, DEFAULT_USER_STORIES_FILENAME)
            user_stories_json_path = default_path
            print(f"(TesterAgent Log): No stories path provided, defaulting to: {user_stories_json_path}")
        else:
             if not os.path.isabs(user_stories_json_path):
                 user_stories_json_path = os.path.normpath(os.path.join(self.project_root, user_stories_json_path))

        if not os.path.isfile(user_stories_json_path):
            print(f"Error: Stories JSON file not found: {user_stories_json_path}")
            return "(Tester stories file not found)"

        print(f"(TesterAgent Log): Reading and filtering stories for 'Tester' from: {user_stories_json_path}")
        try:
            with open(user_stories_json_path, 'r', encoding='utf-8') as f:
                all_stories = json.load(f)
        except Exception as e:
            print(f"Error reading/parsing stories JSON: {e}")
            return f"(Error loading/parsing stories file: {e})"

        if not isinstance(all_stories, list):
            print(f"Error: Stories JSON content is not a list (type: {type(all_stories)}).")
            return "(Invalid stories format - not a list)"

        tester_tasks = []
        for i, story in enumerate(all_stories):
            if not isinstance(story, dict): continue
            role = story.get("role", "").strip().lower()
            if role == "tester":
                action = story.get("action", "").strip()
                user_story_text = story.get("user_story", "").strip()
                if action: tester_tasks.append(action)
                elif user_story_text: tester_tasks.append(user_story_text)

        if not tester_tasks:
            print("(TesterAgent Log): No specific tasks found for the 'Tester' role.")
            return "(No tester tasks extracted)"

        formatted_tasks = "\n".join([f"- {task}" for task in tester_tasks])
        print(f"(TesterAgent Log): Extracted {len(tester_tasks)} tester tasks.")
        return formatted_tasks

    def _run_tests(self, project_folder_path: str, test_script_filename: str) -> tuple[bool, str]:
        """
        Runs the generated unittest script using subprocess and parses the output.

        Returns:
            tuple[bool, str]: (True if tests passed, False otherwise, Test output report/error message)
        """
        test_script_rel_path = os.path.join(UNITTEST_DIR_NAME, test_script_filename)
        test_script_abs_path = os.path.join(project_folder_path, test_script_rel_path)

        print(f"(TesterAgent Log): Running tests for: {test_script_rel_path}")
        print(f"(TesterAgent Log): CWD for test execution: {project_folder_path}")

        if not os.path.exists(test_script_abs_path):
            print(f"Error (Run Tests): Test script not found at {test_script_abs_path}")
            return False, f"Test Error: Test script file missing at {test_script_abs_path}"

        try:
            # Command to run a specific test file using the unittest module
            # Running from the project root directory helps with imports in the test file
            python_exe = sys.executable # Use the same python that runs the main script
            command = [python_exe, "-m", "unittest", test_script_rel_path]

            print(f"(TesterAgent Log): Executing command: {' '.join(command)}")
            process = subprocess.run(
                command,
                cwd=project_folder_path, # Run from the project root
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace', # Handle potential encoding errors in output
                timeout=120 # Add a timeout (e.g., 2 minutes)
            )

            stdout = process.stdout.strip()
            stderr = process.stderr.strip()
            output_report = f"--- Test Standard Output ---\n{stdout}\n\n--- Test Standard Error ---\n{stderr}\n--- End Report ---"

            print(f"(TesterAgent Log): Test execution finished. Return Code: {process.returncode}")
            # print(f"(TesterAgent Log): Test Stdout:\n{stdout}") # Verbose
            # print(f"(TesterAgent Log): Test Stderr:\n{stderr}") # Verbose

            # --- Parse Output ---
            # unittest module typically prints "OK" on success to stderr,
            # and "FAIL" or "ERROR" on failure, also usually to stderr.
            # Return code 0 usually indicates success, but double-check stderr.
            passed = False
            if process.returncode == 0 and ("FAIL" not in stderr and "ERROR" not in stderr):
                 # Sometimes 'OK' might be missing but return code is 0 and no errors/fails
                 passed = True
                 print(f"{COLOR_GREEN}(TesterAgent Log): Tests PASSED (Return Code 0, No FAIL/ERROR in stderr).{COLOR_RESET}")
            elif "OK" in stderr and "FAIL" not in stderr and "ERROR" not in stderr:
                 passed = True # Explicit OK is good
                 print(f"{COLOR_GREEN}(TesterAgent Log): Tests PASSED (Found 'OK' in stderr).{COLOR_RESET}")
            else:
                 passed = False
                 print(f"{COLOR_YELLOW}(TesterAgent Log): Tests FAILED or Errored (Return Code {process.returncode} or FAIL/ERROR in stderr).{COLOR_RESET}")

            return passed, output_report

        except FileNotFoundError:
            print(f"Error (Run Tests): Python executable not found ('{python_exe}'). Check PATH.")
            return False, f"Test Execution Error: Python executable not found: {python_exe}"
        except subprocess.TimeoutExpired:
             print(f"Error (Run Tests): Test execution timed out.")
             return False, "Test Execution Error: Timeout occurred (tests took too long)."
        except Exception as e:
            print(f"Error (Run Tests): Unexpected error running subprocess: {e}")
            traceback.print_exc()
            return False, f"Test Execution Error: {e}\n{traceback.format_exc()}"

    def execute_test_generation(self, blueprint_text: str, developer_code_path: str,
                                project_folder_path: str, user_stories_json_path: str | None) -> tuple[bool | None, str | None, str | None]:
        """
        Orchestrates test generation, saving, and execution.

        Returns:
            tuple[bool | None, str | None, str | None]:
                (test_pass_status, test_report, generated_test_code_path)
                Status is None if generation/extraction failed.
        """
        script_name = os.path.basename(developer_code_path)
        script_name_no_ext = os.path.splitext(script_name)[0]
        test_file_name = f"test_{script_name_no_ext}.py"
        test_dir_path = os.path.join(project_folder_path, UNITTEST_DIR_NAME)
        target_test_script_full_path = os.path.join(test_dir_path, test_file_name)

        print(f"{COLOR_CYAN}--- Tester Agent: Starting Test Generation for '{script_name}' ---{COLOR_RESET}")
        if not self.code_generator or not self.code_generator.model or not self.generator_template_str:
            print("Error: TesterAgent not ready (Generator/Model/Generator Prompt missing).")
            return None, "Tester Agent Error: Core components missing.", None
        if not all([blueprint_text, developer_code_path, project_folder_path]):
            print("Error: Missing critical context: blueprint, developer_code_path, or project_folder_path.")
            return None, "Tester Agent Error: Missing required context.", None

        print("(TesterAgent Gen Log): Preparing context for test generation prompt...")
        developer_code = self._read_developer_code(developer_code_path)
        if not developer_code:
            return None, f"Tester Agent Error: Could not read developer code from {developer_code_path}", None
        tester_actions_text = self._load_tester_stories(user_stories_json_path)

        formatted_prompt = None
        try:
            # Basic safety, though {} likely okay in code context for LLM
            safe_blueprint = blueprint_text #.replace('{', '{{').replace('}', '}}')
            safe_developer_code = developer_code #.replace('{', '{{').replace('}', '}}')
            safe_actions_text = tester_actions_text #.replace('{', '{{').replace('}', '}}')

            formatted_prompt = self.generator_template_str.format(
                 blueprint_text=safe_blueprint,
                 developer_code=safe_developer_code,
                 tester_user_stories_text=safe_actions_text,
                 script_name=script_name,
                 test_file_name=test_file_name,
                 script_name_no_ext=script_name_no_ext
             )
            print("(TesterAgent Gen Log): Test generation prompt formatted.")
        except KeyError as ke:
             print(f"Error formatting prompt: Missing key {ke}. Check prompt template variables."); traceback.print_exc();
             return None, f"Tester Agent Error: Prompt formatting failed (KeyError: {ke})", None
        except Exception as e_fmt:
            print(f"Error formatting prompt: {e_fmt}"); traceback.print_exc();
            return None, f"Tester Agent Error: Prompt formatting failed: {e_fmt}", None

        if not formatted_prompt:
            print("Error: Formatted prompt is empty after formatting attempt.");
            return None, "Tester Agent Error: Prompt formatting resulted in empty prompt.", None

        # --- RETRY LOOP for Test Generation ---
        final_test_code = None
        for attempt in range(MAX_TEST_GENERATION_RETRIES):
            print(f"(TesterAgent Gen Log): Test code generation attempt {attempt + 1}/{MAX_TEST_GENERATION_RETRIES}...")
            animate_ui(f"{COLOR_DIM}Generating test code via LLM (Attempt {attempt+1})...{COLOR_RESET}", duration=3.0, interval=0.2)
            raw_response = self.code_generator.generate_code_native(formatted_prompt)
            clear_line_ui()

            if raw_response is None:
                print(f"Error (Attempt {attempt+1}): Generator returned no response from LLM. Stopping retries.")
                print_ui(f"{COLOR_YELLOW}(Tester): LLM failed to provide test code (Attempt {attempt+1}).{COLOR_RESET}")
                final_test_code = None
                break # Exit the retry loop

            print(f"(TesterAgent Gen Log - Attempt {attempt+1}): Extracting/Cleaning test code from response...")
            # Use the same extractor, relying on the new markers [[[BEGIN_TEST_FILE...]]]
            extracted_code = self.code_generator.extract_code(raw_response)

            if extracted_code:
                print(f"(TesterAgent Gen Log - Attempt {attempt+1}): Test code extracted successfully.")
                final_test_code = extracted_code
                break # Exit the retry loop on success
            else:
                print(f"Error (Attempt {attempt+1}): Failed to extract test code from LLM response.")
                if attempt < MAX_TEST_GENERATION_RETRIES - 1:
                    print("(TesterAgent Gen Log): Retrying after a short delay...")
                    print_ui(f"{COLOR_YELLOW}(Tester): Test code extraction failed (Attempt {attempt+1}). Retrying...{COLOR_RESET}")
                    time.sleep(2) # Wait before retrying
                else:
                    print(f"Error: Test code extraction failed after {MAX_TEST_GENERATION_RETRIES} attempts.")
                    print_ui(f"{COLOR_YELLOW}(Tester): Test code extraction failed after {MAX_TEST_GENERATION_RETRIES} attempts.{COLOR_RESET}")
                    # Optionally save the raw response for debugging
                    # self._save_test_code(raw_response, target_test_script_full_path + f".raw_llm_error_attempt_{attempt+1}")
                    final_test_code = None

        # --- AFTER RETRY LOOP ---
        if final_test_code is None:
            return None, "Tester Agent Error: Failed to generate/extract test code after retries.", None # Indicate overall failure

        # --- Proceed with successful code ---
        print("(TesterAgent Gen Log): Performing basic syntax check on generated test code...")
        # Basic check: does it compile? (Won't catch unittest logic errors)
        syntax_ok = False
        try:
             compile(final_test_code, test_file_name, 'exec')
             syntax_ok = True
             print("(TesterAgent Log): Test code basic syntax check PASSED.")
        except SyntaxError as se:
             print(f"{COLOR_YELLOW}ERROR: Test code syntax error:{COLOR_RESET}\n{se}")
             print_ui(f"{COLOR_YELLOW}(Tester): Generated test code has syntax errors.{COLOR_RESET}")
             # Save the erroneous code for debugging
             self._save_test_code(final_test_code, target_test_script_full_path + ".syntax_error")
             return None, f"Tester Agent Error: Generated test code syntax error:\n{se}", None
        except Exception as ce:
             print(f"{COLOR_YELLOW}ERROR: Test code compile check failed:{COLOR_RESET}\n{ce}")
             print_ui(f"{COLOR_YELLOW}(Tester): Generated test code failed compilation.{COLOR_RESET}")
             self._save_test_code(final_test_code, target_test_script_full_path + ".compile_error")
             return None, f"Tester Agent Error: Generated test code compilation error:\n{ce}", None


        if syntax_ok:
            if self._save_test_code(final_test_code, target_test_script_full_path):
                print(f"{COLOR_GREEN}(TesterAgent): Test code generation successful for '{test_file_name}'.{COLOR_RESET}")
                print_ui(f"{COLOR_GREEN}(Tester): Tests generated for {script_name}. Running...{COLOR_RESET}")

                # --- Run the generated tests ---
                test_passed, test_report = self._run_tests(project_folder_path, test_file_name)
                # -------------------------------

                if test_passed:
                    print_ui(f"{COLOR_GREEN}(Tester): Automated tests PASSED.{COLOR_RESET}")
                else:
                    print_ui(f"{COLOR_YELLOW}(Tester): Automated tests FAILED or ERRORED.{COLOR_RESET}")
                    print(f"{COLOR_YELLOW}--- Test Failure Report (Summary) ---\n{test_report}\n-----------------------------------{COLOR_RESET}") # Log full report

                return test_passed, test_report, target_test_script_full_path
            else:
                print(f"Error: Failed saving generated test code to {target_test_script_full_path}.")
                print_ui(f"{COLOR_YELLOW}(Tester): Failed to save generated tests.{COLOR_RESET}")
                return None, "Tester Agent Error: Failed to save generated test code.", None

        # This part should theoretically not be reached if syntax check handles errors
        return None, "Tester Agent Error: Unknown error after syntax check.", None


    # --- Optional: Refinement Method (Similar structure if needed) ---
    # def execute_test_refinement(self, current_test_code: str, blueprint_text: str,
    #                             user_feedback: str, error_context: str | None,
    #                             test_script_path: str) -> tuple[bool | None, str | None]:
    #     # ... (Implementation similar to Developer's refinement, using refiner prompt)
    #     # ... call self.code_generator.generate_code_native
    #     # ... call self.code_generator.extract_code
    #     # ... call self._save_test_code
    #     # ... call self._run_tests
    #     # ... return test_passed, test_report
    #     print("Warning: Test refinement not fully implemented yet.")
    #     return None, "Refinement not implemented"

# --- END of TesterAgent Class ---