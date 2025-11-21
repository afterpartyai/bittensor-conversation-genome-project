import json
from typing import Dict, List, Literal, Optional, Tuple
import uuid

import bittensor as bt
from pydantic import BaseModel

from conversationgenome.llm.llm_factory import get_llm_backend
from conversationgenome.scoring_mechanism.GroundTruthTagSimilarityScoringMechanism import GroundTruthTagSimilarityScoringMechanism
from conversationgenome.task.Task import Task
from conversationgenome.task.SurveyTaggingTask import SurveyTaggingTask, SurveyTaggingTaskInput, SurveyTaggingTaskInputData
from conversationgenome.task_bundle.TaskBundle import TaskBundle


class SurveyInputData(BaseModel):
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

class SurveyMetadata(BaseModel):
    survey_question: Optional[str] = None
    comment: Optional[str] = None
    possible_choices: Optional[list[str]] = None
    selected_choices: Optional[list[str]] = None

    tags: List[str]
    vectors: Dict[str, Dict[str, List[float]]]
    participantProfiles: Optional[List[str]] = None

class SurveyTaggingInput(BaseModel):
    input_type: Literal['survey'] = "survey"
    guid: str
    data: SurveyInputData
    metadata: Optional[SurveyMetadata] = None

class SurveyTaggingTaskBundle(TaskBundle):
    type: Literal["survey_tagging"] = "survey_tagging"
    input: Optional[SurveyTaggingInput] = None

    def is_ready(self) -> bool:
        return self.input is not None and self.input.metadata is not None

    async def setup(self) -> None:
        await self._generate_metadata()

    async def _generate_metadata(self) -> None:
        bt.logging.info(f"Generating survey metadata for survey tagging task bundle {self.guid}")
        parsed_json = json.loads(self.input.data.lines[0][1])
        llml = get_llm_backend()
        self.input.metadata = SurveyMetadata(
            tags=parsed_json['selected_choices'],
            vectors= await llml.get_vector_embeddings_set(parsed_json['selected_choices']),
            survey_question = parsed_json['survey_question'],
            comment = parsed_json['comment'],
            possible_choices = parsed_json['possible_choices'],
            selected_choices = parsed_json['selected_choices']
        )

    def to_mining_tasks(self, number_of_tasks_per_bundle: int) -> List[Task]:
        return [self._generate_task() for _ in range(number_of_tasks_per_bundle)]

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
                data=SurveyTaggingTaskInputData(
                    survey_question=self.input.metadata.survey_question,
                    comment=self.input.metadata.comment
                )
            ),
            prompt_chain=self.prompt_chain,
            example_output=self.example_output
        )
    
    async def format_results(self, miner_result) -> str:
        miner_result['original_tags'] = miner_result['tags']
        llml = get_llm_backend()
        miner_result['tags'] = await llml.validate_tag_set(tags=miner_result['original_tags'])
        miner_result['vectors'] = await llml.get_vector_embeddings_set(tags=miner_result['tags'])
        return miner_result

    def generate_result_logs(self, miner_result) -> str:
        return (
            f"tags: {len(miner_result.get('tags', [])) if isinstance(miner_result.get('tags'), (list, dict)) else 0} "
            f"vector count: {len(miner_result.get('vectors', [])) if isinstance(miner_result.get('vectors'), (list, dict)) else 0} "
            f"original tags: {len(miner_result.get('original_tags', [])) if isinstance(miner_result.get('original_tags'), (list, dict)) else 0}"
        )

    async def evaluate(self, miner_responses):
        evaluator = GroundTruthTagSimilarityScoringMechanism()
        evaluator.min_tags = 1  # Survey tagging may result in fewer tags, allowing evaluation with at least 1 tag
        return await evaluator.evaluate(self, miner_responses)
