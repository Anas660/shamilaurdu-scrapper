import requests
from bs4 import BeautifulSoup
import json
import time
import os
import re

BASE_URL = "https://tafheem.net/islamikitabein/urduref.php"

# Use hardcoded Surah list - can be expanded to full range later
surah_list = [{'id': str(i), 'name': f'Surah {i}'} for i in range(3, 4)]

def get_total_verses(surah_id):
    """
    Get the total number of verses in a surah
    """
    url = f"{BASE_URL}?sura={surah_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        max_end = 0

        for a in soup.find_all("a"):
            href = a.get("href", "")
            text = a.get_text(strip=True)
            if "?sura=" in href and "verse=" in href and "[" in text and "-" in text and "]" in text:
                try:
                    verse_range = text.split("[")[0].strip()
                    start, end = verse_range.split("-")
                    end_num = int(end)

                    if end_num > max_end:
                        max_end = end_num

                except Exception as e:
                    continue

        return max_end
    except Exception as e:
        print(f"Error getting total verses for surah {surah_id}: {e}")
        return 0

def download_surah_html(surah_id, total_verses):
    """
    Download the HTML content for a surah and save to file
    """
    # Create directory if it doesn't exist
    if not os.path.exists("html_files"):
        os.makedirs("html_files")
        
    # File path for the HTML content
    html_file_path = f"html_files/surah_{surah_id}_html.txt"
    
    # If file already exists, skip download
    if os.path.exists(html_file_path):
        print(f"   ↳ HTML file for Surah {surah_id} already exists, skipping download")
        return True
    
    url = f"{BASE_URL}?sura={surah_id}&verse=1-{total_verses}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    try:
        print(f"   ↳ Downloading Surah {surah_id} content")
        response = requests.get(url, headers=headers)
        
        # Save HTML content to file
        with open(html_file_path, "w", encoding="utf-8") as html_file:
            html_file.write(response.text)
        
        print(f"   ↳ HTML saved to {html_file_path}")
        return True
    except Exception as e:
        print(f"Error downloading surah {surah_id}: {e}")
        return False

def process_surah_html(surah_id, total_verses):
    """
    Process the saved HTML file for a surah and extract content
    """
    html_file_path = f"html_files/surah_{surah_id}_html.txt"
    
    if not os.path.exists(html_file_path):
        print(f"   ↳ HTML file for Surah {surah_id} not found")
        return []
    
    try:
        with open(html_file_path, "r", encoding="utf-8") as html_file:
            html_content = html_file.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        content_div = soup.find("div", style="margin:0px auto; max-width:800px; padding:10px;")
        verses = []

        if not content_div:
            return verses

        # Extract Arabic text
        ar_div = content_div.find("div", class_="ar")
        arabic_spans = ar_div.find_all("span") if ar_div else []
        # Remove verse numbers (spans with class="nm")
        arabic_spans = [span for span in arabic_spans if "nm" not in span.get("class", [])]
        
        # Extract Urdu translations
        ur_div = content_div.find("div", class_="ur")
        urdu_spans = ur_div.find_all("span") if ur_div else []
        
        # Extract Tafseer notes - get all notes with their reference numbers
        nt_div = content_div.find("div", class_="nt")
        tafseer_paragraphs = nt_div.find_all("p") if nt_div else []
        
        # Create a dictionary of tafseer notes by reference number
        tafseer_dict = {}
        for p in tafseer_paragraphs:
            # Each tafseer paragraph starts with a number like "1 -", extract it
            try:
                p_text = p.get_text(strip=True)
                if p.find('n'):
                    ref_num = p.find('n').get_text(strip=True).replace('-', '').strip()
                    tafseer_dict[ref_num] = p_text
            except:
                continue
        
        # Get actual verse count for processing (don't limit to 7)
        verse_count = min(total_verses, len(arabic_spans))
        print(f"   ↳ Processing {verse_count} verses")
        
        for i in range(verse_count):
            # Extract Arabic text
            arabic_text = arabic_spans[i].get_text(strip=True) if i < len(arabic_spans) else ""
            
            # Extract Urdu text and find reference numbers
            urdu_text = ""
            tafseer_refs = []
            
            if i < len(urdu_spans):
                # Get the raw HTML to extract references
                span_html = str(urdu_spans[i])
                urdu_text = urdu_spans[i].get_text(strip=True)
                
                # Find all tafseer references with flexible pattern matching
                # Match both F1_1.html and B2_12.html patterns
                refs = re.findall(r'[FB]' + surah_id + r'_(\d+)\.html', span_html)
                tafseer_refs = [ref for ref in refs]
            
            # Collect all referenced tafseer notes for this verse
            verse_tafseer = ""
            for ref in tafseer_refs:
                if ref in tafseer_dict:
                    if verse_tafseer:
                        verse_tafseer += "\n\n"  # Add separation between different tafseer notes
                    verse_tafseer += tafseer_dict[ref]
            
            verse_data = {
                "verse_number": i + 1,
                "arabic": arabic_text,
                "urdu": urdu_text,
                "tafseer": verse_tafseer,
                "tafseer_refs": tafseer_refs  # Keep track of which refs were used
            }
            verses.append(verse_data)

        return verses
    except Exception as e:
        print(f"Error processing surah {surah_id}: {e}")
        return []

def scrape_tafseer(main_url):
    """
    Scrape the complete tafseer for a surah from the main URL and linked pages
    """
    main_html = download_page(main_url)
    tafseer_links = extract_tafseer_links(main_html)  # Find all links like "1.html", "2.html"
    
    complete_tafseer = main_html
    for link in tafseer_links:
        tafseer_content = download_page(BASE_URL + link)
        complete_tafseer += tafseer_content
        
    return complete_tafseer

def main():
    all_surahs = []
    
    # First, download all surah HTML files
    for surah in surah_list:
        surah_id = surah["id"]
        print(f"⏳ Processing Surah {surah_id}")
        
        total_verses = get_total_verses(surah_id)
        print(f"   ↳ Found {total_verses} verses")
        
        if total_verses == 0:
            print(f"   ↳ No verses found for Surah {surah_id}, skipping")
            continue
        
        download_surah_html(surah_id, total_verses)
        time.sleep(1)  # Avoid overloading the server
    
    # Then, process all downloaded HTML files
    print("\n⏳ Processing downloaded HTML files")
    for surah in surah_list:
        surah_id = surah["id"]
        print(f"⏳ Processing Surah {surah_id} HTML")
        
        total_verses = get_total_verses(surah_id)
        if total_verses == 0:
            continue
            
        verses = process_surah_html(surah_id, total_verses)
        
        if verses:
            all_surahs.append({
                "surah_id": surah_id,
                "surah_name": surah["name"],
                "total_verses": total_verses,
                "verses": verses
            })
            print(f"   ↳ Successfully processed {len(verses)} verses for Surah {surah_id}")
        else:
            print(f"   ↳ Failed to process Surah {surah_id}")

    # Save all data to JSON file
    with open("tafheem_quran_data.json", "w", encoding="utf-8") as f:
        json.dump(all_surahs, f, ensure_ascii=False, indent=2)

    print("✅ Processing complete. Data saved to tafheem_quran_data.json")

if __name__ == "__main__":
    main()