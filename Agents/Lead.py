# Agents/Lead.py
import sys
import os
import time
import json
from collections import defaultdict
from dotenv import load_dotenv
import traceback
import re
import textwrap
import datetime # For timestamping debug files
import subprocess
# ... other imports

# --- Langchain / Google Imports ---
try:
    import google.generativeai as genai
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain.memory import ConversationBufferMemory
    from langchain.prompts import PromptTemplate # Use this for string templates
    from langchain_core.runnables import RunnablePassthrough
    from langchain_core.output_parsers import StrOutputParser
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    LANGCHAIN_AVAILABLE = False
    print(f"Warning (LeadAgent Import): Langchain/Google components not found. Error: {e}", file=sys.stderr)


# --- Local Tool/Agent Imports ---
try:
    from Tools.RAGTool import TemplateRetriever
except ImportError as e:
    print(f"FATAL Error (LeadAgent Import): Could not import TemplateRetriever. Error: {e}", file=sys.stderr); traceback.print_exc(); sys.exit(1)

try:
    from Agents.Analyst import (
        BusinessAnalystAgent, OUTPUT_DIR as ANALYST_OUTPUT_DIR,
        DEFAULT_OUTPUT_FILENAME as ANALYST_DEFAULT_FILENAME,
        OUT_OF_SCOPE_SIGNAL as ANALYST_OUT_OF_SCOPE_SIGNAL
    )
    BUSINESS_ANALYST_AVAILABLE = True
except ImportError as e:
    print("Warning (LeadAgent Import): Could not import BusinessAnalystAgent. BA features disabled.", file=sys.stderr)
    BUSINESS_ANALYST_AVAILABLE = False
    ANALYST_OUTPUT_DIR = "artifacts"; ANALYST_DEFAULT_FILENAME = "user_stories_output.json"; ANALYST_OUT_OF_SCOPE_SIGNAL = "OUT_OF_SCOPE"

try:
    from Agents.Designer import DesignerAgent
    DESIGNER_AGENT_AVAILABLE = True
except ImportError as e:
    print("Warning (LeadAgent Import): Could not import DesignerAgent. Design features disabled.", file=sys.stderr)
    DESIGNER_AGENT_AVAILABLE = False

try:
    from Agents.Developer import DeveloperAgent # Using the manager agent structure
    DEVELOPER_AGENT_AVAILABLE = True
except ImportError as e:
    print("Warning (LeadAgent Import): Could not import DeveloperAgent. Code generation features disabled.", file=sys.stderr)
    DEVELOPER_AGENT_AVAILABLE = False

# --- CORRECTED Tester Agent Import ---
try:
    from Agents.Tester import TesterAgent # Standard import attempt
    TESTER_AGENT_AVAILABLE = True         # Set flag ONLY if import succeeds
except ImportError as e:
    # This executes if Tester.py is missing, has syntax errors, or internal import errors
    print(f"Warning (LeadAgent Import): Could not import TesterAgent. Testing features disabled. Error: {e}", file=sys.stderr)
    TESTER_AGENT_AVAILABLE = False        # Set flag to False on any import failure
# ------------------------------------

# --- Import Utils ---
try:
    import utils
    from utils import print_ui, animate_ui, clear_line_ui, log_context_switch
    from utils import (COLOR_GREY, COLOR_CYAN, COLOR_RESET, COLOR_BLUE, COLOR_DIM,
                       COLOR_GREEN, COLOR_YELLOW, COLOR_BOLD, COLOR_MAGENTA, COLOR_RED) # Ensure COLOR_RED is imported
except ImportError as e:
     print("FATAL Error (LeadAgent Import): Could not import utils. UI features limited.", file=sys.stderr)
     def print_ui(message="", end="\n", flush=False): print(message, end=end, flush=flush)
     def animate_ui(base_message, duration=2.0, interval=0.15): print(f"{base_message}...")
     def clear_line_ui(): pass
     def log_context_switch(f, t): print(f"\nCONTEXT SWITCH: {f} -> {t}")
     COLOR_GREY = COLOR_CYAN = COLOR_RESET = COLOR_BLUE = COLOR_DIM = COLOR_GREEN = COLOR_YELLOW = COLOR_BOLD = COLOR_MAGENTA = COLOR_RED = ""
# ------------------

# --- Helper function to read prompt files ---
def load_prompt_template(file_path_relative: str) -> str | None:
    # (Function unchanged)
    try:
        project_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.normpath(os.path.join(project_root_dir, file_path_relative))
        if os.path.exists(full_path) and os.path.isfile(full_path):
            with open(full_path, 'r', encoding='utf-8') as f: return f.read()
        else: print(f"Error (load_prompt_template): Prompt file not found at '{full_path}' (relative: '{file_path_relative}').", file=sys.stderr); return None
    except Exception as e: print(f"Error (load_prompt_template): Could not read prompt file '{file_path_relative}': {e}", file=sys.stderr); traceback.print_exc(); return None
# --------------------------------------------------------

# --- Configuration ---
MAX_RESULTS_TO_PROCESS = 5 # Limit RAG results shown/processed
PROMPTS_DIR = ".sysprompts"
# Ensure these files contain the correct versions matching expected logic
LEAD_BA_INSTRUCTION_PROMPT_FILE = os.path.join(PROMPTS_DIR, "lead_ba_instruction_generator.prompt")
LEAD_DESIGN_SUMMARIZER_PROMPT_FILE = os.path.join(PROMPTS_DIR, "lead_design_summarizer.prompt")
LEAD_DESIGN_VETTING_PROMPT_FILE = os.path.join(PROMPTS_DIR, "lead_design_vetting.prompt")

