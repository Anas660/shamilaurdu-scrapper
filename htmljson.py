import os
import json
import re
from bs4 import BeautifulSoup
import glob

def process_surah_html_to_json(html_file_path):
    """
    Process a single surah HTML file and save it as a separate JSON file
    """
    # Extract surah_id from filename
    filename = os.path.basename(html_file_path)
    surah_id = filename.split('_')[1]
    
    print(f"Processing Surah {surah_id}...")
    
    try:
        with open(html_file_path, "r", encoding="utf-8") as html_file:
            html_content = html_file.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract surah title from HTML
        title = soup.find('title').text.strip() if soup.find('title') else f"Surah {surah_id}"
        surah_name = title.split(',')[0] if ',' in title else title
        
        content_div = soup.find("div", style="margin:0px auto; max-width:800px; padding:10px;")
        verses = []

        if not content_div:
            print(f"   ↳ No content found for Surah {surah_id}")
            return

        # Extract Arabic text
        ar_div = content_div.find("div", class_="ar")
        arabic_spans = ar_div.find_all("span") if ar_div else []
        # Remove verse numbers (spans with class="nm")
        arabic_spans = [span for span in arabic_spans if "nm" not in span.get("class", [])]
        
        # Extract Urdu translations
        ur_div = content_div.find("div", class_="ur")
        urdu_spans = ur_div.find_all("span") if ur_div else []
        
        # Extract Tafseer notes
        nt_div = content_div.find("div", class_="nt")
        tafseer_paragraphs = nt_div.find_all("p") if nt_div else []
        
        # Debug info about tafseer paragraphs
        print(f"   ↳ Found {len(tafseer_paragraphs)} tafseer paragraphs")
        
        # IMPROVEMENT 1: Enhanced tafseer extraction with better structure handling
        tafseer_dict = {}
        for p in tafseer_paragraphs:
            try:
                # Extract the full paragraph text first
                p_text = p.get_text(strip=True)
                if not p_text:
                    continue
                    
                # Method 1: Look for <n> tag which usually contains the reference number
                if p.find('n'):
                    ref_num = p.find('n').get_text(strip=True).replace('-', '').strip()
                    tafseer_dict[ref_num] = p_text
                    continue
                
                # Method 2: Use regex to extract reference number from the beginning of the text
                # Look for patterns like "1. " or "1 -" at the beginning of paragraphs
                ref_match = re.match(r'^(\d+)[\.:\-\s]+', p_text)
                if ref_match:
                    ref_num = ref_match.group(1)
                    tafseer_dict[ref_num] = p_text
                    continue
                    
                # Method 3: If a paragraph starts with a number, try that
                if p_text and p_text[0].isdigit():
                    num_str = ""
                    for char in p_text:
                        if char.isdigit():
                            num_str += char
                        else:
                            break
                    if num_str:
                        tafseer_dict[num_str] = p_text
            except Exception as e:
                print(f"   ↳ Error parsing tafseer paragraph: {e}")
                continue
        
        # Debug info about extracted tafseer
        print(f"   ↳ Extracted {len(tafseer_dict)} tafseer entries")
        
        # Get actual verse count for processing
        verse_count = len(arabic_spans)
        print(f"   ↳ Found {verse_count} verses")
        
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
                
                # IMPROVEMENT 2: More comprehensive reference extraction
                # Pattern 1: specific format with surah_id
                pattern1 = r'[FB]' + surah_id + r'_(\d+)\.html'
                # Pattern 2: simple number format (common in Surah 3)
                pattern2 = r'href="(\d+)\.html"'
                # Pattern 3: direct number links without .html (some surahs)
                pattern3 = r'href="(\d+)"'
                # Pattern 4: look for superscript numbers (common pattern)
                pattern4 = r'<sup>(\d+)</sup>'
                
                refs1 = re.findall(pattern1, span_html)
                refs2 = re.findall(pattern2, span_html)
                refs3 = re.findall(pattern3, span_html)
                refs4 = re.findall(pattern4, span_html)
                
                # Combine references from all patterns
                tafseer_refs = refs1 + refs2 + refs3 + refs4
                
                # Remove duplicates while preserving order
                seen = set()
                tafseer_refs = [x for x in tafseer_refs if not (x in seen or seen.add(x))]
            
            # Collect all referenced tafseer notes for this verse
            verse_tafseer = ""
            
            # IMPROVEMENT 3: More robust tafseer matching
            for ref in tafseer_refs:
                if ref in tafseer_dict:
                    if verse_tafseer:
                        verse_tafseer += "\n\n"
                    verse_tafseer += tafseer_dict[ref]
                else:
                    # Try matching with different formats (some references might be padded with zeros)
                    ref_int = int(ref) if ref.isdigit() else 0
                    ref_str = str(ref_int)
                    if ref_str in tafseer_dict:
                        if verse_tafseer:
                            verse_tafseer += "\n\n"
                        verse_tafseer += tafseer_dict[ref_str]
            
            # IMPROVEMENT 4: Ensure consistent structure for all verses
            verse_data = {
                "verse_number": i + 1,
                "arabic": arabic_text,
                "urdu": urdu_text,
                "tafseer": verse_tafseer,
                "tafseer_refs": tafseer_refs
            }
            verses.append(verse_data)

        # Create surah data structure
        surah_data = {
            "surah_id": surah_id,
            "surah_name": surah_name,
            "total_verses": verse_count,
            "verses": verses
        }

        # Save to JSON file
        json_filename = f"surah_{surah_id}.json"
        with open(json_filename, "w", encoding="utf-8") as json_file:
            json.dump(surah_data, json_file, ensure_ascii=False, indent=2)
        
        print(f"   ↳ Saved to {json_filename}")
        
        # IMPROVEMENT 5: Generate a report about tafseer coverage
        verses_with_refs = sum(1 for v in verses if v["tafseer_refs"])
        verses_with_tafseer = sum(1 for v in verses if v["tafseer"])
        print(f"   ↳ Verses with references: {verses_with_refs}/{verse_count} ({verses_with_refs/verse_count*100:.1f}%)")
        print(f"   ↳ Verses with tafseer: {verses_with_tafseer}/{verse_count} ({verses_with_tafseer/verse_count*100:.1f}%)")
        
        return surah_data
        
    except Exception as e:
        print(f"Error processing surah {surah_id}: {e}")
        return None

