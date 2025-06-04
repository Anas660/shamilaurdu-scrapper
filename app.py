import requests
from bs4 import BeautifulSoup
import json
import time

BASE_URL = "https://tafheem.net/islamikitabein/urduref.php"

# Use hardcoded Surah list
surah_list = [{'id': str(i), 'name': f'Surah {i}'} for i in range(3, 4)]

def get_total_verses(surah_id):
    url = f"{BASE_URL}?sura={surah_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
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

                #print(f"Found link: href={href}, text='{text}', start={start}, end={end}")

                if end_num > max_end:
                    max_end = end_num

            except Exception as e:
                #print(f"Error parsing: href={href}, text='{text}', error={e}")
                continue

    return max_end

def get_surah_content(surah_id, total_verses):
    url = f"{BASE_URL}?sura={surah_id}&verse=1-{total_verses}"
    total_verses=7
    print(f"total verses {total_verses}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    with open(f"surah_{surah_id}_html.txt", "w", encoding="utf-8") as html_file:
        html_file.write(soup.prettify())
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
    
    for i in range(min(total_verses, len(arabic_spans))):
        # Extract Arabic text
        arabic_text = arabic_spans[i].get_text(strip=True) if i < len(arabic_spans) else ""
        
        # Extract Urdu text and find reference numbers
        urdu_text = ""
        tafseer_refs = []
        
        if i < len(urdu_spans):
            # Get the raw HTML to extract references
            span_html = str(urdu_spans[i])
            urdu_text = urdu_spans[i].get_text(strip=True)
            
            # Find all references like F1_1.html, F1_2.html etc.
            import re
            refs = re.findall(r'F' + surah_id + r'_(\d+)\.html', span_html)
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
            "tafseer_refs": tafseer_refs  # You might want to keep track of which refs were used
        }
        verses.append(verse_data)

    return verses
def main():
    all_surahs = []

    for surah in surah_list:
        surah_id = surah["id"]
        print(f"⏳ Processing Surah {surah_id}")
        total_verses = get_total_verses(surah_id)
        print(f"   ↳ Found {total_verses} verses")
        if total_verses == 0:
            #print(f"   ↳ Scraping Surah {surah_id} content")
            continue
        verses = get_surah_content(surah_id, total_verses)
        all_surahs.append({
            "surah_id": surah_id,
            "surah_name": surah["name"],
            "total_verses": total_verses,
            "verses": verses  # This is the list returned by get_surah_content
        })
        time.sleep(1)  # Avoid overloading the server

    with open("tafheem_quran_data.json", "w", encoding="utf-8") as f:
        json.dump(all_surahs, f, ensure_ascii=False, indent=2)

    print("✅ Scraping complete. Data saved to tafheem_quran_data.json")

if __name__ == "__main__":
    main()
