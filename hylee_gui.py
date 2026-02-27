import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
from bs4 import BeautifulSoup, Comment
import json
import os
import re
import threading
import time
import webbrowser

class HyenaScraper:
    def __init__(self, log_callback=None):
        self.base_url = "https://hyena.cz"
        self.headers = {'User-Agent': 'HyleeArchiver/2.2'}
        self.log = log_callback if log_callback else print
        
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
        
        self.log(f"Fetching calendar for {year_full}: {archive_url}")
        
        try:
            r = requests.get(archive_url, headers=self.headers, timeout=10)
            
            try:
                html_text = r.content.decode('utf-8')
            except UnicodeDecodeError:
                html_text = r.content.decode('windows-1250', errors='replace')
                
            if r.status_code != 200:
                self.log(f"Failed to load calendar (Status: {r.status_code})")
                return []
            
            soup = BeautifulSoup(html_text, 'html.parser')
            links = []
            year_short_str = str(year_full)[-2:] 
            
            for a in soup.find_all('a', href=True):
                href = a['href']
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
            self.log(f"Error fetching calendar: {e}")
            return []

    def scrape_day(self, relative_path, do_sanitize=True):
        url = f"{self.base_url}{relative_path}"
        try:
            r = requests.get(url, headers=self.headers, timeout=10)
            if r.status_code != 200:
                return None

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
            self.log(f"Error scraping {url}: {e}")
            return None


class HyleeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Hyena Leecher - Archive Manager v2.2")
        self.root.geometry("1100x700")
        self.root.configure(bg="#f0f0f0")
        
        self.scraper = HyenaScraper(log_callback=self.log)
        self.current_data = {}
        self.current_year = ""
        self.stop_flag = False

        self.build_ui()

    def build_ui(self):
        main_frame = tk.Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # ---------------- LEFT COLUMN ----------------
        left_col = tk.Frame(main_frame, width=300, bg="#f0f0f0")
        left_col.pack(side="left", fill="y", padx=(0, 10))

        tk.Label(left_col, text="ARCHIVE CRAWLER", font=("Arial", 12, "bold"), bg="#f0f0f0").pack(anchor="w")
        
        config_frame = tk.LabelFrame(left_col, text=" Settings ", bg="#f0f0f0", pady=10, padx=10)
        config_frame.pack(fill="x", pady=5)

        tk.Label(config_frame, text="Year(s):", bg="#f0f0f0").grid(row=0, column=0, sticky="w", pady=2)
        self.year_entry = tk.Entry(config_frame, width=12)
        self.year_entry.insert(0, "2004")
        self.year_entry.grid(row=0, column=1, padx=5, sticky="w", pady=2)
        
        tk.Label(config_frame, text="Max Days:", bg="#f0f0f0").grid(row=1, column=0, sticky="w", pady=2)
        self.limit_entry = tk.Entry(config_frame, width=8)
        self.limit_entry.insert(0, "0")
        self.limit_entry.grid(row=1, column=1, padx=5, sticky="w", pady=2)

        self.clean_var = tk.BooleanVar(value=True)
        tk.Checkbutton(config_frame, text="Sanitize HTML", variable=self.clean_var, bg="#f0f0f0").grid(row=2, columnspan=2, sticky="w", pady=(5,0))
        tk.Label(config_frame, text="(Formats: 2025, 2010-2015, ALL)", bg="#f0f0f0", fg="gray", font=("Arial", 8)).grid(row=3, columnspan=2, sticky="w")

        self.btn_load_tree = tk.Button(left_col, text="1. LOAD YEAR TO EXPLORER", bg="#8e44ad", fg="white", font=("Arial", 9, "bold"), command=self.load_calendar_to_tree)
        self.btn_load_tree.pack(fill="x", pady=(10, 5))

        btn_frame = tk.Frame(left_col, bg="#f0f0f0")
        btn_frame.pack(fill="x", pady=5)

        self.btn_leech = tk.Button(btn_frame, text="2. BATCH LEECH", bg="#2980b9", fg="white", font=("Arial", 9, "bold"), height=2, command=self.start_leech_thread)
        self.btn_leech.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_stop = tk.Button(btn_frame, text="STOP", bg="#c0392b", fg="white", font=("Arial", 9, "bold"), height=2, state="disabled", command=self.trigger_stop)
        self.btn_stop.pack(side="right", fill="x", expand=True, padx=(5, 0))

        tk.Label(left_col, text="System Log:", bg="#f0f0f0").pack(anchor="w", pady=(5, 0))
        self.log_widget = scrolledtext.ScrolledText(left_col, height=15, bg="black", fg="#00ff00", font=("Consolas", 9))
        self.log_widget.pack(fill="both", expand=True)

        # ---------------- MIDDLE COLUMN (Tree Explorer) ----------------
        mid_col = tk.Frame(main_frame, width=250, bg="#f0f0f0")
        mid_col.pack(side="left", fill="y", padx=10)
        
        tk.Label(mid_col, text=" CALENDAR EXPLORER ", bg="#e67e22", fg="white", font=("Arial", 10, "bold")).pack(fill="x")
        
        self.tree = ttk.Treeview(mid_col, selectmode="browse")
        self.tree.pack(fill="both", expand=True, pady=5)
        
        tree_scroll = ttk.Scrollbar(mid_col, orient="vertical", command=self.tree.yview)
        tree_scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=tree_scroll.set)
        
        self.btn_open_browser = tk.Button(mid_col, text="Open Link in Browser", command=self.open_in_browser)
        self.btn_open_browser.pack(fill="x", pady=2)
        
        self.btn_parse_single = tk.Button(mid_col, text="Parse Selected Day", bg="#27ae60", fg="white", font=("Arial", 9, "bold"), command=self.parse_single_day)
        self.btn_parse_single.pack(fill="x", pady=2)

        # ---------------- RIGHT COLUMN (Preview) ----------------
        right_col = tk.Frame(main_frame, bg="#ffffff", bd=1, relief="sunken")
        right_col.pack(side="right", fill="both", expand=True)

        tk.Label(right_col, text=" JSON OUTPUT PREVIEW ", bg="#34495e", fg="white", font=("Arial", 10, "bold")).pack(fill="x")
        
        self.preview_text = scrolledtext.ScrolledText(right_col, bg="#ffffff", fg="#333333", font=("Consolas", 10), state="normal")
        self.preview_text.pack(fill="both", expand=True)

        self.log("System initialized. Token Stream Engine online.")

    # --- UI HELPERS ---
    def log(self, msg):
        self.log_widget.after(0, self._log_insert, msg)

    def _log_insert(self, msg):
        self.log_widget.insert(tk.END, f"> {msg}\n")
        self.log_widget.see(tk.END)

    def trigger_stop(self):
        self.log("Stop requested... finishing current task.")
        self.stop_flag = True

    def reset_buttons(self):
        def _reset():
            self.btn_leech.config(state="normal", text="2. BATCH LEECH")
            self.btn_stop.config(state="disabled")
        self.root.after(0, _reset)

    # --- EXPLORER LOGIC ---
    def load_calendar_to_tree(self):
        year_input = self.year_entry.get().strip()
        if not year_input.isdigit() or len(year_input) != 4:
            messagebox.showerror("Error", "Please enter a single 4-digit year to load into the explorer.")
            return
            
        self.tree.delete(*self.tree.get_children())
        self.log(f"Loading calendar links for {year_input} into Explorer...")
        
        thread = threading.Thread(target=self._fetch_and_populate_tree, args=(year_input,))
        thread.daemon = True
        thread.start()
        
    def _fetch_and_populate_tree(self, year_str):
        links = self.scraper.get_daily_links(year_str)
        if not links:
            self.log(f"No links found for {year_str}.")
            return
            
        self.log(f"Found {len(links)} links. Populating explorer...")
        
        months = {}
        for link in links:
            match = re.search(r'(\d{2})(\d{2})(\d{2})pes', link)
            if match:
                y, m, d = match.groups()
                month_key = f"20{y}-{m}"
                date_str = f"20{y}-{m}-{d}"
                if month_key not in months:
                    months[month_key] = []
                months[month_key].append((date_str, link))
        
        def _update_ui():
            for m_key in sorted(months.keys()):
                month_node = self.tree.insert("", "end", text=f"Month: {m_key}", open=False)
                for date_str, link in sorted(months[m_key]):
                    self.tree.insert(month_node, "end", text=date_str, values=(link,))
        
        self.root.after(0, _update_ui)

    def get_selected_link(self):
        selected = self.tree.selection()
        if not selected:
            return None, None
        item = self.tree.item(selected[0])
        if item['values']:
            return item['text'], item['values'][0]
        return None, None

    def open_in_browser(self):
        date_str, link = self.get_selected_link()
        if link:
            full_url = f"{self.scraper.base_url}{link}"
            self.log(f"Opening browser: {full_url}")
            webbrowser.open(full_url)
        else:
            self.log("Please select a specific day (not a month folder) to open.")

    def parse_single_day(self):
        date_str, link = self.get_selected_link()
        if not link:
            self.log("Please select a specific day to parse.")
            return
            
        self.log(f"Single Test Parsing: {date_str} ...")
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert(tk.END, f"--- Fetching {date_str} ---\n\n")
        
        thread = threading.Thread(target=self._parse_and_display_single, args=(date_str, link, self.clean_var.get()))
        thread.daemon = True
        thread.start()

    def _parse_and_display_single(self, date_str, link, do_sanitize):
        bullets = self.scraper.scrape_day(link, do_sanitize)
        
        def _update():
            if bullets is None:
                self.preview_text.insert(tk.END, "ERROR: Failed to fetch page.")
            elif len(bullets) == 0:
                self.preview_text.insert(tk.END, "WARNING: 0 bullets extracted. Check the format in browser.")
            else:
                formatted_json = json.dumps({date_str: bullets}, ensure_ascii=False, indent=2)
                self.preview_text.insert(tk.END, formatted_json)
                self.log(f"Successfully extracted {len(bullets)} bullets for {date_str}.")
        self.root.after(0, _update)

    # --- BATCH SCRAPING ---
    def start_leech_thread(self):
        year_input = self.year_entry.get().strip().upper()
        limit_str = self.limit_entry.get().strip()
        
        years_to_process = []
        if year_input == "ALL":
            years_to_process = sorted(list(self.scraper.archive_map.keys()))
        elif "-" in year_input:
            parts = year_input.split("-")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                start_y, end_y = int(parts[0]), int(parts[1])
                y_min, y_max = min(start_y, end_y), max(start_y, end_y)
                years_to_process = list(range(y_min, y_max + 1))
        elif year_input.isdigit() and len(year_input) == 4:
            years_to_process = [int(year_input)]
            
        valid_years = [y for y in years_to_process if y in self.scraper.archive_map]
        
        if not valid_years:
            messagebox.showerror("Input Error", "Invalid year input. Use YYYY, YYYY-YYYY, or ALL.")
            return
            
        max_days = int(limit_str) if limit_str.isdigit() else 0

        self.stop_flag = False
        self.btn_leech.config(state="disabled", text="LEECHING...")
        self.btn_stop.config(state="normal")
        self.preview_text.delete("1.0", tk.END)
        
        thread = threading.Thread(target=self.run_batch_scraper, args=(valid_years, self.clean_var.get(), max_days))
        thread.daemon = True
        thread.start()

    def run_batch_scraper(self, valid_years, do_sanitize, max_days):
        self.log(f"Starting batch queue for {len(valid_years)} year(s)...")
        
        for year in valid_years:
            if self.stop_flag: break
                
            self.log(f"\n--- INITIATING CRAWL: {year} ---")
            self.current_year = str(year)
            self.current_data = {}
            
            links = self.scraper.get_daily_links(year)
            if not links:
                self.log(f"No links found for {year}.")
                continue

            self.log(f"Found {len(links)} daily links for {year}.")
            
            days_processed = 0
            for link in links:
                if self.stop_flag: break
                    
                match = re.search(r'(\d{2})(\d{2})(\d{2})pes', link)
                if match:
                    date_str = f"20{match.group(1)}-{match.group(2)}-{match.group(3)}"
                    self.log(f"Scraping: {date_str}")
                    
                    bullets = self.scraper.scrape_day(link, do_sanitize)
                    
                    if bullets is None:
                        self.log(f"[ERROR] Failed to fetch {date_str}")
                    elif len(bullets) == 0:
                        self.log(f"[WARNING] 0 bullets extracted for {date_str}.")
                    else:
                        self.current_data[date_str] = bullets
                        
                    days_processed += 1
                    if max_days > 0 and days_processed >= max_days:
                        self.log(f"--- Reached limit ({max_days} days) ---")
                        break
                    
                    time.sleep(0.2) 

            if self.current_data:
                sorted_data = dict(sorted(self.current_data.items()))
                
                def _update_ui(data):
                    self.preview_text.delete("1.0", tk.END)
                    self.preview_text.insert(tk.END, json.dumps(data, ensure_ascii=False, indent=2))
                self.root.after(0, _update_ui, sorted_data)
                
                filename = f"hyena_{self.current_year}.json"
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(sorted_data, f, ensure_ascii=False, indent=2)
                    self.log(f"AUTO-SAVED: {filename}")
                except Exception as e:
                    self.log(f"[CRITICAL ERROR] Failed to save {filename}: {e}")

        if not self.stop_flag:
            self.log("\n+++ BATCH SCRAPING COMPLETE +++")
        self.reset_buttons()


if __name__ == "__main__":
    root = tk.Tk()
    app = HyleeGUI(root)
    root.mainloop()