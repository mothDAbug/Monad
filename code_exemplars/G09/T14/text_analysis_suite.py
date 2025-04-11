# text_analysis_suite.py

import nltk
import json
import re
import os
import csv
import sys
import heapq
from collections import defaultdict, Counter
from string import punctuation
import datetime # <--- Added import

import pyinputplus as pyip
import requests
from bs4 import BeautifulSoup
# Ensure matplotlib is installed: pip install matplotlib
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: Matplotlib not found. Visualization features will be disabled.")
    print("Install it using: pip install matplotlib")


# --- Configuration ---
RESULTS_DIR = "results"
PLOT_DIR = "plots"
DATE_FORMAT = "%Y%m%d_%H%M%S"

# --- NLTK Setup ---
# Ensure necessary NLTK data is downloaded.
REQUIRED_NLTK_DATA = ['vader_lexicon', 'punkt', 'stopwords', 'punkt_tab'] # <-- Added punkt_tab
MISSING_DATA = []
for resource_id in REQUIRED_NLTK_DATA:
    try:
        # Use find() to check without raising an error immediately for each
        nltk.data.find(f'tokenizers/{resource_id}' if resource_id.startswith('punkt') else f'corpora/{resource_id}' if resource_id == 'stopwords' else f'sentiment/{resource_id}')
        # Specific paths for clarity (adjust if needed based on actual NLTK structure)
        if resource_id == 'vader_lexicon':
            nltk.data.find('sentiment/vader_lexicon.zip')
        elif resource_id == 'punkt' or resource_id == 'punkt_tab': # Check common punkt location
             nltk.data.find('tokenizers/punkt')
        elif resource_id == 'stopwords':
             nltk.data.find('corpora/stopwords')
    except LookupError:
        MISSING_DATA.append(resource_id)

if MISSING_DATA:
    print("NLTK data not found. Attempting to download...")
    print(f"Required: {', '.join(MISSING_DATA)}")
    # Add averaged_perceptron_tagger if using POS: nltk.download('averaged_perceptron_tagger', quiet=True)
    try:
        for resource_id in MISSING_DATA:
             print(f"Downloading {resource_id}...")
             nltk.download(resource_id, quiet=True)
        print("NLTK data downloaded successfully.")
        # Re-verify after download attempt (optional but good practice)
        try:
             from nltk.sentiment.vader import SentimentIntensityAnalyzer
             from nltk.tokenize import sent_tokenize, word_tokenize
             from nltk.corpus import stopwords
        except LookupError as e:
             print(f"Error: A required NLTK resource might still be missing after download attempt: {e}")
             print("Please try downloading manually or check NLTK installation.")
             sys.exit(1)

    except Exception as e:
        print(f"Error downloading NLTK data: {e}")
        print(f"Please try downloading manually: run python -m nltk.downloader {' '.join(MISSING_DATA)}")
        sys.exit(1)

# Import NLTK components after ensuring data exists
try:
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords
    # from nltk import pos_tag # Needed for POS-based keyphrase extraction
except ImportError as e:
    print(f"Failed to import NLTK components: {e}")
    print("Ensure NLTK is installed (`pip install nltk`) and data is downloaded.")
    sys.exit(1)
except LookupError as e:
     print(f"Failed to load NLTK data even after download check: {e}")
     print("Please verify NLTK installation and data paths.")
     sys.exit(1)


