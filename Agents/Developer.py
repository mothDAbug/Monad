# Agents/Developer.py
import sys
import os
import json
from dotenv import load_dotenv
import traceback
import time # Needed for retry delay
import re
import datetime
import google.generativeai as genai

# --- Import Utils (Essential) ---
try:
    # Ensure project root is in path for utils and other agents
    project_root_dir_utils = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root_dir_utils not in sys.path:
        sys.path.insert(0, project_root_dir_utils)

    import utils
    from utils import print_ui, animate_ui, clear_line_ui
    from utils import COLOR_RESET, COLOR_DIM, COLOR_YELLOW, COLOR_GREEN, COLOR_MAGENTA

    # Try to get the artifacts directory name consistently
    try:
        from Agents.Analyst import OUTPUT_DIR as ARTIFACTS_DIR_NAME
    except (ImportError, AttributeError):
        ARTIFACTS_DIR_NAME = "artifacts"
        print(f"Warning (DeveloperAgent): Could not determine artifacts dir from Analyst. Defaulting to '{ARTIFACTS_DIR_NAME}'.")

except ImportError:
     print("FATAL Error (DeveloperAgent): Could not import utils. UI and logging might fail.")
     def print_ui(message="", end="\n", flush=False): print(message, end=end, flush=flush)
     def animate_ui(base_message, duration=2.0, interval=0.15): print(f"{base_message}...")
     def clear_line_ui(): pass
     COLOR_RESET=COLOR_DIM=COLOR_YELLOW=COLOR_GREEN=COLOR_MAGENTA=""; ARTIFACTS_DIR_NAME = "artifacts"
# --------------------------------------------------------

