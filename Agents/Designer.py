# Agents/Designer.py
import sys
import os
import re
from dotenv import load_dotenv
import traceback
import textwrap
import json
import shutil

# --- Langchain / Google Imports ---
try:
    import google.generativeai as genai
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain.prompts import PromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("Warning (DesignerAgent): Langchain/Google components not installed.")

# --- Import Utils ---
try:
    project_root_dir_utils = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root_dir_utils not in sys.path: sys.path.insert(0, project_root_dir_utils)
    import utils
    from utils import print_ui, animate_ui, clear_line_ui
    from utils import COLOR_RESET, COLOR_BOLD, COLOR_DIM, COLOR_MAGENTA, COLOR_YELLOW, COLOR_GREY, COLOR_CYAN, COLOR_GREEN
except ImportError:
     print("Warning (DesignerAgent): Could not import utils.")
     def print_ui(message="", end="\n", flush=False): print(message, end=end, flush=flush)
     def animate_ui(base_message, duration=2.0, interval=0.15): print(f"{base_message}...")
     def clear_line_ui(): pass
     COLOR_RESET=COLOR_BOLD=COLOR_DIM=COLOR_MAGENTA=COLOR_YELLOW=COLOR_GREY=COLOR_CYAN=COLOR_GREEN=""
# ------------------

# --- Helper function to load prompts ---
def load_prompt_template(file_path_relative: str) -> str | None:
    try:
        _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.normpath(os.path.join(_project_root, file_path_relative))
        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8') as f: return f.read()
        else: print(f"Error (Designer Prompt Loader): Prompt file not found: {full_path}"); return None
    except Exception as e: print(f"Error reading prompt '{file_path_relative}': {e}"); return None
# --------------------------------------------------------


# --- Configuration ---
PROMPTS_DIR = ".sysprompts"
# IMPORTANT: Ensure these files contain the OLD prompt versions that generate "Script:"
DESIGNER_GENERATOR_PROMPT_FILE = os.path.join(PROMPTS_DIR, "designer_blueprint_generator.prompt")
DESIGNER_REFINER_PROMPT_FILE = os.path.join(PROMPTS_DIR, "designer_blueprint_refiner.prompt")
README_TEMPLATE_PATH = os.path.join(PROMPTS_DIR, "readme_template.prompt")
TEMPLATES_JSON_PATH_RELATIVE = "templates.json"
CODE_EXEMPLARS_DIR = "code_exemplars"
AGENTIC_PROJECTS_DIR = "AgenticProjects" # Base dir for generated projects

# --- Constants for Scaffolding ---
PYTHON_BUILTINS = {
    'python', 'os', 'sys', 'json', 'math', 'datetime', 're',
    'shutil', 'sqlite3', 'csv', 'hashlib', 'argparse', 'random',
    'collections', 'itertools', 'functools', 'typing', 'time',
    'logging', 'traceback', 'subprocess', 'multiprocessing', 'threading'
}
SPECIAL_FILES = {"requirements.txt", "readme.md", ".env", ".env.example"}
SKIP_EXTENSIONS = {".db", ".sqlite", ".sqlite3", ".pyc", ".log", ".cache", ".py", ".ps1"}
SKIP_DIRS = {"__pycache__", ".git", ".idea", ".vscode", "venv"}
# ---------------------------------