# --- Sentiment Analyzer ---
class SentimentAnalyzerModule:
    def __init__(self):
        try:
             self.analyzer = SentimentIntensityAnalyzer()
        except LookupError:
             print("Error: VADER lexicon not found. Please ensure NLTK data is correctly installed.")
             self.analyzer = None

    def analyze(self, text):
        """Analyzes sentiment of the input text (English)."""
        if not self.analyzer:
            return None, "VADER Analyzer not initialized."
        if not text or not isinstance(text, str) or not text.strip():
            return None, "Input text is empty or invalid."

        try:
             vs = self.analyzer.polarity_scores(text)
             # Determine overall sentiment based on compound score
             if vs['compound'] >= 0.05:
                 sentiment = 'Positive'
             elif vs['compound'] <= -0.05:
                 sentiment = 'Negative'
             else:
                 sentiment = 'Neutral'
             return {'overall': sentiment, 'scores': vs}, None # Return result and no error
        except Exception as e:
             return None, f"Error during sentiment analysis: {e}"

    def visualize_sentiment(self, scores, filename_prefix="sentiment"):
        """Creates a bar chart of sentiment scores."""
        if not MATPLOTLIB_AVAILABLE:
             print("Matplotlib not installed. Cannot generate visualization.")
             return
        if not scores or 'scores' not in scores:
             print("Invalid scores data for visualization.")
             return

        labels = ['Positive', 'Negative', 'Neutral', 'Compound']
        values = [scores['scores'].get('pos', 0),
                  scores['scores'].get('neg', 0),
                  scores['scores'].get('neu', 0),
                  scores['scores'].get('compound', 0)]
        colors = ['lightgreen', 'lightcoral', 'lightskyblue', 'gold']

        try:
             plt.figure(figsize=(8, 5))
             bars = plt.bar(labels, values, color=colors)
             plt.ylabel("Score")
             plt.title("Sentiment Analysis Scores")
             plt.bar_label(bars, fmt='%.3f')
             # Adjust ylim slightly beyond max/min for better visibility
             min_val = min(values) if values else 0
             max_val = max(values) if values else 0
             plt.ylim(min(min_val, 0) - 0.1, max(max_val, 1.0) + 0.1)


             os.makedirs(PLOT_DIR, exist_ok=True)
             timestamp = datetime.datetime.now().strftime(DATE_FORMAT) # Uses imported datetime
             filename = os.path.join(PLOT_DIR, f"{filename_prefix}_{timestamp}.png")
             plt.savefig(filename)
             plt.close() # Close the plot to free memory
             print(f"Sentiment visualization saved to '{filename}'")
        except Exception as e:
             print(f"Error during visualization: {e}")


# --- Text Summarizer ---
class TextSummarizerModule:
    def __init__(self):
        try:
            self.stop_words = set(stopwords.words('english'))
        except LookupError:
            print("Warning: NLTK stopwords not found. Summarization quality may be affected.")
            self.stop_words = set() # Allow continuing without stopwords

    def _calculate_sentence_scores(self, sentences, word_frequencies):
        """Scores sentences based on word frequencies."""
        sentence_scores = defaultdict(float) # Use float for division result
        for i, sentence in enumerate(sentences):
            words = word_tokenize(sentence.lower())
            sentence_word_count_in_freq = 0
            score = 0
            for word in words:
                if word in word_frequencies:
                    sentence_word_count_in_freq += 1
                    score += word_frequencies[word] # Score based on contained word frequencies

            # Normalize score by the number of non-stop/non-punctuation words found in the sentence
            if sentence_word_count_in_freq > 0:
                 sentence_scores[i] = score / sentence_word_count_in_freq
            else:
                 sentence_scores[i] = 0.0 # Assign 0 if no frequent words found
        return sentence_scores

    def summarize_extractive(self, text, num_sentences=3):
        """Generates an extractive summary using word frequency."""
        if not text or not isinstance(text, str) or not text.strip():
            return "", "Input text is empty or invalid."

        try:
            # 1. Tokenize into sentences
            sentences = sent_tokenize(text)
            if len(sentences) <= num_sentences:
                 print(f"Text has {len(sentences)} sentences, which is less than or equal to the requested summary length ({num_sentences}). Returning original text.")
                 return text, None # Return original text if already short enough

            # 2. Tokenize into words, clean, and calculate frequencies
            words = word_tokenize(text.lower())
            # Ensure stopwords are available
            current_stopwords = self.stop_words if self.stop_words else set()
            clean_words = [word for word in words if word not in punctuation and word not in current_stopwords]
            if not clean_words:
                return "", "No valid words found after cleaning for summarization."

            word_frequencies = Counter(clean_words)

            # 3. Score sentences
            sentence_scores = self._calculate_sentence_scores(sentences, word_frequencies)
            if not sentence_scores: # Handle case where no sentences could be scored
                 return "", "Could not score sentences for summarization."

            # 4. Select top N sentences using heapq for efficiency
            # Ensure num_sentences isn't larger than the actual number of scored sentences
            num_to_select = min(num_sentences, len(sentence_scores))
            summary_sentence_indices = heapq.nlargest(num_to_select, sentence_scores, key=sentence_scores.get)

            # Sort the selected indices to maintain original order
            summary_sentence_indices.sort()

            # 5. Join selected sentences
            summary = " ".join(sentences[i] for i in summary_sentence_indices)
            return summary, None
        except Exception as e:
            # Provide more context if it's an NLTK resource error
            if isinstance(e, LookupError):
                 return "", f"Error during extractive summarization: NLTK resource missing - {e}. Please ensure all required NLTK data is downloaded."
            return "", f"Error during extractive summarization: {e}"


    def extract_key_phrases(self, text, num_phrases=5):
        """Extracts key phrases based on word frequency (simple method)."""
        if not text or not isinstance(text, str) or not text.strip():
            return [], "Input text is empty or invalid."

        try:
             words = word_tokenize(text.lower()) # <--- This uses punkt_tab implicitly sometimes
             # Ensure stopwords are available
             current_stopwords = self.stop_words if self.stop_words else set()
             clean_words = [word for word in words if word not in punctuation and word not in current_stopwords]

             if not clean_words:
                 return [], "No valid words found after cleaning for key phrase extraction."

             # Simple approach: return N most frequent non-stop words
             word_frequencies = Counter(clean_words)
             # Ensure num_phrases doesn't exceed available unique words
             num_to_extract = min(num_phrases, len(word_frequencies))
             key_phrases = [word for word, freq in word_frequencies.most_common(num_to_extract)]

             return key_phrases, None
        except Exception as e:
             # Provide more context if it's an NLTK resource error
            if isinstance(e, LookupError):
                 return [], f"Error extracting key phrases: NLTK resource missing - {e}. Please ensure all required NLTK data is downloaded."
            return [], f"Error extracting key phrases: {e}"

