import json
import random
import os
import time

import hashlib
import sqlite3

from Utils import Utils

ss58_decode = None
try:
    from scalecodec.utils.ss58 import ss58_decode
except:
    print("scalecodec is not installed. Try: pip install scalecodec")


CYAN = "\033[96m" # field color
GREEN = "\033[92m" # indicating success
RED = "\033[91m" # indicating error
YELLOW = '\033[0;33m'
COLOR_END = '\033[m'
DIVIDER = '_' * 120

# Test convo read endpoint:
# curl -XPOST https://api.conversations.xyz/api/v1/conversation/reserve | python -m json.tool
# curl -XPOST http://localhost:8000/api/v1/conversation/reserve | python -m json.tool

# Test convo write endpoint:
# curl -XPOST http://localhost:8000/api/v1/conversation/reserve | python -m json.tool


from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles


app = FastAPI()

class Db:
    source_type = 2 # Non-CGP
    db_name = None
    table_name = None
    sql_create_results = """CREATE TABLE IF NOT EXISTS cgp_results (
	"id"	INTEGER UNIQUE,
	"status"	INTEGER DEFAULT 1,
	"batch_num"	INTEGER,
	"c_guid"	TEXT,
	"convo_window_index"	INTEGER DEFAULT 1,
	"source_type"	INTEGER DEFAULT 2,
	"mode"	TEXT,
	"hotkey"	TEXT,
	"coldkey"	TEXT,
	"uid"	INTEGER,
	"llm_type"	TEXT,
	"model"	TEXT,
	"tags"	JSON,
	"marker_id"	INTEGER,
	"json"	JSON,
	"created_at"	TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	"cgp_version"	TEXT
	"updated_at"	TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	"updated_by"	INTEGER,
	"created_by"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT)
)"""

    def __init__(self, db_name, table_name):
        self.db_name = db_name
        self.table_name = table_name

    def get_cursor(self):
        db_name = "conversations.sqlite"
        conn = sqlite3.connect(db_name)
        conn.row_factory = Db.dict_factory
        cursor = conn.cursor()

        return cursor


    def insert_into_table(self, c_guid, content):
        today = Utils.get_time("%Y.%m.%d")
        db_name = f"{self.db_name}_{today}.sqlite"
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute(self.sql_create_results)
        updateRow = {
            "c_guid": c_guid,
            "mode": Utils.get(content, "mode"),
            "model": Utils.get(content, "model"),
            "llm_type": Utils.get(content, "llm_type"),
            "convo_window_index": Utils.get(content, "convo_window_index"),
            "marker_id": Utils.get(content, "marker_id"),
            "source_type": self.source_type,
            "hotkey": Utils.get(content, "hotkey"),
            "coldkey": Utils.get(content, "coldkey"),
            "batch_num": Utils.get(content, "batch_num"),
            "tags": Utils.get(content, "tags"),
            "cgp_version": Utils.get(content, "cgp_version"),
            "json": json.dumps(content)
        }
        fields = []
        questions = []
        values = []
        for field, val in updateRow.items():
            fields.append(field)
            questions.append("?")
            values.append(val)
        fields_str = ",".join(fields)
        questions_str = ",".join(questions)
        cursor.execute(f"INSERT INTO cgp_results ({fields_str}) VALUES ({questions_str})", (values))
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

# Get account functionality for decrypting public key
def get_account_from_coldkey(ss58_coldkey):
    # Relevant sites: https://github.com/polkascan/py-substrate-interface/blob/c15d699c87810c041d851fbd556faa2f3626c496/substrateinterface/base.py#L2745
    # https://ss58.org/
    if not ss58_decode:
        print("scalecodec is not installed. Aborting.")
        return
    return ss58_decode(ss58_coldkey, valid_ss58_format=42)

def get_account():
    validator_info['account_id'] = raal.get_account_from_coldkey(validator_info['coldkey'])
    print(f"The decoded account ID for the address {ss58_hotkey} is: {validator_info['account_id']}")


app.mount("/static", StaticFiles(directory="static"), name="static")


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
    if data:
        db = Db("cgp_tags", "tags")
        db.insert_into_table(c_guid, data)
        out['data']['msg'] = {"message": f"Stored tag data for {c_guid}"}
        out['success'] = 1
    else:
        out['errors'].append([9893843, "Missing hotkey",])
    return out

import hashlib
import binascii

def hashReadyAiMessage(password):
    salt = "THIS IS MY SALT"
    password = password.encode('utf-8')
    salt = salt.encode('utf-8')
    pwdhash = hashlib.pbkdf2_hmac('sha512', password, salt, 100000)
    pwdhashAscii = binascii.hexlify(pwdhash)
    return (pwdhashAscii).decode('ascii')

@app.post("/api/v1/generate_message")
def post_get_api_key_message(data: dict):
    out = {"success": 0, "errors":[], "data":{}}
    if False:
        out['errors'].append([9893844, "Missing hotkey",])
    else:
        out['success'] = 1
        basicMessage = u"This is it and more:"
        out['data']['message'] = basicMessage #"Message seed: akldjslakjdlkajsldkjalskdjalskdj llka jsljdj lah uioeryo uq023 4h lsdfclasd f90 408roi hlkad lakk sdo"
    return out

Keypair = None
try:
    from substrateinterface import Keypair
except:
    print(f"substrateinterface is not installed. Try: pip install substrateinterface")

@app.post("/api/v1/generate_api_key")
def post_get_api_generate_key(data: dict):
    out = {"success": 0, "errors":[], "data":{}}
    if False:
        out['errors'].append([9893845, "Missing stuff",])
    else:
        # Junk local address
        ss58_address = "5EhPJEicfJRF6EZyq82YtwkFyg4SCTqeFAo7s5Nbw2zUFDFi"
        message = "HELLOWORLD"
        # Signed example
        signature = "eca79a777366194d9eef83379b413b1c6349473ed0ca19bc7f33e2c0461e0c75ccbd25ffdd6e25b93ee2c7ac6bf80815420ddb8c61e8c5fc02dfa27ba105b387"
        if Keypair:
            keypair = Keypair(ss58_address=ss58_address)
            is_valid = keypair.verify(message.encode("utf-8"), bytes.fromhex(signature))
            if is_valid:
                out['success'] = 1
                out['data'] = {"api_key":239423}
            else:
                out['errors'].append([9893845, "Signature didn't verify",])
        else:
            out['errors'].append([9893846, "Keypair not installed",])
    return out

@app.get("/api/v1/queue")
def get_api_get_queue_item():
    out = {"success": 0, "errors":[], "data":{}}
    taskType = "ad"
    out['data'] = [
        {"id": 1, "title": "Hello"},
        {"id": 2, "title": "World"},
        {"id": 3, "title": "From"},
        {"id": 4, "title": "Below"},
    ];


    out['success'] = 1
    return out


