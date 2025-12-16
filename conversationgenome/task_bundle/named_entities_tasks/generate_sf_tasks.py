from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import json
import time

class LegistarScraper:
    def __init__(self):
        self.base_url = "https://sfgov.legistar.com/Calendar.aspx"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        # Dictionary to store results (Key = URL ensures no duplicates)
        self.results_dict = {}
        
        # Compile regex once for efficiency
        self.transcript_pattern = re.compile(r"window\.open\('([^']*Transcript\.aspx[^']*)'")

    def get_hidden_fields(self, soup):
        """Extracts standard ASP.NET hidden fields."""
        data = {}
        for item in soup.find_all('input', type='hidden'):
            if item.get('name'):
                data[item['name']] = item.get('value', '')
        return data

    def extract_meeting_data(self, soup):
        """Iterates through table rows to extract metadata + transcript link."""
        count = 0
        
        # Find the main data grid
        grid = soup.find('table', class_='rgMasterTable')
        if not grid:
            return 0
        
        # Iterate over all rows in the table
        for row in grid.find_all('tr'):
            cols = row.find_all('td')
            
            # Ensure it's a valid data row (must have enough columns)
            # User specified: Name(1), Date(2), Time(4), Location(5) -> Index 0, 1, 3, 4
            if len(cols) < 5:
                continue

            # Check if this row has a transcript link
            found_url = None
            
            # Search specifically inside this row's links
            for link in row.find_all('a'):
                onclick = link.get('onclick', '')
                href = link.get('href', '')

                if onclick and "Transcript.aspx" in onclick:
                    match = self.transcript_pattern.search(onclick)
                    if match:
                        found_url = match.group(1)
                        break
                elif "Transcript.aspx" in href:
                    found_url = href
                    break
            
            # If a transcript was found in this row, grab the metadata
            if found_url:
                full_url = urljoin(self.base_url, found_url)
                
                # Extract Metadata based on user indices
                # 1st td = Name
                name = cols[0].get_text(strip=True)
                
                # 2nd td = Date
                date_part = cols[1].get_text(strip=True)
                
                # 4th td = Time (Index 3)
                time_part = cols[3].get_text(strip=True)
                
                # 5th td = Location (Index 4)
                location = cols[4].get_text(strip=True)
                
                # Combine Date and Time
                full_date_str = f"{date_part} {time_part}".strip()
                full_date_timestamp = datetime.strptime(full_date_str, "%m/%d/%Y %I:%M %p").timestamp()

                # Store object if not already present
                if full_url not in self.results_dict:
                    self.results_dict[full_url] = {
                        "name": name,
                        "timestamp": full_date_timestamp,
                        "context": location,
                        "transcript_link": full_url
                    }
                    count += 1
                    
        return count

    def get_next_page_payload(self, soup, current_page):
        """Finds the __EVENTTARGET for the next page."""
        next_page_num = str(current_page + 1)
        # Find link text " 2 ", " 3 ", etc.
        next_link = soup.find('a', string=re.compile(rf"^\s*{next_page_num}\s*$"))
        
        if next_link and 'href' in next_link.attrs:
            href = next_link['href']
            if "doPostBack" in href:
                match = re.search(r"__doPostBack\('([^']*)','([^']*)'\)", href)
                if match:
                    return match.group(1), match.group(2)
        return None, None

    def scrape_year(self, year):
        print(f"--- Processing Year: {year} ---")
        
        response = self.session.get(self.base_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Identify Controls
        year_input = soup.find('input', {'name': re.compile(r'lstYears')}) or \
                     soup.find('select', {'name': re.compile(r'lstYears')})
        year_control_name = year_input.get('name') if year_input else "ctl00$ContentPlaceHolder1$lstYears"

        search_btn = soup.find('input', {'name': re.compile(r'btnSearch')})
        search_btn_name = search_btn.get('name') if search_btn else "ctl00$ContentPlaceHolder1$btnSearch"

        # Construct Telerik Payload
        form_data = self.get_hidden_fields(soup)
        form_data[year_control_name] = str(year)
        
        client_state_name = year_control_name.replace('$', '_') + "_ClientState"
        client_state_json = {
            "logEntries": [], "value": str(year), "text": str(year),
            "enabled": True, "checkedIndices": [], "checkedItemsTextOverflows": False
        }
        form_data[client_state_name] = json.dumps(client_state_json)

        # Click Search
        form_data[search_btn_name] = "Search"
        form_data['__EVENTTARGET'] = "" 
        form_data['__EVENTARGUMENT'] = ""

        print(f"  Applying filter for {year}...")
        response = self.session.post(self.base_url, data=form_data)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Pagination Loop
        current_page = 1
        while True:
            # Extract Objects instead of just links
            new_count = self.extract_meeting_data(soup)
            print(f"  Page {current_page}: Found {new_count} new meetings.")
            
            target, argument = self.get_next_page_payload(soup, current_page)
            
            if target:
                print(f"  Moving to page {current_page + 1}...")
                
                form_data = self.get_hidden_fields(soup)
                form_data[year_control_name] = str(year)
                form_data[client_state_name] = json.dumps(client_state_json)
                form_data['__EVENTTARGET'] = target
                form_data['__EVENTARGUMENT'] = argument
                
                if search_btn_name in form_data:
                    del form_data[search_btn_name]
                
                response = self.session.post(self.base_url, data=form_data)
                soup = BeautifulSoup(response.content, 'html.parser')
                current_page += 1
            else:
                print(f"  Finished year {year}.")
                break

    def run(self):
        # Scrape 2020 - 2025
        for year in range(2020, 2026):
            self.scrape_year(year)
            time.sleep(1)
            
        print(f"\nDONE! Found {len(self.results_dict)} unique meetings.")
        
        # Convert dict to list for final output
        final_list = list(self.results_dict.values())
        
        # Save to JSON file (easier to read objects)
        with open("./sf_transcript_data.json", "w", encoding='utf-8') as f:
            json.dump(final_list, f, indent=4)

if __name__ == "__main__":
    scraper = LegistarScraper()
    scraper.run()