def process_all_surahs():
    """
    Process all surah HTML files and save each as a separate JSON file
    """
    # Create directory for JSON files if it doesn't exist
    if not os.path.exists("json_files"):
        os.makedirs("json_files")
    
    # Get list of all HTML files
    html_files = glob.glob(os.path.join("html_files", "surah_*_html.txt"))
    
    print(f"Found {len(html_files)} HTML files to process")
    
    if len(html_files) == 0:
        print("No HTML files found. Make sure the files exist in the html_files directory.")
        return
    
    # Sort files by surah number
    def get_surah_number(filepath):
        filename = os.path.basename(filepath)
        parts = filename.split('_')
        if len(parts) >= 2:
            try:
                return int(parts[1])
            except ValueError:
                return 0
        return 0
    
    html_files.sort(key=get_surah_number)
    
    # Process each file
    all_surahs_data = []
    
    for html_file in html_files:
        surah_data = process_surah_html_to_json(html_file)
        if surah_data:
            all_surahs_data.append(surah_data)
    
    # Also save a complete collection in one file
    with open("all_surahs.json", "w", encoding="utf-8") as f:
        json.dump(all_surahs_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Processing complete. Created {len(all_surahs_data)} individual JSON files")
    print(f"✅ Also saved all surahs to all_surahs.json")

if __name__ == "__main__":
    process_all_surahs()