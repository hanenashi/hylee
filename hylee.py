import requests
from bs4 import BeautifulSoup, Comment
import json
import os
import re
import time
import logging

# Configure logging: Errors go to both the console and a local .log file
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("hylee_errors.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class HyenaScraper:
    def __init__(self):
        self.base_url = "https://hyena.cz"
        self.headers = {'User-Agent': 'HyleeArchiver-CLI/2.2'}
        
        self.archive_map = {
            2026: "/", 
            2025: "/inc/archiv20.htm",
            2024: "/inc/archiv19.htm",
            2023: "/inc/archiv18.htm",
            2022: "/inc/archiv17.htm",
            2021: "/inc/archiv16.htm",
            2020: "/inc/archiv15.htm",
            2019: "/inc/archiv14.htm",
            2018: "/inc/archiv13.htm",
            2017: "/inc/archiv12.htm",
            2016: "/archiv11.htm",
            2015: "/archiv10.htm",
            2014: "/archiv9.htm",
            2013: "/archiv8.htm",
            2012: "/archiv7.htm",
            2011: "/archiv6.htm",
            2010: "/archiv5.html",
            2009: "/archiv4.html",
            2008: "/archiv3.html",
            2007: "/archiv2.html",
            2006: "/archiv2.html",
            2005: "/archiv1.html",
            2004: "/archiv1.html",
            2003: "/archiv1.html"
        }

    def sanitize_text(self, text):
        text = re.sub(r'<[^>]*>', '', text)
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&quot;', '"')
        return " ".join(text.split())

    def get_daily_links(self, year_full):
        year_int = int(year_full)
        archive_path = self.archive_map.get(year_int, "/")
        archive_url = f"{self.base_url}{archive_path}"
        
        try:
            r = requests.get(archive_url, headers=self.headers, timeout=10)
            
            # SMART ENCODING FALLBACK
            try:
                html_text = r.content.decode('utf-8')
            except UnicodeDecodeError:
                html_text = r.content.decode('windows-1250', errors='replace')
                
            if r.status_code != 200:
                logging.error(f"Failed to load calendar for {year_full} (Status: {r.status_code})")
                return []
            
            soup = BeautifulSoup(html_text, 'html.parser')
            links = []
            year_short_str = str(year_full)[-2:] 
            
            for a in soup.find_all('a', href=True):
                href = a['href']
                # Strictly extract the YY from the YYMMDDpes.htm filename
                match = re.search(r'(\d{2})\d{4}pes\.html?', href)
                if match:
                    link_year = match.group(1)
                    if link_year == year_short_str:
                        links.append(href)
            
            clean_links = []
            for link in set(links):
                if link.startswith('/'):
                    clean_links.append(link)
                else:
                    clean_links.append(f"/{link}")
            
            clean_links.sort()
            return clean_links
        except Exception as e:
            logging.error(f"Error fetching calendar for {year_full}: {e}")
            return []

    def scrape_day(self, relative_path, do_sanitize=True):
        url = f"{self.base_url}{relative_path}"
        try:
            r = requests.get(url, headers=self.headers, timeout=10)
            if r.status_code != 200:
                return None

            # SMART ENCODING FALLBACK
            try:
                html_text = r.content.decode('utf-8')
            except UnicodeDecodeError:
                html_text = r.content.decode('windows-1250', errors='replace')

            soup = BeautifulSoup(html_text, 'html.parser')
            bullets = []
            
            start_node = soup.find(
                string=lambda t: isinstance(t, Comment) and 'odsud' in t.lower()
            )
            
            if start_node:
                curr = start_node.next_element
                text_buffer = []
                html_tag_bypass = "<" + "!--"
                
                # Helper function to compile buffered text into a bullet
                def flush_buffer():
                    if not text_buffer: return False
                    
                    bullet = " ".join(text_buffer).strip()
                    if do_sanitize: 
                        bullet = self.sanitize_text(bullet)
                    
                    text_buffer.clear()
                    
                    if len(bullet) > 5 and not bullet.startswith(html_tag_bypass):
                        if "Pokud vám nějaká zpráva přijde debilní" in bullet:
                            return True # Kill switch
                            
                        b_lower = bullet.lower()
                        if "facebook.com" not in b_lower and "digineff.cz" not in b_lower:
                            bullets.append(bullet)
                            
                            # WEATHER KILL-SWITCH
                            weather_prefixes = [
                                "počasí", "u nás", "mrazy", "slunečn", "zataženo", 
                                "oblačno", "jasno", "dnes", "čeká se", "ráno lilo"
                            ]
                            if any(b_lower.startswith(w) for w in weather_prefixes) or \
                               "počasí v praze" in b_lower or "počasí praha" in b_lower:
                                return True # Stop parsing immediately
                    return False

                # Linear Token Stream Parser
                while curr:
                    curr_name = getattr(curr, 'name', '')
                    
                    # 1. STOP CONDITIONS (Legacy comments)
                    if isinstance(curr, Comment):
                        c_text = curr.lower()
                        if 'konec' in c_text or ('xxxxxxxx' in c_text and 'odsud' not in c_text):
                            flush_buffer()
                            break
                            
                    # 2. STOP CONDITIONS (Major structural shifts)
                    if curr_name in ['table', 'div']:
                        flush_buffer()
                        break
                    if curr_name == 'font' and curr.get('color') == 'navy':
                        flush_buffer()
                        break

                    # 3. BULLET SPLITTERS (Flush buffer on new lines)
                    if curr_name in ['li', 'br', 'p', 'ul', 'ol', 'hr']:
                        if flush_buffer():
                            break

                    # 4. COLLECT PURE TEXT (Ignores formatting tags like <b>)
                    if type(curr).__name__ == 'NavigableString':
                        t = str(curr).strip()
                        if t:
                            text_buffer.append(t)
                            
                    curr = curr.next_element
                    
                # Final flush for the last item
                flush_buffer()
                
            return bullets
        except Exception as e:
            logging.error(f"Error scraping {url}: {e}")
            return None


def main():
    print("="*50)
    print("HYLEE CLI BATCH SCRAPER v2.2 (SILENT MODE)")
    print("="*50)
    print("Notice: Linear Token Stream Engine Online.")
    print("Daily progress spam is hidden. Only years and completions will print.")
    print("Errors are being saved to 'hylee_errors.log'.\n")
    
    scraper = HyenaScraper()
    years = sorted(list(scraper.archive_map.keys()))
    
    for year in years:
        print(f"--- STARTING YEAR: {year} ---")
        links = scraper.get_daily_links(year)
        
        if not links:
            logging.error(f"No daily links found for {year}. Skipping.")
            continue
            
        year_data = {}
        
        for link in links:
            match = re.search(r'(\d{2})(\d{2})(\d{2})pes', link)
            if match:
                date_str = f"20{match.group(1)}-{match.group(2)}-{match.group(3)}"
                
                bullets = scraper.scrape_day(link)
                
                if bullets is None:
                    logging.error(f"Failed to fetch {date_str} (HTTP Error / Timeout)")
                elif len(bullets) == 0:
                    logging.error(f"0 bullets extracted for {date_str}. Unusual HTML format.")
                else:
                    year_data[date_str] = bullets
                
                # Polite scraping delay
                time.sleep(0.2)
                
        if year_data:
            sorted_data = dict(sorted(year_data.items()))
            filename = f"hyena_{year}.json"
            
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(sorted_data, f, ensure_ascii=False, indent=2)
                print(f"[+] SUCCESS: Saved {len(sorted_data)} days to {filename}\n")
            except Exception as e:
                logging.error(f"CRITICAL ERROR saving {filename}: {e}")

    print("="*50)
    print("ALL YEARS PROCESSED.")
    print("="*50)

if __name__ == "__main__":
    main()