# --- Input/Output Utilities ---
def load_text_from_file(filepath):
    """Loads text content from a file."""
    try:
        # Use input validation result directly if possible
        expanded_path = os.path.expanduser(filepath) # Handle ~ paths
        with open(expanded_path, 'r', encoding='utf-8') as f:
            return f.read(), None
    except FileNotFoundError:
        return None, f"Error: File not found at '{expanded_path}'."
    except Exception as e:
        return None, f"Error reading file '{expanded_path}': {e}"

def fetch_text_from_url(url):
    """Fetches and extracts text content from a URL."""
    print(f"Fetching content from {url}...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'} # More standard user agent
        response = requests.get(url, headers=headers, timeout=20) # Increased timeout
        response.raise_for_status() # Check for HTTP errors (4xx or 5xx)

        # Check content type - only parse HTML
        content_type = response.headers.get('content-type', '').lower()
        if 'html' not in content_type:
            print(f"Warning: Content type is '{content_type}', not HTML. Attempting basic text extraction.")
            # For non-HTML, just return the text content if available
            # Decode explicitly using detected encoding or fallback to utf-8
            encoding = response.encoding or 'utf-8'
            return response.content.decode(encoding, errors='ignore'), None


        # Use BeautifulSoup to parse HTML and extract text
        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove script, style, nav, header, footer elements (common noise)
        for element_type in ["script", "style", "nav", "header", "footer", "aside", "form"]:
             for element in soup.find_all(element_type):
                 element.decompose()

        # Get text using get_text() with separator and stripping
        text = soup.get_text(separator=' ', strip=True)

        # Optional: Further cleaning (remove excessive whitespace)
        text = re.sub(r'\s+', ' ', text).strip()

        if not text:
             return None, "Could not extract significant text content from the URL."

        print("Content fetched successfully.")
        return text, None
    except requests.exceptions.Timeout:
        return None, f"Error: Request timed out after {timeout} seconds."
    except requests.exceptions.SSLError as e:
        return None, f"Error: SSL certificate verification failed for {url}. Details: {e}"
    except requests.exceptions.RequestException as e:
        return None, f"Error fetching URL '{url}': {e}"
    except Exception as e:
        return None, f"Error processing URL content from '{url}': {e}"

# --- Helper for Flattening Dictionary for CSV ---
def _flatten_dict(d, parent_key='', sep='_'):
    """Flattens a nested dictionary."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            # Convert lists to a delimited string for CSV
            items.append((new_key, "; ".join(map(str, v))))
        else:
            items.append((new_key, v))
    return dict(items)

def save_results(results, filename_prefix):
    """Saves analysis results to JSON and CSV."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime(DATE_FORMAT) # Uses imported datetime
    base_path = os.path.join(RESULTS_DIR, f"{filename_prefix}_{timestamp}")

    # --- Save as JSON ---
    json_path = base_path + ".json"
    try:
        # Make a copy to avoid modifying the original results dict if needed later
        results_to_save = results.copy()
        # Optionally add timestamp to JSON content itself
        results_to_save['saved_timestamp'] = datetime.datetime.now().isoformat()

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results_to_save, f, indent=4, ensure_ascii=False)
        print(f"Results saved to '{json_path}'")
    except Exception as e:
        print(f"Error saving results to JSON: {e}")

    # --- Save as CSV ---
    csv_path = base_path + ".csv"
    try:
        # Flatten the dictionary for CSV
        flat_results = _flatten_dict(results)

        if not flat_results:
            print("No data to save to CSV.")
            return

        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Write header
            headers = list(flat_results.keys())
            writer.writerow(headers)
            # Write data row
            writer.writerow(list(flat_results.values()))

        print(f"Results saved to '{csv_path}'")
    except Exception as e:
        print(f"Error saving results to CSV: {e}")

