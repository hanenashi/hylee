import os

# Define your file paths (using raw strings 'r' to handle Windows backslashes)
input_log = r"C:\GIT\hylee\fullscrape.log"
output_log = r"C:\GIT\hylee\fullscrape_clean.log"

try:
    with open(input_log, 'r', encoding='utf-8') as infile, \
         open(output_log, 'w', encoding='utf-8') as outfile:
        
        removed_count = 0
        kept_count = 0
        
        for line in infile:
            # If the line contains our spam trigger, skip it
            if "> Scraping:" in line:
                removed_count += 1
            else:
                # Otherwise, write it to the new clean log
                outfile.write(line)
                kept_count += 1
                
    print("Log cleanup complete!")
    print(f"[-] Removed {removed_count} spam lines.")
    print(f"[+] Kept {kept_count} important lines.")
    print(f"Saved clean log to: {output_log}")

except FileNotFoundError:
    print(f"Error: Could not find the file at {input_log}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")