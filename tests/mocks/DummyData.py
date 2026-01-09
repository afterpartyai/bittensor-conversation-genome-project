import json
from typing import Dict
from typing import List
from typing import Tuple

from conversationgenome.api.models.conversation import Conversation
from conversationgenome.api.models.conversation_metadata import ConversationMetadata, ConversationQualityMetadata
from conversationgenome.task.ConversationTaggingTask import ConversationTaggingTask
from conversationgenome.task.SurveyTaggingTask import SurveyTaggingTask
from conversationgenome.task.task_factory import try_parse_task
from conversationgenome.task_bundle.task_bundle_factory import try_parse_task_bundle
from conversationgenome.task_bundle.TaskBundle import TaskBundle


class DummyData:
    @staticmethod
    def guid() -> str:
        return "103733224526844599340117036848021470924"

    @staticmethod
    def task_guid() -> str:
        return "165816516541685165168546984894894984984"

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
    def conversation_tagging_task_json() -> dict:
        return {
            "mode": "local",
            "api_version": 1.4,
            "guid": DummyData.task_guid(),
            "bundle_guid": DummyData.guid(),
            "type": "conversation_tagging",
            "scoring_mechanism": "ground_truth_tag_similarity_scoring",
            "input": {
                "input_type": "conversation",
                "guid": DummyData.guid(),
                "data": {
                    "participants": DummyData.participants(),
                    "window_idx": DummyData.windows()[0][0],
                    "window": DummyData.windows()[0][1],
                    "prompt": "Analyze conversation in terms of topic interests of the participants. Analyze the conversation (provided in structured XML format) where <p0> has the questions and <p1> has the answers . Return comma-delimited tags.  Only return the tags without any English commentary.:\n\n{{ input }}",
                    "min_convo_windows": 1,
                },
                "quality_score": 9,
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
        }

    @staticmethod
    def conversation_tagging_task() -> ConversationTaggingTask:
        return try_parse_task(DummyData.conversation_tagging_task_json())

    @staticmethod
    def survey_tagging_task_json() -> dict:
        return {
            "mode": "local",
            "api_version": 1.4,
            "guid": DummyData.task_guid(),
            "bundle_guid": DummyData.guid(),
            "type": "survey_tagging",
            "scoring_mechanism": "ground_truth_tag_similarity_scoring",
            "input": {
                "input_type": "survey",
                "guid": DummyData.guid(),
                "data": {
                    "survey_question": "What do you think about our mobile application?",
                    "comment": "It's very user-friendly and convenient."
                }
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
        }

    @staticmethod
    def survey_tagging_task_bundle_json() -> dict:
        survey_tagging_task_guid = "1234567890"
        survey_input_data =   {
            "id": "EXAMPLE_001_SOFTWARE_ENGLISH",
            "survey_question": "What did you like most about our new aCRM software? (Select all that apply)",
            "comment": "The user interface is incredibly clean and intuitive, which makes training new team members a breeze. Also, the integration with our existing email client was seamless and saved us a lot of time.",
            "possible_choices": [
                "Affordable pricing",
                "Easy to use / Intuitive UI",
                "Advanced reporting features",
                "Helpful customer support",
                "Smooth Third-Party Integrations",
                "High level of customization"
            ],
            "selected_choices": [
                "Easy to use / Intuitive UI",
                "Smooth Third-Party Integrations"
            ]
        }
        survey_input_data_lines = [[0, json.dumps(survey_input_data)]]

        survey_input_data_participants = ["UNKNOWN_SPEAKER"]
        survey_input_data_total = 1

        return {
            "mode": "local",
            "type": "survey_tagging",
            "guid": survey_tagging_task_guid,
            "scoring_mechanism": "ground_truth_tag_similarity_scoring",
            "input": {
                "input_type": "survey",
                "guid": survey_tagging_task_guid,
                "data": {
                    "lines": survey_input_data_lines,
                    "participants": survey_input_data_participants,
                    "total": survey_input_data_total,
                },
            },
            "prompt_chain": [
                {
                    "step": 0,
                    "id": "12346546999",
                    "crc": 32132132,
                    "title": "Infer the survey answers from the given free-form comment",
                    "name": "infer_tags_for_survey_from_comment",
                    "description": "Returns selected survey answers from the content free-form comment and provided choices.",
                    "type": "inference",
                    "input_path": "survey",
                    "prompt_template": """You are given information regarding a survey response, the data is in json format with the following fields: ["survey_question": str, "comment": str, "possible_choices": list]. Identify wich choices among the "possible choices" the user has made.  Return only a flat list of tags in lowercase, separated by commas, with no explanations, formatting, or extra text. Example of required format: tag1, tag2, tag3""",
                    "output_variable": "final_output",
                    "output_type": "List[str]",
                }
            ],
            "example_output": {
                "tags": ["guitar", "barn", "farm", "nashville"],
                "type": "List[str]",
            },
            "errors": [],
            "warnings": [],
            "data_type": 1,
            "job_type": "survey_metadata_generation",
            "total": survey_input_data_total,
            "guid": survey_tagging_task_guid,
            "participants": survey_input_data_participants,
            "lines": survey_input_data_lines,
            "min_convo_windows": 0
        }

    @staticmethod
    def survey_tagging_task() -> SurveyTaggingTask:
        return try_parse_task(DummyData.survey_tagging_task_json())

    @staticmethod
    def survey_tagging_task_bundle() -> TaskBundle:
        return try_parse_task_bundle(DummyData.survey_tagging_task_bundle_json())

    @staticmethod
    def setup_survey_tagging_task_bundle() -> TaskBundle:
        from conversationgenome.task_bundle.SurveyTaggingTaskBundle import SurveyMetadata
        task_bundle = try_parse_task_bundle(DummyData.survey_tagging_task_bundle_json())
        # Simulate the metadata generation
        import json
        parsed_json = json.loads(task_bundle.input.data.lines[0][1])
        task_bundle.input.metadata = SurveyMetadata(
            survey_question=parsed_json['survey_question'],
            comment=parsed_json['comment'],
            possible_choices=parsed_json['possible_choices'],
            selected_choices=parsed_json['selected_choices'],
            tags=parsed_json['selected_choices'],
            vectors={"tag1": {"vectors": [0.1]}},
            participantProfiles=task_bundle.input.data.participants
        )
        return task_bundle

    @staticmethod
    def conversation_tagging_task_bundle_json():
        return {
            "mode": "local",
            "api_version": 1.4,
            "type": "conversation_tagging",
            "scoring_mechanism": "ground_truth_tag_similarity_scoring",
            "input": {
                "input_type": "conversation",
                "guid": DummyData.guid(),
                "data": {
                    "participants": DummyData.participants(),
                    "lines": DummyData.lines(),
                    "total": len(DummyData.lines()),
                },
                "quality_score": 9
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
            "guid": DummyData.guid(),
            "data_type": 1,
        }

    @staticmethod
    def conversation_tagging_task_bundle() -> TaskBundle:
        return try_parse_task_bundle(DummyData.conversation_tagging_task_bundle_json())

    @staticmethod
    def setup_conversation_tagging_task_bundle() -> TaskBundle:
        task_bundle = try_parse_task_bundle(DummyData.conversation_tagging_task_bundle_json())
        task_bundle.input.data.indexed_windows = DummyData.windows()
        task_bundle.input.metadata = DummyData.metadata()
        return task_bundle

    @staticmethod
    def named_entities_extraction_task_bundle_json():
        return {
            "mode": "validator",
            "api_version": 1.4,
            "type": "named_entities_extraction",
            "scoring_mechanism": "no_penalty_ground_truth_tag_similarity_scoring",
            "input": {
                "input_type": "document",
                "guid": DummyData.guid(),
                "data": {
                    "lines": DummyData.lines(),
                    "total": len(DummyData.lines()),
                },
                "metadata": DummyData.metadata()
            },
            "prompt_chain": [
                {
                    "step": 0,
                    "id": "12346546889",
                    "crc": 1321322,
                    "title": "Extract named entities from transcript",
                    "name": "extract_named_entities_from_transcript",
                    "description": "Returns named entities from the transcript.",
                    "type": "inference",
                    "input_path": "transcript",
                    "prompt_template": "Analyze the text provided to identify all specific Named Entities. Focus on: People, Organizations, Locations, Laws/Statutes, Budgets, and Specific Projects. Return a single list that contains all named entities.",
                    "output_variable": "final_output",
                    "output_type": "List[str]",
                }
            ],
            "example_output": {"tags": ["Mayor Adams", "Local Law 55", "Downtown Grant"], "type": "List[str]"},
            "errors": [],
            "warnings": [],
            "guid": DummyData.guid(),
            "data_type": 1,
        }

    @staticmethod
    def named_entities_extraction_task_bundle() -> TaskBundle:
        return try_parse_task_bundle(DummyData.named_entities_extraction_task_bundle_json())

    @staticmethod
    def setup_named_entities_extraction_task_bundle() -> TaskBundle:
        task_bundle = try_parse_task_bundle(DummyData.named_entities_extraction_task_bundle_json())
        task_bundle.input.metadata = DummyData.metadata()
        return task_bundle

    @staticmethod
    def webpage_metadata_generation_task_bundle_json():
        return {
            "mode": "validator",
            "api_version": 1.4,
            "type": "webpage_metadata_generation",
            "scoring_mechanism": "ground_truth_tag_similarity_scoring",
            "input": {
                "input_type": "webpage_markdown",
                "guid": DummyData.guid(),
                "data": {
                    "lines": DummyData.lines(),
                    "total": len(DummyData.lines()),
                    "participants": DummyData.participants(),
                },
                "metadata": DummyData.metadata()
            },
            "prompt_chain": [
                {
                    "step": 0,
                    "id": "12346546890",
                    "crc": 1321323,
                    "title": "Extract metadata from webpage markdown",
                    "name": "extract_metadata_from_webpage_markdown",
                    "description": "Returns metadata tags from webpage markdown content.",
                    "type": "inference",
                    "input_path": "webpage_markdown",
                    "prompt_template": "You are given the content of a webpage inside <markdown>...</markdown> tags. Identify the most relevant high-level topics, entities, and concepts that describe the page. Focus only on the core subject matter and ignore navigation menus, boilerplate, or contact info. Return only a flat list of tags in lowercase, separated by commas, with no explanations, formatting, or extra text. Example of required format: tag1, tag2, tag3",
                    "output_variable": "final_output",
                    "output_type": "List[str]",
                }
            ],
            "example_output": {"tags": ["artificial intelligence", "machine learning", "data science"], "type": "List[str]"},
            "errors": [],
            "warnings": [],
            "guid": DummyData.guid(),
            "data_type": 1,
        }

    @staticmethod
    def webpage_metadata_generation_task_bundle() -> TaskBundle:
        return try_parse_task_bundle(DummyData.webpage_metadata_generation_task_bundle_json())

    @staticmethod
    def conversation_quality_metadata_high():
        from conversationgenome.api.models.conversation_metadata import ConversationQualityMetadata
        return ConversationQualityMetadata(
            quality_score=9,
            primary_reason="High quality conversation",
            reason_details="Detailed analysis shows high engagement"
        )