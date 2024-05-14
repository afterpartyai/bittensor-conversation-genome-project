import json
import random
import os
import time


import hashlib
import sqlite3

from fastapi import FastAPI, Request

app = FastAPI()

# GET request
@app.get("/")
def get_request():
    return {"message": "This is a GET request2"}

# PUT request
@app.put("/put_request")
def put_request():
    return {"message": "This is a PUT request"}

# POST request
@app.post("/post_request")
def post_request():
    return {"message": "This is a POST request"}

# Example of a JSON response
@app.get("/json_response")
def json_response():
    data = {"name": "John", "age": 30, "city": "New York"}
    return json.dumps(data)

@app.post("/api/v1/conversation/reserve")
def post_request():
    # Used for testing long or bad responses
    if False:
        time.sleep(10)
    path = '../data/facebook-chat-data.json'

    f = open(path)
    body = f.read()
    f.close()
    convos = json.loads(body)
    convoKeys = list(convos.keys())
    convoTotal = len(convoKeys)
    #print("convoTotal", convoTotal)
    selectedConvoKey = random.choice(convoKeys)
    selectedConvo = convos[selectedConvoKey]
    selectedConvoKey2 = random.choice(convoKeys)
    selectedConvo2 = convos[selectedConvoKey]
    selectedConvoKey3 = random.choice(convoKeys)
    selectedConvo3 = convos[selectedConvoKey]
    #print("selectedConvo", selectedConvo)

    # Concatenate several for length
    lines = selectedConvo["lines"] + selectedConvo2["lines"] + selectedConvo3["lines"]


    convo = {
        "total":len(convoKeys),
        "guid":selectedConvo["guid"],
        #"participants": selectedConvo["participants"],
        "lines": lines,
    }
    return convo

def write_directory(key, dictionary, base_path='.'):
    # generate md5 from key
    md5 = hashlib.md5(key.encode()).hexdigest()

    # create directory with first letter of md5
    first_dir = os.path.join(base_path, md5[0])
    os.makedirs(first_dir, exist_ok=True)

    # create directory within first directory with last letter of md5
    last_dir = md5[-1]
    final_path = os.path.join(first_dir, last_dir)
    os.makedirs(final_path, exist_ok=True)
    print(f"DIR PATH: {final_path}")

    # create filename with md5 and key
    filename = f"{md5}-{key}.json"

    # create file with filename and write dictionary as JSON string
    full_path = os.path.join(first_dir, last_dir, filename)
    print(f"Full path: {full_path}")
    with open(full_path, "w") as file:
        json.dump(dictionary, file)

    return filename

def insert_into_table(hotkey, key, dictionary):
    db_name = "cgp_tags.sqlite"
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    #cursor.execute('CREATE TABLE IF NOT EXISTS tags (key TEXT, value TEXT)')
    cursor.execute('INSERT INTO tags (hotkey, c_guid, json) VALUES (?, ?, ?)', (hotkey, key, str(dictionary)))
    conn.commit()
    conn.close()

@app.put("/api/v1/conversation/record/{c_guid}")
def put_record_request(c_guid, data: dict):
    out = {"success": 0, "errors":[], "data":{}}
    if "hotkey" in data:
        print("data", c_guid, data)
        hotkey = data['hotkey']
        #fname = write_directory(data['hotkey'], c_guid, data)
        insert_into_table(hotkey, c_guid, data)
        out['data']['msg'] = {"message": f"Stored tag data for {c_guid}"}
        out['success'] = 1
    else:
        out['errors'].append([9893843, "Missing hotkey",])
    return out