# --- Optional Dictionary API ---
DICTIONARY_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/"
def get_definition(word):
    """Gets definition from Free Dictionary API."""
    if not word or not isinstance(word, str):
        return "Invalid word provided for definition."
    word = word.strip().lower() # Clean input
    if not word:
         return "Empty word provided for definition."

    print(f"Looking up '{word}'...")
    try:
        response = requests.get(f"{DICTIONARY_API_URL}{word}", timeout=10) # Increased timeout
        # Check status code carefully
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and data:
                 # Extract the first relevant definition found
                 for entry in data:
                     meanings = entry.get('meanings', [])
                     if meanings:
                         first_meaning = meanings[0]
                         part_of_speech = first_meaning.get('partOfSpeech', 'N/A')
                         definitions = first_meaning.get('definitions', [])
                         if definitions:
                             definition_text = definitions[0].get('definition', 'No definition text found.')
                             return f"{word.capitalize()} ({part_of_speech}): {definition_text}"
                 return f"Definition structure found for '{word}', but no specific definition text available." # If loop completes
            else:
                # API might return 200 with empty list or unexpected structure
                return f"Unexpected response structure from dictionary API for '{word}'."
        elif response.status_code == 404:
             return f"Definition not found for '{word}'."
        else:
             # Provide more info from the response if available (e.g., error message)
             try:
                 error_details = response.json()
                 message = error_details.get('message', 'No details provided.')
                 title = error_details.get('title', f'Status {response.status_code}')
                 return f"Dictionary API error ({title}): {message}"
             except json.JSONDecodeError:
                 return f"Dictionary API error: Status {response.status_code}, Response: {response.text[:100]}..." # Show start of non-JSON error
    except requests.exceptions.Timeout:
         return f"Could not connect to Dictionary API: Request timed out."
    except requests.exceptions.RequestException as e:
        return f"Could not connect to Dictionary API: {e}"
    except json.JSONDecodeError:
         return f"Error: Invalid JSON response received from Dictionary API."
    except Exception as e:
        return f"An unexpected error occurred during dictionary lookup: {e}"


