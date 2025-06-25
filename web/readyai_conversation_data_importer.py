import datetime
import json
import os
import sqlite3
import time
import uuid

from datasets import load_dataset
from faker import Faker
from Utils import Utils


class ConversationDbProcessor:
    db_name = os.path.join(os.path.dirname(__file__), 'conversations.sqlite')
    table_name = 'conversations'
    huggingface_dataset = 'ReadyAi/5000-podcast-conversations-with-metadata-and-embedding-dataset'
    source_id = 1

    def __init__(self):
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        sql_create = f"""CREATE TABLE IF NOT EXISTS {self.table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER,
            guid TEXT,
            idx INTEGER,
            topic TEXT,
            json JSON,
            created_at TEXT,
            updated_at TEXT
        )"""
        self.cursor.execute(sql_create)

    def process_conversation_dataset(self):
        print(Utils.get_time() + f" Loading Hugging Face dataset: {self.huggingface_dataset}")
        dataset = load_dataset(self.huggingface_dataset, data_files={"train": "conversations_train.parquet"}, cache_dir="./my_cache", split="train")
        dataset = load_dataset(self.huggingface_dataset, data_files={"train": "conversations_to_tags.parquet"}, split="train")
        dataset = load_dataset(self.huggingface_dataset, data_files={"train": "tag_to_id.parquet"}, split="train")
        print(Utils.get_time() + f" Dataset loaded. Total rows: {len(dataset)}")
        return
        row_count = 0
        fake = Faker()

        for row in dataset:
            c_guid = row["c_guid"]
            transcript = row["transcript"]
            participants = row["participants"]

            participantGuids = {p.strip('"'): {"idx": idx, "guid": Utils.guid(), "title": fake.name()} for idx, p in enumerate(participants)}

            lines = []
            for t in transcript:
                speaker = t["speaker"]
                speaker_idx = participantGuids.get(speaker, {"idx": 0})["idx"]
                text = t["text"]
                lines.append([speaker_idx, text])

            row_dict = {
                "id": c_guid,
                "guid": c_guid,
                "lines": lines,
                "participant": participantGuids,
            }

            created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            json_data = json.dumps(row_dict)

            sql_insert = f"""
                INSERT INTO {self.table_name}
                (source_id, json, idx, guid, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            insert_data = (
                self.source_id,
                json_data,
                row_dict["id"],
                str(row_dict["guid"]),
                created_at,
                created_at,
            )
            self.cursor.execute(sql_insert, insert_data)

            row_count += 1
            if row_count % 100 == 0:
                print(Utils.get_time() + f" Committing {row_count} rows...")
                self.conn.commit()

        self.conn.commit()
        self.conn.close()
        print(Utils.get_time() + f" Done. Inserted {row_count} rows.")

import random
import time

def randomized_sleep(min_minutes=3, max_minutes=30):
    """
    Randomly sleep between min_minutes and max_minutes.

    Args:
    min_minutes (int): Minimum sleep time in minutes (default: 3)
    max_minutes (int): Maximum sleep time in minutes (default: 30)
    """
    sleep_time = random.randint(min_minutes * 60, max_minutes * 60)  # convert minutes to seconds
    print(f"Sleeping for {sleep_time / 60:.2f} minutes...", flush=True)
    time.sleep(sleep_time)


cdp = ConversationDbProcessor()
randomized_sleep()
cdp.process_conversation_dataset()
