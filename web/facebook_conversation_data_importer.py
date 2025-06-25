import csv
import datetime
import json
import os
import sqlite3
import time
import uuid
import sys
from constants import *


Faker = None
try:
    from faker import Faker
except:
    print("Faker not installed")
    

BeautifulSoup = None
try:
    from bs4 import BeautifulSoup
except:
    print("BeautifulSoup not installed -- python3 -m pip install beautifulsoup4")

from Utils import Utils

markdownify = None
try:
    import markdownify
except:
    print("markdownify not installed -- python3 -m pip install markdownify")

from Utils import Utils


class ConversationDbProcessor:
    db_name = os.path.join(os.path.dirname(__file__), 'conversations.sqlite')
    table_name = 'conversations'
    # This 2000 row subset is from the 140K row Kaggle Facebook conversation data:
    #     https://www.kaggle.com/datasets/atharvjairath/personachat/data
    raw_data_path = 'facebook-chat-data_2000rows.csv'
    source_id = 1
    max_rows = 1200

    def __init__(self):
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        sql_create = f"CREATE TABLE IF NOT EXISTS {self.table_name} (id INTEGER PRIMARY KEY AUTOINCREMENT, source_id INTEGER, guid TEXT, idx INTEGER, topic TEXT, json JSON, created_at TEXT, updated_at TEXT )"
        self.cursor.execute(sql_create)

    def process_conversation_csv(self):
        max_rows = self.max_rows
        row_count = 1

        print(Utils.get_time() + " Starting Facebook data insert of max_rows=%d..." % (max_rows))
        with open(self.raw_data_path, 'r') as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')

            # skip the header row
            next(csv_reader)
            for row in csv_reader:
                # Create a global-unique-identifier for each conversation
                guid = Utils.guid()

                id = row[0]
                topic = row[1].strip()
                chat = row[2]

                # split the chat into individual lines
                chat_lines = chat.split('\n')
                lines = []
                fake = Faker()
                # Data doesn't have participant names, so generate fake ones
                participantGuids = {
                    "0": {"idx": 0, "guid": Utils.guid(), "title": fake.name()},
                    "1": {"idx": 1, "guid": Utils.guid(), "title": fake.name()},
                }
                numParticipant = len(participantGuids)
                cycle = 0
                for line in chat_lines:
                    lines.append([cycle, line.strip()])
                    cycle = (cycle + 1) % numParticipant

                # Create an row of the data. If you have a DAL, you could simply insert
                row_dict = {
                    "id": id,
                    "guid": guid,
                    "topic": topic,
                    "lines": lines,
                    "participant": participantGuids,
                }
                now = datetime.datetime.now()
                created_at = now.strftime("%Y-%m-%d %H:%M:%S")
                jsonData = json.dumps(row_dict)

                # Generate SQLite insert statement
                sql_insert = f"INSERT INTO {self.table_name} (source_id, json, idx, topic, guid, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
                insert_data = (self.source_id, jsonData, row_dict['id'], row_dict['topic'], str(row_dict['guid']), created_at, created_at)
                self.cursor.execute(sql_insert, insert_data)

                row_count += 1
                # Commit every 100 rows and report progress
                if row_count % 100 == 0:
                    print(Utils.get_time() + " Committing 100 rows. Total count: " + str(row_count))
                    self.conn.commit()
                    try:
                        self.conn.commit()
                    except:
                        pass

                # Convenience max_rows so small amount of data can be tested
                if max_rows and row_count > max_rows:
                    print(Utils.get_time() + " Reached max rows. Total count: " + str(row_count - 1))
                    break

        self.conn.commit()
        self.conn.close()
        print(Utils.get_time() + " Insert complete. Total count: " + str(row_count - 1))

    def process_cc_cache(self, path):
        print(f"{GREEN}Indexing common crawl pages in {path}...{COLOR_END}")
        fileList = Utils.getFilesByExtension(path, ["html"])
        for filename in fileList:
            filePath = os.path.join(path, filename)
            f =open(filePath)
            body = f.read()
            f.close()
            markdown = markdownify.markdownify(body, wrap=True, wrap_width=120)
            lines = markdown.split("\n")
            out = []
            carryOver = ""
            #lines = lines[0:15]
            for idx, line in enumerate(lines):
                if Utils.isAlphaNumeric(line):
                    #print(idx, line)
                    line = line.strip()
                    firstChar = line[0:1]
                    # Most bulletted lists with links are menus, hyperlink lists, etc. so skip
                    if (firstChar == "*" or firstChar == "-" or firstChar == "+") and line.find("[") != -1:
                        continue
                    # If the line didn't wrap in markdownify, it's probably junk -- truncate
                    if len(line) > 120:
                        line = line[0:120]
                    elif len(line) < 15 and len(carryOver) < 120:
                        #print("  CO", line)
                        carryOver += line + ", "
                        continue
                    if len(carryOver) > 0:
                        #print("L+CO", carryOver, line)
                        line = carryOver + line 
                        carryOver = ""
                    out.append(line.strip())
            # Append any leftover carryOver
            if len(carryOver) > 0:
                out.append(carryOver.strip())
            print(f"{filename} -- {len(out)} lines")
            Utils.writeFile(filePath+".md", "\n".join(out))
        print("fileList", fileList)
        

args = [None] * 20
for idx, i in enumerate(sys.argv):
    args[idx] = i

if __name__ == "__main__":
    cdp = ConversationDbProcessor()
    action = args[1]
    if action == "commoncrawl":
        path = "./page_cache/"
        cdp.process_cc_cache(path)
    else:
        cdp.process_conversation_csv()
