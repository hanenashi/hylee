# Hylee (Hyena Leecher)

Hylee is an offline Python web scraper and GUI dashboard designed to archive daily news summaries from the legacy Czech blog hyena.cz. It crawls the site's historical calendar, parses 20+ years of inconsistent, manually written HTML, and compiles the daily news bullets into static, yearly sharded JSON files.

These JSON files act as a backendless database for a Tampermonkey userscript.

## Features
* **Zero-Dependency GUI:** Built with standard Python `tkinter` for maximum portability and fast execution, even on legacy hardware (e.g., older macOS systems).
* **Yearly Sharding:** Data is saved into discrete yearly files (e.g., `hyena_2024.json`, `hyena_2025.json`) to prevent massive, monolithic database files.
* **Live Preview & Logging:** The dashboard features a real-time console log to monitor the scraper's progress and a split-pane JSON preview window to verify data before saving.
* **Debug Mode:** Allows fetching a limited number of days to test parsing logic against anomalous HTML layouts without crawling an entire year.

## Technical Details: How the Scraper Works

Scraping hyena.cz requires navigating over two decades of evolving, hand-coded HTML. Hylee handles several specific edge cases:

### 1. Legacy Encoding
The target website uses `windows-1250` encoding. The scraper explicitly forces this encoding via the `requests` library to prevent corruption of Czech diacritics during the fetch phase.

### 2. The "odsud" Anchor
Because the site lacks modern semantic HTML classes or IDs, the scraper relies on a specific workflow habit of the author. The target data (daily news bullets) is consistently located immediately following a hidden HTML comment containing the word "odsud" (e.g., `` or similar variations). 

Hylee uses `BeautifulSoup4` to locate this specific comment node in the DOM, and then iterates through the subsequent sibling elements to extract the text.

### 3. Evolving HTML Formats
The extraction engine is built to handle the structural shifts that occurred over the years:
* **Legacy Format:** Older posts use raw text separated by `<br>` tags. The scraper extracts these text nodes and filters out common footers, scripts, and navigational noise.
* **Modern Format (2025+):** Newer posts utilize standard `<ul>` and `<li>` tags. The scraper detects `<li>` elements and cleanly extracts their text contents.

### 4. Sanitization Pipeline
Extracted strings are passed through a regex-based sanitization function that:
* Strips lingering inline HTML tags.
* Unescapes common HTML entities (e.g., `&nbsp;`, `&quot;`).
* Normalizes whitespace.
* Discards known footer artifacts (e.g., links to social media or related domains).

## Output Data Structure
The final output is a flat JSON dictionary where the key is the ISO 8601 date, and the value is an array of cleaned strings.

{
  "2025-01-02": [
    "Prezident Pavel řekl v novoročním projevu, že volby jsou důležité a že máme mít euro",
    "Podle statistiky za rok 2024 zahynulo 443 lidí na silnici, nejméně od roku 1961"
  ]
}

## Installation & Usage

1. Install the required dependencies:
   pip install requests beautifulsoup4

2. Launch the dashboard:
   python hylee.py

3. Enter the 4-digit year you wish to archive, select your sanitization preferences, and click "FETCH". Once the JSON preview looks correct, save the shard.