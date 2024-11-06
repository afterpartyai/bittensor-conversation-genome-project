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


from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles

from Db import Db

app = FastAPI()


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


@app.get("/favicon.ico")
async def favicon():
    favicon_data = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
            <rect x="10" y="10" width="80" height="80" rx="15" fill="#5bc0de"></rect>
        </svg>""".encode("utf-8")
    return Response(content=favicon_data, media_type="image/svg+xml")



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

def get_default_json():
    return {"success": 0, "errors":[], "warnings":[], "data":{}}

@app.get("/api/v1/job")
def get_api_get_jobs():
    out = get_default_json()
    taskType = "ad"
    db = Db("cgp_tags.sqlite", "jobs")
    sql = 'SELECT * FROM jobs ORDER BY updated_at DESC LIMIT 25'
    out['data'] = db.get_all(sql)

    out['success'] = 1
    return out

@app.get("/api/v1/job/{id}")
def get_api_get_job(id: int):
    out = get_default_json()
    taskType = "ad"
    db = Db("cgp_tags.sqlite", "jobs")
    sql = f'SELECT * FROM jobs WHERE id = {id} LIMIT 1'
    out['data'] = db.get_row(sql)

    out['success'] = 1
    return out

@app.get("/api/v1/task")
def get_api_get_tasks():
    out = get_default_json()
    taskType = "ad"
    db = Db("cgp_tags.sqlite")
    sql = 'SELECT * FROM tasks ORDER BY updated_at DESC LIMIT 25'
    out['data'] = db.get_all(sql)

    out['success'] = 1
    return out

@app.get("/api/v1/task/{id}")
def get_api_get_task(id: int):
    out = get_default_json()
    taskType = "ad"
    db = Db("cgp_tags.sqlite", "jobs")
    sql = f'SELECT * FROM tasks WHERE id = {id} LIMIT 1'
    out['data'] = db.get_row(sql)

    out['success'] = 1
    return out



@app.post("/api/v1/job")
@app.put("/api/v1/job/{id}")
def post_put_api_create_job(data: dict, id=None):
    out = get_default_json()
    if id:
        data['id'] = id
    db = Db("cgp_tags.sqlite", "jobs")
    db.save("jobs", data)

    out['data'] = data
    return out

def random_sqlite_integer():
    return random.randint(1, 9223372036854775807)


@app.get("/api/v1/reserve_task")
def get_api_get_reserve_task():
    out = get_default_json()
    taskType = "ad"
    db = Db("cgp_tags.sqlite", "tasks")
    sql = 'SELECT * FROM tasks WHERE status = 1 ORDER BY updated_at DESC LIMIT 1'
    sql = "SELECT * from tasks WHERE status = 1 LIMIT 1"
    lock_value = random_sqlite_integer()

    data = {"id":5, "lock_value":21}
    db.save("tasks", data)
    update_query = f"UPDATE tasks SET lock_value = {lock_value}, status = 3,  locked_at = STRFTIME('%s', 'NOW') WHERE status = 2 AND id = (SELECT id FROM tasks WHERE status = 2 ORDER BY updated_at ASC, id ASC LIMIT 1); "
    print(update_query)
    cursor = db.execute(update_query)
    if cursor.rowcount < 1:
        print("No rows were updated.", cursor.rowcount)
    else:
        print(f"{cursor.rowcount} row(s) were updated.")
        sql = f"SELECT * from tasks WHERE lock_value = {lock_value} LIMIT 1"
        row = db.get_row(sql)
        out['data'] = row
        out['success'] = 1
    return out


