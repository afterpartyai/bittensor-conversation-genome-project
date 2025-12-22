from datetime import datetime
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# This script is only used to manually generate the json that is consumed by the validator, it is not called at runtime
def get_la_transcription_links(url='https://lacity.granicus.com/ViewPublisher.php?view_id=129'):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"Error: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    results = []

    grids = soup.find_all('table', class_='listingTable')
    for grid in grids:
        for row in grid.find_all('tr'):
            try:
                cols = row.find_all('td')
                if len(cols) >= 8:
                    transcript = urljoin(url, cols[8].find('a')['href'])
                    name = cols[0].get_text(strip=True)
                    date = cols[1].get_text(strip=True)
                    duration = cols[2].get_text(strip=True)

                    results.append({
                        "name": name,
                        "timestamp": datetime.strptime(date, "%m/%d/%y").timestamp(),
                        "duration": duration,
                        "transcript_link": transcript
                    })
            except Exception as e:
                continue
            
    return results

if __name__ == '__main__':
    la_links = get_la_transcription_links()
    with open('./la_transcript_data.json', 'w', encoding='utf-8') as f:
        json.dump(la_links, f, indent=4)
    print(f"Found: {len(la_links)} transcription links")
