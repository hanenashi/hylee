# Hylee (Hyena Leecher)

Hylee is an offline Python web scraper and GUI dashboard designed to archive daily news summaries from the legacy Czech blog hyena.cz. It crawls the site's historical calendar, parses 20+ years of inconsistent, manually written HTML, and compiles the daily news bullets into static, yearly sharded JSON files.

These JSON files act as a backendless database for a Tampermonkey userscript.

## Features
* **Zero-Dependency GUI:** Built with standard Python `tkinter` for maximum portability and fast execution.
* **Batch Processing & Sharding:** Automatically crawls single years (2025), ranges (2010-2015), or the entire archive (ALL), saving data into discrete yearly files (e.g., `hyena_2024.json`) to prevent monolithic databases.
* **Interactive Calendar Explorer:** A built-in Treeview lets you load a year, browse days by month, open specific articles in your browser, and run single-day test parses.
* **Live Preview & Logging:** Features a real-time console log and a live JSON preview window to verify data structures before they are saved.
* **Debug Limits:** Allows fetching a limited number of days (e.g., 5 days per year) to quickly test parsing logic against anomalous HTML layouts across multiple years.

## Technical Details: How the Scraper Works

Scraping hyena.cz requires navigating over two decades of evolving, hand-coded HTML. Hylee handles several specific edge cases using a custom extraction engine:

### 1. Smart Encoding Fallback
The target website historically used `windows-1250` encoding, but transitioned over time. The scraper intercepts the raw server bytes and first attempts a strict `utf-8` decode. If a `UnicodeDecodeError` is thrown, it instantly falls back to `windows-1250`, ensuring Czech diacritics are perfectly preserved regardless of the era.

### 2. The "odsud" Anchor & Linear Token Stream
The site lacks semantic HTML classes. However, the target data consistently follows a hidden HTML comment containing the word "odsud" (e.g., ``). 

Because early posts (2003-2006) frequently utilized unclosed `<li>` tags, standard DOM traversal (which assumes infinite nesting for unclosed tags) causes massive data bleeding. To defeat this, Hylee abandons strict DOM hierarchy and uses a **Linear Token Stream Engine**. It walks through elements one-by-one, buffering pure text nodes and ignoring formatting tags, then instantly "flushes" the buffer into a clean bullet whenever it hits a structural tag (`<li>`, `<br>`, `<p>`, etc.).

### 3. The Weather Kill-Switch
To prevent the scraper from bleeding past the news section into long editorial essays (which often lack clear HTML boundaries), Hylee utilizes a content-aware kill-switch. The author historically concludes the news section with a local weather report. The engine scans the flushed text buffers for specific prefixes (e.g., "Počasí v Praze", "Ráno lilo", "U nás slunečno") and halts extraction immediately upon detection.

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

3. Choose your workflow:
   * **Explore & Debug:** Enter a single year, click "1. LOAD YEAR TO EXPLORER", and use the middle panel to test specific days.
   * **Batch Leech:** Enter a year, range (e.g. 2010-2015), or "ALL", then click "2. BATCH LEECH" to automatically crawl and save the JSON shards to your directory.