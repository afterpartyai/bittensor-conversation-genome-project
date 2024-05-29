import csv
import json
import time
import uuid
from faker import Faker
import sqlite3
import datetime

class Utils:
    @staticmethod
    def get(obj, path, default=None):
        out = default
        try:
            out = obj[path]
        except:
            pass
        return out

    @staticmethod
    def guid():
        current_time = int(round(time.time() * 1000))
        guid = uuid.uuid1(node=current_time)
        guid_int = int(guid.int)
        return guid_int

    @staticmethod
    def get_time(format_str="%H:%M:%S"):
        import time
        return time.strftime(format_str)


class ConversationDbProcessor:
    db_name = 'conversations.sqlite'
    table_name = 'conversationsF'
    # This 2000 row subset is from the 140K row Kaggle Facebook conversation data:
    #     https://www.kaggle.com/datasets/atharvjairath/personachat/data
    raw_data_path = 'facebook-chat-data_2000rows.csv'
    source_id = 1
    max_rows = 1200

    def __init__(self):
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        sql_create = "CREATE TABLE IF NOT EXISTS conversationsF (id INTEGER PRIMARY KEY AUTOINCREMENT, source_id INTEGER, guid TEXT, idx INTEGER, topic TEXT, json JSON, created_at TEXT, updated_at TEXT )"
        self.cursor.execute(sql_create)

    def process_conversation_csv(self):
        max_rows = self.max_rows
        row_count = 1

        print(Utils.get_time() + " Starting data insert of max_rows=%d..." % (max_rows))
        with open(self.raw_data_path, 'r') as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')

            # skip the header row
            next(csv_reader)
            for row in csv_reader:
                # extract the id, persona, and chat from the row
                guid = Utils.guid()

                id = row[0]
                persona = row[1].strip()
                chat = row[2]

                # split the chat into individual lines
                chat_lines = chat.split('\n')
                lines = []
                fake = Faker()
                participantGuids = {
                    "0": {"idx": 0, "guid":Utils.guid(), "title":fake.name()},
                    "1": {"idx": 1, "guid":Utils.guid(), "title":fake.name()},
                }
                numParticipant = len(participantGuids)
                cycle = 0
                for line in chat_lines:
                    lines.append([ cycle, line.strip() ])
                    cycle = (cycle + 1) % numParticipant

                # Create an row of the data. If you have a DAL, you could simply insert
                row_dict = {"id": id, "guid": guid, "topic": persona, "lines": lines, "participant": participantGuids, }
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
