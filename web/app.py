import json
import random
import os
import time

import hashlib
import sqlite3

from Utils import Utils

# Test convo read endpoint:
# curl -XPOST https://api.conversations.xyz/api/v1/conversation/reserve | python -m json.tool
# curl -XPOST http://localhost:8000/api/v1/conversation/reserve | python -m json.tool

# Test convo write endpoint:
# curl -XPOST http://localhost:8000/api/v1/conversation/reserve | python -m json.tool


from fastapi import FastAPI, Request

app = FastAPI()

class Db:
    db_name = None
    table_name = None

    def __init__(self, db_name, table_name):
        self.db_name = db_name
        self.table_name = table_name

    def get_cursor(self):
        db_name = "conversations.sqlite"
        conn = sqlite3.connect(db_name)
        conn.row_factory = Db.dict_factory
        cursor = conn.cursor()

        return cursor


    def insert_into_table(self, hotkey, key, dictionary):
        db_name = "cgp_tags.sqlite"
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS tags (key TEXT, value TEXT)')
        cursor.execute('INSERT INTO tags (hotkey, c_guid, json) VALUES (?, ?, ?)', (hotkey, key, str(dictionary)))
        conn.commit()
        conn.close()

    def get_random_conversation(self):
        cursor = self.get_cursor()
        sql = 'SELECT * FROM conversations ORDER BY RANDOM() LIMIT 1'
        cursor.execute(sql)
        rows = cursor.fetchall()
        if rows and len(rows) == 1:
            return rows[0]
        else:
            return None

    @staticmethod
    def dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            if col[0] == "json":
                try:
                    d["data"] = json.loads(row[idx])
                except:
                   d["data"] = json.loads("{}")
            else:
                d[col[0]] = row[idx]
        return d


@app.get("/")
def get_request():
    return {"message": "Forbidden"}

@app.post("/api/v1/conversation/reserve")
def post_request():
    # Used for testing long or bad responses
    if False:
        time.sleep(30)
    path = '../data/facebook-chat-data.json'

    db = Db("conversations", "conversations")
    conversation = db.get_random_conversation()

    convo = {
        "guid": Utils.get(conversation, "data.guid"),
        "lines": Utils.get(conversation, "data.lines"),
    }

    convo['total'] = len(convo['lines'])


    # Anonymize the participants
    participants = Utils.get(conversation, "data.participant")
    out_participants = []
    p_count = 0
    for key, participant in participants.items():
        out_participants.append(f"SPEAKER_{participant['idx']}")
        p_count += 1
    convo['participants'] = out_participants

    return convo

# Mock endpoint for testing OpenAI call failures
@app.post("/v1/chat/completions")
def post_openai_mock_request():
    # Used for testing long or bad responses
    if False:
        time.sleep(10)
    return {"errors":{"id":923123, "msg":"Mock error"}}



@app.put("/api/v1/conversation/record/{c_guid}")
def put_record_request(c_guid, data: dict):
    out = {"success": 0, "errors":[], "data":{}}
    if "hotkey" in data:
        print("data", c_guid, data)
        hotkey = data['hotkey']
        #fname = write_directory(data['hotkey'], c_guid, data)
        db = Db()
        db.insert_into_table(hotkey, c_guid, data)
        out['data']['msg'] = {"message": f"Stored tag data for {c_guid}"}
        out['success'] = 1
    else:
        out['errors'].append([9893843, "Missing hotkey",])
    return out

