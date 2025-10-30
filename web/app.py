
import os
import random
import time
from typing import Optional

from prometheus_client import CONTENT_TYPE_LATEST
from prometheus_client import generate_latest
from pydantic import BaseModel

from Db import Db
from middlewares.authentication_middleware import AuthMiddleware
from middlewares.metrics_middleware import MetricsMiddleware
from tasks import get_conversation_task, get_survey_task, get_website_task

from fastapi import FastAPI
from fastapi import Request
from fastapi import Response

# Test convo read endpoint:
# curl -XPOST https://api.conversations.xyz/api/v1/conversation/reserve | python -m json.tool
# curl -XPOST http://localhost:8000/api/v1/conversation/reserve | python -m json.tool

# Test convo write endpoint:
# curl -XPOST http://localhost:8000/api/v1/conversation/reserve | python -m json.tool

class ReserveRequest(BaseModel):
    task_type: Optional[str] = None
    task_guid: Optional[str] = None

app = FastAPI()
app.add_middleware(MetricsMiddleware)
app.add_middleware(AuthMiddleware)

@app.get("/")
def get_request():
    return {"message": "Forbidden"}


@app.post("/api/v1/conversation/reserve")
def post_request(request: ReserveRequest = None):
    # Used for testing long or bad responses
    if False:
        time.sleep(30)
    try:
        task_mapping = {
            "conversation": get_conversation_task,
            "website": get_website_task,
            "survey": get_survey_task,
        }

        if request and request.task_type:
            if request.task_type in task_mapping:
                task_func = task_mapping[request.task_type]
            else:
                raise ValueError(f'Unsupported task type: {request.task_type}')
        else:
            task_func = random.choice(list(task_mapping.values()))

        task_guid = request.task_guid if request else None
        task = task_func(task_guid)
        # choice = random.choice([webpage_tagging_task])
        print(f"Selected task: {task['type']} with GUID {task['guid']}")
        return task

    except Exception as e:
        print(f"Error: {e}")
        return {
            "mode": "error",
            "api_version": 1.4,
            "type": "unknown",
            "scoring_mechanism": None,
            "input": None,
            "prompt_chain": [],
            "example_output": None,
            "errors": [f"post_request failed: {str(e)}"],
            "warnings": [],
            "guid": "ERROR",
            "total": 0,
            "participants": [],
            "lines": [],
            "min_convo_windows": 0,
        }


@app.put("/api/v1/conversation/record/{c_guid}")
def put_record_request(c_guid, data: dict):
    out = {"success": 0, "errors": [], "data": {}}
    if data:
        db_name = os.path.join(os.path.dirname(__file__), 'cgp_tags')
        db = Db(db_name, "tags")
        db.insert_into_table(c_guid, data)
        out['data']['msg'] = {"message": f"Stored tag data for {c_guid}"}
        out['success'] = 1
    else:
        out['errors'].append(
            [
                9893843,
                "Missing hotkey",
            ]
        )
    return out


@app.get("/metrics")
def metrics(request: Request):
    if request.client.host != "127.0.0.1":
        return Response(status_code=403)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
