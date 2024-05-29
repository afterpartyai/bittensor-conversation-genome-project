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
    def compare_arrays(arr1, arr2):
        result_dict = {}

        set1 = set(arr1)
        set2 = set(arr2)

        result_dict["both"] = list(set1.intersection(set2))
        result_dict["unique_1"] = list(set1.difference(set2))
        result_dict["unique_2"] = list(set2.difference(set1))

        return result_dict

    @staticmethod
    def pluck(dicts, key):
        values = []
        for dictionary in dicts:
            if key in dictionary:
                values.append(dictionary[key])
        return values

    @staticmethod
    def guid():
        current_time = int(round(time.time() * 1000))
        guid = uuid.uuid1(node=current_time)
        guid_int = int(guid.int)
        return guid_int

    @staticmethod
    def split_overlap_array(array, size=10, overlap=2):
        result = []
        lenArray = len(array)
        num_splits = lenArray//(size-overlap) + 1

        for i in range(num_splits):
            start = i*(size-overlap)
            end = start + size
            window = array[start:end]
            #print("Start/end/elements", start, end, window)
            result.append(array[start:end])
            if end >= lenArray:
                break
        return result

    @staticmethod
    def get_time(format_str="%H:%M:%S"):
        import time
        return time.strftime(format_str)



# create an empty dictionary to store the output
output_dict = {}
outputCount = 0
useDb = True

class ConversationDbProcessor:
    db_name = 'conversations.sqlite'
    # This 2000 row subset is from the 140K row Kaggle Facebook conversation data:
    #     https://www.kaggle.com/datasets/atharvjairath/personachat/data
    raw_data_path = 'facebook-chat-data_2000rows.csv'
    source_id = 1
    max_rows = 1000

    def __init__(self):
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        sql_create = "CREATE TABLE IF NOT EXISTS conversationsF (id INTEGER PRIMARY KEY AUTOINCREMENT, source_id INTEGER, guid TEXT, idx INTEGER, topic TEXT, json JSON, created_at TEXT, updated_at TEXT )"
        self.cursor.execute(sql_create)

    def process_conversation_csv(self):
        max_rows = self.max_rows
        row_count = 1
        # open the CSV file and iterate through each row
        with open(self.raw_data_path, 'r') as csv_file:
            total_rows = sum(1 for line in csv_file)

        print(Utils.get_time() + " Starting data insert of max_rows %d rows from %d dataset total..." % (max_rows, total_rows))
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
                row_dict = {"id": id, "guid": guid, "topic": persona, "lines": lines, "participant": participantGuids, }
                now = datetime.datetime.now()
                created_at = now.strftime("%Y-%m-%d %H:%M:%S")
                jsonData = json.dumps(row_dict)
                sql_insert = "INSERT INTO conversationsF (source_id, json, idx, topic, guid, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
                insert_data = (self.source_id, jsonData, row_dict['id'], row_dict['topic'], str(row_dict['guid']), created_at, created_at)
                self.cursor.execute(sql_insert, insert_data)

                #print(row_dict)

                row_count += 1
                if row_count % 100 == 0:
                    print(Utils.get_time() + " Committing 100 rows. Total count: "+str(row_count))
                    try:
                        self.conn.commit()
                    except:
                        pass

                if row_count > max_rows:
                    print(Utils.get_time() + " Reached max rows. Total count: "+str(row_count))
                    break
                    #break

        self.conn.commit()
        self.conn.close()
        print(Utils.get_time() + " Insert complete.")

cdp = ConversationDbProcessor()
cdp.process_conversation_csv()