# --- Main Application ---
def main():
    print("-" * 30)
    print("   Text Analysis Suite")
    print("-" * 30)

    # Initialize modules here to reuse them
    sentiment_analyzer = SentimentAnalyzerModule()
    summarizer = TextSummarizerModule()

    # Check if analyzer is usable
    if sentiment_analyzer.analyzer is None:
         print("Critical Error: Sentiment Analyzer could not be initialized (VADER lexicon missing?). Exiting.")
         sys.exit(1)

    text_source = ""
    source_info = {"type": "None", "origin": ""} # Keep track of source origin (filename/url)
    last_results = {} # Store results of last *successful* analysis operation

    while True:
        print("\n--- Main Menu ---")
        # Display current text source info
        if text_source:
            print(f"Current text loaded from: {source_info['type']} ({source_info.get('origin','N/A')[:50]}{'...' if len(source_info.get('origin',''))>50 else ''}), Length: {len(text_source)} chars")
        else:
            print("No text loaded.")

        menu_options = [
            'Load Text (File/URL/Input)',
            'Analyze Sentiment',
            'Summarize Text',
            'Extract Key Phrases',
            'Define Word/Phrase (Dictionary)',
            'Save Last Analysis Results',
            'Exit'
        ]
        action = pyip.inputMenu(menu_options, numbered=True)

        # Clear previous results when loading new text or performing a new analysis
        # but keep them for saving if requested just before exiting or loading new text
        if action not in ['Save Last Analysis Results', 'Exit', 'Define Word/Phrase (Dictionary)']:
            # Reset results for new analysis, but don't clear if user might want to save previous
             pass # Decide when to clear last_results carefully

        if action == 'Load Text (File/URL/Input)':
             source_choice = pyip.inputChoice(['File', 'URL', 'Manual'], prompt="Load text from (File/URL/Manual): ")
             loaded_text = ""
             error_msg = None
             origin = ""

             if source_choice == 'File':
                  filepath = pyip.inputFilepath("Enter path to text file: ", mustExist=True)
                  loaded_text, error_msg = load_text_from_file(filepath)
                  if not error_msg: origin = os.path.basename(filepath)
             elif source_choice == 'URL':
                  url = pyip.inputURL("Enter URL to fetch text from: ")
                  loaded_text, error_msg = fetch_text_from_url(url)
                  if not error_msg: origin = url
             elif source_choice == 'Manual':
                  print("Enter text (Press Enter twice or Ctrl+Z/D on Unix/Win to finish):")
                  lines = []
                  try:
                      while True:
                          line = input()
                          if line == "" and sys.stdin.isatty(): # Check for double enter in interactive terminal
                              # Heuristic: if previous line was also empty, likely end of input
                              if lines and lines[-1] == "":
                                  lines.pop() # Remove the extra blank line indicator
                                  break
                              elif not lines: # First line is empty, maybe signal end? Or just empty line? Wait for another.
                                   lines.append(line) # Keep empty line for now
                              else:
                                   lines.append(line)
                          else:
                              lines.append(line)
                  except EOFError: # Handle Ctrl+Z/D
                      pass
                  loaded_text = "\n".join(lines).strip()
                  if not loaded_text:
                       error_msg = "No text entered."
                  else:
                       origin = "Manual Input"

             if error_msg:
                  print(error_msg)
                  # Don't change existing text_source if load failed
             elif loaded_text is not None: # Check for None return on error
                 if not loaded_text.strip():
                     print("Warning: Loaded text is empty or contains only whitespace.")
                     text_source = ""
                     source_info = {"type": "None", "origin": ""}
                 else:
                     text_source = loaded_text
                     source_info['type'] = source_choice
                     source_info['origin'] = origin
                     print(f"\nText loaded successfully from {source_info['type']} ({origin}). Length: {len(text_source)} chars.")
                     last_results = {} # Clear previous results when new text is successfully loaded
             else:
                  print("Loading failed, but no specific error message returned.") # Fallback


        elif action == 'Analyze Sentiment':
            if not text_source: print("No text loaded. Please load text first."); continue
            print("\nAnalyzing sentiment...")
            result, error = sentiment_analyzer.analyze(text_source)
            if error: print(f"Error: {error}"); continue

            print("\n--- Sentiment Analysis Results ---")
            print(f"Overall Sentiment: {result['overall']}")
            print("Scores:")
            for key, value in result['scores'].items():
                print(f"  {key.capitalize():<10}: {value:.4f}") # Aligned output
            print("-" * 32)

            # Store results *only* if analysis was successful
            last_results = {
                'analysis_type': 'sentiment',
                'source_type': source_info['type'],
                'source_origin': source_info['origin'],
                'text_length': len(text_source),
                'sentiment': result
            }

            if MATPLOTLIB_AVAILABLE:
                visualize = pyip.inputYesNo("Generate sentiment score chart? (y/N): ", default='no', blank=True)
                if visualize == 'yes':
                     # Generate filename prefix based on source
                     prefix = f"sentiment_{source_info['type']}_{os.path.splitext(source_info['origin'])[0]}" if source_info['type'] == 'File' else f"sentiment_{source_info['type']}"
                     prefix = re.sub(r'[\\/*?:"<>|]', "", prefix) # Clean filename
                     sentiment_analyzer.visualize_sentiment(result, filename_prefix=prefix[:50]) # Limit prefix length
            else:
                 print("(Visualization unavailable as Matplotlib is not installed)")


        elif action == 'Summarize Text':
            if not text_source: print("No text loaded. Please load text first."); continue
            # Suggest a default based on text length? E.g., min(3, len(sent_tokenize(text)) // 5)
            try:
                initial_sentences = len(sent_tokenize(text_source))
            except Exception: # Fallback if sentence tokenization fails early
                 initial_sentences = 0
            default_summary_len = max(1, min(5, initial_sentences // 5 if initial_sentences > 5 else 3)) # Suggest 1-5 sentences

            num_sent = pyip.inputInt(f"Number of sentences for summary (e.g., {default_summary_len}): ", default=default_summary_len, min=1)
            print(f"\nGenerating summary ({num_sent} sentences)...")
            summary, error = summarizer.summarize_extractive(text_source, num_sentences=num_sent)
            if error: print(f"Error: {error}"); continue

            print("\n--- Text Summary ---")
            print(summary)
            print("-"*(len("--- Text Summary ---")))

            # Store results *only* if analysis was successful
            last_results = {
                'analysis_type': 'summary',
                'source_type': source_info['type'],
                'source_origin': source_info['origin'],
                'text_length': len(text_source),
                'requested_sentences': num_sent,
                'summary': summary
            }


        elif action == 'Extract Key Phrases':
            if not text_source: print("No text loaded. Please load text first."); continue
            default_phrases = 5
            num_phr = pyip.inputInt("Number of key phrases to extract: ", default=default_phrases, min=1)
            print("\nExtracting key phrases...")
            phrases, error = summarizer.extract_key_phrases(text_source, num_phrases=num_phr)
            if error: print(f"Error: {error}"); continue

            print("\n--- Key Phrases ---")
            if phrases:
                 for i, phrase in enumerate(phrases): print(f"{i+1}. {phrase}")
            else:
                 print("No distinct key phrases found (or text might be too short/simple).")
            print("-"*(len("--- Key Phrases ---")))

            # Store results *only* if analysis was successful
            last_results = {
                'analysis_type': 'key_phrases',
                'source_type': source_info['type'],
                'source_origin': source_info['origin'],
                'text_length': len(text_source),
                'requested_phrases': num_phr,
                'key_phrases': phrases
            }


        elif action == 'Define Word/Phrase (Dictionary)':
             # Check if there are key phrases from last analysis to suggest
             suggested_word = ""
             if last_results and last_results.get('analysis_type') == 'key_phrases' and last_results.get('key_phrases'):
                 suggested_word = last_results['key_phrases'][0] # Suggest the first key phrase
                 prompt = f"Enter word/phrase to define (e.g., '{suggested_word}'): "
             else:
                 prompt = "Enter word/phrase to define: "

             phrase = pyip.inputStr(prompt, default=suggested_word if suggested_word else None, blank=False)
             # Define the first word of the phrase for simplicity with this API
             word_to_define = phrase.split()[0] if phrase else ""
             definition = get_definition(word_to_define)
             print(f"\nDefinition: {definition}")
             # Defining a word doesn't overwrite 'last_results' for saving


        elif action == 'Save Last Analysis Results':
            if not last_results:
                 print("No analysis results from the last operation to save.")
                 print("Perform an analysis (Sentiment, Summary, Key Phrases) first.")
                 continue

            # Generate a more informative default prefix
            analysis_type = last_results.get('analysis_type', 'results')
            source_type = last_results.get('source_type', 'unknown')
            origin = last_results.get('source_origin', '')
            origin_slug = ""
            if source_type == 'File':
                origin_slug = os.path.splitext(os.path.basename(origin))[0]
            elif source_type == 'URL':
                 # Create a basic slug from URL
                 try:
                     from urllib.parse import urlparse
                     domain = urlparse(origin).netloc
                     origin_slug = domain.replace('.', '_')
                 except: # Fallback if parsing fails
                     origin_slug = 'url_source'
            elif source_type == 'Manual':
                 origin_slug = 'manual_input'

            default_prefix = f"{analysis_type}_{source_type}_{origin_slug}".lower()
            # Clean default prefix for filesystem compatibility
            default_prefix = re.sub(r'[\\/*?:"<>| \t\n\r]', "_", default_prefix)
            default_prefix = re.sub(r'_+', '_', default_prefix).strip('_') # Remove multiple/leading/trailing underscores
            default_prefix = default_prefix[:50] # Limit length


            prefix_prompt = f"Enter filename prefix\n(default: '{default_prefix}'): "
            user_prefix = pyip.inputStr(prefix_prompt, default=default_prefix, blank=True)
            # If user enters blank, use the generated default
            final_prefix = user_prefix if user_prefix else default_prefix

            # Pass a copy to avoid modification issues if save fails partially
            save_results(last_results.copy(), final_prefix)


        elif action == 'Exit':
            print("Exiting Text Analysis Suite. Goodbye!")
            sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user. Exiting.")
        sys.exit(0) # Use exit code 0 for user cancellation via Ctrl+C in menu
    except Exception as e:
        print(f"\nAn unexpected critical error occurred in the main loop: {e}")
        # Log traceback for debugging
        import traceback
        print("\n--- Traceback ---")
        traceback.print_exc()
        print("-----------------")
        sys.exit(1) # Use non-zero exit code for unexpected errors
