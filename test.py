import requests
from bs4 import BeautifulSoup

url = "https://tafheem.net/islamikitabein/urduref.php"
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

surah_links = soup.find_all('a', href=True)

for link in surah_links:
    href = link['href']
    if 'sura=' in href and '&' not in href:
        print(soup.prettify())