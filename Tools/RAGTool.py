import os
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
import sys
import json
import re
import time
from collections import defaultdict

# --- Configuration ---
# Moved relevant configs here
SENTENCE_TRANSFORMER_MODEL = 'all-mpnet-base-v2'
COLLECTION_NAME = 'template_rag_collection_v2'
N_RESULTS_CANDIDATES = 15
DISTANCE_THRESHOLD = 1.05
MIN_COMPONENT_SCORE_THRESHOLD = 2
COMPONENT_NAME_WEIGHT = 2

# --- Load Environment Variables ---
load_dotenv()
CHROMA_DB_PATH = os.getenv('CHROMADB_PATH', './chroma_db')

class TemplateRetriever:
    """
    Tool responsible for connecting to ChromaDB and retrieving relevant
    template information based on a query.
    """
    def __init__(self):
        self.client = None
        self.collection = None
        self.is_initialized = False
        self.error_message = None
        self._initialize_db() # Attempt initialization on creation

    # --- Helper Functions (Internal) ---
    def _simple_tokenize(self, text):
        # (Keep the same simple_tokenize function)
        if not text: return set()
        words = re.findall(r'[A-Z]?[a-z]+|\d+|[A-Z]+(?![a-z])', text)
        return set(word.lower() for word in words if len(word) > 1)

    def _calculate_keyword_overlap(self, prompt_tokens, target_text):
        # (Keep the same calculate_keyword_overlap function)
        if not prompt_tokens or not target_text: return 0
        target_tokens = self._simple_tokenize(target_text)
        if not target_tokens: return 0
        intersection = prompt_tokens.intersection(target_tokens)
        return len(intersection)

    # --- Initialization ---
    def _initialize_db(self):
        """Initializes ChromaDB connection."""
        if self.is_initialized: return True
        print("[RAGTool] Initializing knowledge base connection...") # Log internal status
        try:
            if not CHROMA_DB_PATH: raise ValueError("CHROMADB_PATH env var not set.")
            if not os.path.exists(CHROMA_DB_PATH): raise FileNotFoundError(f"ChromaDB path '{CHROMA_DB_PATH}' does not exist.")

            self.client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
            # Fast check for collection existence before loading heavy model
            collections = self.client.list_collections()
            if COLLECTION_NAME not in [col.name for col in collections]:
                 raise ValueError(f"Collection '{COLLECTION_NAME}' not found.")

            st_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=SENTENCE_TRANSFORMER_MODEL)
            self.collection = self.client.get_collection(name=COLLECTION_NAME, embedding_function=st_ef)
            count = self.collection.count()
            self.is_initialized = True
            print(f"[RAGTool] Initialization successful ({count} items loaded).")
            return True
        except Exception as e:
            self.error_message = f"FATAL [RAGTool]: Failed to initialize knowledge base: {e}"
            print(self.error_message, file=sys.stderr)
            self.client = None; self.collection = None; self.is_initialized = False
            return False

    # --- Main Retrieval Method ---
    def find_matches(self, user_prompt):
        """
        Finds relevant templates and component(s) based on the query.
        Returns a LIST of matching dictionaries, sorted by relevance, or an empty list.
        """
        if not self.is_initialized:
             print("[RAGTool] Error: Not initialized.", file=sys.stderr)
             return [] # Cannot proceed if not initialized
        if not user_prompt: return []

        prompt_tokens = self._simple_tokenize(user_prompt)
        if not prompt_tokens: return []

        all_matches = []
        results = None
        try:
            # print(f"[RAGTool Debug] Querying for: '{user_prompt[:50]}...'") # Optional Debug
            results = self.collection.query(
                query_texts=[user_prompt],
                n_results=N_RESULTS_CANDIDATES,
                include=['metadatas', 'distances']
            )
        except Exception as e:
            print(f"[RAGTool] Error querying knowledge base: {e}", file=sys.stderr)
            return [] # Return empty list on query error

        if results and results.get('ids') and results['ids'][0]:
            ids = results['ids'][0]; distances = results['distances'][0]; metadatas = results['metadatas'][0]
            # print(f"[RAGTool Debug] Processing {len(ids)} candidates...") # Optional Debug

            for i, dist in enumerate(distances):
                if dist > DISTANCE_THRESHOLD: continue
                metadata = metadatas[i]; project_id = metadata.get('project_id')
                if not project_id: continue
                project_name = metadata.get('project_name', 'N/A'); group_name = metadata.get('group_name', 'N/A')
                group_id = metadata.get('template_group_id', 'N/A'); code_template = metadata.get('code_template', 'N/A')
                component_details = []; best_components_info = []; max_weighted_score = -1
                try:
                    component_details_json = metadata.get('component_details', '[]')
                    if component_details_json and component_details_json != '[]': component_details = json.loads(component_details_json)
                except json.JSONDecodeError: pass
                current_template_best_score = 0; final_component_names = ["(No specific components listed)"]
                if not component_details:
                     base_context = f"{project_name} {group_name}"; overall_score = self._calculate_keyword_overlap(prompt_tokens, base_context)
                     if overall_score >= 1: current_template_best_score = overall_score
                     else: continue
                else:
                    for comp in component_details:
                        comp_name = comp.get('name', 'N/A'); comp_features_str = " ".join(comp.get('features', []))
                        name_score = self._calculate_keyword_overlap(prompt_tokens, comp_name); feature_score = self._calculate_keyword_overlap(prompt_tokens, comp_features_str)
                        weighted_score = (name_score * COMPONENT_NAME_WEIGHT) + feature_score
                        if weighted_score >= MIN_COMPONENT_SCORE_THRESHOLD:
                            best_components_info.append((weighted_score, name_score, comp_name))
                            if weighted_score > max_weighted_score: max_weighted_score = weighted_score
                    if not best_components_info: continue
                    current_template_best_score = max_weighted_score
                    top_components_info = [info for info in best_components_info if info[0] == max_weighted_score]
                    if len(top_components_info) > 1:
                        max_name_score = max(info[1] for info in top_components_info)
                        final_components_info = [info for info in top_components_info if info[1] == max_name_score]
                    else: final_components_info = top_components_info
                    final_component_names = sorted([info[2] for info in final_components_info])
                all_matches.append({
                    "distance": dist,
                    "score": current_template_best_score,
                    "group_id": group_id,
                    "group_name": group_name,
                    "template_id": project_id,
                    "template_name": project_name,
                    "relevant_components": final_component_names,
                    "code_template": code_template
                })

        all_matches.sort(key=lambda x: (x['distance'], -x['score']))
        # print(f"[RAGTool Debug] Returning {len(all_matches)} matches.") # Optional Debug
        return all_matches

# Example Usage (Optional, for testing RAGTool directly)
# if __name__ == '__main__':
#     retriever = TemplateRetriever()
#     if retriever.is_initialized:
#         test_query = "create a notes application that supports encryption"
#         matches = retriever.find_matches(test_query)
#         print("Matches found:")
#         print(json.dumps(matches, indent=2))
#     else:
#         print("Retriever failed to initialize.")