class LeadAgent:
    """
    The central orchestrator of the agentic workflow. Manages the flow between
    Analyst, Designer, Developer, and Tester agents, handles user interaction,
    and maintains the overall project state.
    """
    def __init__(self, original_stdout_handle=None):
        print("(LeadAgent Log): Initializing...")
        if original_stdout_handle: utils.original_stdout = original_stdout_handle
        else: print("Warning (LeadAgent Log): No original stdout handle provided. UI prints might go to log.")
        load_dotenv()
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        print(f"(LeadAgent Log): Project Root detected as: {self.project_root}")
        self.rag_tool = None
        try:
            self.rag_tool = TemplateRetriever()
            if self.rag_tool.is_initialized: print("(LeadAgent Log): RAG Tool initialized successfully.")
            else: print("Error (LeadAgent Log): RAG Tool failed initialization.")
        except Exception as rag_e: print(f"Error (LeadAgent Log): Exception during RAG Tool initialization: {rag_e}"); traceback.print_exc()

        # Central Project State
        self.project_context = {
            "initial_prompt": None,
            "rag_matches": [],        # List of dicts from RAG tool
            "ba_instructions": None,  # String instructions for BA
            "user_stories": [],       # List of dicts (parsed user stories)
            "user_stories_filepath": None, # Path to saved JSON stories
            "cli_design_blueprint": None, # String blueprint from Designer
            "cli_design_libraries": [],   # List of strings (libraries from design)
            "initial_essential_libraries": [], # Backup list from initial design
            "main_script_name": None, # String (e.g., script.py)
            "final_constraints": "(Placeholder: No specific constraints defined yet)",
            "project_folder_path": None, # Path to the generated project dir
            "generated_code": None,   # String containing the final code
            "test_report": None,      # String output from Tester
            "test_status": None,      # Boolean (True=pass, False=fail, None=not run/error)
            "test_script_path": None  # Path to the generated test script
        }

        self.llm = None; self.summarizer_llm = None; self.memory = None
        self.designer_instance = None # Hold Designer instance for feedback loops

        # Load Lead Agent Specific Prompts
        print("(LeadAgent Log): Loading Lead Agent prompt templates...")
        self.ba_instruction_template = load_prompt_template(LEAD_BA_INSTRUCTION_PROMPT_FILE)
        self.design_summarizer_template = load_prompt_template(LEAD_DESIGN_SUMMARIZER_PROMPT_FILE)
        self.design_vetting_template_str = load_prompt_template(LEAD_DESIGN_VETTING_PROMPT_FILE)

        # Check if prompts loaded
        if not self.ba_instruction_template: print(f"FATAL Error (LeadAgent): Could not load BA instruction prompt: {LEAD_BA_INSTRUCTION_PROMPT_FILE}.")
        if not self.design_vetting_template_str: print(f"FATAL Error (LeadAgent): Could not load Design Vetting prompt: {LEAD_DESIGN_VETTING_PROMPT_FILE}.")
        if not self.design_summarizer_template: print(f"Warning (LeadAgent): Could not load Design Summarizer prompt: {LEAD_DESIGN_SUMMARIZER_PROMPT_FILE}. Summarization disabled.")

        # Set agent availability flags using imported constants
        self.analyst_available = BUSINESS_ANALYST_AVAILABLE
        self.designer_available = DESIGNER_AGENT_AVAILABLE
        self.developer_available = DEVELOPER_AGENT_AVAILABLE
        self.tester_available = TESTER_AGENT_AVAILABLE # Uses the flag set by the import block

        print(f"(LeadAgent Log): Agent Availability - Analyst:{self.analyst_available}, Designer:{self.designer_available}, Developer:{self.developer_available}, Tester:{self.tester_available}")

        # Initialize LLM and Memory
        if LANGCHAIN_AVAILABLE:
            google_api_key = os.getenv("GOOGLE_API_KEY")
            if not google_api_key: print("Warning (LeadAgent Log): GOOGLE_API_KEY not found in .env. LLM features disabled.")
            else:
                try:
                    print("(LeadAgent Log): Configuring Google Generative AI...")
                    genai.configure(api_key=google_api_key)

                    # Conversation Memory for context (optional, adjust as needed)
                    self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
                    print("(LeadAgent Log): Conversation Memory Initialized.")

                    # Primary LLM for instructions/vetting
                    model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash") # Use fallback
                    print(f"(LeadAgent Log): Using primary LLM model (Instructions/Vetting): {model_name}")
                    self.llm = ChatGoogleGenerativeAI(model=model_name, temperature=0.5, convert_system_message_to_human=True)

                    # Separate LLM for summarization (can use same model with different temp)
                    print(f"(LeadAgent Log): Using summarizer LLM model: {model_name}")
                    self.summarizer_llm = ChatGoogleGenerativeAI(model=model_name, temperature=0.2, convert_system_message_to_human=True)

                    print("(LeadAgent Log): Lead LLMs initialized successfully.")
                except Exception as e:
                    print(f"Error (LeadAgent Log): Failed to initialize Langchain/Google components: {e}"); traceback.print_exc();
                    self.memory=None; self.llm=None; self.summarizer_llm=None
        else:
            print("(LeadAgent Log): Langchain is not available. LLM features disabled.")

        print("(LeadAgent Log): Lead Agent Initialization complete.")

    # --- Helper Methods ---

    def _display_results_tree(self, results):
        # (Method unchanged)
        results_to_display = results[:MAX_RESULTS_TO_PROCESS]
        if not results_to_display: print_ui(f"{COLOR_DIM}(no relevant matches found){COLOR_RESET}\n"); return
        print_ui(f"\n{COLOR_GREEN}code_exemplar/{COLOR_RESET}"); print_ui(f"{COLOR_GREEN}│{COLOR_RESET}")
        grouped_results = defaultdict(list); processed_groups = set(); ordered_group_keys = []
        for result in results_to_display:
            group_id = result.get('group_id', 'N/A');
            if group_id not in processed_groups: ordered_group_keys.append(group_id); processed_groups.add(group_id)
            grouped_results[group_id].append(result)
        num_groups = len(ordered_group_keys)
        for i, group_id in enumerate(ordered_group_keys):
            is_last_group = (i == num_groups - 1); templates_in_group = grouped_results[group_id]
            group_name = templates_in_group[0].get('group_name', 'UnknownGroup') if templates_in_group else 'UnknownGroup'
            group_prefix = "└──" if is_last_group else "├──"; group_connector = "   " if is_last_group else "│  "
            group_str = f"{group_id}-{group_name.replace(' ', '')}" if group_id != 'N/A' else group_name.replace(' ', '')
            print_ui(f"{COLOR_GREEN}{group_prefix}{group_str}/{COLOR_RESET}")
            num_templates = len(templates_in_group)
            for j, template in enumerate(templates_in_group):
                is_last_template = (j == num_templates - 1); template_prefix = "└──" if is_last_template else "├──"; template_connector = "   " if is_last_template else "│  "
                template_id_str = template.get('template_id', 'N/A')
                template_name_str = template.get('template_name', 'N/A').replace(' ', '')
                template_str = f"{template_id_str}-{template_name_str}" if template_id_str != 'N/A' else template_name_str
                print_ui(f"{COLOR_GREEN}{group_connector}{template_prefix}{template_str}/{COLOR_RESET}")
                components = template.get('relevant_components', [])
                num_components = len(components)
                component_indent_prefix = f"{group_connector}{template_connector}"
                if not components or components == ['N/A']: print_ui(f"{COLOR_GREEN}{component_indent_prefix}└──{COLOR_RESET} {COLOR_DIM}(No components listed){COLOR_RESET}")
                else:
                    for k, component_name in enumerate(components):
                        is_last_component = (k == num_components - 1); component_prefix_str = "└──" if is_last_component else "├──"
                        prefix_part = f"{COLOR_GREEN}{component_indent_prefix}{component_prefix_str}{COLOR_RESET}"
                        if component_name == "(No specific components listed)": component_part = f" {COLOR_DIM}{component_name}{COLOR_RESET}"
                        else: component_part = f" {COLOR_GREEN}{component_name}{COLOR_RESET}"
                        print_ui(prefix_part + component_part)
                code_path = template.get('code_template')
                base_indent = f"{group_connector}{template_connector}"; code_indent = base_indent + "    "
                if not code_path or code_path == 'N/A': code_path_display = "[ Code Template: Not specified ]"; print_ui(f"{code_indent}{COLOR_DIM}{code_path_display}{COLOR_RESET}")
                else: code_path_display = f"[ Code Template: ...{code_path[-40:]} ]" if len(code_path) > 40 else f"[ Code Template: {code_path} ]"; print_ui(f"{code_indent}{COLOR_YELLOW}{code_path_display}{COLOR_RESET}")
            if not is_last_group: print_ui(f"{COLOR_GREEN}│{COLOR_RESET}")


    def _run_initial_rag_phase(self):
        # (Method unchanged)
        print("(LeadAgent Log): Starting initial RAG phase...")
        print_ui(f"\n{COLOR_GREY}# Describe your Project Idea{COLOR_RESET}")
        prompt_text = f"Tell me what's on your mind: "
        print_ui(f"{COLOR_GREY}{prompt_text}{COLOR_RESET}", end="", flush=True)
        try: user_input = input()
        except EOFError: print_ui(f"\n{COLOR_YELLOW}Input stream closed. Exiting.{COLOR_RESET}"); return False
        if user_input and user_input.strip():
            cleaned_input = user_input.strip(); self.project_context["initial_prompt"] = cleaned_input
            print(f"(LeadAgent Log): Received initial prompt: '{cleaned_input}'")
            print_ui(f"\t{COLOR_GREY}...searching relevant templates...{COLOR_RESET}", end='\r', flush=True)
            if not self.rag_tool or not self.rag_tool.is_initialized:
                 clear_line_ui(); print("Error (LeadAgent Log): RAG tool not ready."); print_ui(f"{COLOR_YELLOW}(LeadAgent): RAG tool unavailable.{COLOR_RESET}"); self.project_context["rag_matches"] = []
            else:
                 try:
                     print("(LeadAgent Log): Querying RAG tool..."); matches = self.rag_tool.find_matches(self.project_context["initial_prompt"])
                     clear_line_ui()
                     self.project_context["rag_matches"] = matches;
                     print(f"(LeadAgent Log): RAG tool returned {len(matches)} matches."); self._display_results_tree(matches)
                 except Exception as rag_query_e:
                     clear_line_ui(); print(f"Error (LeadAgent Log): RAG query exception: {rag_query_e}"); traceback.print_exc(); print_ui(f"{COLOR_YELLOW}(LeadAgent): Error querying RAG.{COLOR_RESET}"); self.project_context["rag_matches"] = []
            return True
        else: print("(LeadAgent Log): No valid input."); print_ui(f"\n{COLOR_DIM}No input received.{COLOR_RESET}"); return False


    def _initiate_analysis_phase(self) -> str | None:
        # (Method reverted to version before explicit marker inclusion instruction)
        print("(LeadAgent Log): Initiating analysis phase...")
        if not self.ba_instruction_template: print("Error (LeadAgent Log): BA instruction template missing."); return None
        if not self.project_context.get("initial_prompt"): print("Error (LeadAgent Log): No initial prompt in context."); return None
        if not self.llm: print("Error (LeadAgent): Primary LLM unavailable for BA instructions."); return None

        history = []
        if self.memory: history = self.memory.load_memory_variables({}).get('chat_history', [])
        else: print("Warning (LeadAgent Log): Memory not available for BA instruction context.")

        log_context_switch("Lead", "Analyst")
        initial_prompt = self.project_context["initial_prompt"]
        rag_matches = self.project_context.get("rag_matches", [])
        rag_summary = "No relevant code exemplars found."
        code_template_paths = [] # List to hold absolute paths found

        if rag_matches:
             rag_summary = "Found potential code exemplars during the initial search:\n"
             for i, match in enumerate(rag_matches[:MAX_RESULTS_TO_PROCESS]):
                 template_name = match.get('template_name', 'N/A'); group_name = match.get('group_name', 'N/A')
                 components_list = match.get('relevant_components', ['N/A']); components = ', '.join(c for c in components_list if c != 'N/A')
                 code_path_relative = match.get('code_template')
                 summary_line = f"- {template_name} (Group: {group_name or 'N/A'}, Components: {components or 'N/A'})"
                 if code_path_relative and code_path_relative != 'N/A':
                      abs_code_path = os.path.normpath(os.path.join(self.project_root, code_path_relative))
                      summary_line += f" [Ref Path: {code_path_relative}]"
                      if os.path.exists(abs_code_path) and os.path.isfile(abs_code_path): code_template_paths.append(abs_code_path)
                      else: print(f"Warning (LeadAgent Log): RAG code path does not exist or is not a file: {abs_code_path}")
                 else: summary_line += " [No specific code path]"
                 rag_summary += summary_line + "\n"

        # Format code paths block with markers for the Analyst prompt
        code_paths_str_for_prompt = "--- RAG FILE PATHS START ---\n"
        code_paths_str_for_prompt += "\n".join(code_template_paths) if code_template_paths else "(No valid code template paths found)"
        code_paths_str_for_prompt += "\n--- RAG FILE PATHS END ---"
        print(f"(LeadAgent Log): Preparing BA instructions with {len(code_template_paths)} code path(s).")

        try:
             prompt = PromptTemplate(template=self.ba_instruction_template, input_variables=["initial_prompt", "rag_summary", "code_template_paths", "chat_history"])
             chain = ( RunnablePassthrough.assign(chat_history=lambda x: x.get('chat_history', [])) | prompt | self.llm | StrOutputParser())
        except Exception as prompt_e: print(f"Error (LeadAgent) creating BA prompt/chain: {prompt_e}"); traceback.print_exc(); log_context_switch("Analyst", "Lead"); return None

        ba_instructions = None; animation_active = False
        try:
            animate_ui(f"{COLOR_DIM}Generating instructions for Analyst...{COLOR_RESET}", duration=1.5, interval=0.2); animation_active = True
            print("(LeadAgent Log): Invoking LLM for BA instructions...");
            input_data = { "initial_prompt": initial_prompt, "rag_summary": rag_summary,
                           "code_template_paths": code_paths_str_for_prompt, # Pass block with markers
                           "chat_history": history }
            ba_instructions = chain.invoke(input_data)
            animation_active = False; clear_line_ui()
            if not ba_instructions or len(ba_instructions.strip()) < 50:
                 print(f"Warning (LeadAgent Log): LLM returned potentially insufficient BA instructions (length {len(ba_instructions or '')}).");
                 if not ba_instructions: log_context_switch("Analyst", "Lead"); return None # Consider empty instructions a failure
            else:
                print("(LeadAgent Log): LLM invocation complete for BA instructions.")
                if self.memory:
                    try: self.memory.save_context({"input": f"(Lead Log) User idea: {initial_prompt[:100]}..."}, {"output": ba_instructions})
                    except Exception as mem_e: print(f"Error saving context to memory: {mem_e}")
            print(f"\n--- BA Instructions Generated (LOG) ---\n{ba_instructions if ba_instructions else '<None>'}\n-------------------------------------")
        except Exception as e:
            if animation_active: clear_line_ui();
            print(f"Error (LeadAgent Log): LLM Exception during BA instruction generation: {e}"); traceback.print_exc();
            print_ui(f"{COLOR_YELLOW}(LeadAgent): Error generating BA instructions.{COLOR_RESET}"); ba_instructions = None
            log_context_switch("Analyst", "Lead")
        return ba_instructions


    def _interpret_feedback(self, feedback: str) -> str:
        # (Method unchanged)
        feedback_lower = feedback.lower().strip(); approval_keywords = ["no", "looks good", "good", "ok", "okay", "proceed", "continue", "correct", "fine", "naah", "all good", "yes", "yep", "yeah"]; modify_keywords = ["remove", "delete", "change", "add", "modify", "update", "don't want", "dont want", "instead"]
        # Simple approval: short, common approval words without modification terms
        if any(keyword == feedback_lower for keyword in ["no", "yes", "ok", "okay", "good", "fine"]) or \
           (any(feedback_lower.startswith(keyword) for keyword in approval_keywords) and len(feedback_lower) < 35):
             if not any(mod_keyword in feedback_lower for mod_keyword in modify_keywords):
                 print("(LeadAgent Log): Interpreted feedback as: approve (simple)")
                 return "approve"
        # Modification: contains keywords or is longer
        if any(keyword in feedback_lower for keyword in modify_keywords) or len(feedback_lower) >= 10:
            print("(LeadAgent Log): Interpreted feedback as: modify")
            return "modify"
        # Default / Unclear
        print("(LeadAgent Log): Interpreted feedback as: approve (default/unclear)")
        return "approve"


    def _handle_analyst_user_feedback(self) -> bool:
        # (Method unchanged)
        print("(LeadAgent Log): Entering Analyst user feedback loop...")
        if not self.project_context.get("user_stories"): print("Error (Lead Feedback): No stories to get feedback on."); return False
        if not self.analyst_available: print("Error (Lead Feedback): Analyst unavailable."); return False
        analyst_agent_instance = None
        try:
            analyst_agent_instance = BusinessAnalystAgent(output_dir=ANALYST_OUTPUT_DIR, original_stdout_handle=utils.original_stdout)
            if not analyst_agent_instance.llm: print("(Lead Log): Analyst LLM not ready for feedback."); return False
        except Exception as analyst_init_e: print(f"Error init Analyst Agent for feedback: {analyst_init_e}"); return False
        while True:
            current_stories_in_context = self.project_context.get("user_stories", [])
            log_context_switch("Analyst", "Lead") # Signal start of user interaction
            print_ui(f"\n{COLOR_GREY}Review User Stories. Changes needed? ('no' to approve):{COLOR_RESET} ", end="")
            try: user_feedback = input()
            except EOFError: print_ui(f"\n{COLOR_YELLOW}Input stream closed.{COLOR_RESET}"); return False
            interpretation = self._interpret_feedback(user_feedback)
            if interpretation == "approve": print_ui(f"{COLOR_GREEN}(LeadAgent): User stories approved.{COLOR_RESET}"); return True
            elif interpretation == "modify":
                if not user_feedback.strip(): print_ui(f"{COLOR_YELLOW}Please provide specific feedback...{COLOR_RESET}"); continue
                print("(Lead Log): Delegating story refinement to Analyst."); log_context_switch("Lead", "Analyst") # Signal delegation
                animate_ui(f"{COLOR_DIM}Analyst refining stories...{COLOR_RESET}", duration=1.5, interval=0.15)
                refined_stories_result = None
                try: refined_stories_result = analyst_agent_instance.refine_user_stories(current_stories_in_context, user_feedback.strip())
                except Exception as refine_call_e: print(f"Error DURING analyst.refine call: {refine_call_e}"); refined_stories_result = None
                finally: clear_line_ui()
                if isinstance(refined_stories_result, list):
                    print("(Log): Analyst returned refined list.")
                    if refined_stories_result != current_stories_in_context:
                         print("(Log): Stories changed, updating context and display..."); self.project_context["user_stories"] = refined_stories_result
                         analyst_agent_instance._print_stories_table(refined_stories_result)
                         saved_path = self.project_context.get("user_stories_filepath")
                         if saved_path:
                              try:
                                   new_filepath = analyst_agent_instance._save_stories(refined_stories_result, os.path.basename(saved_path))
                                   if new_filepath: self.project_context["user_stories_filepath"] = new_filepath
                              except Exception as save_e: print(f"Error re-saving refined stories: {save_e}")
                         else: print("Warn: Cannot re-save stories, path unknown.")
                    else: print("(Log): No changes detected by Analyst."); print_ui(f"{COLOR_DIM}(No apparent changes){COLOR_RESET}")
                elif isinstance(refined_stories_result, str) and refined_stories_result == ANALYST_OUT_OF_SCOPE_SIGNAL:
                     print("(Log): Analyst indicated out of scope."); print_ui(f"{COLOR_YELLOW}Analyst: Feedback seems unrelated. Please rephrase.{COLOR_RESET}")
                else:
                     print(f"(Log): Refinement failed or returned unexpected result ({type(refined_stories_result)}).");
                     print_ui(f"{COLOR_YELLOW}Failed to refine stories. Please try different feedback.{COLOR_RESET}")
        # This line should ideally not be reached if the loop logic is correct
        print("(LeadAgent Log): Exiting Analyst feedback loop unexpectedly."); return False


    def _summarize_and_display_design(self, blueprint_text: str, required_libraries: list[str]):
        # (Method unchanged)
        print("(LeadAgent Log): Summarizing design blueprint for UI display...")
        purpose_line = "(Purpose not summarized)"; script_name = "(Not extracted)"

        # Summarize Purpose using the dedicated summarizer LLM
        if self.summarizer_llm and self.design_summarizer_template:
            if blueprint_text:
                try:
                    summary_prompt = PromptTemplate(template=self.design_summarizer_template, input_variables=["design_blueprint"])
                    summary_chain = summary_prompt | self.summarizer_llm | StrOutputParser()
                    animate_ui(f"{COLOR_DIM}Summarizing design purpose...{COLOR_RESET}", duration=0.8, interval=0.15)
                    raw_summary_output = summary_chain.invoke({"design_blueprint": blueprint_text})
                    clear_line_ui()
                    if raw_summary_output and raw_summary_output.strip(): purpose_line = raw_summary_output.strip().split('\n', 1)[0].strip()
                    else: print("(Log): Summarizer LLM returned empty output.")
                except Exception as e: clear_line_ui(); print(f"Error summarizing design: {e}"); purpose_line = "(Error during summarization)"
            else: purpose_line = "(No design details provided)"
        else: purpose_line = "(Purpose summary unavailable - LLM/template missing)"

        # Extract Script Name using Regex (Handles `Script: script_name.py`)
        try:
            script_name_pattern = r"^\s*Script:\s*[`'\"]?(\S+\.(?:py|ps1))[`'\"]?\s*$"
            match = re.search(script_name_pattern, blueprint_text, re.MULTILINE | re.IGNORECASE)
            if match:
                script_name = match.group(1).strip() # Get the captured filename
                self.project_context['main_script_name'] = script_name # Store in context immediately
                print(f"(LeadAgent Log): Extracted script name '{script_name}' for summary using 'Script:' pattern.")
            else:
                print(f"Warning (LeadAgent Log): Could not extract script name from blueprint using 'Script:' pattern.")
                self.project_context['main_script_name'] = None # Ensure it's None if not found
                script_name = "(Not extracted)" # Keep the default for display
        except Exception as regex_e:
             print(f"Error (LeadAgent Log): Regex error extracting script name for summary: {regex_e}"); traceback.print_exc()
             script_name = "(Error extracting)"
             self.project_context['main_script_name'] = None

        # Format for UI Display
        WRAP_WIDTH = 70; output_lines = []; purpose_prefix = "- Purpose : "; purpose_indent = " " * len(purpose_prefix)
        purpose_line_str = str(purpose_line) if purpose_line is not None else "(Purpose missing)"
        wrapped_purpose = textwrap.fill(purpose_line_str, width=WRAP_WIDTH, initial_indent=purpose_prefix, subsequent_indent=purpose_indent)
        output_lines.append(wrapped_purpose); commands_prefix = "- Main Script : "; output_lines.append(f"{commands_prefix}{script_name}")
        tech_prefix = "- Tech Stack : { "; tech_indent = " " * (len(tech_prefix) - 2); output_lines.append(tech_prefix.rstrip())
        if required_libraries:
             # Simple display logic, can be enhanced
             tech_list = sorted(list(set(required_libraries)))
             if 'python' not in [lib.lower() for lib in tech_list] and any(lib in ['os', 'sys', 'json'] for lib in tech_list):
                 tech_list.insert(0, 'Python (implied)') # Add implied Python if core builtins present
             wrapped_tech = textwrap.wrap(", ".join(tech_list), width=WRAP_WIDTH - len(tech_indent))
             for i, line in enumerate(wrapped_tech):
                 output_lines.append(f"{tech_indent}{line}{',' if i < len(wrapped_tech)-1 else ''}")
        else: output_lines.append(f"{tech_indent}(None specified or only built-ins)")
        output_lines.append(f"{tech_indent.rstrip()}}}")
        print_ui(""); # Blank line before summary
        for line in output_lines: print_ui(f"{COLOR_CYAN}{line}{COLOR_RESET}")
        print(f"(LeadAgent Log): Displayed formatted design summary to UI (Script Name: '{script_name}').")


    def _handle_designer_user_feedback(self) -> bool:
        # (Method unchanged - includes library vetting)
        print("(LeadAgent Log): Entering Designer user feedback loop...")
        ABSOLUTE_ESSENTIALS = {'python', 'os', 'sys', 'argparse'}
        rag_group_id = self.project_context.get("rag_matches", [{}])[0].get("group_id")
        if rag_group_id == 'G04': ABSOLUTE_ESSENTIALS.add('shutil') # Example adjustment

        current_blueprint = self.project_context.get("cli_design_blueprint")
        if not current_blueprint: print("Error Log: No blueprint context"); return False
        if not self.designer_available: print("Error Log: Designer unavailable"); return False
        if not self.designer_instance or not self.designer_instance.llm: print("Error Log: Designer instance/LLM not ready"); return False
        if not self.llm: print("Warn Log: Lead LLM not available for vetting.");
        if not self.design_vetting_template_str: print("Warn Log: Vetting prompt missing.");

        while True:
            current_blueprint_in_loop = self.project_context.get("cli_design_blueprint")
            current_design_libraries = self.project_context.get('cli_design_libraries', [])
            approved_user_stories = self.project_context.get('user_stories', [])
            if not current_blueprint_in_loop: print("Error Log: Blueprint disappeared mid-loop!"); return False

            log_context_switch("Designer", "Lead") # Signal user interaction start
            print_ui(f"\n{COLOR_GREY}Review Design Summary. Any changes needed? ('no' to approve):{COLOR_RESET} ", end="")
            try: user_feedback_raw = input(); user_feedback = user_feedback_raw.lower().strip();
            except EOFError: print_ui(f"\n{COLOR_YELLOW}Input stream closed.{COLOR_RESET}"); return False
            interpretation = self._interpret_feedback(user_feedback_raw)

            if interpretation == "approve": print_ui(f"{COLOR_GREEN}Design approved.{COLOR_RESET}"); print("Log: User approved design."); return True
            elif interpretation == "modify":
                if not user_feedback_raw.strip(): print_ui(f"{COLOR_YELLOW}Please provide specific feedback.{COLOR_RESET}"); continue
                feedback_words = user_feedback_raw.split(); library_to_remove = None; library_to_add = None; proceed_with_refinement = True

                # --- Handle Library Removal Request ---
                if ("remove" in feedback_words or "delete" in feedback_words or "exclude" in feedback_words):
                    current_libs_copy = list(current_design_libraries); lib_lower = None
                    for lib in current_libs_copy:
                         if lib.lower() in feedback_words: library_to_remove = lib; lib_lower = lib.lower(); break
                    if library_to_remove:
                        print(f"(Lead Log): Detected request to remove library: '{library_to_remove}'")
                        if lib_lower in ABSOLUTE_ESSENTIALS:
                             print(f"Log: Removal denied - '{library_to_remove}' is essential."); print_ui(f"{COLOR_YELLOW}(LeadAgent): Library '{library_to_remove}' is essential and cannot be removed.{COLOR_RESET}")
                             proceed_with_refinement = False; continue # Stay in loop, ask again
                        else:
                            # --- Library Removal Vetting ---
                            vetting_decision = "UNSAFE"; # Default to unsafe if vetting fails
                            if self.llm and self.design_vetting_template_str:
                                try:
                                    print("Log: Vetting library removal with LLM..."); animate_ui(f"{COLOR_DIM}Evaluating removal request...{COLOR_RESET}", duration=1.0, interval=0.15)
                                    # Use Designer's helper to format stories if needed, or just pass list
                                    stories_text_for_prompt = self.designer_instance._format_stories_for_prompt(approved_user_stories)
                                    vetting_prompt = PromptTemplate(template=self.design_vetting_template_str, input_variables=["user_stories_text", "current_blueprint_text", "library_to_remove"])
                                    vetting_chain = vetting_prompt | self.llm | StrOutputParser()
                                    vetting_result_raw = vetting_chain.invoke({"user_stories_text": stories_text_for_prompt, "current_blueprint_text": current_blueprint_in_loop, "library_to_remove": library_to_remove})
                                    clear_line_ui(); vetting_decision = vetting_result_raw.strip().upper(); print(f"Log: LLM Vetting Result: {vetting_decision}")
                                except Exception as vet_e: clear_line_ui(); print(f"Error Log: LLM vetting exception: {vet_e}"); print_ui(f"{COLOR_YELLOW}Warning: Error during removal check.{COLOR_RESET}")
                            else: print("Log: Skipping LLM vetting (LLM/Prompt unavailable)."); print_ui(f"{COLOR_YELLOW}Warning: Cannot automatically vet removal.{COLOR_RESET}")
                            # --- End Vetting ---

                            if vetting_decision == "SAFE":
                                print(f"Log: LLM deemed removal SAFE.")
                                updated_libs_list = [ctx_lib for ctx_lib in current_design_libraries if ctx_lib.lower() != lib_lower]
                                if len(updated_libs_list) < len(current_design_libraries):
                                     self.project_context['cli_design_libraries'] = updated_libs_list
                                     current_design_libraries = updated_libs_list # Update local copy for display
                                     print(f"Log: Updated context libs: {current_design_libraries}")
                                     print_ui(f"{COLOR_GREEN}(LeadAgent Info): Library '{library_to_remove}' marked for removal. Refining blueprint text accordingly.{COLOR_RESET}")
                                else: print(f"Log: Library '{library_to_remove}' wasn't in current list.")
                                proceed_with_refinement = True # Still refine blueprint text
                            else: # UNSAFE or unclear vetting
                                print(f"Log: LLM deemed removal UNSAFE or response unclear.")
                                print_ui(f"{COLOR_YELLOW}(LeadAgent): Evaluation suggests library '{library_to_remove}' may still be needed. Removal blocked.{COLOR_RESET}")
                                proceed_with_refinement = False; continue # Stay in loop, ask again
                    # If removal wasn't the primary focus, still proceed to general refinement
                    if not library_to_remove: proceed_with_refinement = True

                # --- Handle Library Addition Request ---
                elif ("add" in feedback_words or "include" in feedback_words or ("put" in feedback_words and "back" in feedback_words)):
                    potential_lib = None; action_index = -1
                    # Simple parsing: find action word, take next word
                    if "add" in feedback_words: action_index = feedback_words.index("add")
                    elif "include" in feedback_words: action_index = feedback_words.index("include")
                    elif "put" in feedback_words and "back" in feedback_words: action_index = feedback_words.index("put") # Handle "put back"
                    if action_index != -1 and action_index < len(feedback_words) - 1:
                         potential_lib = feedback_words[action_index + 1]
                         # Basic cleanup
                         potential_lib = potential_lib.strip('.,!?;:"\'').lower()
                         if potential_lib in ['module', 'library', 'the']: # Ignore filler words
                             if action_index < len(feedback_words) - 2: potential_lib = feedback_words[action_index + 2].strip('.,!?;:"\'').lower()
                             else: potential_lib = None
                    if potential_lib:
                        library_to_add = potential_lib # Keep it lower for comparison
                        print(f"(Lead Log): Detected request to add library: '{library_to_add}'")
                        # Check if already present (case-insensitive)
                        if library_to_add not in (l.lower() for l in current_design_libraries):
                            # Try to find original casing from initial list if possible
                            original_casing = library_to_add
                            for initial_lib in self.project_context.get('initial_essential_libraries', []):
                                if initial_lib.lower() == library_to_add: original_casing = initial_lib; break
                            current_design_libraries.append(original_casing) # Add with best guess casing
                            self.project_context['cli_design_libraries'] = current_design_libraries
                            print(f"(Log): Updated context libs: {current_design_libraries}")
                            print_ui(f"{COLOR_GREEN}(LeadAgent Info): Library '{original_casing}' added to requirements. Refining blueprint text.{COLOR_RESET}")
                        else: print(f"(Log): Library '{library_to_add}' already in list."); print_ui(f"{COLOR_DIM}(LeadAgent Info): Library '{library_to_add}' is already included.{COLOR_RESET}")
                        proceed_with_refinement = True # Refine blueprint text
                    else: print("(Log): Could not parse library name from add request. Proceeding with general text refinement."); proceed_with_refinement = True
                else: # No specific library add/remove detected, just general modification
                    proceed_with_refinement = True


                # --- Perform Blueprint Refinement ---
                if proceed_with_refinement:
                    print("Log: Delegating blueprint refinement to Designer."); log_context_switch("Lead", "Designer")
                    refined_blueprint_result = None
                    try:
                        refined_blueprint_result = self.designer_instance.refine_cli_design(current_blueprint_in_loop, user_feedback_raw.strip())
                    except Exception as refine_call_e: print(f"Error DURING designer refine call: {refine_call_e}"); traceback.print_exc(); refined_blueprint_result = None; print_ui(f"{COLOR_YELLOW}Error during design refinement call.{COLOR_RESET}")

                    if isinstance(refined_blueprint_result, str) and refined_blueprint_result.strip():
                        print("Log: Designer returned refined blueprint text.")
                        # --- IMPORTANT: Update context AFTER refinement ---
                        self.project_context["cli_design_blueprint"] = refined_blueprint_result
                        print(f"\n--- Refined Blueprint (LOG) ---\n{refined_blueprint_result}\n-----------------------------")
                        # --- Re-display the summary with potentially updated libs ---
                        self._summarize_and_display_design(refined_blueprint_result, self.project_context['cli_design_libraries']) # Use updated libs from context
                        if refined_blueprint_result == current_blueprint_in_loop and library_to_remove is None and library_to_add is None: print("Log: No textual changes detected in blueprint refinement."); print_ui(f"{COLOR_DIM}(No textual changes detected){COLOR_RESET}")
                    else: print(f"Log: Designer refinement failed or returned empty/None."); print_ui(f"{COLOR_YELLOW}Failed to refine blueprint text.{COLOR_RESET}")
                # --- End Blueprint Refinement ---
        # This line should not be reached if loop logic is correct
        print("(LeadAgent Log): Exiting Designer feedback loop unexpectedly."); return False


    # --- UPDATED Feedback Loop for Developer & Tester ---
    def _handle_developer_tester_feedback(self) -> bool:
        print("(LeadAgent Log): Entering Developer/Tester feedback and execution loop...")
        # Get necessary context items
        project_path = self.project_context.get("project_folder_path")
        script_name = self.project_context.get("main_script_name")
        blueprint = self.project_context.get("cli_design_blueprint", "")
        stories_path = self.project_context.get("user_stories_filepath") # Needed for Tester

        # Basic validation of context needed for this phase
        if not project_path or not script_name: print("Error Log (Dev/Test): Missing project path/script name."); return False
        if not os.path.isdir(project_path): print(f"Error Log (Dev/Test): Project path is not a directory: {project_path}"); return False
        current_script_path = os.path.normpath(os.path.join(project_path, script_name))
        if not os.path.exists(current_script_path):
            # If the script file doesn't exist here, it means the developer failed to save it initially.
            print(f"Error Log (Dev/Test): Script file missing at expected path: {current_script_path}");
            print_ui(f"{COLOR_YELLOW}Developer failed to create the initial script file. Cannot proceed with testing/feedback.{COLOR_RESET}")
            return False # Cannot proceed without the code file

        # --- Initial Test Run ---
        test_pass_status: bool | None = None # Can be None if testing fails entirely
        test_report: str | None = "(Testing Skipped - Agent Unavailable)"
        test_script_path: str | None = None
        first_run_error_context = None # Store errors from the first test run
        tester_instance = None # Keep instance for potential reuse

        if self.tester_available:
            log_context_switch("Developer", "Tester")
            print("(LeadAgent Log): Initiating automated test generation and execution...")
            try:
                tester_instance = TesterAgent(original_stdout_handle=utils.original_stdout)
                if not tester_instance or not tester_instance.code_generator or not tester_instance.code_generator.model:
                    print_ui(f"{COLOR_YELLOW}(LeadAgent): Tester Agent component error. Skipping tests.{COLOR_RESET}")
                    raise RuntimeError("Tester Agent Component Error")

                # Get latest developer code path (should be same as current_script_path initially)
                dev_code_path = self.project_context.get("generated_code_path", current_script_path) # Use context if available, fallback

                # Execute test generation AND the initial run
                test_pass_status, test_report, test_script_path = tester_instance.execute_test_generation(
                    blueprint_text=blueprint,
                    developer_code_path=dev_code_path, # Use the actual path of generated code
                    project_folder_path=project_path,
                    user_stories_json_path=stories_path
                )
                # Update context with test results
                self.project_context['test_status'] = test_pass_status
                self.project_context['test_report'] = test_report
                self.project_context['test_script_path'] = test_script_path # Store path

                if test_pass_status is None: # Generation/Extraction failed
                     print_ui(f"{COLOR_YELLOW}(LeadAgent): Failed to generate or run initial tests. Check logs.{COLOR_RESET}")
                     # test_report might contain the error message from the tester agent
                elif test_pass_status is False:
                    first_run_error_context = test_report # Store the failure report for potential dev feedback
                    print_ui(f"{COLOR_RED}Initial tests FAILED.{COLOR_RESET}")
                    # Optionally display summary here if needed
                    # print_ui(f"{COLOR_DIM}Failure Report:\n{test_report[:500]}...{COLOR_RESET}")
                else:
                    print_ui(f"{COLOR_GREEN}Initial tests PASSED.{COLOR_RESET}")

            except Exception as test_e:
                 print(f"Error during Tester execution: {test_e}"); traceback.print_exc()
                 print_ui(f"{COLOR_YELLOW}Error running automated tests.{COLOR_RESET}")
                 test_pass_status = False; test_report = f"Error during testing: {test_e}"
                 first_run_error_context = traceback.format_exc()
                 self.project_context['test_status'] = test_pass_status
                 self.project_context['test_report'] = test_report
            finally:
                 log_context_switch("Tester", "Lead") # Switch context back after test phase
        else:
            print("(LeadAgent Log): Tester unavailable. Skipping automated tests.");
            self.project_context['test_status'] = None # Indicate tests weren't run
            self.project_context['test_report'] = test_report
            test_pass_status = True # Assume pass if no tester available for workflow progression, or handle as needed

        # --- User Feedback Loop ---
        while True:
            log_context_switch("Lead", "User") # Signal interaction start

            # Display current status
            print_ui(f"\n--- Current Status ---")
            if test_pass_status is None:
                print_ui(f"{COLOR_YELLOW}- Tests: Generation/Execution Failed.{COLOR_RESET}")
                if test_report: print_ui(f"{COLOR_DIM}  Reason: {test_report[:100]}...{COLOR_RESET}")
            elif test_pass_status:
                print_ui(f"{COLOR_GREEN}- Tests: Passed.{COLOR_RESET}")
            else:
                print_ui(f"{COLOR_RED}- Tests: Failed.{COLOR_RESET}")
                if test_report: print_ui(f"{COLOR_DIM}  Report Snippet:\n{test_report[:300]}...{COLOR_RESET}")
            print_ui(f"{COLOR_GREY}----------------------{COLOR_RESET}")

            prompt_msg = "Review code/tests. Any changes? ('no' to approve):"
            if test_pass_status is False:
                 prompt_msg = f"{COLOR_YELLOW}Tests failed.{COLOR_RESET} Provide feedback for Developer/Tester? ('no' to approve anyway):"

            print_ui(f"\n{prompt_msg} ", end="")

            try: user_feedback_raw = input()
            except EOFError: print_ui(f"\n{COLOR_YELLOW}Input stream closed.{COLOR_RESET}"); return False

            interpretation = self._interpret_feedback(user_feedback_raw)

            if interpretation == "approve":
                 print_ui(f"{COLOR_GREEN}(LeadAgent): Code approved by user.{COLOR_RESET}")
                 if test_pass_status is False: print_ui(f"{COLOR_YELLOW}(Warning: Approving code with failing tests){COLOR_RESET}")
                 return True # Exit the feedback loop successfully

            elif interpretation == "modify":
                if not user_feedback_raw.strip():
                     print_ui(f"{COLOR_YELLOW}Please provide specific feedback for the developer or tester.{COLOR_RESET}"); continue

                # --- Determine Target: Developer or Tester ---
                feedback_lower = user_feedback_raw.lower()
                target_agent = "Developer" # Default to Developer
                if self.tester_available and self.project_context.get('test_script_path'):
                    # If feedback mentions test-related terms, target Tester
                    if any(keyword in feedback_lower for keyword in ["test", "tests", "assert", "verify", "tester", "fixture"]):
                        target_agent = "Tester"
                elif any(keyword in feedback_lower for keyword in ["test", "tests", "assert", "verify", "tester", "fixture"]):
                    # Tester mentioned but unavailable/no script path
                     print_ui(f"{COLOR_YELLOW}(LeadAgent): Feedback seems test-related, but Tester is unavailable or test script path is missing. Directing to Developer.{COLOR_RESET}")

                # --- Code Refinement (Developer) ---
                if target_agent == "Developer":
                    if not self.developer_available:
                         print_ui(f"{COLOR_YELLOW}(LeadAgent): Developer unavailable. Cannot refine code.{COLOR_RESET}"); continue

                    print("(LeadAgent Log): Delegating code refinement to Developer Agent..."); log_context_switch("Lead", "Developer")
                    developer_instance = None; refined_code = None
                    try:
                        developer_instance = DeveloperAgent(original_stdout_handle=utils.original_stdout)
                        if not developer_instance or not developer_instance.code_generator or not developer_instance.code_generator.model:
                             print_ui(f"{COLOR_YELLOW}(LeadAgent): Developer Agent not ready.{COLOR_RESET}"); raise RuntimeError("Developer Agent Component Error")

                        # Read the absolute latest code from the file system before refinement
                        latest_code_content = None
                        try:
                             with open(current_script_path, 'r', encoding='utf-8') as f_read: latest_code_content = f_read.read()
                        except Exception as read_err:
                             print(f"Error Log: Failed to re-read code from {current_script_path}: {read_err}")
                             raise RuntimeError(f"Cannot read code file for refinement: {current_script_path}") from read_err

                        if not latest_code_content: print("Error Log: Lost code context before refinement!"); raise RuntimeError("Missing generated code context")

                        # Provide error context ONLY if tests failed previously in this loop
                        error_ctx_for_dev = test_report if test_pass_status is False else None

                        refined_code = developer_instance.execute_code_refinement(
                            current_code=latest_code_content,
                            blueprint_text=blueprint,
                            user_feedback=user_feedback_raw.strip(),
                            error_context=error_ctx_for_dev, # Pass relevant error context
                            script_path=current_script_path # Pass the path for saving
                        )
                    except Exception as dev_refine_e: print(f"Error during Developer refinement call: {dev_refine_e}"); traceback.print_exc(); print_ui(f"{COLOR_YELLOW}Error occurred during code refinement.{COLOR_RESET}"); refined_code = None
                    finally: log_context_switch("Developer", "Lead") # Context switch back

                    if refined_code:
                        print("(LeadAgent Log): Developer returned refined code.");
                        self.project_context["generated_code"] = refined_code # Update context with the *string* content
                        print_ui(f"{COLOR_GREEN}(LeadAgent): Code refined by Developer.{COLOR_RESET}")

                        # --- Trigger Re-Testing ---
                        if self.tester_available:
                            log_context_switch("Lead", "Tester")
                            print("(LeadAgent Log): Re-running tests after Developer refinement...")
                            try:
                                current_test_script_path = self.project_context.get('test_script_path')
                                if tester_instance and current_test_script_path and os.path.exists(current_test_script_path):
                                    # Re-run tests using the existing test script
                                    test_pass_status, test_report = tester_instance._run_tests(project_path, os.path.basename(current_test_script_path))
                                    # Update context
                                    self.project_context['test_status'] = test_pass_status
                                    self.project_context['test_report'] = test_report
                                    # Update error context ONLY IF tests failed again
                                    # first_run_error_context = test_report if test_pass_status is False else None # Reset if pass
                                else:
                                     print("Error: Tester instance or test path lost/invalid during re-run.");
                                     test_pass_status = None; test_report = "Error re-running tests: context/path lost."
                                     self.project_context['test_status'] = test_pass_status
                                     self.project_context['test_report'] = test_report
                            except Exception as test_e:
                                 print(f"Error during Tester re-run: {test_e}"); traceback.print_exc();
                                 print_ui(f"{COLOR_YELLOW}Error re-running tests.{COLOR_RESET}")
                                 test_pass_status = False; test_report = f"Error re-testing: {test_e}"
                                 # first_run_error_context = traceback.format_exc()
                                 self.project_context['test_status'] = test_pass_status
                                 self.project_context['test_report'] = test_report
                            finally:
                                 log_context_switch("Tester", "Lead")
                        else:
                             # No tester, assume pass for workflow
                             test_pass_status = True;
                             # first_run_error_context = None; # Reset error context
                             self.project_context['test_status'] = None # Still mark as not run
                        # --- End Re-Testing ---
                    else:
                        print("(LeadAgent Log): Developer refinement failed or returned None.");
                        print_ui(f"{COLOR_YELLOW}(LeadAgent): Failed to refine code. Please try different feedback.{COLOR_RESET}")
                        # Test status remains unchanged from before the failed refinement attempt

                # --- Test Refinement (Tester) ---
                elif target_agent == "Tester":
                    # --- Placeholder for Tester Refinement ---
                    print_ui(f"{COLOR_YELLOW}(LeadAgent): Test refinement is not yet implemented.{COLOR_RESET}")
                    print("(LeadAgent Log): Test refinement requested but not implemented. Skipping.")
                    # If/When implemented:
                    # log_context_switch("Lead", "Tester")
                    # Call tester_instance.execute_test_refinement(...)
                    # Receive new test_pass_status, test_report
                    # Update context: self.project_context['test_status'] = ... etc.
                    # log_context_switch("Tester", "Lead")
                    # --- End Placeholder ---
                    continue # Go back to loop prompt as nothing changed

        # This line should not be reached if loop logic is correct
        print("(LeadAgent Log): Exiting Dev/Test feedback loop unexpectedly."); return False
    
    # --- Main Execution Flow ---
    # --- Main Execution Flow ---
    def run(self):
        print(f"{COLOR_BOLD}{COLOR_MAGENTA}--- Starting Agentic Workflow ---{COLOR_RESET}")
        stories_approved = False
        design_approved = False
        scaffold_created = False
        code_generated_successfully = False
        code_approved = False
        top_match_info = None

        # --- Phase 1: RAG Search & Context Gathering ---
        log_context_switch("User", "RAG")
        try:
            context_gathered = self._run_initial_rag_phase()
            if not context_gathered: return # Exit if no user input
            rag_matches = self.project_context.get("rag_matches", [])
            if not rag_matches:
                print_ui(f"\n{COLOR_YELLOW}No relevant code exemplars found. Cannot proceed.{COLOR_RESET}"); return
            top_match_info = rag_matches[0] # Select the top match for subsequent phases
            print(f"(LeadAgent Log): Top RAG match selected: {top_match_info.get('template_name', 'N/A')}")
        except Exception as phase1_e:
            print(f"Error (LeadAgent Run): Unhandled RAG phase exception: {phase1_e}"); traceback.print_exc();
            print_ui(f"\n{COLOR_YELLOW}Error during initial search.{COLOR_RESET}"); return

        # --- Phase 2: Analysis (User Stories) ---
        ba_instructions = None
        if self.analyst_available:
            try:
                ba_instructions = self._initiate_analysis_phase()
                if not ba_instructions: print_ui(f"{COLOR_YELLOW}(LeadAgent): Failed to generate instructions for Analyst.{COLOR_RESET}"); return
                self.project_context['ba_instructions'] = ba_instructions
            except Exception as phase2_e:
                print(f"Error (LeadAgent Run): BA instruction phase exception: {phase2_e}"); traceback.print_exc();
                print_ui(f"\n{COLOR_YELLOW}Error preparing for Analyst.{COLOR_RESET}"); return

            # --- Execute Analyst ---
            try:
                default_stories_filename = ANALYST_DEFAULT_FILENAME or "user_stories_output.json"
                analyst_instance = BusinessAnalystAgent( output_dir=ANALYST_OUTPUT_DIR, original_stdout_handle=utils.original_stdout )
                if analyst_instance.llm:
                     generated_stories, saved_filepath = analyst_instance.generate_user_stories( ba_instructions, default_stories_filename )
                     if generated_stories:
                          self.project_context['user_stories'] = generated_stories; self.project_context['user_stories_filepath'] = saved_filepath
                          print(f"(LeadAgent Log): Analyst generated {len(generated_stories)} stories (Saved to: {saved_filepath}).")
                          analyst_instance._print_stories_table(generated_stories)
                          stories_approved = self._handle_analyst_user_feedback() # Feedback loop
                     else: print_ui(f"{COLOR_YELLOW}Analyst generated no stories.{COLOR_RESET}"); stories_approved = False
                else: print_ui(f"{COLOR_YELLOW}Analyst not ready (LLM init failed?).{COLOR_RESET}"); stories_approved = False
            except Exception as ba_run_e:
                print(f"Error (LeadAgent Run): BA Agent execution exception: {ba_run_e}"); traceback.print_exc();
                print_ui(f"{COLOR_YELLOW}An error occurred running the Analyst Agent.{COLOR_RESET}"); stories_approved = False
        else:
            print("(LeadAgent Log): Skipping Analysis phase (Analyst unavailable).")
            print_ui(f"{COLOR_YELLOW}Analyst agent is unavailable. Workflow cannot continue.{COLOR_RESET}"); return # Exit

        # --- Phase 3: Design (Blueprint) ---
        if stories_approved:
            if self.designer_available:
                log_context_switch("Analyst", "Designer")
                try:
                    if not self.designer_instance: self.designer_instance = DesignerAgent(original_stdout_handle=utils.original_stdout)
                    if self.designer_instance and self.designer_instance.llm:
                        initial_design, design_libraries = self.designer_instance.generate_cli_design( self.project_context["user_stories"], self.project_context.get("ba_instructions", ""), top_match_info )
                        if initial_design:
                            self.project_context['cli_design_blueprint'] = initial_design; self.project_context['cli_design_libraries'] = design_libraries
                            self.project_context['initial_essential_libraries'] = list(design_libraries) # Keep original list
                            print("(LeadAgent Log): Initial design generated by Designer.")
                            self._summarize_and_display_design(initial_design, design_libraries)
                            design_approved = self._handle_designer_user_feedback() # Feedback loop
                        else: print("(LeadAgent Log): Designer failed to generate initial blueprint."); print_ui(f"{COLOR_YELLOW}Designer could not generate the blueprint.{COLOR_RESET}"); design_approved = False; log_context_switch("Designer", "Lead")
                    else: print_ui(f"{COLOR_YELLOW}Designer agent not ready (LLM init failed?).{COLOR_RESET}"); design_approved = False; log_context_switch("Designer", "Lead")
                except Exception as designer_run_e:
                    print(f"Error (LeadAgent Run): Designer execution exception: {designer_run_e}"); traceback.print_exc();
                    print_ui(f"{COLOR_YELLOW}An error occurred running the Designer Agent.{COLOR_RESET}"); design_approved = False; log_context_switch("Designer", "Lead")
            else: print("(LeadAgent Log): Skipping Design phase (Designer unavailable)."); print_ui(f"{COLOR_YELLOW}Designer agent is unavailable. Workflow cannot continue.{COLOR_RESET}"); log_context_switch("Analyst", "Lead"); return # Exit
        else: print("(LeadAgent Log): Skipping Design phase (Stories not approved or Analyst failed).")

        # --- Phase 4: Scaffold, Code Generation, and Testing ---
        developer_handoff_package = None
        if stories_approved and design_approved:
            print("(LeadAgent Log): Design approved. Triggering project scaffold creation...")
            if self.designer_instance:
                try:
                    approved_blueprint = self.project_context.get('cli_design_blueprint')
                    final_libs = self.project_context.get('cli_design_libraries', [])
                    if not top_match_info: # Ensure RAG info is still available
                        rag_matches = self.project_context.get("rag_matches", [])
                        if rag_matches: top_match_info = rag_matches[0]
                    if not top_match_info: raise ValueError("Missing RAG match info for scaffold")

                    scaffold_created = self.designer_instance.create_project_scaffold( approved_blueprint, final_libs, top_match_info )
                    if scaffold_created:
                        print("(LeadAgent Log): Designer scaffold successful. Preparing handoff...")
                        developer_handoff_package = self.designer_instance._prepare_developer_handoff( approved_blueprint, final_libs, top_match_info )
                        if developer_handoff_package:
                             self.project_context['project_folder_path'] = developer_handoff_package['project_folder_path']
                             self.project_context['main_script_name'] = developer_handoff_package['script_name']
                             print(f"(LeadAgent Log): Handoff ready. Project Path: {self.project_context['project_folder_path']}")
                        else: print("Error (LeadAgent): Failed to get developer handoff package from Designer."); print_ui(f"{COLOR_YELLOW}Internal error preparing for developer.{COLOR_RESET}"); scaffold_created = False
                    else: print("(LeadAgent Log): Designer scaffold creation failed (returned False)."); print_ui(f"{COLOR_YELLOW}Failed project structure creation.{COLOR_RESET}")
                except Exception as scaffold_call_e: print(f"Error (LeadAgent Log): Exception calling Designer scaffold/handoff: {scaffold_call_e}"); traceback.print_exc(); print_ui(f"{COLOR_YELLOW}Error during scaffold creation/handoff.{COLOR_RESET}"); scaffold_created = False
            else: print("Error (LeadAgent Log): Designer instance missing for scaffold."); print_ui(f"{COLOR_YELLOW}Internal error (Designer instance).{COLOR_RESET}"); scaffold_created = False

            # --- Developer and Tester Execution ---
            if scaffold_created and developer_handoff_package:
                if self.developer_available:
                     log_context_switch("Designer", "Developer")
                     print("(LeadAgent Log): Proceeding to Developer Agent with full context...")
                     developer_instance = None
                     try:
                         developer_instance = DeveloperAgent(original_stdout_handle=utils.original_stdout)
                         if developer_instance and developer_instance.code_generator and developer_instance.code_generator.model:
                             stories_json_filepath = self.project_context.get("user_stories_filepath")
                             if not stories_json_filepath: # Attempt to default if needed
                                 print("Warning (LeadAgent Log): User stories file path not found. Attempting default.")
                                 if self.analyst_available: stories_json_filepath = os.path.join(ANALYST_OUTPUT_DIR, ANALYST_DEFAULT_FILENAME)
                                 else: stories_json_filepath = None
                             if not stories_json_filepath or not os.path.exists(stories_json_filepath):
                                 print(f"Error (LeadAgent Log): Cannot call Developer without valid user stories JSON path (Tried: {stories_json_filepath}).")
                                 print_ui(f"{COLOR_YELLOW}Internal error: Missing stories path for Developer.{COLOR_RESET}")
                                 raise ValueError("Missing required user stories JSON file")

                             print(f"(LeadAgent Log): Passing stories JSON path '{stories_json_filepath}' to Developer.")
                             generated_code_content = developer_instance.execute_code_generation(
                                 **developer_handoff_package,
                                 user_stories_json_path=stories_json_filepath
                             )
                             if generated_code_content:
                                 script_name_generated = developer_handoff_package['script_name']
                                 generated_code_path = os.path.join(developer_handoff_package['project_folder_path'], script_name_generated)
                                 print(f"(LeadAgent Log): Developer generated code for {script_name_generated}.")
                                 self.project_context['generated_code'] = generated_code_content # Store content
                                 self.project_context['generated_code_path'] = generated_code_path # Store path
                                 code_generated_successfully = True

                                 # ---> Trigger the integrated feedback/testing loop <---
                                 code_approved = self._handle_developer_tester_feedback()
                                 # ---> Feedback loop handles context switching internally <---

                             else: # Developer failed code generation
                                 print("(LeadAgent Log): Developer Agent failed code generation (returned None)."); print_ui(f"{COLOR_YELLOW}Developer failed to generate code.{COLOR_RESET}");
                                 code_generated_successfully = False; log_context_switch("Developer", "Lead")
                         else: print("(LeadAgent Log): Developer Agent or its Native Generator not ready."); print_ui(f"{COLOR_YELLOW}Developer agent component error.{COLOR_RESET}"); code_generated_successfully = False; log_context_switch("Developer", "Lead")
                     except Exception as dev_run_e:
                         print(f"Error (LeadAgent Run): Developer execution exception: {dev_run_e}"); traceback.print_exc();
                         print_ui(f"{COLOR_YELLOW}An error occurred running the Developer Agent.{COLOR_RESET}"); code_generated_successfully = False; log_context_switch("Developer", "Lead")
                else: print("(LeadAgent Log): Skipping Code Generation (Developer unavailable)."); print_ui(f"{COLOR_YELLOW}Developer agent is unavailable.{COLOR_RESET}"); log_context_switch("Designer", "Lead")
            elif not scaffold_created: print("(LeadAgent Log): Skipping Code Generation phase (Scaffold failed)."); log_context_switch("Designer", "Lead")
            else: print("(LeadAgent Log): Skipping Code Generation phase (Developer Handoff failed)."); log_context_switch("Designer", "Lead")
        elif stories_approved and not design_approved: print("(LeadAgent Log): Skipping final phase (Design not approved).")
        elif not stories_approved: print("(LeadAgent Log): Skipping final phase (Stories not approved).")
        else: print("(LeadAgent Log): Skipping final phase (Workflow did not reach scaffold stage).")


        # --- Final Summary & Auto-Execution ---
        print(f"\n{COLOR_BOLD}{COLOR_MAGENTA}--- Agentic Workflow Finished ---{COLOR_RESET}")

        final_message = ""
        project_path_final = self.project_context.get('project_folder_path', '')
        final_test_status = self.project_context.get('test_status') # Get final test status from context

        # Determine the final summary message *before* potential execution output
        if stories_approved and design_approved and scaffold_created and code_generated_successfully and code_approved:
            test_msg = ""
            if self.tester_available: # Only mention tests if tester was supposed to run
                if final_test_status is True: test_msg = f" ({COLOR_GREEN}Tests Passed{COLOR_RESET})"
                elif final_test_status is False: test_msg = f" ({COLOR_YELLOW}Tests Failed - Approved Anyway{COLOR_RESET})"
                elif final_test_status is None: test_msg = f" ({COLOR_RED}Test Generation/Execution Failed{COLOR_RESET})"
                else: test_msg = f" ({COLOR_DIM}Test Status Unknown{COLOR_RESET})" # Fallback

            final_message = (f"\n{COLOR_GREEN}{COLOR_BOLD}Workflow Complete!{COLOR_RESET} Project created & code approved"
                             f"{test_msg} in:\n{project_path_final}")
        elif stories_approved and design_approved and scaffold_created and code_generated_successfully and not code_approved:
             final_message = (f"\n{COLOR_YELLOW}{COLOR_BOLD}Workflow Halted.{COLOR_RESET} Code generated but not approved by user."
                              f" Project files are in:\n{project_path_final}")
        elif stories_approved and design_approved and scaffold_created and not code_generated_successfully:
             final_message = (f"\n{COLOR_YELLOW}{COLOR_BOLD}Workflow Halted.{COLOR_RESET} Scaffold created, but code generation failed."
                              f" Check logs. Structure is in:\n{project_path_final}")
        elif stories_approved and design_approved and not scaffold_created:
             final_message = f"\n{COLOR_YELLOW}{COLOR_BOLD}Workflow Halted.{COLOR_RESET} Design approved, but scaffold creation failed."
        elif stories_approved and not design_approved:
             final_message = f"\n{COLOR_YELLOW}{COLOR_BOLD}Workflow Halted.{COLOR_RESET} Design not finalized."
        else: # Primarily handles stories_approved == False
             final_message = f"\n{COLOR_YELLOW}{COLOR_BOLD}Workflow Halted.{COLOR_RESET} Stories not approved or initial phases failed."


        # --- WINDOWS-ONLY Auto-Execution Step: Install Req, Clear Screen & Run Script via PowerShell ---
        if stories_approved and design_approved and scaffold_created and code_generated_successfully and code_approved:
            print("(LeadAgent Log): Workflow successful and approved. Attempting install, clear & run via PowerShell (Windows).")
            working_dir = self.project_context.get('project_folder_path')
            script_name = self.project_context.get('main_script_name')
            python_cmd = "python" # Assumes 'python' is in PATH for PowerShell

            if working_dir and script_name:
                # Construct the full path to the script and requirements file
                script_path = os.path.normpath(os.path.join(working_dir, script_name))
                requirements_path = os.path.normpath(os.path.join(working_dir, "requirements.txt"))

                # Ensure the working directory and the script file exist
                if os.path.isdir(working_dir) and os.path.exists(script_path):

                    print_ui(f"\n{COLOR_YELLOW}--- Attempting to install requirements, clear screen, and run script in new PowerShell window ---{COLOR_RESET}")
                    print_ui(f"{COLOR_DIM}Directory: {working_dir}{COLOR_RESET}")
                    print_ui(f"{COLOR_DIM}Script: {script_path}{COLOR_RESET}")

                    # Check for requirements.txt *before* launching PowerShell for logging purposes
                    install_logic = ""
                    if os.path.exists(requirements_path):
                        print(f"(LeadAgent Log): Found requirements.txt at {requirements_path}. Will attempt installation in new window.")
                        print_ui(f"{COLOR_DIM}Requirements: requirements.txt found - will attempt install{COLOR_RESET}")
                        # PowerShell command sequence to install requirements if file exists
                        # Ends with a semicolon to chain commands
                        install_logic = (
                            f"if (Test-Path -Path '{requirements_path}') {{ "
                            f"Write-Host ''; Write-Host '--- Installing requirements ---'; pip install -r '{requirements_path}'; Write-Host '--- Requirement installation finished ---'; Write-Host '' "
                            f"}} else {{ Write-Host 'No requirements.txt found, skipping install.' }}; "
                        )
                    else:
                        print("(LeadAgent Log): No requirements.txt found. Skipping installation step.")
                        print_ui(f"{COLOR_DIM}Requirements: requirements.txt not found{COLOR_RESET}")
                        # install_logic remains empty

                    print_ui(f"{COLOR_GREY}------------------------------------------------------------------------------------------{COLOR_RESET}")

                    # Define the clear screen and run script commands
                    clear_screen_command = "cls" # PowerShell alias for Clear-Host
                    run_script_command = f"Write-Host '--- Running script: {script_name} ---'; {python_cmd} '{script_path}'"

                    # Combine all commands: Set Location -> Install Logic (if any) -> Clear Screen -> Run Script
                    command_to_run_in_powershell = f"Set-Location -Path '{working_dir}'; {install_logic}{clear_screen_command}; {run_script_command}"

                    # The command list for Popen
                    full_command = ['start', 'powershell', '-NoExit', '-Command', command_to_run_in_powershell]
                    shell_needed = True # 'start' requires shell=True

                    try:
                        print(f"(LeadAgent Log): Using PowerShell command: {' '.join(full_command)}")
                        print(f"(LeadAgent Log): Inner command for PowerShell: {command_to_run_in_powershell}")

                        # Use Popen to launch the terminal independently (non-blocking)
                        subprocess.Popen(full_command, shell=shell_needed)
                        print("(LeadAgent Log): Launched command to open PowerShell, install (if needed), clear, and run script.")
                        print_ui(f"{COLOR_GREEN}--- New PowerShell window should be opening... ---{COLOR_RESET}")
                        print_ui(f"{COLOR_DIM}(Installation (if any) will run, then screen clears, then script runs in new window){COLOR_RESET}")

                    except FileNotFoundError:
                         error_msg = f"Error: Command failed ('start' or 'powershell' not found?). Check system PATH."
                         print(f"(LeadAgent Log): {error_msg}")
                         print_ui(f"\n{COLOR_RED}{error_msg}{COLOR_RESET}")
                    except Exception as term_e:
                         error_msg = f"Error launching install/run process via PowerShell: {term_e}"
                         print(f"(LeadAgent Log): {error_msg}"); traceback.print_exc()
                         print_ui(f"\n{COLOR_RED}{error_msg}\nPlease try running manually in:{COLOR_RESET}\n{working_dir}")

                    print_ui(f"{COLOR_GREY}------------------------------------------------------------------------------------------{COLOR_RESET}")

                else: # Working directory or script doesn't exist
                    missing = []
                    if not os.path.isdir(working_dir): missing.append("project directory")
                    if not os.path.exists(script_path): missing.append("script file")
                    print(f"(LeadAgent Log): Cannot run script - missing {', '.join(missing)} at {working_dir} / {script_name}")
                    print_ui(f"\n{COLOR_YELLOW}Could not auto-run script: Required {', '.join(missing)} not found.{COLOR_RESET}")
            else:
                missing_ctx = []
                if not working_dir: missing_ctx.append("project path (working directory)")
                if not script_name: missing_ctx.append("script name")
                print(f"(LeadAgent Log): Skipping auto-run - missing from context: {', '.join(missing_ctx)}.")
                print_ui(f"\n{COLOR_YELLOW}Could not auto-run script: Missing context ({', '.join(missing_ctx)}).{COLOR_RESET}")
        else:
             print("(LeadAgent Log): Skipping auto-run as workflow was not fully successful or approved.")

        # --- Final Summary Message (Now printed AFTER auto-run attempt) ---
        print_ui(final_message)
        print("(LeadAgent Log): Run sequence complete.")

    # --- END of run method ---
# --- END of LeadAgent Class ---