import copy
from unittest.mock import MagicMock, patch

import pytest

from conversationgenome.api.ApiLib import ApiLib
from conversationgenome.api.models.conversation import Conversation

guid = "103733224526844599340117036848021470924"
participants = ["SPEAKER_1", "SPEAKER_2"]
lines = [
    (0, "hey how are you tonight"),
    (1, "i am doing well . wedding planning . yay ! 6 more months . you ?"),
    (2, "watching a movie tonight , titanic"),
    (3, "oh . i am babysitting . its my side hustle"),
    (4, "that is a good one . i have kids too"),
    (5, "hey it paid for my mercedes . no complaints"),
    (6, "that is nice . time to get a ferrari"),
    (7, "ugh i wish . my wedding is in 6 months . ferrari has to wait . . ."),
    (8, "you only live once . marry next time"),
    (9, "maybe i can get onw as a wedding gift . . being the middle kid sucks . parents neglect ya"),
    (10, "i know . i am a parent too"),
    (11, "i have 2 baby boys . but i am the middle odf my brither 27 and sister 16"),
    (12, "that is one too many i think"),
    (13, "oh why do you say ?"),
    (14, ""),
]

fake_api_response = {
    "mode": "local",
    "api_version": 1.4,
    "job_type": "conversation_tagging",
    "scoring_mechanism": "ground_truth_tag_similarity_scoring",
    "input": {
        "input_type": "conversation",
        "guid": guid,
        "data": {
            "participants": participants,
            "lines": lines,
            "total": 15,
        },
    },
    "prompt_chain": [
        {
            "step": 0,
            "id": "12346546888",
            "crc": 1321321,
            "title": "Infer tags from a conversation window",
            "name": "infer_tags_from_a_conversation_window",
            "description": "Returns tags representing the conversation as a whole from the window received.",
            "type": "inference",
            "input_path": "conversation",
            "prompt_template": "Analyze conversation in terms of topic interests of the participants. Analyze the conversation (provided in structured XML format) where <p0> has the questions and <p1> has the answers . Return comma-delimited tags.  Only return the tags without any English commentary.:\n\n{{ input }}",
            "output_variable": "final_output",
            "output_type": "List[str]",
        }
    ],
    "example_output": {"tags": ["guitar", "barn", "farm", "nashville"], "type": "List[str]"},
    "errors": [],
    "warnings": [],
    "total": 15,
    "guid": guid,
    "participants": participants,
    "lines": lines,
    "prompts": {},
    "data_type": 1,
}

hotkey = "hotkey123"
api_key = "apikey123secret"

override_env_variables = {"SYSTEM_MODE": "prod", "CGP_API_READ_HOST": "https://fake.api", "CGP_API_READ_PORT": "443", "HTTP_TIMEOUT": 10, "MAX_CONVO_LINES": 100}


@pytest.mark.asyncio
@patch("conversationgenome.api.ApiLib.requests.post")
@patch("conversationgenome.api.ApiLib.c.get")
async def test_when_reserving_conversation_then_conversation_is_returned(mock_config_get, mock_requests_post):
    def config_side_effect(section, key, default=None):
        overrides = override_env_variables
        return overrides.get(key, default)

    mock_config_get.side_effect = config_side_effect

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = fake_api_response
    mock_requests_post.return_value = mock_response

    api = ApiLib()
    convo = await api.reserveConversation(hotkey=hotkey, api_key=api_key)

    assert isinstance(convo, Conversation)
    assert convo.guid == guid
    assert convo.participants == participants
    assert convo.lines == lines
    assert convo.miner_task_prompt != None


@pytest.mark.asyncio
@patch("conversationgenome.api.ApiLib.requests.post")
@patch("conversationgenome.api.ApiLib.c.get")
async def test_when_reserving_conversation_with_old_api_version_then_conversation_is_returned_with_none_task_prompt(mock_config_get, mock_requests_post):
    def config_side_effect(section, key, default=None):
        overrides = override_env_variables
        return overrides.get(key, default)

    mock_config_get.side_effect = config_side_effect

    no_prompt_fake_api_response = copy.deepcopy(fake_api_response)
    del no_prompt_fake_api_response["prompt_chain"]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = no_prompt_fake_api_response
    mock_requests_post.return_value = mock_response

    api = ApiLib()
    convo = await api.reserveConversation(hotkey=hotkey, api_key=api_key)

    assert isinstance(convo, Conversation)
    assert convo.guid == guid
    assert convo.participants == participants
    assert convo.lines == lines
    assert convo.miner_task_prompt == None


@pytest.mark.asyncio
@patch("conversationgenome.api.ApiLib.requests.post")
@patch("conversationgenome.api.ApiLib.c.get")
async def test_when_reserving_conversation_then_endpoint_is_called_properly(mock_config_get, mock_requests_post):
    def config_side_effect(section, key, default=None):
        overrides = override_env_variables
        return overrides.get(key, default)

    mock_config_get.side_effect = config_side_effect

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = fake_api_response
    mock_requests_post.return_value = mock_response

    api = ApiLib()
    convo = await api.reserveConversation(hotkey=hotkey, api_key=api_key)

    args, kwargs = mock_requests_post.call_args
    assert "https://fake.api:443/api/v1/conversation/reserve" in args[0]
    assert kwargs["headers"]["Authorization"] == f"Bearer {api_key}"


@pytest.mark.asyncio
@patch("conversationgenome.api.ApiLib.requests.post")
@patch("conversationgenome.api.ApiLib.c.get")
async def test_when_reserving_conversation_with_max_lines_then_max_lines_is_respected(mock_config_get, mock_requests_post):
    MAX_CONVO_LINES = 1

    def config_side_effect(section, key, default=None):
        overrides = override_env_variables
        overrides["MAX_CONVO_LINES"] = MAX_CONVO_LINES
        return overrides.get(key, default)

    mock_config_get.side_effect = config_side_effect

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = fake_api_response
    mock_requests_post.return_value = mock_response

    api = ApiLib()
    convo = await api.reserveConversation(hotkey=hotkey, api_key=api_key)

    assert len(convo.lines) == MAX_CONVO_LINES
    assert convo.lines == lines[0:MAX_CONVO_LINES]