# --- Helper function to load prompts ---
def load_prompt_template(file_path_relative: str) -> str | None:
    """Loads a prompt template string from a file relative to the project root."""
    try:
        _project_root = project_root_dir_utils
        full_path = os.path.normpath(os.path.join(_project_root, file_path_relative))
        if os.path.exists(full_path) and os.path.isfile(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            print(f"Error (Developer Prompt Loader): Prompt file not found or is not a file: {full_path}")
            return None
    except NameError:
        print(f"Error (Developer Prompt Loader): Project root directory not defined. Cannot load prompt '{file_path_relative}'.")
        return None
    except Exception as e:
        print(f"Error reading prompt '{file_path_relative}': {e}"); traceback.print_exc(); return None
# --------------------------------------------------------

# --- Configuration ---
PROMPTS_DIR = ".sysprompts"
DEVELOPER_GENERATOR_PROMPT_FILE = os.path.join(PROMPTS_DIR, "developer_code_generator.prompt")
DEVELOPER_REFINER_PROMPT_FILE = os.path.join(PROMPTS_DIR, "developer_code_refiner.prompt")
DEFAULT_USER_STORIES_FILENAME = "user_stories_output.json"
MAX_CODE_GENERATION_RETRIES = 3 # Total attempts including the first one

# --- Marker Definitions ---
# NEW Markers for Generator Prompt
GENERATOR_CODE_START_MARKER_PATTERN = r"\[\[\[BEGIN_FILE:.*?\]\]\]" # Regex pattern
GENERATOR_CODE_END_MARKER_PATTERN = r"\[\[\[END_FILE:.*?\]\]\]"     # Regex pattern

# OLD Markers (kept for Refiner Prompt compatibility)
REFINER_CODE_START_MARKER = "<<<<<python>>>>>"
REFINER_CODE_END_MARKER = "<<<<<\\/python>>>>>" # Use forward slash as in original

# === Native Gemini Code Generator Component (Worker) ===
# NativeCodeGenerator class remains the same as the previous version you provided
# It correctly handles API calls and extraction based on multiple marker types.
class NativeCodeGenerator:
    """Handles direct interaction with Gemini API and robust code extraction using various marker formats."""
    def __init__(self):
        print("(NativeCodeGenerator Log): Initializing...")
        self.model = None
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            print("FATAL Error (NativeCodeGenerator): GOOGLE_API_KEY not found.")
        else:
            try:
                genai.configure(api_key=self.api_key)
                model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")
                # Use temperature specified in previous version or adjust if needed
                self.model = genai.GenerativeModel(model_name, generation_config={"temperature": 0.3})
                print(f"(NativeCodeGenerator Log): Native Gemini Model ({self.model.model_name}) Ready.")
            except Exception as e:
                print(f"Error (NativeCodeGenerator) init: {e}"); traceback.print_exc(); self.model = None

    def generate_code_native(self, formatted_prompt: str) -> str | None:
        """Calls Gemini API, logs prompt/response, returns raw text response or None on error."""
        if not self.model:
            print("Error (NativeCodeGenerator): Model not ready.")
            return None
        try:
            if not isinstance(formatted_prompt, str):
                print(f"Error: Prompt must be string, got {type(formatted_prompt)}.")
                return None

            # === Log the prompt being sent ===
            print("\n" + "="*20 + " PROMPT SENT TO GEMINI " + "="*20)
            print(formatted_prompt)
            print("="*20 + " END OF PROMPT SENT TO GEMINI " + "="*20 + "\n")
            # ================================

            # Increase timeout slightly? Maybe not needed if issue is token limit.
            # Consider adding request_options={'timeout': 600} if needed
            response = self.model.generate_content(formatted_prompt)

            # === Log the raw response ===
            raw_response_text = None
            # Standard way to access text in google.generativeai response
            try:
                 raw_response_text = response.text
            except ValueError: # Handle cases where response is blocked (no .text attribute)
                 print("Warning: Could not directly access response.text (potentially blocked). Checking candidates...")
                 if response.candidates and hasattr(response.candidates[0], 'content') and hasattr(response.candidates[0].content, 'parts') and response.candidates[0].content.parts:
                      raw_response_text = response.candidates[0].content.parts[0].text
                 else:
                      print("Error: No valid candidates or parts found after block/error.")

            print("\n" + "+"*20 + " RAW RESPONSE FROM GEMINI " + "+"*20)
            if raw_response_text is not None: # Check if we got text
                print(raw_response_text)
            else:
                print("(No text content found in response)")
                if hasattr(response, 'prompt_feedback'):
                     if response.prompt_feedback.block_reason:
                          print(f"Block Reason: {response.prompt_feedback.block_reason}")
                     if response.prompt_feedback.safety_ratings:
                          print(f"Safety Ratings: {response.prompt_feedback.safety_ratings}")
                # Log the full response object if text extraction failed
                print("\n--- Full Response Object (Debug) ---")
                try:
                    print(response)
                except Exception as print_e:
                    print(f"Could not print full response object: {print_e}")
                print("------------------------------------")

            print("+"*20 + " END OF RAW RESPONSE FROM GEMINI " + "+"*20 + "\n")
            # ===========================

            if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                print(f"Error: API call blocked ({response.prompt_feedback.block_reason})");
                return None # Explicitly return None if blocked

            # Return the text if available, otherwise None
            return raw_response_text if raw_response_text is not None else None

        except Exception as e:
            # Catch potential DeadlineExceeded or other API errors
            print(f"Error (NativeCodeGenerator) API call: {e}"); traceback.print_exc(); return None

    def extract_code(self, raw_text: str) -> str | None:
        """
        Extracts code using multiple marker strategies and fallbacks.
        Prioritizes NEW generator markers, then OLD refiner markers, then markdown.
        """
        if not raw_text or not isinstance(raw_text, str):
            print("(Extractor Log): Invalid or empty text received.")
            return None

        extracted_code = None
        raw_text_stripped = raw_text.strip()
        strategy_used = "None"

        # 1. Try NEW Generator Markers first (`[[[BEGIN_FILE...]]]` / `[[[END_FILE...]]]`)
        start_marker_re = re.escape("[[[BEGIN_FILE:") + r".*?" + re.escape("]]]")
        end_marker_re = re.escape("[[[END_FILE:") + r".*?" + re.escape("]]]")
        generator_match = re.search(f"{start_marker_re}(.*?){end_marker_re}", raw_text_stripped, re.DOTALL)

        if generator_match:
            extracted_code = generator_match.group(1).strip()
            strategy_used = "New Generator Markers"
            print(f"(Extractor Log): Extracted code via {strategy_used}.")
        else:
            # 2. Try OLD Refiner Markers (`<<<<<python>>>>>` / `<<<<<\\/python>>>>>`)
            print("(Extractor Log): New generator markers not found. Trying old refiner markers...")
            start_marker_re_old = re.escape(REFINER_CODE_START_MARKER)
            end_marker_re_old = re.escape(REFINER_CODE_END_MARKER)
            refiner_match = re.search(f"{start_marker_re_old}(.*?){end_marker_re_old}", raw_text_stripped, re.DOTALL)

            if refiner_match:
                extracted_code = refiner_match.group(1).strip()
                strategy_used = "Old Refiner Markers"
                print(f"(Extractor Log): Extracted code via {strategy_used}.")
            else:
                # 3. Fallback: Try markdown
                print("(Extractor Log): Old refiner markers not found. Trying markdown block fallback...")
                markdown_match = re.search(r"```(?:python|powershell|py|ps1)?\s*\n(.*?)\n```", raw_text_stripped, re.DOTALL | re.IGNORECASE)
                if markdown_match:
                    extracted_code = markdown_match.group(1).strip()
                    strategy_used = "Markdown Fallback"
                    print(f"(Extractor Log): Extracted code via {strategy_used}.")
                else:
                    # 4. Final fallback: Check if the whole thing looks like code
                    print("(Extractor Log): Markdown block not found. Checking if entire response is code...")
                    looks_like_code = (
                        raw_text_stripped.startswith(('import ', 'def ', '#', 'import\n', 'def\n', '#\n', '$')) and
                        "Here's the code" not in raw_text_stripped[:100].lower() and
                        "[[[BEGIN_FILE:" not in raw_text_stripped and
                        REFINER_CODE_START_MARKER not in raw_text_stripped and
                        "```" not in raw_text_stripped
                    )
                    if looks_like_code:
                        print("(Extractor Log): Assuming entire stripped response is code (final fallback).")
                        extracted_code = raw_text_stripped
                        strategy_used = "Raw Code Fallback"
                    else:
                        # Check specifically if only the BEGIN marker was found (common truncation case)
                        if re.search(start_marker_re, raw_text_stripped, re.DOTALL):
                            print("Error (Extractor Log): Found BEGIN marker but no corresponding END marker. Likely truncated response.")
                        else:
                             print("Error (Extractor Log): Code extraction failed. No clear markers or code structure found.")
                        return None # Failed extraction

        # --- Cleaning (Applied AFTER extraction attempt) ---
        if extracted_code:
            if extracted_code.startswith('\ufeff'):
                extracted_code = extracted_code[1:]
                print("(Extractor Clean): Removed BOM.")

            lines = extracted_code.splitlines()
            cleaned_lines = []
            marker_patterns_to_remove = [
                r"\[\[\[BEGIN_FILE:.*?\]\]\]",
                r"\[\[\[END_FILE:.*?\]\]\]",
                re.escape(REFINER_CODE_START_MARKER),
                re.escape(REFINER_CODE_END_MARKER),
                r"```(?:python|powershell|py|ps1)?",
                r"```"
            ]
            combined_pattern = re.compile(r"^\s*(" + "|".join(marker_patterns_to_remove) + r")\s*$")

            for line in lines:
                if not combined_pattern.match(line):
                    cleaned_lines.append(line)
                else:
                    print(f"(Extractor Clean): Removed stray marker/fence line: '{line.strip()}'")
            extracted_code = "\n".join(cleaned_lines).strip()

        return extracted_code if extracted_code else None

# === Developer Agent (Manager using Native Generator) ===
class DeveloperAgent:
    """
    Orchestrates code generation/refinement using NativeCodeGenerator.
    Uses appropriate prompts and extraction strategies, includes retry logic.
    """
    def __init__(self, original_stdout_handle=None):
        print("(DeveloperAgent Log): Initializing Manager Agent...")
        if original_stdout_handle: utils.original_stdout = original_stdout_handle
        load_dotenv()
        self.project_root = project_root_dir_utils # Store project root
        self.code_generator = NativeCodeGenerator()
        if not self.code_generator.model:
            print("CRITICAL Warning: Native Generator model failed init.")

        # Load prompts - assumes the file content at DEVELOPER_GENERATOR_PROMPT_FILE has been updated
        self.generator_template_str = load_prompt_template(DEVELOPER_GENERATOR_PROMPT_FILE)
        self.refiner_template_str = load_prompt_template(DEVELOPER_REFINER_PROMPT_FILE)

        if not self.generator_template_str: print(f"FATAL Error: Missing GENERATOR prompt ({DEVELOPER_GENERATOR_PROMPT_FILE}).")
        if not self.refiner_template_str: print(f"FATAL Error: Missing REFINER prompt ({DEVELOPER_REFINER_PROMPT_FILE}).")
        print("(DeveloperAgent Log): Manager Agent Init complete.")

    def _save_code(self, code_content: str, script_path: str) -> bool:
        # (Keep _save_code as previously implemented)
        if not script_path or code_content is None:
            print(f"Error (Save): Invalid path or content provided for saving.")
            return False
        try:
            script_dir = os.path.dirname(script_path)
            if script_dir: # Ensure directory exists only if it's not the root
                os.makedirs(script_dir, exist_ok=True)
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(code_content)
            print(f"(DevAgent Log): Code saved successfully to {script_path}.")
            return True
        except Exception as e:
            print(f"Error (Save): Failed to save code to {script_path}: {e}"); traceback.print_exc()
            return False

    def _read_template_files(self, rag_match_info: dict | None) -> tuple[str, str]:
        # (Keep _read_template_files as previously implemented)
        template_code = "(No relevant template code found or provided)"
        template_readme = "(README content intentionally omitted from prompt)" # Explicit placeholder
        if not rag_match_info or not isinstance(rag_match_info, dict):
            return template_code, template_readme

        code_rel_path = rag_match_info.get('code_template')
        if code_rel_path and code_rel_path != 'N/A':
            code_abs = os.path.normpath(os.path.join(self.project_root, code_rel_path))
            if os.path.isfile(code_abs):
                try:
                    with open(code_abs, 'r', encoding='utf-8', errors='ignore') as f:
                        template_code = f.read()
                except Exception as e:
                    print(f"Warn (Read): Failed read code template '{code_abs}': {e}")
            else:
                print(f"Warn (Read): Template code file not found: {code_abs}")
        else:
            print("(DevAgent Log): No valid code template path in RAG info.")

        print("(DevAgent Log): Skipping README read for prompt context.")
        return template_code, template_readme

    def _load_and_filter_developer_stories(self, user_stories_json_path: str | None) -> str:
        # (Keep _load_and_filter_developer_stories as previously implemented)
        if not user_stories_json_path:
            default_path = os.path.join(self.project_root, ARTIFACTS_DIR_NAME, DEFAULT_USER_STORIES_FILENAME)
            user_stories_json_path = default_path
            print(f"(DevAgent Log): No stories path provided, defaulting to: {user_stories_json_path}")
        else:
             if not os.path.isabs(user_stories_json_path):
                 user_stories_json_path = os.path.normpath(os.path.join(self.project_root, user_stories_json_path))

        if not os.path.isfile(user_stories_json_path):
            print(f"Error: Stories JSON file not found: {user_stories_json_path}")
            return "(Stories file not found)"

        print(f"(DevAgent Log): Reading and filtering stories from: {user_stories_json_path}")
        try:
            with open(user_stories_json_path, 'r', encoding='utf-8') as f:
                all_stories = json.load(f)
        except json.JSONDecodeError as json_e:
             print(f"Error parsing stories JSON: {json_e}")
             return f"(Error parsing stories JSON: {json_e})"
        except Exception as e:
            print(f"Error reading stories JSON: {e}")
            return "(Error loading stories file)"

        if not isinstance(all_stories, list):
            print(f"Error: Stories JSON content is not a list (type: {type(all_stories)}).")
            return "(Invalid stories format - not a list)"

        developer_tasks = []
        for i, story in enumerate(all_stories):
            if not isinstance(story, dict):
                print(f"Warning: Skipping non-dict item in stories list at index {i}")
                continue

            role = story.get("role", "").strip().lower()
            if role == "developer":
                action = story.get("action", "").strip()
                user_story_text = story.get("user_story", "").strip()

                if action:
                    developer_tasks.append(action)
                elif user_story_text:
                    developer_tasks.append(user_story_text)
                else:
                    print(f"Warning: Developer story at index {i} has no 'action' or 'user_story' text.")

        if not developer_tasks:
            print("(DevAgent Log): No specific tasks found for the 'Developer' role in stories.")
            return "(No developer tasks extracted)"

        formatted_tasks = "\n".join([f"{idx + 1}. {task}" for idx, task in enumerate(developer_tasks)])
        print(f"(DevAgent Log): Extracted {len(developer_tasks)} developer tasks.")
        return formatted_tasks

    def _perform_syntax_check(self, code_to_check: str | None, script_name_for_check: str) -> bool:
        # (Keep _perform_syntax_check as previously implemented)
        if not code_to_check:
            print("Error (Syntax Check): Cannot check None or empty code.")
            return False

        print(f"(DevAgent Log): Performing syntax check for {script_name_for_check}...")
        language = None
        if script_name_for_check.lower().endswith(".py"): language = "Python"
        elif script_name_for_check.lower().endswith(".ps1"): language = "PowerShell"
        else: language = "Unknown"

        if language == "Python":
            try:
                compile(code_to_check, script_name_for_check, 'exec')
                print("(DevAgent Log): Python syntax check PASSED.")
                return True
            except SyntaxError as se:
                print(f"{COLOR_YELLOW}ERROR: Python syntax error:{COLOR_RESET}\n{se}")
                return False
            except Exception as ce:
                print(f"{COLOR_YELLOW}ERROR: Python compile check failed:{COLOR_RESET}\n{ce}")
                return False
        elif language == "PowerShell":
            print("Warning (Syntax Check): PowerShell syntax check is currently skipped.")
            return True
        else:
            print(f"Warning (Syntax Check): Syntax check skipped for unknown language script: {script_name_for_check}.")
            return True

    # --- Main Orchestration Methods with RETRY Logic ---

    def execute_code_generation(self, blueprint_text: str, libraries: list[str], script_name: str,
                                project_folder_path: str, rag_match_info: dict | None,
                                user_stories_json_path: str | None) -> str | None:
        """Orchestrates code generation with retry logic for extraction failures."""
        print(f"{COLOR_MAGENTA}--- Developer Agent: Starting Code Generation for '{script_name}' ---{COLOR_RESET}")
        if not self.code_generator or not self.code_generator.model or not self.generator_template_str:
            print("Error: DevAgent not ready (Generator/Model/Generator Prompt missing).")
            return None
        if not all([blueprint_text, script_name, project_folder_path]):
            print("Error: Missing critical context: blueprint, script_name, or project_folder_path.")
            return None

        target_script_full_path = os.path.normpath(os.path.join(project_folder_path, script_name))
        print(f"(DevAgent Gen Log): Target script path: {target_script_full_path}")

        print("(DevAgent Gen Log): Preparing context for generation prompt...")
        template_code, template_readme = self._read_template_files(rag_match_info)
        developer_actions_text = self._load_and_filter_developer_stories(user_stories_json_path)
        formatted_prompt = None
        try:
            # (Prompt formatting logic remains the same)
            safe_blueprint = blueprint_text.replace('{', '{{').replace('}', '}}')
            safe_template_code = template_code.replace('{', '{{').replace('}', '}}')
            safe_template_readme = template_readme.replace('{', '{{').replace('}', '}}')
            safe_actions_text = developer_actions_text.replace('{', '{{').replace('}', '}}')
            formatted_prompt = self.generator_template_str.format(
                 blueprint_text=safe_blueprint, libraries=", ".join(libraries) if libraries else "(None)",
                 script_name=script_name, template_code_content=safe_template_code,
                 template_readme_content=safe_template_readme, developer_user_stories_text=safe_actions_text
             )
            print("(DevAgent Gen Log): Generation prompt formatted.")
        except KeyError as ke:
             print(f"Error formatting prompt: Missing key {ke}. Check prompt template variables."); traceback.print_exc(); return None
        except Exception as e_fmt:
            print(f"Error formatting prompt: {e_fmt}"); traceback.print_exc(); return None

        if not formatted_prompt:
            print("Error: Formatted prompt is empty after formatting attempt."); return None

        # --- RETRY LOOP ---
        final_code = None
        for attempt in range(MAX_CODE_GENERATION_RETRIES):
            print(f"(DevAgent Gen Log): Code generation attempt {attempt + 1}/{MAX_CODE_GENERATION_RETRIES}...")
            animate_ui(f"{COLOR_DIM}Generating code via LLM (Attempt {attempt+1})...{COLOR_RESET}", duration=3.0, interval=0.2)
            raw_response = self.code_generator.generate_code_native(formatted_prompt)
            clear_line_ui()

            if raw_response is None:
                # API call itself failed (e.g., blocked, network error, timeout) - No point retrying this specific prompt
                print(f"Error (Attempt {attempt+1}): Generator returned no response from LLM. Stopping retries.")
                print_ui(f"{COLOR_YELLOW}(Dev): LLM failed to provide a response (Attempt {attempt+1}).{COLOR_RESET}")
                final_code = None # Ensure final_code is None
                break # Exit the retry loop

            print(f"(DevAgent Gen Log - Attempt {attempt+1}): Extracting/Cleaning code from response...")
            extracted_code = self.code_generator.extract_code(raw_response)

            if extracted_code:
                print(f"(DevAgent Gen Log - Attempt {attempt+1}): Code extracted successfully.")
                final_code = extracted_code
                break # Exit the retry loop on success
            else:
                # Extraction failed, likely due to truncation/missing markers
                print(f"Error (Attempt {attempt+1}): Failed to extract code from LLM response.")
                if attempt < MAX_CODE_GENERATION_RETRIES - 1:
                    print("(DevAgent Gen Log): Retrying after a short delay...")
                    print_ui(f"{COLOR_YELLOW}(Dev): Code extraction failed (Attempt {attempt+1}). Retrying...{COLOR_RESET}")
                    time.sleep(2) # Wait 2 seconds before retrying
                else:
                    # Last attempt failed
                    print(f"Error: Code extraction failed after {MAX_CODE_GENERATION_RETRIES} attempts.")
                    print_ui(f"{COLOR_YELLOW}(Dev): Code extraction failed after {MAX_CODE_GENERATION_RETRIES} attempts. LLM response might be malformed.{COLOR_RESET}")
                    # Optionally save the last raw response for debugging
                    # self._save_code(raw_response, target_script_full_path + f".raw_llm_error_attempt_{attempt+1}")
                    final_code = None # Ensure final_code is None

        # --- AFTER RETRY LOOP ---
        if final_code is None:
            # Handles both API failure and extraction failure after all retries
            return None # Indicate overall generation failure

        # --- Proceed with successful code ---
        if self._perform_syntax_check(final_code, script_name):
            if self._save_code(final_code, target_script_full_path):
                print(f"{COLOR_GREEN}(DevAgent): Code generation successful for '{script_name}'.{COLOR_RESET}")
                print_ui(f"{COLOR_GREEN}(Dev): Code generated successfully for {script_name}.{COLOR_RESET}")
                return final_code # Return the generated code on success
            else:
                print(f"Error: Failed saving generated code to {target_script_full_path}.")
                print_ui(f"{COLOR_YELLOW}(Dev): Failed to save generated code.{COLOR_RESET}")
                return None
        else:
            print("Error: Generated code failed syntax check.")
            print_ui(f"{COLOR_YELLOW}(Dev): Generated code has syntax errors.{COLOR_RESET}")
            self._save_code(final_code, target_script_full_path + ".syntax_error")
            return None

    def execute_code_refinement(self, current_code: str, blueprint_text: str, user_feedback: str,
                                error_context: str | None, script_path: str ) -> str | None:
        """Orchestrates code refinement with retry logic for extraction failures."""
        script_name = os.path.basename(script_path)
        print(f"{COLOR_MAGENTA}--- Developer Agent: Starting Code Refinement for '{script_name}' ---{COLOR_RESET}")
        if not self.code_generator or not self.code_generator.model or not self.refiner_template_str:
            print("Error: DevAgent not ready (Generator/Model/Refiner Prompt missing)."); return None
        if current_code is None or not script_path:
            print("Error: Missing current_code or script_path for refinement."); return None

        print("(DevAgent Refine Log): Formatting refinement prompt...")
        formatted_prompt = None
        try:
            # (Prompt formatting logic remains the same)
            safe_current_code = current_code.replace('{', '{{').replace('}', '}}')
            safe_blueprint = (blueprint_text or "").replace('{', '{{').replace('}', '}}')
            safe_feedback = (user_feedback or "").replace('{', '{{').replace('}', '}}')
            safe_error = (error_context or "").replace('{', '{{').replace('}', '}}')
            formatted_prompt = self.refiner_template_str.format(
                 current_code=safe_current_code, blueprint_text=safe_blueprint or "(N/A)",
                 user_feedback=safe_feedback or "(None)", error_context=safe_error or "(None)",
                 script_name=script_name
             )
        except KeyError as ke:
             print(f"Error formatting refinement prompt: Missing key {ke}."); traceback.print_exc(); return None
        except Exception as e_fmt:
            print(f"Error formatting refinement prompt: {e_fmt}"); traceback.print_exc(); return None

        if not formatted_prompt:
            print("Error: Formatted refinement prompt is empty after formatting attempt."); return None

        # --- RETRY LOOP for Refinement ---
        final_code = None
        for attempt in range(MAX_CODE_GENERATION_RETRIES):
            print(f"(DevAgent Refine Log): Code refinement attempt {attempt + 1}/{MAX_CODE_GENERATION_RETRIES}...")
            animate_ui(f"{COLOR_DIM}Refining code via LLM (Attempt {attempt+1})...{COLOR_RESET}", duration=2.5, interval=0.2)
            raw_response = self.code_generator.generate_code_native(formatted_prompt)
            clear_line_ui()

            if raw_response is None:
                print(f"Error (Attempt {attempt+1}): Generator returned no response for refinement. Stopping retries.")
                print_ui(f"{COLOR_YELLOW}(Dev): LLM failed refinement response (Attempt {attempt+1}).{COLOR_RESET}")
                final_code = None
                break # Exit retry loop

            print(f"(DevAgent Refine Log - Attempt {attempt+1}): Extracting/Cleaning refined code...")
            # Use the same extractor - it will fall back to OLD markers if needed
            extracted_code = self.code_generator.extract_code(raw_response)

            if extracted_code:
                print(f"(DevAgent Refine Log - Attempt {attempt+1}): Refined code extracted successfully.")
                final_code = extracted_code
                break # Exit loop on success
            else:
                print(f"Error (Attempt {attempt+1}): Failed to extract refined code.")
                if attempt < MAX_CODE_GENERATION_RETRIES - 1:
                    print("(DevAgent Refine Log): Retrying after a short delay...")
                    print_ui(f"{COLOR_YELLOW}(Dev): Refined code extraction failed (Attempt {attempt+1}). Retrying...{COLOR_RESET}")
                    time.sleep(1) # Shorter delay for refinement maybe
                else:
                    print(f"Error: Refined code extraction failed after {MAX_CODE_GENERATION_RETRIES} attempts.")
                    print_ui(f"{COLOR_YELLOW}(Dev): Refined code extraction failed after {MAX_CODE_GENERATION_RETRIES} attempts.{COLOR_RESET}")
                    # self._save_code(raw_response, script_path + f".raw_refine_error_attempt_{attempt+1}")
                    final_code = None

        # --- AFTER RETRY LOOP for Refinement ---
        if final_code is None:
            return None # Indicate overall refinement failure

        # --- Proceed with successful refined code ---
        if final_code == current_code:
            print("Warning: Refined code is identical to the original code.")
            print_ui(f"{COLOR_DIM}(Dev): No changes detected after refinement.{COLOR_RESET}")

        if self._perform_syntax_check(final_code, script_name):
            if self._save_code(final_code, script_path): # Overwrite
                print(f"{COLOR_GREEN}(DevAgent): Code refinement successful for '{script_name}'.{COLOR_RESET}")
                print_ui(f"{COLOR_GREEN}(Dev): Code refined successfully for {script_name}.{COLOR_RESET}")
                return final_code
            else:
                print(f"Error: Failed saving refined code to {script_path}.")
                print_ui(f"{COLOR_YELLOW}(Dev): Failed saving refined code.{COLOR_RESET}")
                return None
        else:
            print("Error: Refined code failed syntax check.")
            print_ui(f"{COLOR_YELLOW}(Dev): Refined code syntax error.{COLOR_RESET}")
            self._save_code(final_code, script_path + ".refined_syntax_error")
            return None

# --- END of DeveloperAgent Class ---