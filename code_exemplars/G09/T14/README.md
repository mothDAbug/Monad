# Text Analysis Suite (Project T14)

## Description

A command-line Natural Language Processing (NLP) toolkit offering capabilities for sentiment analysis (determining emotional tone) and automatic text summarization (condensing long documents). Useful for analyzing customer feedback, research papers, news articles, and other text data.

## Features

*   **Text Input:** Load text from local files (`.txt`), fetch directly from URLs, or input manually.
*   **Sentiment Analysis:**
    *   Uses NLTK's VADER (Valence Aware Dictionary and sEntiment Reasoner) for English sentiment analysis.
    *   Provides polarity scores (positive, negative, neutral) and a compound score.
    *   Determines overall sentiment (Positive, Negative, Neutral).
    *   Option to visualize scores with a bar chart (saved to `plots/`).
*   **Text Summarization:**
    *   Performs basic *extractive* summarization based on word frequency.
    *   Allows configuring the desired number of sentences in the summary.
*   **Key Phrase Extraction:**
    *   Extracts a specified number of key phrases based on simple word frequency (after removing stopwords).
*   **Dictionary Lookup (Optional):**
    *   Fetch definition for a word using the Free Dictionary API (requires internet).
*   **Results Export:**
    *   Save the results of the last analysis (sentiment scores, summary, key phrases) to JSON and CSV files in the `results/` directory.

## Requirements

*   Python 3.7+
*   Libraries listed in `requirements.txt`:
    *   `nltk`: The core NLP library.
    *   `matplotlib`: For generating plot visualizations.
    *   `pyinputplus`: For robust user input validation.
    *   `requests`: For fetching URL content and dictionary API calls.
    *   `beautifulsoup4`: For parsing HTML content from URLs.
*   **NLTK Data:** Requires specific NLTK data packages.

## Setup

1.  **Clone or Download:** Get the project files (`text_analysis_suite.py`, `requirements.txt`).
2.  **Navigate to Directory:** Open terminal/cmd into the `text_analysis_suite/` directory.
3.  **Create Virtual Environment (Recommended):** `python -m venv venv` then activate it.
4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
5.  **Download NLTK Data:**
    *   Run the script once: `python text_analysis_suite.py`
    *   The script will attempt to automatically download the required NLTK data (`vader_lexicon`, `punkt`, `stopwords`).
    *   If the automatic download fails, run the following command in your terminal (with the virtual environment activated):
        ```bash
        python -m nltk.downloader vader_lexicon punkt stopwords
        ```
    *   *(Optional: If extending key phrase extraction to use Part-of-Speech tagging, also download `averaged_perceptron_tagger`)*

## Usage

1.  Make sure your virtual environment is activated.
2.  Run the script: `python text_analysis_suite.py`
3.  Use the main menu:
    *   **Load Text:** Choose to load text from a File, URL, or Manual input. This text is used for subsequent analyses.
    *   **Analyze Sentiment:** Performs sentiment analysis on the loaded text and displays scores. Optionally generates a plot.
    *   **Summarize Text:** Generates an extractive summary of the loaded text with a specified number of sentences.
    *   **Extract Key Phrases:** Extracts the most frequent non-stopwords from the loaded text.
    *   **Define Key Phrase:** Looks up the definition of a word using an online dictionary API.
    *   **Save Last Results:** Saves the output of the last analysis (sentiment, summary, or key phrases) to JSON and CSV files in the `results/` folder.
    *   **Exit:** Quits the application.

## Limitations

*   **Sentiment Analysis Language:** The current implementation using VADER is primarily optimized for **English**, especially text similar to social media. Sentiment analysis for other languages requires different models or libraries.
*   **Summarization Quality:** The extractive summarization is basic (frequency-based) and may not always produce the most coherent or contextually accurate summaries compared to more advanced models. Abstractive summarization (generating new sentences) is not implemented.
*   **Key Phrase Quality:** Key phrase extraction is basic (frequency-based) and might miss more nuanced or multi-word phrases.
*   **URL Fetching:** Text extraction from URLs depends heavily on the website's structure and may fail or produce noisy results for complex sites, JavaScript-heavy pages, or sites with anti-scraping measures.
*   **Error Handling:** Basic error handling is included, but real-world text analysis often requires more sophisticated preprocessing and handling of diverse edge cases.

## License

This project can be considered under the MIT License (or specify otherwise if needed).