from typing import Dict, List, Tuple

from conversationgenome.api.models.conversation import Conversation
from conversationgenome.api.models.conversation_metadata import ConversationMetadata
from conversationgenome.task.Task import Task


class DummyData:
    @staticmethod
    def guid() -> str:
        return "103733224526844599340117036848021470924"

    @staticmethod
    def participants() -> List[str]:
        return ["SPEAKER_1", "SPEAKER_2"]

    @staticmethod
    def tags() -> List[str]:
        return ["greeting", "farewell", "small_talk"]

    @staticmethod
    def vectors() -> Dict[str, Dict[str, List[float]]]:
        return {"greeting": {"vector": [0.1]}, "farewell": {"vector": [0.2]}, "small_talk": {"vector": [0.3]}}

    @staticmethod
    def lines() -> List[str]:
        return [
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

    @staticmethod
    def windows() -> List[Tuple[int, List[Tuple[int, str]]]]:
        return [
            (
                0,
                [
                    (0, 'hey how are you tonight'),
                    (1, 'i am doing well . wedding planning . yay ! 6 more months . you ?'),
                    (2, 'watching a movie tonight , titanic'),
                    (3, 'oh . i am babysitting . its my side hustle'),
                    (4, 'that is a good one . i have kids too'),
                    (5, 'hey it paid for my mercedes . no complaints'),
                    (6, 'that is nice . time to get a ferrari'),
                    (7, 'ugh i wish . my wedding is in 6 months . ferrari has to wait . . .'),
                    (8, 'you only live once . marry next time'),
                    (9, 'maybe i can get onw as a wedding gift . . being the middle kid sucks . parents neglect ya'),
                ],
            ),
            (
                1,
                [
                    (8, 'you only live once . marry next time'),
                    (9, 'maybe i can get onw as a wedding gift . . being the middle kid sucks . parents neglect ya'),
                    (10, 'i know . i am a parent too'),
                    (11, 'i have 2 baby boys . but i am the middle odf my brither 27 and sister 16'),
                    (12, 'that is one too many i think'),
                    (13, 'oh why do you say ?'),
                    (14, ''),
                ],
            ),
        ]

    @staticmethod
    def metadata() -> ConversationMetadata:
        return ConversationMetadata(participantProfiles=DummyData.participants(), tags=["risk", "security"], vectors={"risk": {"vectors": [0.1, 0.2, 0.3]}})

    @staticmethod
    def conversation_tagging_task_json():
        return {
            "mode": "local",
            "api_version": 1.4,
            "job_type": "conversation_tagging",
            "scoring_mechanism": "ground_truth_tag_similarity_scoring",
            "input": {
                "input_type": "conversation",
                "guid": DummyData.guid(),
                "data": {
                    "participants": DummyData.participants(),
                    "lines": DummyData.lines(),
                    "total": len(DummyData.lines()),
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
            "total": len(DummyData.lines()),
            "guid": DummyData.guid(),
            "participants": DummyData.participants(),
            "lines": DummyData.lines(),
            "prompts": {},
            "data_type": 1,
        }

    @staticmethod
    def conversation_tagging_task() -> Task:
        return Task.model_validate(DummyData.conversation_tagging_task_json())

    @staticmethod
    def conversation() -> Conversation:
        return Conversation(
            guid=DummyData.guid(),
            lines=DummyData.lines(),
            participants=DummyData.participants(),
            indexed_windows=DummyData.windows(),
            metadata=DummyData.metadata(),
        )
