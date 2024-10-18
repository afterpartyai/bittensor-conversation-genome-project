import csv
import json
import time
import uuid
from faker import Faker
import sqlite3
import datetime

from Utils import Utils

class ConversationDbProcessor:
    db_name = 'conversations.sqlite'
    table_name = 'conversations'
    # This 2000 row subset is from the 140K row Kaggle Facebook conversation data:
    #     https://www.kaggle.com/datasets/atharvjairath/personachat/data
    raw_data_path = "task_data.json"
    source_id = 1
    max_rows = 1200

    def __init__(self):
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        sql_drop = f"DROP TABLE IF EXISTS {self.table_name}"
        self.cursor.execute(sql_drop)
        sql_create = f"CREATE TABLE {self.table_name} (id INTEGER PRIMARY KEY AUTOINCREMENT, source_id INTEGER, guid TEXT, idx INTEGER, topic TEXT, json JSON, prompts TEXT, created_at TEXT, updated_at TEXT )"
        self.cursor.execute(sql_create)

    def process_conversation_csv(self):
        max_rows = self.max_rows
        row_count = 1

        print(Utils.get_time() + " Starting data insert of max_rows=%d..." % (max_rows))
        with open(self.raw_data_path, 'r') as json_file:
            data = json.load(json_file)

            for row in data:
                # Create a global-unique-identifier for each conversation
                guid = row["guid"]

                id = guid
                chat = row["lines"]
                prompts = row["prompts"]
                prompts_json = json.dumps(prompts)
                print(prompts_json)

                # split the chat into individual lines
                chat_lines = [line[1] for line in chat]
                lines = []
                fake = Faker()
                # Data doesn't have participant names, so generate fake ones
                participants = row["participants"]
                participantGuids = {}
                for idx, participant in enumerate(participants):
                    participantGuids[str(idx)] = {
                        "idx": idx,
                        "guid": Utils.guid(),
                        "title": fake.name()
                    }
                numParticipant = len(participantGuids)
                cycle = 0
                for line in chat_lines:
                    lines.append([ cycle, line.strip() ])
                    cycle = (cycle + 1) % numParticipant

                # Create an row of the data. If you have a DAL, you could simply insert
                row_dict = {"id": id, "guid": guid, "lines": lines, "prompts":prompts_json, "participant": participantGuids, }
                now = datetime.datetime.now()
                created_at = now.strftime("%Y-%m-%d %H:%M:%S")
                jsonData = json.dumps(row_dict)
                print(row_dict['prompts'])

                # Generate SQLite insert statement
                sql_insert = f"INSERT INTO {self.table_name} (source_id, json, idx, prompts, guid, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
                insert_data = (self.source_id, jsonData, row_dict['id'], row_dict['prompts'], str(row_dict['guid']), created_at, created_at)
                self.cursor.execute(sql_insert, insert_data)

                row_count += 1
                # Commit every 100 rows and report progress
                if row_count % 100 == 0:
                    print(Utils.get_time() + " Committing 100 rows. Total count: "+str(row_count))
                    self.conn.commit()
                    try:
                        self.conn.commit()
                    except:
                        pass

                # Convenience max_rows so small amount of data can be tested
                if max_rows and row_count > max_rows:
                    print(Utils.get_time() + " Reached max rows. Total count: "+str(row_count-1))
                    break

        self.conn.commit()
        self.conn.close()
        print(Utils.get_time() + " Insert complete. Total count: "+str(row_count-1))

cdp = ConversationDbProcessor()
cdp.process_conversation_csv()
