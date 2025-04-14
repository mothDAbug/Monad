# Agents/Analyst.py
import sys
import os
import json
import re
from dotenv import load_dotenv
import textwrap
import traceback

# --- Langchain / Google Imports ---
try:
    import google.generativeai as genai
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain.prompts import PromptTemplate # Use this for string templates
    from langchain_core.output_parsers import StrOutputParser
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("Warning (AnalystAgent): Langchain or google-generativeai not installed. Agent will not function.")

# --- Import Utils ---
try:
    import utils
    from utils import print_ui, animate_ui, clear_line_ui
    from utils import COLOR_RESET, COLOR_BOLD, COLOR_DIM, COLOR_BLUE, COLOR_CYAN, COLOR_YELLOW
except ImportError:
     print("Warning (AnalystAgent): Could not import utils. UI prints might not work.")
     def print_ui(message="", end="\n", flush=False): print(message, end=end, flush=flush)
     def animate_ui(base_message, duration=2.0, interval=0.15): print(f"{base_message}...")
     def clear_line_ui(): pass
     COLOR_RESET = COLOR_BOLD = COLOR_DIM = COLOR_BLUE = COLOR_CYAN = COLOR_YELLOW = ""
# ------------------

# --- Helper function to read prompt files ---
def load_prompt_template(file_path_relative: str) -> str | None:
    """
    Loads a prompt template from the specified file path relative to the project root.
    Project root is assumed to be the parent directory of this script's parent directory.
    """
    try:
        project_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.normpath(os.path.join(project_root_dir, file_path_relative))
        # print(f"[Prompt Loader Debug] Attempting path: {full_path}") # Uncomment for debug

        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            print(f"Error (load_prompt_template): Prompt file not found at normalized path '{full_path}'. Check the relative path ('{file_path_relative}') and project structure.", file=sys.stderr)
            return None
    except Exception as e:
        print(f"Error (load_prompt_template): Could not read prompt file '{file_path_relative}': {e}", file=sys.stderr)
        traceback.print_exc()
        return None
# --------------------------------------------------------


# --- Configuration ---
DEFAULT_OUTPUT_FILENAME = "user_stories_output.json"
OUTPUT_DIR = "artifacts"
PROMPTS_DIR = ".sysprompts"
ANALYST_GENERATOR_PROMPT_FILE = os.path.join(PROMPTS_DIR, "analyst_story_generator.prompt")
ANALYST_REFINER_PROMPT_FILE = os.path.join(PROMPTS_DIR, "analyst_story_refiner.prompt")
MAX_CODE_FILE_SIZE_MB = 1
MAX_TOTAL_CODE_CONTENT_CHARS = 30000

# --- Define OUT_OF_SCOPE signal ---
OUT_OF_SCOPE_SIGNAL = "OUT_OF_SCOPE"