class DesignerAgent:
    def __init__(self, original_stdout_handle=None):
        print("(DesignerAgent Log): Initializing...")
        if original_stdout_handle: utils.original_stdout = original_stdout_handle
        load_dotenv()
        self.llm = None
        # Load prompts (assuming these files now contain the older versions)
        self.generator_template_str = load_prompt_template(DESIGNER_GENERATOR_PROMPT_FILE)
        self.refiner_template_str = load_prompt_template(DESIGNER_REFINER_PROMPT_FILE)
        self.readme_template_str = load_prompt_template(README_TEMPLATE_PATH) # Load readme template

        if not self.generator_template_str: print(f"FATAL Error: Could not load GENERATOR prompt: {DESIGNER_GENERATOR_PROMPT_FILE}.")
        if not self.refiner_template_str: print(f"FATAL Error: Could not load REFINER prompt: {DESIGNER_REFINER_PROMPT_FILE}.")
        if not self.readme_template_str: print(f"Warning: Could not load README template: {README_TEMPLATE_PATH}.")

        self.templates_data = self._load_templates_json()

        # Store last generated paths/names for handoff
        self._last_project_path = None
        self._last_script_name = None

        if LANGCHAIN_AVAILABLE:
            google_api_key = os.getenv("GOOGLE_API_KEY")
            if not google_api_key: print("Warning: GOOGLE_API_KEY not found.")
            else:
                model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")
                print(f"(Log): LLM init model: {model_name}")
                try:
                    genai.configure(api_key=google_api_key)
                    self.llm = ChatGoogleGenerativeAI(model=model_name, temperature=0.4, convert_system_message_to_human=True)
                    print("(Log): LLM Initialized.")
                except Exception as e: print(f"Error init LLM '{model_name}': {e}"); self.llm = None
        else: print("(Log): Langchain not available."); self.llm = None
        print("(Log): Designer Init complete.")

    def _load_templates_json(self) -> list | None:
        # (Method unchanged)
        try:
            project_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            full_path = os.path.normpath(os.path.join(project_root_dir, TEMPLATES_JSON_PATH_RELATIVE))
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f: return json.load(f)
            else: print(f"Error: {TEMPLATES_JSON_PATH_RELATIVE} not found: '{full_path}'."); return None
        except Exception as e: print(f"Error reading {TEMPLATES_JSON_PATH_RELATIVE}: {e}"); return None

    def _read_code_files(self, file_paths: list[str]) -> str:
        # (Method unchanged)
        all_code_content = []
        project_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if not file_paths: return "(No code template paths provided)"
        print(f"(Designer Log): Reading code from {len(file_paths)} path(s).")
        for file_path in file_paths:
            if not file_path or not isinstance(file_path, str) or file_path == 'N/A': continue
            abs_path = os.path.normpath(os.path.join(project_root_dir, file_path)) if not os.path.isabs(file_path) else file_path
            if not os.path.exists(abs_path):
                print(f"Warning (Designer Log): Code template file not found: {abs_path}")
                continue
            try:
                with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                all_code_content.append(f"\n--- Start File: {os.path.basename(abs_path)} ---\n")
                all_code_content.append(content)
                all_code_content.append(f"\n--- End File: {os.path.basename(abs_path)} ---")
            except Exception as e:
                print(f"Error (Designer Log): Failed reading code file '{abs_path}': {e}")
        result = "\n".join(all_code_content) if all_code_content else "(No valid code content read)"
        print(f"(Designer Log): Total code content length read: {len(result)}")
        return result

    def _format_stories_for_prompt(self, user_stories: list[dict]) -> str:
        # (Method unchanged)
        if not user_stories: return "(No user stories provided)"
        return "\n".join([
            f"{i+1}. {story.get('user_story', f'As a {story.get("role","User")}, I want {story.get("action","...")}, so that {story.get("benefit","...")}')}"
            for i, story in enumerate(user_stories)
        ])

    def generate_cli_design(self, user_stories: list[dict], requirements_text: str, rag_match_info: dict | None ) -> tuple[str | None, list[str]]:
        # (Method unchanged)
        print("(Designer Log): Starting CLI design generation...")
        if not self.llm or not self.generator_template_str:
            print("Error (Designer): LLM or Generator Template missing."); return None, []
        if not user_stories:
             print("Error (Designer): User stories are required for design generation."); return None, []

        required_libraries = []
        code_content = "(Code content from template N/A)"
        required_libraries_text = "(Initial libraries N/A)"

        if rag_match_info:
            template_code_path = rag_match_info.get('code_template')
            template_id = rag_match_info.get('template_id')
            group_id = rag_match_info.get('group_id')

            if template_code_path and template_code_path != 'N/A':
                code_content = self._read_code_files([template_code_path]) # Pass as list

            if template_id and self.templates_data:
                print(f"(Designer Log): Searching templates.json for {group_id}/{template_id} libraries...")
                for group in self.templates_data:
                    if group_id and group.get('template_group_id') != group_id: continue
                    for template in group.get('templates', []):
                        if template.get('project_id') == template_id:
                            required_libraries = template.get('required_libraries', [])
                            print(f"(Designer Log): Found initial libraries: {required_libraries}")
                            break
                    if required_libraries: break
            required_libraries_text = ", ".join(required_libraries) if required_libraries else "(None defined in template)"
        else:
            print("(Designer Log): No RAG match info provided for design context.")

        user_stories_text = self._format_stories_for_prompt(user_stories)

        try:
             prompt = PromptTemplate(
                 template=self.generator_template_str,
                 input_variables=["user_stories_text", "requirements_text", "code_content", "required_libraries_text"]
             )
             chain = prompt | self.llm | StrOutputParser()
        except Exception as e:
             print(f"Error (Designer) creating generation chain: {e}"); traceback.print_exc()
             return None, required_libraries

        generated_blueprint = None
        try:
            print("(Designer Log): Invoking LLM for design generation...")
            animate_ui(f"{COLOR_DIM}Generating initial design blueprint...{COLOR_RESET}", duration=2.0, interval=0.2)
            input_data = {
                "user_stories_text": user_stories_text,
                "requirements_text": requirements_text if requirements_text else "(No specific requirements text)",
                "code_content": code_content,
                "required_libraries_text": required_libraries_text
            }
            generated_blueprint = chain.invoke(input_data)
            clear_line_ui()
            if not generated_blueprint or not generated_blueprint.strip():
                print("Warning (Designer): LLM returned an empty blueprint.")
                return None, required_libraries
            else:
                print("(Designer Log): LLM generated blueprint successfully.")
        except Exception as e:
            clear_line_ui()
            print(f"Error (Designer) during design generation LLM call: {e}"); traceback.print_exc()
            return None, required_libraries

        return generated_blueprint.strip(), required_libraries

    def refine_cli_design(self, current_design_blueprint: str, user_feedback: str) -> str | None:
        # (Method unchanged)
        print("(Designer Log): Starting design refinement...")
        if not self.llm or not self.refiner_template_str:
            print("Error (Designer): LLM or Refiner Template missing."); return None
        if not current_design_blueprint:
            print("Error (Designer): No current blueprint provided for refinement."); return None
        if not user_feedback or not user_feedback.strip():
            print("Warning (Designer): Empty feedback provided. Returning original blueprint."); return current_design_blueprint

        try:
            prompt = PromptTemplate(
                template=self.refiner_template_str,
                input_variables=["current_design_blueprint", "user_feedback"]
            )
            chain = prompt | self.llm | StrOutputParser()
        except Exception as e:
            print(f"Error (Designer) creating refinement chain: {e}"); traceback.print_exc()
            return None

        refined_blueprint = None
        try:
            print("(Designer Log): Invoking LLM for design refinement...")
            animate_ui(f"{COLOR_DIM}Refining design blueprint...{COLOR_RESET}", duration=1.5, interval=0.15)
            input_data = {
                "current_design_blueprint": current_design_blueprint,
                "user_feedback": user_feedback.strip()
            }
            refined_blueprint = chain.invoke(input_data)
            clear_line_ui()
            if not refined_blueprint or not refined_blueprint.strip():
                print("Warning (Designer): LLM returned empty refinement. Returning original.")
                return current_design_blueprint
            else:
                 print("(Designer Log): LLM refinement successful.")
        except Exception as e:
            clear_line_ui()
            print(f"Error (Designer) during refinement LLM call: {e}"); traceback.print_exc()
            return None

        return refined_blueprint.strip()

    # --- REVERTED: Project Scaffolding Creation Method (Uses "Script:") ---
    def create_project_scaffold(self, blueprint_text: str, final_approved_libraries: list[str], rag_match_info: dict | None) -> bool:
        """
        Creates the project directory structure. Returns True on success, False on failure.
        Stores the created project path and script name internally for handoff.
        EXPECTS 'Script:' line in blueprint_text.
        """
        print("(DesignerAgent Log): Starting detailed project scaffold creation...")
        self._last_project_path = None # Reset internal state
        self._last_script_name = None  # Reset internal state

        # --- Input Validation ---
        if not blueprint_text: print("Error Log: Blueprint missing."); print_ui(f"{COLOR_YELLOW}(DesignerAgent): Blueprint missing.{COLOR_RESET}"); return False
        if not rag_match_info or not rag_match_info.get('code_template'): print("Error Log: RAG info missing."); print_ui(f"{COLOR_YELLOW}(DesignerAgent): Template path missing.{COLOR_RESET}"); return False

        script_name_final = None
        destination_project_dir = None
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Define project root early

        # --- 1. Extract Final Script Name (using REVERTED Regex) ---
        try:
            # This regex looks for "Script:" at the beginning of a line
            match = re.search(r"^\s*Script:\s*[`'\"]?(\S+\.(?:py|ps1))[`'\"]?\s*$", blueprint_text, re.MULTILINE | re.IGNORECASE)
            if match:
                script_name_final = match.group(1).strip()
                print(f"(Designer Log): Extracted Script Name: '{script_name_final}' using 'Script:' pattern.")
            else:
                print("Error Log: Cannot extract final script name using 'Script:' pattern.")
                 # --- Log blueprint snippet for debugging ---
                print("--- Blueprint Snippet (for script name debug) ---")
                print(blueprint_text[:500] + "\n...") # Log first 500 chars
                print("---------------------------------------------")
                # --- End Log ---
                print_ui(f"{COLOR_YELLOW}(DesignerAgent): Cannot find 'Script:' line in the blueprint.{COLOR_RESET}")
                return False # Stop if script name extraction fails
        except Exception as regex_e:
            print(f"Error Log: Regex error script name: {regex_e}"); traceback.print_exc()
            return False
        print(f"(Designer Log): Final script name for scaffold: {script_name_final}")

        # --- 2. Determine Paths ---
        # (This section remains the same)
        try:
            base_projects_dir = os.path.join(project_root, AGENTIC_PROJECTS_DIR)
            project_folder_name = os.path.splitext(script_name_final)[0] or "default_project"
            destination_project_dir = os.path.normpath(os.path.join(base_projects_dir, project_folder_name))
            original_template_rel_path = rag_match_info['code_template']
            source_template_dir = os.path.normpath(os.path.join(project_root, os.path.dirname(original_template_rel_path)))
            if not os.path.isdir(source_template_dir): print(f"Error Log: Source template directory not found: {source_template_dir}"); print_ui(f"{COLOR_YELLOW}(DesignerAgent): Source template dir missing.{COLOR_RESET}"); return False
            print(f"(Designer Log): Source Dir: {source_template_dir}")
            print(f"(Designer Log): Destination Dir: {destination_project_dir}")
            print_ui(f"{COLOR_DIM}Creating project structure at '{destination_project_dir}'...{COLOR_RESET}", end="", flush=True)
        except Exception as path_e: print(f"Error Log: Path determination error: {path_e}"); traceback.print_exc(); return False

        # --- 3. Replicate Structure & Handle Special Files ---
        # (This section remains the same as previous correct version)
        copied_files_count, created_files_count, skipped_files_count = 0, 0, 0
        generated_special_files = set()

        try:
            os.makedirs(destination_project_dir, exist_ok=True)

            # --- Create/Handle Requirements.txt ---
            req_dest_path = os.path.join(destination_project_dir, "requirements.txt")
            pip_libs = sorted([lib for lib in final_approved_libraries if lib.lower() not in PYTHON_BUILTINS])
            if pip_libs:
                try:
                    with open(req_dest_path, 'w', encoding='utf-8') as f: f.write("\n".join(pip_libs) + "\n")
                    print(f"\n(Designer Log): Generated requirements.txt ({len(pip_libs)} libs).")
                    created_files_count += 1
                except IOError as e_req: print(f"\nWarning: Failed generating requirements.txt: {e_req}")
            else:
                 print("\n(Designer Log): No external libraries, skipping requirements.txt.")
                 if os.path.exists(req_dest_path):
                     try: os.remove(req_dest_path)
                     except OSError as e_rem: print(f"Warning: Could not remove existing reqs file: {e_rem}")
            generated_special_files.add("requirements.txt")

            # --- Create/Handle README.md and .env.example ---
            readme_dest_path = os.path.join(destination_project_dir, "README.md")
            env_example_dest_path = os.path.join(destination_project_dir, ".env.example")
            loaded_readme_template = getattr(self, 'readme_template_str', None) # Use correct attribute name
            if loaded_readme_template:
                 try:
                    readme_project_name = project_folder_name.replace('_', ' ').title()
                    purpose_match = re.search(r"^\s*(?:Description|Purpose):\s*(.*?)(?:\n\n|\nArgs:|\nArguments:|$)", blueprint_text, re.I | re.M | re.S)
                    brief_purpose = purpose_match.group(1).strip() if purpose_match else "A command-line utility."
                    brief_purpose = brief_purpose or "A command-line utility." # Ensure fallback
                    req_install_line = ("```bash\npip install -r requirements.txt\n```" if pip_libs else "(No external Python dependencies defined)") # Use updated template format
                    api_integrations = rag_match_info.get("api_integrations", []) if rag_match_info else []
                    needs_env = bool(api_integrations)
                    env_instructions = ""

                    if needs_env:
                         env_instructions = ("This project requires API keys or other secrets. "
                                             "Copy `.env.example` to a new file named `.env` and fill in your credentials.")
                         try:
                             with open(env_example_dest_path, 'w', encoding='utf-8') as f_env:
                                 f_env.write("# Environment variables required by this project.\n")
                                 f_env.write("# Copy this file to .env and replace placeholder values.\n\n")
                                 if api_integrations:
                                      for integr in api_integrations: f_env.write(f"{integr.upper()}_API_KEY=YOUR_{integr.upper()}_API_KEY_HERE\n")
                                 else: f_env.write("EXAMPLE_API_KEY=YOUR_VALUE_HERE\n")
                             created_files_count += 1
                             generated_special_files.add(".env.example")
                         except IOError as e_env: print(f"Warning: Could not create .env.example: {e_env}")
                    else:
                         env_instructions = "(No specific API integrations noted; .env file likely not required.)"
                         if os.path.exists(env_example_dest_path):
                             try: os.remove(env_example_dest_path)
                             except OSError as e_rem: print(f"Warning: Could not remove existing env.example file: {e_rem}")
                         generated_special_files.add(".env.example")

                    readme_content = loaded_readme_template.format(
                        PROJECT_NAME=readme_project_name, SCRIPT_NAME=script_name_final,
                        PROJECT_FOLDER_NAME=project_folder_name,
                        REQUIREMENTS_INSTALL_SECTION=req_install_line,
                        ENV_INSTRUCTIONS=env_instructions,
                        BRIEF_PURPOSE=brief_purpose
                    )
                    with open(readme_dest_path, 'w', encoding='utf-8') as f: f.write(readme_content)
                    print(f"(Designer Log): Generated README.md.")
                    created_files_count += 1
                 except KeyError as key_err: print(f"\nWarning: Missing key '{key_err}' in README template. Skipping README.md."); traceback.print_exc()
                 except Exception as e_readme: print(f"\nWarning: Failed generating README: {e_readme}"); traceback.print_exc()
            else: print(f"\nWarning: README template content not loaded. Skipping README.md generation.")
            generated_special_files.add("readme.md")

            # --- Walk and Copy remaining structure (Excluding Scripts) ---
            print("\n(Designer Log): Copying remaining template structure (excluding scripts)...")
            for root, dirs, files in os.walk(source_template_dir, topdown=True):
                dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS]
                relative_path = os.path.relpath(root, source_template_dir)
                current_dest_dir = destination_project_dir if relative_path == '.' else os.path.normpath(os.path.join(destination_project_dir, relative_path))
                if not os.path.exists(current_dest_dir):
                    try: os.makedirs(current_dest_dir, exist_ok=True)
                    except OSError as e_mkdir: print(f"Warn: Could not create dir {current_dest_dir}: {e_mkdir}"); continue

                for filename in files:
                    source_file_path = os.path.join(root, filename)
                    dest_file_path = os.path.join(current_dest_dir, filename)
                    file_ext = os.path.splitext(filename)[1].lower()
                    filename_lower = filename.lower()
                    if filename_lower in generated_special_files or \
                       filename_lower == ".env" or \
                       file_ext in SKIP_EXTENSIONS:
                        skipped_files_count += 1
                        continue
                    try:
                        shutil.copy2(source_file_path, dest_file_path)
                        copied_files_count += 1
                    except Exception as copy_e:
                        print(f"\nWarning: Error copying file {filename} to {dest_file_path}: {copy_e}")
                        skipped_files_count += 1

            # --- Final Step: Ensure the target script file is EMPTY ---
            final_script_relative_dir = ""
            try:
                 original_script_dir_in_source = os.path.dirname(os.path.normpath(os.path.join(project_root, original_template_rel_path)))
                 original_script_rel_path = os.path.relpath(original_script_dir_in_source, source_template_dir)
                 if original_script_rel_path and original_script_rel_path != '.':
                      final_script_relative_dir = original_script_rel_path
                      print(f"(Designer Log): Determined script relative dir: {final_script_relative_dir}")
            except ValueError: print("Warning: Could not determine relative script path. Placing script in project root."); pass

            final_script_dest_dir = os.path.normpath(os.path.join(destination_project_dir, final_script_relative_dir))
            final_script_dest_path = os.path.join(final_script_dest_dir, script_name_final)
            print(f"(Designer Log): Ensuring final script file is empty at: {final_script_dest_path}")
            try:
                os.makedirs(final_script_dest_dir, exist_ok=True)
                with open(final_script_dest_path, 'w', encoding='utf-8') as f: pass
                created_files_count += 1
            except IOError as e_final_script:
                print(f"\nFATAL Error: Failed to create/truncate final script {final_script_dest_path}: {e_final_script}")
                clear_line_ui(); print_ui(f"\n{COLOR_YELLOW}Error creating empty main script file. Scaffold failed.{COLOR_RESET}")
                return False

            clear_line_ui()
            print(f"\n(DesignerAgent Log): Scaffold creation successful. Copied: {copied_files_count}, Generated/Handled: {created_files_count}, Skipped: {skipped_files_count}")

            self._last_project_path = destination_project_dir
            self._last_script_name = script_name_final
            return True

        except Exception as e:
            clear_line_ui()
            print(f"\nError (DesignerAgent Log): Unexpected error during scaffold replication: {e}"); traceback.print_exc()
            print_ui(f"\n{COLOR_YELLOW}Error creating project structure: {e}{COLOR_RESET}")
            self._last_project_path = None; self._last_script_name = None
            return False
    # --- END of create_project_scaffold method ---

    def _prepare_developer_handoff(self, approved_blueprint: str, final_approved_libraries: list[str], original_rag_match_info: dict | None) -> dict | None:
        """
        Gathers the necessary context for the Developer Agent AFTER scaffold creation.
        Includes the original RAG match info.
        """
        # (Method unchanged)
        print("(DesignerAgent Log): Preparing handoff package for Developer...")
        if not self._last_project_path or not self._last_script_name:
             print("Error Log: Handoff failed - missing internal project path or script name.")
             return None
        if not approved_blueprint:
             print("Error Log: Handoff failed - missing approved blueprint.")
             return None
        if final_approved_libraries is None: # Check specifically for None
             print("Error Log: Handoff failed - missing final libraries list (should be empty list if none).")
             return None

        handoff_package = {
            "blueprint_text": approved_blueprint,
            "libraries": final_approved_libraries,
            "script_name": self._last_script_name,
            "project_folder_path": self._last_project_path,
            "rag_match_info": original_rag_match_info # Include RAG info
        }

        print("(DesignerAgent Log): Developer Handoff package details:")
        print(f"  - Blueprint Length : {len(handoff_package['blueprint_text'])}")
        print(f"  - Libraries        : {handoff_package['libraries']}")
        print(f"  - Script Name      : {handoff_package['script_name']}")
        print(f"  - Project Path     : {handoff_package['project_folder_path']}")
        print(f"  - RAG Info Keys    : {list(handoff_package['rag_match_info'].keys()) if handoff_package['rag_match_info'] else 'None'}")

        return handoff_package
    # +++++++++++++++++++++++++++++++++++++++++++++

# --- END of DesignerAgent Class ---