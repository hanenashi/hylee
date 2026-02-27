import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
from bs4 import BeautifulSoup, Comment
import json
import os
import re
import threading
import time

class HyenaScraper:
    def __init__(self, log_callback=None):
        self.base_url = "https://hyena.cz"
        self.headers = {'User-Agent': 'HyleeArchiver/0.5'}
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
        
        self.log(f"Fetching calendar: {archive_url}")
        
        try:
            r = requests.get(archive_url, headers=self.headers, timeout=10)
            r.encoding = 'windows-1250'
            if r.status_code != 200:
                self.log(f"Failed to load calendar (Status: {r.status_code})")
                return []
            
            soup = BeautifulSoup(r.text, 'html.parser')
            links = []
            year_short_str = str(year_full)[-2:] 
            
            for a in soup.find_all('a', href=True):
                href = a['href']
                # Changed filter to 'pes.htm' to catch both .htm and .html extensions
                if 'pes.htm' in href and f"/{year_short_str}/" in href:
                    links.append(href)
            
            clean_links = []
            for link in set(links):
                if link.startswith('/'):
                    clean_links.append(link)
                else:
                    clean_links.append(f"/{link}")
            
            # Sort chronologically before returning
            clean_links.sort()
            return clean_links
        except Exception as e:
            self.log(f"Error fetching calendar: {e}")
            return []

    def scrape_day(self, relative_path, do_sanitize=True):
        url = f"{self.base_url}{relative_path}"
        try:
            r = requests.get(url, headers=self.headers, timeout=10)
            r.encoding = 'windows-1250'
            if r.status_code != 200:
                return None

            soup = BeautifulSoup(r.text, 'html.parser')
            bullets = []
            
            start_node = soup.find(
                string=lambda t: isinstance(t, Comment) and 'odsud' in t.lower()
            )
            
            if start_node:
                curr = start_node.next_element
                while curr:
                    if isinstance(curr, Comment):
                        c_text = curr.lower()
                        if 'konec' in c_text or ('xxxxxxxx' in c_text and 'odsud' not in c_text):
                            break
                    
                    if isinstance(curr, str):
                        text = curr.strip()
                        
                        if "Pokud vám nějaká zpráva přijde debilní" in text:
                            break
                            
                        if do_sanitize:
                            text = self.sanitize_text(text)
                        
                        if len(text) > 15:
                            html_tag_bypass = "<" + "!--" 
                            if not text.startswith(html_tag_bypass):
                                text_lower = text.lower()
                                if "facebook.com" not in text_lower and "digineff.cz" not in text_lower:
                                    bullets.append(text)
                    
                    curr = curr.next_element
            return bullets
        except Exception as e:
            self.log(f"Error scraping {url}: {e}")
            return None


class HyleeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Hyena Leecher - Archive Manager v0.5")
        self.root.geometry("950x650")
        self.root.configure(bg="#f0f0f0")
        
        self.scraper = HyenaScraper(log_callback=self.log)
        self.current_data = {}
        self.current_year = ""
        self.stop_flag = False

        self.build_ui()

    def build_ui(self):
        main_frame = tk.Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        left_col = tk.Frame(main_frame, width=350, bg="#f0f0f0")
        left_col.pack(side="left", fill="y", padx=(0, 10))

        tk.Label(
            left_col, text="ARCHIVE CRAWLER", font=("Arial", 12, "bold"), bg="#f0f0f0"
        ).pack(anchor="w")
        
        config_frame = tk.LabelFrame(
            left_col, text=" Settings ", bg="#f0f0f0", pady=10, padx=10
        )
        config_frame.pack(fill="x", pady=5)

        tk.Label(config_frame, text="Year (YYYY):", bg="#f0f0f0").grid(row=0, column=0, sticky="w", pady=2)
        self.year_entry = tk.Entry(config_frame, width=8)
        self.year_entry.insert(0, "2020")
        self.year_entry.grid(row=0, column=1, padx=5, sticky="w", pady=2)
        
        tk.Label(config_frame, text="Max Days (0=all):", bg="#f0f0f0").grid(row=1, column=0, sticky="w", pady=2)
        self.limit_entry = tk.Entry(config_frame, width=8)
        self.limit_entry.insert(0, "10")
        self.limit_entry.grid(row=1, column=1, padx=5, sticky="w", pady=2)

        self.clean_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            config_frame, text="Sanitize HTML", variable=self.clean_var, bg="#f0f0f0"
        ).grid(row=2, columnspan=2, sticky="w", pady=(5,0))

        btn_frame = tk.Frame(left_col, bg="#f0f0f0")
        btn_frame.pack(fill="x", pady=10)

        self.btn_leech = tk.Button(
            btn_frame, text="FETCH", bg="#2980b9", fg="white", 
            font=("Arial", 10, "bold"), height=2, command=self.start_leech_thread
        )
        self.btn_leech.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_stop = tk.Button(
            btn_frame, text="STOP", bg="#c0392b", fg="white", 
            font=("Arial", 10, "bold"), height=2, state="disabled", command=self.trigger_stop
        )
        self.btn_stop.pack(side="right", fill="x", expand=True, padx=(5, 0))

        self.btn_save = tk.Button(
            left_col, text="SAVE TO JSON SHARD", bg="#27ae60", fg="white", 
            font=("Arial", 10, "bold"), state="disabled", command=self.save_shard
        )
        self.btn_save.pack(fill="x")

        tk.Label(left_col, text="System Log:", bg="#f0f0f0").pack(anchor="w", pady=(15, 0))
        self.log_widget = scrolledtext.ScrolledText(
            left_col, height=15, bg="black", fg="#00ff00", font=("Consolas", 9)
        )
        self.log_widget.pack(fill="both", expand=True)

        right_col = tk.Frame(main_frame, bg="#ffffff", bd=1, relief="sunken")
        right_col.pack(side="right", fill="both", expand=True)

        tk.Label(
            right_col, text=" JSON OUTPUT PREVIEW ", bg="#34495e", 
            fg="white", font=("Arial", 10, "bold")
        ).pack(fill="x")
        
        self.preview_text = scrolledtext.ScrolledText(
            right_col, bg="#ffffff", fg="#333333", font=("Consolas", 10), state="disabled"
        )
        self.preview_text.pack(fill="both", expand=True)

        self.log("System initialized. Ready to leech.")

    def log(self, msg):
        self.log_widget.after(0, self._log_insert, msg)

    def _log_insert(self, msg):
        self.log_widget.insert(tk.END, f"> {msg}\n")
        self.log_widget.see(tk.END)

    def trigger_stop(self):
        self.log("Stop requested... finishing current day.")
        self.stop_flag = True

    def update_preview(self, data_dict):
        def _update():
            self.preview_text.config(state="normal")
            self.preview_text.delete("1.0", tk.END)
            self.preview_text.insert(
                tk.END, json.dumps(data_dict, ensure_ascii=False, indent=2)
            )
            self.preview_text.config(state="disabled")
            
            if data_dict:
                self.btn_save.config(state="normal")
            
            self.btn_leech.config(state="normal", text="FETCH")
            self.btn_stop.config(state="disabled")
        self.root.after(0, _update)

    def start_leech_thread(self):
        year_str = self.year_entry.get().strip()
        limit_str = self.limit_entry.get().strip()
        
        if not year_str.isdigit() or len(year_str) != 4:
            messagebox.showerror("Input Error", "Please enter a 4-digit year (e.g., 2020).")
            return
            
        max_days = 0
        if limit_str.isdigit():
            max_days = int(limit_str)

        self.current_year = year_str
        self.stop_flag = False
        
        self.btn_leech.config(state="disabled", text="LEECHING...")
        self.btn_stop.config(state="normal")
        self.btn_save.config(state="disabled")
        self.current_data = {}
        self.update_preview({})
        
        thread = threading.Thread(
            target=self.run_scraper, args=(year_str, self.clean_var.get(), max_days)
        )
        thread.daemon = True
        thread.start()

    def run_scraper(self, year_str, do_sanitize, max_days):
        links = self.scraper.get_daily_links(year_str)
        
        if not links:
            self.log("No links found or failed to parse calendar.")
            self.update_preview({})
            return

        self.log(f"Found {len(links)} daily links to process.")
        
        days_processed = 0
        for link in links:
            if self.stop_flag:
                self.log("--- HALTED BY USER ---")
                break
                
            match = re.search(r'(\d{2})(\d{2})(\d{2})pes', link)
            if match:
                date_str = f"20{match.group(1)}-{match.group(2)}-{match.group(3)}"
                self.log(f"Scraping: {date_str}")
                
                bullets = self.scraper.scrape_day(link, do_sanitize)
                
                if bullets is None:
                    self.log(f"[ERROR] Failed to fetch {date_str}")
                elif len(bullets) == 0:
                    self.log(f"[WARNING] 0 bullets extracted for {date_str}. Unusual format?")
                else:
                    self.current_data[date_str] = bullets
                    
                days_processed += 1
                if max_days > 0 and days_processed >= max_days:
                    self.log(f"--- Reached debug limit ({max_days} days) ---")
                    break
                
                time.sleep(0.2) 

        self.log("Scraping cycle concluded.")
        sorted_data = dict(sorted(self.current_data.items()))
        self.current_data = sorted_data
        self.update_preview(self.current_data)

    def save_shard(self):
        if not self.current_data:
            return
        
        filename = f"hyena_{self.current_year}.json"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.current_data, f, ensure_ascii=False, indent=2)
            self.log(f"SUCCESS: Data saved to {filename}")
            messagebox.showinfo("Saved", f"Archive saved to {filename} successfully.")
        except Exception as e:
            self.log(f"ERROR saving file: {e}")
            messagebox.showerror("Save Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = HyleeGUI(root)
    root.mainloop()