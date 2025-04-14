# setup_chroma.py (Modified to store component details)

import json
import os
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
import uuid
import shutil # Added for directory deletion

# --- Configuration ---
JSON_FILE_PATH = 'templates.json'
SENTENCE_TRANSFORMER_MODEL = 'all-mpnet-base-v2'
COLLECTION_NAME = 'template_rag_collection_v2' # Use a new name to avoid conflicts

# --- Load Environment Variables ---
load_dotenv()
CHROMA_DB_PATH = os.getenv('CHROMADB_PATH')

if not CHROMA_DB_PATH:
    raise ValueError("CHROMADB_PATH environment variable not set. Please create a .env file.")

# --- Helper functions (format_list, format_components - keep as is) ---
def format_list(items, prefix="- "):
    if not items: return "N/A"
    return "\n".join([f"{prefix}{item}" for item in items])

def format_components(components):
    if not components: return "Components: N/A\n"
    component_texts = []
    for comp in components:
        comp_name = comp.get('component_name', 'Unnamed Component')
        features_text = format_list(comp.get('features', []), prefix="  - ")
        component_texts.append(f"  Component: {comp_name}\n  Features:\n{features_text}")
    return "Components:\n" + "\n".join(component_texts) + "\n"

# --- Main Processing Function ---
def setup_database():
    # 1. Load JSON data (same as before)
    try:
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Successfully loaded data from {JSON_FILE_PATH}")
    except Exception as e:
        print(f"Error loading {JSON_FILE_PATH}: {e}")
        return

    # 2. Initialize ChromaDB Client and Embedding Function (same as before)
    print(f"Initializing ChromaDB client with persistence path: {CHROMA_DB_PATH}")
    os.makedirs(CHROMA_DB_PATH, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

    print(f"Using Sentence Transformer model: {SENTENCE_TRANSFORMER_MODEL}")
    st_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=SENTENCE_TRANSFORMER_MODEL
    )

    # --- Explicitly delete and recreate collection ---
    try:
        print(f"Checking for existing collection: {COLLECTION_NAME}")
        existing_collections = [col.name for col in client.list_collections()]
        if COLLECTION_NAME in existing_collections:
            print(f"Deleting existing collection: {COLLECTION_NAME}")
            client.delete_collection(name=COLLECTION_NAME)
            print(f"Collection {COLLECTION_NAME} deleted.")
    except Exception as e:
        print(f"Warning: Could not check/delete collection. Error: {e}")

    print(f"Creating ChromaDB collection: {COLLECTION_NAME}")
    try:
        collection = client.create_collection(
            name=COLLECTION_NAME,
            embedding_function=st_ef
        )
        print(f"Collection '{COLLECTION_NAME}' created.")
    except Exception as e:
        print(f"FATAL: Failed to create collection '{COLLECTION_NAME}': {e}")
        return

    # 4. Process and Add Data to Collection
    documents_to_add = []
    metadatas_to_add = []
    ids_to_add = []
    doc_count = 0

    print("Processing templates and preparing data for ChromaDB...")
    for group in data:
        group_id = group.get('template_group_id', 'UNKNOWN_GROUP')
        group_name = group.get('group_name', 'Unnamed Group')

        for template in group.get('templates', []):
            project_id = template.get('project_id')
            if not project_id:
                print(f"Warning: Skipping template in group '{group_name}' - missing 'project_id'.")
                continue

            project_name = template.get('project_name', 'Unnamed Project')
            project_desc = template.get('description', '')
            components_list = template.get('components', [])

            # --- Format document text (same as before) ---
            components_text = format_components(components_list)
            core_features_text = "Core Features:\n" + format_list(template.get('core_features', []))
            libraries_text = "Required Libraries: " + ", ".join(template.get('required_libraries', ['None']))
            apis_text = "API Integrations:\n" + format_list(template.get('api_integrations', []))
            database_text = f"Database: {template.get('database', 'N/A')}"
            code_template_path = f"Code Template Path: {template.get('code_template', 'N/A')}"

            document_text = f"""
Template Group: {group_name} ({group_id})
Project: {project_name} ({project_id})
Project Description: {project_desc}
{components_text}
{core_features_text}
{libraries_text}
{apis_text}
{database_text}
{code_template_path}
            """.strip()

            # --- Prepare metadata (MODIFIED PART) ---
            # Store component details (name and features) as a JSON string
            component_details_list = []
            if components_list:
                for comp in components_list:
                    component_details_list.append({
                        "name": comp.get('component_name', 'Unnamed'),
                        "features": comp.get('features', []) # Store the list of features
                    })

            metadata = {
                "project_id": project_id,
                "project_name": project_name,
                "template_group_id": group_id,
                "group_name": group_name,
                "code_template": template.get('code_template', 'N/A'),
                "database": template.get('database', 'N/A'),
                # Store the list of component details as a JSON string
                "component_details": json.dumps(component_details_list) if component_details_list else "[]"
            }
            # --- End of Modification ---

            documents_to_add.append(document_text)
            metadatas_to_add.append(metadata)
            ids_to_add.append(project_id)
            doc_count += 1

    # 5. Add documents in batches (same as before)
    if documents_to_add:
        print(f"Adding {len(documents_to_add)} documents...")
        try:
            batch_size = 100
            for i in range(0, len(documents_to_add), batch_size):
                 batch_ids = ids_to_add[i:i+batch_size]
                 batch_docs = documents_to_add[i:i+batch_size]
                 batch_metadatas = metadatas_to_add[i:i+batch_size]
                 # print(f"  Adding batch {i//batch_size + 1} ({len(batch_ids)} docs)...") # Optional verbose print
                 collection.add(ids=batch_ids, documents=batch_docs, metadatas=batch_metadatas)
            print(f"Successfully added {len(documents_to_add)} documents.")
        except Exception as e:
             print(f"Error adding documents to ChromaDB: {e}")
    else:
        print("No valid documents found to add.")

    # 6. Verify count (same as before)
    try:
        count = collection.count()
        print(f"Collection '{COLLECTION_NAME}' now contains {count} documents.")
    except Exception as e: print(f"Could not verify count: {e}")

# --- Run the script ---
if __name__ == "__main__":
    print("--- Starting ChromaDB Setup ---")
    # Explicit deletion of directory first is generally safer for rebuilds
    if os.path.exists(CHROMA_DB_PATH):
         print(f"Deleting existing ChromaDB directory: {CHROMA_DB_PATH}")
         try:
              shutil.rmtree(CHROMA_DB_PATH)
              print("Directory deleted.")
         except OSError as e:
              print(f"Error deleting directory {CHROMA_DB_PATH}: {e}. Exiting.")
              exit(1)

    setup_database()
    print("--- ChromaDB Setup Complete ---")