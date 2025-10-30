import json
from typing import List, Literal, Optional, Tuple
import uuid

from pydantic import BaseModel

from conversationgenome.llm.LlmLib import LlmLib
from conversationgenome.scoring_mechanism.GroundTruthTagSimilarityScoringMechanism import GroundTruthTagSimilarityScoringMechanism
from conversationgenome.task.Task import Task
from conversationgenome.task.SurveyTaggingTask import SurveyTaggingTask, SurveyTaggingTaskInput
from conversationgenome.task_bundle.TaskBundle import TaskBundle
from conversationgenome.utils.Utils import Utils


class SurveyTaggingTaskInputData(BaseModel):
    # For now we reuse the conversation input data type but the API could be modified to simplify the task dispatching
    participants: List[str]
    lines: List[Tuple[int, str]]
    total: int
    min_convo_windows: int = 1
    prompt: str = (
        """Analyze a participant's free-form survey comment to identify all reasons substantiated by the text.
        The comment may be in any language. Return a comma-delimited list of tags that summarize the core reasons mentioned in the comment.
        The data is given in JSON format where
            - The "question" field contains the survey question
            - The "comment" field contains the free form comment to tag
        Only return the tags without any English commentary.
        Example data: {
            "question": "Why are you a customer of XYZ Bank?"
            "comment": "I primarily stick with them because their mobile app is fantastic for transfers, and the branch is conveniently located right next to my office.",
            }
        Example response: ["Good mobile application", "Proximity/Convenience"]
        """
    )


class SurveyTaggingInput(BaseModel):
    input_type: str = "survey_tagging"
    guid: str
    data: SurveyTaggingTaskInputData
    # Main inputs for survey task
    survey_question: Optional[str] = None
    comment: Optional[str] = None
    possible_choices: Optional[list[str]] = None
    selected_choices: Optional[list[str]] = None

class SurveyTaggingTaskBundle(TaskBundle):
    type: Literal["survey_tagging"] = "survey_tagging"
    input: Optional[SurveyTaggingInput] = None

    def is_ready(self) -> bool:
        checks = [
            self.input is not None,
            self.input.survey_question is not None,
            self.input.comment is not None,
            self.input.possible_choices is not None,
            self.input.selected_choices is not None
        ]
        return all(checks)

    async def setup(self) -> None:
        self._parse_input_json()

    def _parse_input_json(self) -> None:
        parsed_json = json.loads(self.input.data.lines[0][1])
        self.input.survey_question = parsed_json['survey_question']
        self.input.comment = parsed_json['comment']
        self.input.possible_choices = parsed_json['possible_choices']
        self.input.selected_choices = parsed_json['selected_choices']

    def to_mining_tasks(self, number_of_tasks_per_bundle: int) -> List[Task]:
        return [self._generate_task for _ in range(number_of_tasks_per_bundle)]

    def _generate_task(self) -> SurveyTaggingTask:
        random_id = str(uuid.uuid4())
        return SurveyTaggingTask(
            mode = self.mode,
            api_version = self.api_version,
            guid = random_id,
            bundle_guid = self.guid,
            type = self.type,
            scoring_mechanism = self.scoring_mechanism,
            input = SurveyTaggingTaskInput(
                guid=self.input.guid,
                input_type=self.input.input_type,
                survey_question=self.input.survey_question,
                comment=self.input.comment
            ),
            prompt_chain=self.prompt_chain,
            example_output=self.example_output
        )
    
    async def format_results(self, miner_result) -> str:
        miner_result['original_tags'] = miner_result['tags']
        # Clean and validate tags for duplicates or whitespace matches
        llml = LlmLib()
        miner_result['tags'] = await Utils.validate_tag_set(llml=llml, tags=miner_result['original_tags'])
        miner_result['vectors'] = await self._get_vector_embeddings_set(llml=llml, tags=miner_result['tags'])

        return miner_result
    
    async def _get_vector_embeddings_set(self, llml: LlmLib, tags):
        response = await llml.get_vector_embeddings_set(tags)
        return response

    def generate_result_logs(self, miner_result) -> str:
        return (
            f"tags: {len(miner_result.get('tags', [])) if isinstance(miner_result.get('tags'), (list, dict)) else 0} "
            f"vector count: {len(miner_result.get('vectors', [])) if isinstance(miner_result.get('vectors'), (list, dict)) else 0} "
            f"original tags: {len(miner_result.get('original_tags', [])) if isinstance(miner_result.get('original_tags'), (list, dict)) else 0}"
        )

    async def evaluate(self, miner_responses):
        evaluator = GroundTruthTagSimilarityScoringMechanism()
        return await evaluator.evaluate(self, miner_responses)
