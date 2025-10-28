import requests
import random
import json
import re
from warcio.archiveiterator import ArchiveIterator
from constants import *

from Utils import Utils

def fetch_cc_index():
    # Fetch the list of Common Crawl indexes
    index_url = 'https://index.commoncrawl.org/collinfo.json'
    response = requests.get(index_url)
    return response.json()

def query_index(cc_index, page_size_threshold=40*1024):
    # Construct the query URL for the index
    query_url = f"https://index.commoncrawl.org/{cc_index}-index?url=*&output=json"
    response = requests.get(query_url, stream=True)
    
    if response.status_code == 200:
        for line in response.iter_lines():
            print("line", line)
            if line:
                record = json.loads(line)
                pageLength = int(record.get('length', 0))
                print("record", record, pageLength)
                if pageLength >= page_size_threshold:
                    yield record
    else:
        print("ERROR", query_url, response)
        

def get_random_pages(records, num_pages):
    # Randomly select a specified number of pages
    records_list = list(records)
    if len(records_list) < num_pages:
        print("Not enough pages meet the size criteria.")
        return None
    return random.sample(records_list, num_pages)

import io

def download_and_extract_warc(warc_url, offset, length):
    # 1) ask requests to stream it
    response = requests.get(
        warc_url,
        headers={'Range': f'bytes={offset}-{offset + length - 1}'},
        stream=True
    )
    if response.status_code != 206:
        print("Range request failed:", response.status_code)
        return None

    # 2) tell requests to decompress GZIP on the fly
    response.raw.decode_content = True

    # 3) read the bytes into a BytesIO so warcio sees a clean GZIP header
    chunk = response.raw.read()              # reads exactly your slice
    bio = io.BytesIO(chunk)

    # 4) let WARCI/O auto‐detect the compression
    for record in ArchiveIterator(bio):
        if record.rec_type == 'response':
            return record.content_stream().read()
        else:
            print("Skipping record type:", record.rec_type)

    print("No response record found")
    return None
   
import markdownify

def convertToMarkdown(htmlContent):
    try:
        if htmlContent is not None:
            return markdownify.markdownify(htmlContent)
    except Exception as e:
        print(f"Markdownify error: {e}")
    return None

def main(num_pages):
    host = "http://dan.soindrop.com"
    host = "http://admin.afterparty.ai"
    
    popUrl = f"{host}/rai/api/v1/get_cc_url"
    pushUrl = f"{host}/rai/api/v1/push_cc_convo"
    skipped = 0
    num = 10 # 10000
    for i in range(num):
        # Get URL for page from queue
        page = Utils.getUrl(popUrl)
        pageData = Utils.get(page, 'json.data.data')
        if pageData:
            selected_pages = [pageData]
            offsetField = 'warc_record_offset'
            lenField = 'warc_record_length'
            filenameField = 'warc_filename'
        
            # Download and extract pages
            for idx, page in enumerate(selected_pages):
                print(f"{GREEN}Processing page {i}{COLOR_END}", page)
                #continue
                filename = Utils.get(page, filenameField)
                pageOffset = int(Utils.get(page, offsetField))
                pageLen = int(Utils.get(page, lenField))
                warc_url = f"https://commoncrawl.s3.amazonaws.com/{filename}"
                pageUrl = Utils.get(page, "url")
                pageCrc = Utils.dictToCrc(pageUrl)
                # Works: wget https://data.commoncrawl.org/crawl-data/CC-MAIN-2018-17/segments/1524125937193.1/warc/CC-MAIN-20180420081400-20180420101400-00000.warc.gz
                # warc_url = "https://data.commoncrawl.org/crawl-data/CC-MAIN-2025-26/segments/1749709481468.19/warc/CC-MAIN-20250618011621-20250618041621-00387.warc.gz"
                warc_url = f"https://data.commoncrawl.org/{filename}"
                print("URL", warc_url, pageOffset, pageLen, pageCrc)
                #return
                page_content = download_and_extract_warc(warc_url, pageOffset, pageLen)
                htmlContent = page_content.decode('utf-8', errors='replace')
                #print(htmlContent[0:300])
                markdownContent = convertToMarkdown(htmlContent)
                if markdownContent == None:
                    print(f"{YELLOW}No markdown content for {pageUrl} found. Skipping.  {skipped}{COLOR_END}")
                    skipped += 1
                    continue
                markdownContent = Utils.collapseRepeatChars(markdownContent)
                markdownContentLen = len(markdownContent)
                print(f"MD: {markdownContentLen} : {markdownContent[0:300]}")
                if markdownContentLen > 5000:
                    # Push to queue for SN processing
                    page['crc'] = pageCrc
                    page['md'] = markdownContent
                    response = Utils.postUrl(pushUrl, jsonData=page)
                    print("RESP", Utils.get(response, 'body')[0:300])
                else:
                    print(f"{YELLOW}Markdown too short. Skipping. {skipped}{COLOR_END}")
                    skipped += 1
                
                #break
        else:
            print(f"Error. no page returned from endpoint: {page}")
            break

if __name__ == "__main__":
    # Specify the number of pages you want to randomly pick
    num_pages = 5  # Example: 5 pages
    main(num_pages)
