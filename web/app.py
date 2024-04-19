import json
import random


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
    path = '../facebook-chat-data.json'
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