class BusinessAnalystAgent:
    def __init__(self, output_dir=OUTPUT_DIR, original_stdout_handle=None):
        print(f"(AnalystAgent Log): Initializing Analyst Agent (Output Dir: {output_dir})...")
        if original_stdout_handle:
            utils.original_stdout = original_stdout_handle
        load_dotenv()
        self.llm = None
        self.output_dir = output_dir
        try:
             abs_output_dir = os.path.abspath(self.output_dir)
             if not os.path.isdir(abs_output_dir):
                 print(f"(AnalystAgent Log): Creating output directory: {abs_output_dir}")
                 os.makedirs(abs_output_dir, exist_ok=True)
             self.output_dir = abs_output_dir
             print(f"(AnalystAgent Log): Output directory set to: {self.output_dir}")
        except OSError as e:
             print(f"Error (AnalystAgent Log): Could not create/access output directory '{self.output_dir}': {e}")
             self.output_dir = os.path.abspath(".")
             print(f"(AnalystAgent Log): Falling back to output directory: {self.output_dir}")

        self.generator_template = load_prompt_template(ANALYST_GENERATOR_PROMPT_FILE)
        self.refiner_template = load_prompt_template(ANALYST_REFINER_PROMPT_FILE)
        if not self.generator_template:
             print(f"FATAL Error (AnalystAgent): Could not load GENERATOR prompt template.")
        if not self.refiner_template:
             print(f"FATAL Error (AnalystAgent): Could not load REFINER prompt template.")

        if LANGCHAIN_AVAILABLE:
            google_api_key = os.getenv("GOOGLE_API_KEY")
            if not google_api_key: print("Warning (AnalystAgent Log): GOOGLE_API_KEY not found.")
            else:
                model_name_from_env = os.getenv("GEMINI_MODEL_NAME")
                model_name = model_name_from_env if model_name_from_env else "gemini-1.5-flash"
                if not model_name_from_env: print("Warning (AnalystAgent Log): GEMINI_MODEL_NAME not found/empty. Falling back to 'gemini-1.5-flash'.")
                print(f"(AnalystAgent Log): Attempting to initialize LLM with model: {model_name}")
                try:
                    genai.configure(api_key=google_api_key)
                    self.llm = ChatGoogleGenerativeAI(model=model_name, temperature=0.5, convert_system_message_to_human=True)
                    print("(AnalystAgent Log): LLM Initialized successfully.")
                except Exception as e:
                    print(f"Error (AnalystAgent Log): Failed to initialize LLM with model '{model_name}': {e}"); traceback.print_exc(); self.llm = None
        else:
             print("(AnalystAgent Log): Langchain not available."); self.llm = None
        print("(AnalystAgent Log): Analyst Agent Initialization complete.")

    # --- CORRECTED PARSER ---
    def _parse_stories(self, llm_output: str) -> list[dict] | str | None: # Added None return type
        """
        Parses LLM output. Returns list of stories, the string signal "OUT_OF_SCOPE",
        or None if parsing fails or the response is not recognized.
        """
        stories = []
        print("(AnalystAgent Log): Starting story parsing (robust)...")
        if not llm_output or not llm_output.strip():
            print("(AnalystAgent Log): Warning - Received empty LLM output for parsing.")
            return None # Return None for empty input

        llm_output_cleaned = llm_output.strip()
        llm_output_lower = llm_output_cleaned.lower()
        out_of_scope_phrases = [ # Keep existing phrases
            "request is outside the current scope",
            "feedback is unrelated to the project scope",
            "cannot fulfill this request as it is out of scope",
            "outside the scope",
            "this request is outside the scope",
            "outside of the current scope",
            "that request is outside the current scope" # Added variation
        ]

        contains_refusal_phrase = False
        # Check if the response *starts with* or primarily consists of a refusal phrase
        for phrase in out_of_scope_phrases:
             # Use lowercased cleaned output for comparison
             if llm_output_lower.startswith(phrase) or (phrase in llm_output_lower and len(llm_output_cleaned) < 150) :
                  contains_refusal_phrase = True
                  break

        if contains_refusal_phrase:
             print(f"(AnalystAgent Log): LLM response appears to be an out-of-scope refusal: '{llm_output_cleaned[:50]}...'")
             return OUT_OF_SCOPE_SIGNAL # Return the explicit signal

        # --- Proceed with parsing lines if not flagged as out-of-scope ---
        strict_pattern = re.compile(r"^\s*\d*\.?\s*(As an?|As a)\s+(.+?),\s+I want\s+(.+?)(?:,\s+so that\s+(.+?))?\s*$", re.IGNORECASE)
        looks_like_story_pattern = re.compile(r"^\s*\d*\.?\s*(As an?|As a).+I want", re.IGNORECASE)
        lines = llm_output_cleaned.splitlines()

        for line in lines:
            line = line.strip()
            if not line: continue

            # Simple check to ignore lines that are obviously just refusal text
            is_likely_refusal_line = False
            for phrase in out_of_scope_phrases:
                 if phrase in line.lower():
                      is_likely_refusal_line = True
                      break
            if is_likely_refusal_line and len(line) < 100: # Skip short lines containing refusal text
                 continue

            match = strict_pattern.match(line)
            if match:
                role = match.group(2).strip(); action = match.group(3).strip()
                benefit = match.group(4).strip() if match.group(4) else "Benefit not explicitly stated"
                stories.append({"role": role, "action": action, "benefit": benefit, "user_story": line})
            elif looks_like_story_pattern.match(line):
                 # Consider if we want to capture these less structured ones. Maybe only if strict fails?
                 # For now, let's keep it to avoid capturing parts of refusal messages sometimes.
                 # If you need looser parsing, add: stories.append({"user_story": line})
                 pass
            # else: Don't append random non-story lines

        # --- FINAL CHECK ---
        if not stories:
            # If we didn't find any stories AND it wasn't flagged as OUT_OF_SCOPE earlier
            print("(AnalystAgent Log): Warning - No user stories could be parsed from the LLM output.")
            return None # Indicate parsing failure or unrecognized response
        # -----------------

        print(f"(AnalystAgent Log): Robust parsing finished. Found {len(stories)} potential stories.")
        return stories
    # --- END CORRECTED PARSER ---

    def _save_stories(self, user_stories: list[dict], filename: str) -> str | None:
        # (Keep saving logic as previously provided)
        if not user_stories:
            print("(AnalystAgent Log): No user stories provided to save.")
            return None
        output_filename = filename if filename else DEFAULT_OUTPUT_FILENAME
        filepath = os.path.join(self.output_dir, output_filename)
        print(f"(AnalystAgent Log): Attempting to save {len(user_stories)} stories to: {filepath}")
        try:
            with open(filepath, 'w', encoding='utf-8') as f: json.dump(user_stories, f, indent=4)
            print(f"(AnalystAgent Log): User stories saved successfully.")
            return filepath
        except IOError as e: print(f"Error (AnalystAgent Log): Failed to save user stories to {filepath}: {e}"); traceback.print_exc(); return None
        except Exception as e: print(f"Error (AnalystAgent Log): Unexpected error during saving: {e}"); traceback.print_exc(); return None

    # --- UPDATED TABLE PRINTING ---
    def _print_stories_table(self, user_stories: list[dict]):
        """Prints user stories in a fixed-width table format."""
        if not user_stories:
             print("(AnalystAgent Log): No stories to print in table.")
             # Optionally print a message to UI if desired when empty
             # print_ui(f"{COLOR_DIM}(No user stories to display){COLOR_RESET}")
             return

        print("(AnalystAgent Log): Preparing fixed-width stories table for UI...")

        # --- Define Fixed Column Widths ---
        # Adjust these values as needed for your preferred layout
        fixed_widths = {
            "id": 2,
            "role": 10,
            "action": 27, # User request target
            "benefit": 30 # User request target
        }
        # Width for the simplified "User Story" column if needed
        simple_story_width = fixed_widths["role"] + fixed_widths["action"] + fixed_widths["benefit"] + 4 # Sum of others + padding approx

        # --- Prepare Data and Determine Structure ---
        table_data = []
        has_parsed_structure = False
        for i, story in enumerate(user_stories):
            row = {"id": str(i + 1)}
            parsed_role = story.get("role")
            parsed_action = story.get("action")
            parsed_benefit = story.get("benefit")

            if parsed_role and parsed_action:
                row["role"] = parsed_role
                row["action"] = parsed_action
                row["benefit"] = parsed_benefit if parsed_benefit and parsed_benefit != "Benefit not explicitly stated" else f"{COLOR_DIM}(N/A){COLOR_RESET}"
                has_parsed_structure = True # Mark that we have at least one structured row
            elif "user_story" in story:
                row["role"] = f"{COLOR_DIM}(Raw){COLOR_RESET}"
                row["action"] = story["user_story"] # Store raw story in 'action' key for simple view
                row["benefit"] = ""
            else: # Fallback
                row["role"] = f"{COLOR_YELLOW}ERR{COLOR_RESET}"
                row["action"] = f"{COLOR_YELLOW}Parse?{COLOR_RESET}"
                row["benefit"] = ""
            table_data.append(row)

        # --- Select Columns and Widths based on Structure ---
        if has_parsed_structure:
            columns = ["ID", "Role", "Action", "Benefit"]
            data_keys = ["id", "role", "action", "benefit"]
            current_widths = fixed_widths # Use the standard fixed widths
            print("(AnalystAgent Log): Using structured table format (fixed widths).")
        else:
            # Use simplified view if NO structured stories were found
            columns = ["ID", "User Story"]
            data_keys = ["id", "action"] # 'action' key holds the raw story
            current_widths = { # Define widths specifically for the simple view
                "id": fixed_widths["id"],
                "action": simple_story_width
            }
            print("(AnalystAgent Log): Using simple table format (fixed widths).")

        # --- Draw Table ---
        padding = 1
        # Create separator line based on selected columns and widths
        separator = "+" + "+".join(["-" * (current_widths[data_keys[i]] + padding * 2) for i, col_name in enumerate(columns)]) + "+"
        # Create header line
        header_line = "|" + "|".join([f"{' ' * padding}{col_name.ljust(current_widths[data_keys[i]])}{' ' * padding}" for i, col_name in enumerate(columns)]) + "|"

        print_ui("\n" + separator)
        print_ui(header_line)
        print_ui(separator)

        # Data rows with wrapping using fixed widths
        for row in table_data:
            wrapped_row_data = {}
            max_lines_in_row = 1
            # Wrap data for each cell based on the CURRENT widths being used
            for i, col_name in enumerate(columns):
                key = data_keys[i]
                value = str(row.get(key, ''))
                width = current_widths[key] # Use the fixed width for this key
                # Wrap text using the determined fixed width
                wrapped_lines = textwrap.wrap(value, width=width, replace_whitespace=False, drop_whitespace=False) if value else ['']
                wrapped_row_data[key] = wrapped_lines
                max_lines_in_row = max(max_lines_in_row, len(wrapped_lines))

            # Print all lines needed for this wrapped row
            for line_index in range(max_lines_in_row):
                data_line = "|"
                for i, col_name in enumerate(columns):
                    key = data_keys[i]
                    width = current_widths[key] # Use fixed width again
                    cell_lines = wrapped_row_data[key]
                    line_segment = cell_lines[line_index] if line_index < len(cell_lines) else ""
                    # Ljust for printing, including padding
                    data_line += f"{' ' * padding}{line_segment.ljust(width)}{' ' * padding}|"
                print_ui(data_line)
            print_ui(separator) # Separator after each row's wrapped lines

        print("(AnalystAgent Log): Fixed-width stories table printed to UI.")
    # --- END UPDATED TABLE PRINTING ---

    def _read_code_files(self, file_paths: list[str]) -> str:
        # (Keep code reading logic as previously provided)
        all_code_content = []
        total_chars = 0
        print(f"(AnalystAgent Log): Reading code from {len(file_paths)} file(s)...")
        for file_path in file_paths:
            if not file_path or not isinstance(file_path, str): continue
            abs_path = os.path.abspath(file_path)
            if not os.path.exists(abs_path):
                print(f"Warning (AnalystAgent Log): Code file not found: {abs_path}")
                continue
            try:
                file_size = os.path.getsize(abs_path)
                if file_size > MAX_CODE_FILE_SIZE_MB * 1024 * 1024:
                     print(f"Warning (AnalystAgent Log): Skipping large code file (> {MAX_CODE_FILE_SIZE_MB}MB): {abs_path}")
                     continue

                with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    content_len = len(content)
                    if total_chars + content_len > MAX_TOTAL_CODE_CONTENT_CHARS:
                         remaining_chars = MAX_TOTAL_CODE_CONTENT_CHARS - total_chars
                         if remaining_chars > 100:
                             all_code_content.append(f"\n--- Start File: {os.path.basename(abs_path)} (truncated) ---\n")
                             all_code_content.append(content[:remaining_chars])
                             all_code_content.append(f"\n--- End File: {os.path.basename(abs_path)} (truncated) ---")
                             total_chars = MAX_TOTAL_CODE_CONTENT_CHARS
                             print(f"Warning (AnalystAgent Log): Truncated code file due to total size limit: {abs_path}")
                         else:
                             print(f"Warning (AnalystAgent Log): Skipping code file due to total size limit already reached: {abs_path}")
                         break
                    else:
                         all_code_content.append(f"\n--- Start File: {os.path.basename(abs_path)} ---\n")
                         all_code_content.append(content)
                         all_code_content.append(f"\n--- End File: {os.path.basename(abs_path)} ---")
                         total_chars += content_len + 80 # Approx marker overhead

            except Exception as e:
                print(f"Error (AnalystAgent Log): Failed to read code file '{abs_path}': {e}")
                traceback.print_exc()

        print(f"(AnalystAgent Log): Total code characters read: {total_chars}")
        return "\n".join(all_code_content) if all_code_content else "(No code content read or provided)"

    # --- CORRECTED CODE PATH EXTRACTION ---
    def _extract_code_paths_from_instructions(self, requirements_text: str) -> list[str]:
        """Extracts code file paths from the instruction text block using regex."""
        code_file_paths = []
        # Use the exact markers from the Lead Agent's prompt template
        start_marker = r"--- RAG FILE PATHS START ---"
        end_marker = r"--- RAG FILE PATHS END ---"
        # Regex to find content between markers, ignoring case, across multiple lines
        pattern = re.compile(rf"{start_marker}(.*?){end_marker}", re.DOTALL | re.IGNORECASE)
        match = pattern.search(requirements_text)

        if match:
            paths_block = match.group(1).strip() # Get content between markers
            if paths_block and paths_block != "(No valid code template paths found)":
                # Split by newline, strip whitespace, filter empty lines
                code_file_paths = [p.strip() for p in paths_block.splitlines() if p.strip() and not p.startswith('(')] # Filter out the placeholder too
        else:
            print("Warning (AnalystAgent Log): Could not find code file path markers using regex in instructions.")

        print(f"(AnalystAgent Log): Extracted {len(code_file_paths)} code paths from instructions.")
        return code_file_paths
    # ----------------------------------------


    def generate_user_stories(self, requirements_text: str, output_filename=DEFAULT_OUTPUT_FILENAME) -> tuple[list[dict], str | None]:
        """
        Generates user stories based on requirements AND code content from specified paths.
        """
        if not self.llm: print("(AnalystAgent Log): LLM not initialized."); return [], None
        if not self.generator_template: print("(AnalystAgent Log): Generator template not loaded."); return [], None
        if not requirements_text or not requirements_text.strip(): print("(AnalystAgent Log): Received empty requirements text."); return [], None

        print("(AnalystAgent Log): Generating user stories from requirements and code...")

        # --- Extract Code File Paths using corrected helper ---
        code_file_paths = self._extract_code_paths_from_instructions(requirements_text)
        # -------------------------------------------------------

        # --- Read Code Content ---
        code_content = self._read_code_files(code_file_paths)
        # -----------------------------------

        # --- Prepare Chain ---
        try:
             prompt = PromptTemplate(
                 template=self.generator_template,
                 input_variables=["requirements_text", "code_content"]
             )
             chain = prompt | self.llm | StrOutputParser()
        except Exception as prompt_e:
             print(f"Error (AnalystAgent Log): Failed to create generator prompt template or chain: {prompt_e}"); traceback.print_exc(); return [], None
        # ---------------------

        generated_stories_text = ""; parsed_stories = []; saved_filepath = None
        try:
            print(f"--- DIAGNOSTIC (Analyst Gen): Passing to LLM ---");
            print(f"Requirements Text (Context):\n{requirements_text[:1000]}...")
            print(f"Code Content Snippet:\n{code_content[:1000]}...")
            print(f"--- END DIAGNOSTIC ---")

            generated_stories_text = chain.invoke({
                "requirements_text": requirements_text,
                "code_content": code_content
            })
            print("(AnalystAgent Log): LLM invocation complete for story generation.")
            print(f"--- Analyst Raw LLM Output (Generation) ---\n{generated_stories_text}\n---------------------------------------")
            if generated_stories_text and generated_stories_text.strip():
                print("(AnalystAgent Log): Parsing generated stories...")
                parsing_result = self._parse_stories(generated_stories_text)

                if isinstance(parsing_result, list):
                    parsed_stories = parsing_result
                    if parsed_stories:
                         print("(AnalystAgent Log): Saving generated stories...")
                         saved_filepath = self._save_stories(parsed_stories, output_filename)
                    else: print("(AnalystAgent Log): Warning - Parsing generation output resulted in zero stories.")
                else: # Got OUT_OF_SCOPE or unexpected string from generation parser
                     print(f"Error (AnalystAgent Log): Parsing generation output resulted in unexpected signal: {parsing_result}")
                     parsed_stories = [] # Ensure empty list on failure
            else: print("(AnalystAgent Log): Warning - LLM returned empty output for story generation.")
        except Exception as e:
            print(f"Error (AnalystAgent Log): Exception during story generation/processing: {e}"); traceback.print_exc()
            parsed_stories = []; saved_filepath = None

        print("(AnalystAgent Log): User story generation step finished.")
        return parsed_stories, saved_filepath


    def refine_user_stories(self, current_stories: list[dict], user_feedback: str) -> list[dict] | str | None:
        """
        Refines user stories based on feedback using the loaded refiner prompt.
        Returns the updated list of stories, the string signal "OUT_OF_SCOPE", or None if refinement fails internally.
        """
        print("(AnalystAgent Log): Received request to refine stories.")
        if not self.llm: print("Error (AnalystAgent Log): LLM not available for refinement."); return None
        if not self.refiner_template: print("(AnalystAgent Log): Refiner template not loaded. Cannot refine stories."); return None
        if not isinstance(current_stories, list): print("Error (AnalystAgent Log): Invalid 'current_stories' provided (not a list)."); return None
        if not user_feedback or not user_feedback.strip(): print("Warning (AnalystAgent Log): Empty user feedback provided. No refinement performed."); return current_stories # Return original if no feedback

        # --- Format current stories (Keep existing logic) ---
        current_stories_text = ""
        if not current_stories: current_stories_text = "(No current stories provided)"
        else:
            print("(AnalystAgent Log): Formatting current stories for refinement prompt...")
            for i, story in enumerate(current_stories):
                story_line = story.get('user_story')
                if not story_line:
                    role = story.get("role", "User"); action = story.get("action", "[No action]"); benefit = story.get("benefit", "[No benefit]")
                    story_line = f"As a {role}, I want {action}, so that {benefit}"
                current_stories_text += f"{i+1}. {story_line.strip()}\n"
        # --- End Formatting ---

        # --- Prepare Chain (Keep existing logic) ---
        try:
            refinement_prompt = PromptTemplate(
                template=self.refiner_template, input_variables=["current_stories_text", "user_feedback"]
            )
            refinement_chain = refinement_prompt | self.llm | StrOutputParser()
        except Exception as prompt_e:
            print(f"Error (AnalystAgent Log): Failed to create refinement prompt template or chain: {prompt_e}"); traceback.print_exc();
            return None # Indicate failure to create chain
        # --- End Prepare Chain ---

        # --- Invoke LLM and Parse (ADDED Robustness) ---
        refined_stories_text = None
        try:
            print("(AnalystAgent Log): Invoking LLM for story refinement...")
            # (Keep diagnostic prints)
            print(f"--- Analyst DIAGNOSTIC (Refinement Input) ---")
            print(f"Current Stories Text:\n{current_stories_text}")
            print(f"User Feedback: {user_feedback}")
            print(f"--- END DIAGNOSTIC ---")

            refined_stories_text = refinement_chain.invoke({
                "current_stories_text": current_stories_text, "user_feedback": user_feedback
            })

            print("(AnalystAgent Log): LLM invocation complete for refinement.")
            print(f"--- Analyst Raw LLM Output (Refinement) ---\n{refined_stories_text}\n----------------------------------------")

        # --- Catch potential LLM/API errors ---
        except Exception as llm_e:
            print(f"Error (AnalystAgent Log): Exception during story refinement LLM call: {llm_e}"); traceback.print_exc();
            return None # Indicate failure during LLM call

        # --- Proceed to parsing only if LLM call succeeded ---
        if refined_stories_text is not None: # Check if we got output
            try:
                print("(AnalystAgent Log): Parsing refined stories...")
                parsing_result = self._parse_stories(refined_stories_text) # Returns list or OUT_OF_SCOPE_SIGNAL

                # Check the result of parsing
                if isinstance(parsing_result, str) and parsing_result == OUT_OF_SCOPE_SIGNAL:
                     print(f"(AnalystAgent Log): Parsing detected OUT_OF_SCOPE signal.")
                     return OUT_OF_SCOPE_SIGNAL # Return the signal clearly
                elif isinstance(parsing_result, list):
                     print(f"(AnalystAgent Log): Parsing successful, returning list with {len(parsing_result)} stories.")
                     return parsing_result # Return the list of stories
                else:
                     # This case means _parse_stories returned None or unexpected type
                     print(f"Error (AnalystAgent Log): Parsing refined stories returned unexpected result: {type(parsing_result)}")
                     return None # Indicate failure during parsing

            # --- Catch potential parsing errors ---
            except Exception as parse_e:
                 print(f"Error (AnalystAgent Log): Exception during story refinement parsing: {parse_e}"); traceback.print_exc();
                 return None # Indicate failure during parsing
        else:
             # Handle case where LLM returned empty string or None (without exception)
             print("(AnalystAgent Log): LLM returned empty output during refinement.");
             return None # Indicate failure (LLM gave nothing usable back)
        # --- End Invoke LLM and Parse ---
        # (Use the corrected version from the previous step)
        """
        Refines user stories based on feedback using the loaded refiner prompt.
        Returns the updated list of stories, the string signal "OUT_OF_SCOPE", or None if refinement fails.
        """
        print("(AnalystAgent Log): Received request to refine stories.")
        if not self.llm: print("Error (AnalystAgent Log): LLM not available for refinement."); return None
        if not self.refiner_template: print("(AnalystAgent Log): Refiner template not loaded. Cannot refine stories."); return None
        if not isinstance(current_stories, list): print("Error (AnalystAgent Log): Invalid 'current_stories' provided (not a list)."); return None
        if not user_feedback or not user_feedback.strip(): print("Warning (AnalystAgent Log): Empty user feedback provided. No refinement performed."); return current_stories

        current_stories_text = ""
        if not current_stories: current_stories_text = "(No current stories provided)"
        else:
            print("(AnalystAgent Log): Formatting current stories for refinement prompt...")
            for i, story in enumerate(current_stories):
                story_line = story.get('user_story')
                if not story_line:
                    role = story.get("role", "User"); action = story.get("action", "[No action]"); benefit = story.get("benefit", "[No benefit]")
                    story_line = f"As a {role}, I want {action}, so that {benefit}"
                current_stories_text += f"{i+1}. {story_line.strip()}\n"
        try:
            refinement_prompt = PromptTemplate(
                template=self.refiner_template, input_variables=["current_stories_text", "user_feedback"]
            )
            refinement_chain = refinement_prompt | self.llm | StrOutputParser()
        except Exception as prompt_e:
            print(f"Error (AnalystAgent Log): Failed to create refinement prompt template or chain: {prompt_e}"); traceback.print_exc(); return None

        try:
            print("(AnalystAgent Log): Invoking LLM for story refinement...")
            print(f"--- Analyst DIAGNOSTIC (Refinement Input) ---")
            print(f"Current Stories Text:\n{current_stories_text}")
            print(f"User Feedback: {user_feedback}")
            print(f"--- END DIAGNOSTIC ---")
            refined_stories_text = refinement_chain.invoke({
                "current_stories_text": current_stories_text, "user_feedback": user_feedback
            })
            print("(AnalystAgent Log): LLM invocation complete for refinement.")
            print(f"--- Analyst Raw LLM Output (Refinement) ---\n{refined_stories_text}\n----------------------------------------")

            if refined_stories_text:
                 print("(AnalystAgent Log): Parsing refined stories...")
                 parsing_result = self._parse_stories(refined_stories_text) # Returns list or OUT_OF_SCOPE_SIGNAL

                 if parsing_result is not None: # Check needed in case parser somehow returns None
                     if isinstance(parsing_result, str): print(f"(AnalystAgent Log): Returning signal: {parsing_result}")
                     else: print(f"(AnalystAgent Log): Returning list with {len(parsing_result)} stories.")
                     return parsing_result
                 else:
                     print("Error (AnalystAgent Log): Parsing refined stories returned None unexpectedly.")
                     return None # Indicate failure
            else:
                 print("(AnalystAgent Log): LLM returned empty output during refinement.");
                 return None # Indicate failure (LLM gave nothing back)

        except Exception as e:
            print(f"Error (AnalystAgent Log): Exception during story refinement LLM call/parsing: {e}"); traceback.print_exc(); return None # Indicate failure