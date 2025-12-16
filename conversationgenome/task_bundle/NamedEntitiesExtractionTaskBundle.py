import json
import random
import uuid
from typing import List
from typing import Literal
from typing import Optional
from typing import Tuple
import requests

from bs4 import BeautifulSoup
import bittensor as bt
from pydantic import BaseModel

from conversationgenome.api.models.conversation_metadata import ConversationMetadata

from conversationgenome.api.models.raw_metadata import RawMetadata
from conversationgenome.ConfigLib import c
from conversationgenome.llm.llm_factory import get_llm_backend
from conversationgenome.llm.LlmLib import LlmLib
from conversationgenome.scoring_mechanism.GroundTruthTagSimilarityScoringMechanism import (
    GroundTruthTagSimilarityScoringMechanism,
)
from conversationgenome.task.NamedEntitiesExtrationTask import NamedEntitiesExtractionTask, NamedEntitiesExtractionTaskInput, NamedEntitiesExtractionTaskInputData
from conversationgenome.task.Task import Task
from conversationgenome.task_bundle.TaskBundle import TaskBundle
from conversationgenome.utils.types import ForceStr
from conversationgenome.utils.Utils import Utils

NAMED_ENTITIES_CATEGORIES = ["people", "organizations", "locations", "laws_statutes", "budgets", "specific_projects"]

class TranscriptMetadata(BaseModel):
    name: str
    timestamp: float
    transcript_link: str

    # Optionnal
    duration: Optional[str] = None
    context: Optional[str] = None


class NamedEntitiesExtractionTaskBundleInputData(BaseModel):
    lines: List[Tuple[int, str]]
    total: int
    min_convo_windows: int = 1
    indexed_windows: Optional[List[Tuple[int, List[Tuple[int, str]]]]] = None
    prompt: str = (
        """Analyze the text provided to identify all specific Named Entities.
           Focus on: People, Organizations, Locations, Laws/Statutes, Budgets, and Specific Projects.

           Return a single list that contains all named entities.

           Normalize the names (e.g., "Mayor Adams" and "Adams" should be aggregated into one entry).
           Only return the list object. Do not include any conversational text or surrounding arrays.

           Example Data: "Mayor Adams proposed an amendment to Local Law 55 regarding the Downtown Grant. Adams stated that the Grant is essential for the city."
           Example Response: ["Mayor Adams", "Local Law 55", "Downtown Grant"]
        """
    )


class NamedEntitiesExtractionTaskBundleInput(BaseModel):
    input_type: Literal["document"]
    guid: ForceStr
    data: NamedEntitiesExtractionTaskBundleInputData
    metadata: Optional[ConversationMetadata] = None
    def to_raw_text(self):
        return "\n".join((line[1] for line in self.data.lines))

class NamedEntitiesExtractionTaskBundle(TaskBundle):
    mode:str = 'validator'
    type: Literal["named_entities_extraction"] = "named_entities_extraction"
    input: Optional[NamedEntitiesExtractionTaskBundleInput] = None
    _QUALITY_THRESHOLD = Utils._int(c.get('env', 'CONVO_QUALITY_THRESHOLD', 5))

    def __init__(self):
        super().__init__()
        bt.logging.info(f"Initializing named-entities task")
        transcript_metadata = self._get_random_transcript()
        transcript_lines = self._load_transcript(transcript_metadata.transcript_link)
        parsed_lines = self._parse_raw_transcript(transcript_lines)
        # For now we limit to 1000 lines
        parsed_lines = parsed_lines[:1000]
        data = NamedEntitiesExtractionTaskBundleInputData(
            lines = parsed_lines,
            total = len(transcript_lines)
        )
        self.guid = str(uuid.uuid4())
        self.input = NamedEntitiesExtractionTaskBundleInput(
            input_type='document',
            guid=self.guid,
            data=data
        )

    def _parse_raw_transcript(self, raw_transcript: str) -> Tuple[int, str]:
        soup = BeautifulSoup(raw_transcript, 'html.parser')
        # Remove all script and style elements
        for script in soup(["script", "style"]):
            script.extract()
            
        text = soup.get_text()
        return [[i, line] for i, line in enumerate(text.splitlines())]

    def _load_transcript(self, transcript_link: str) -> str:
        res = requests.get(transcript_link)
        return res.content

    def _get_random_transcript(self) -> TranscriptMetadata:
        # Build the task locally from the pre-processed extractions
        extraction_paths = [
            "conversationgenome/task_bundle/named_entities_tasks/la_transcript_data.json",
            "conversationgenome/task_bundle/named_entities_tasks/sf_transcript_data.json"
        ]
        raw_extractions = []
        for extraction_path in extraction_paths:
            with open(extraction_path, 'r') as f:
                raw_extractions.extend(json.load(f))
        print(len(raw_extractions))
        return TranscriptMetadata(**random.choice(raw_extractions))

    def is_ready(self) -> bool:
        if self.input.metadata is not None and self.input.data.lines is not None:
            return True
        return False

    async def setup(self) -> None:
        self._generate_metadata()

    def to_mining_tasks(self, number_of_tasks_per_bundle: int) -> List[Task]:
        tasks = []
        for _ in range(number_of_tasks_per_bundle):
            random_id = str(uuid.uuid4())
            task: NamedEntitiesExtractionTask = NamedEntitiesExtractionTask(
                mode=self.mode,
                api_version=self.api_version,
                guid=random_id,
                bundle_guid=self.guid,
                type=self.type,
                scoring_mechanism=self.scoring_mechanism,
                input=NamedEntitiesExtractionTaskInput(
                    input_type=self.input.input_type,
                    guid=self.input.guid,
                    data=NamedEntitiesExtractionTaskInputData(window=self.input.data.lines),
                ),
                prompt_chain=self.prompt_chain,
                example_output=self.example_output,
            )
            tasks.append(task)
        return tasks

    async def format_results(self, miner_result) -> str:
        miner_result['original_tags'] = miner_result['tags']
        # Clean and validate tags for duplicates or whitespace matches
        llml = get_llm_backend()
        miner_result['tags'] = llml.validate_named_entities_tag_set(miner_result['original_tags'])
        miner_result['vectors'] = await self._get_vector_embeddings_set(llml=llml, tags=miner_result['tags'])
        return miner_result

    def generate_result_logs(self, miner_result) -> str:
        return (
            f"tags: {len(miner_result.get('tags', [])) if isinstance(miner_result.get('tags'), (list, dict)) else 0} "
            f"vector count: {len(miner_result.get('vectors', [])) if isinstance(miner_result.get('vectors'), (list, dict)) else 0} "
            f"original tags: {len(miner_result.get('original_tags', [])) if isinstance(miner_result.get('original_tags'), (list, dict)) else 0}"
        )

    async def evaluate(self, miner_responses):
        evaluator = GroundTruthTagSimilarityScoringMechanism()
        return await evaluator.evaluate(self, miner_responses)

    def mask_task_for_miner(self, task: Task) -> Task:
        masked_task = super().mask_task_for_miner(task)
        HIDDEN_WINDOW_IDX = -1
        masked_task.input.data.window_idx = HIDDEN_WINDOW_IDX
        return masked_task

    def _generate_metadata(self) -> None:
        bt.logging.info(f"Generating metadata")
        llml = get_llm_backend()
        result = llml.raw_transcript_to_named_entities(self.input.to_raw_text())
        if not result:
            bt.logging.error(f"ERROR:2873226353. No metadata returned. Aborting.")
            return
        try:
            result = json.loads(result)
        except Exception:
            bt.logging.error(f"ERROR: Failed to parse the json response in metadata processing: {result}. Aborting.")
            return
        
        tags = []
        # For now we combine all categories in order to reuse the current scoring mechanism
        for category in NAMED_ENTITIES_CATEGORIES:
            tags.extend(result.get(category, []))
        vectors = llml.get_vector_embeddings_set(tags)

        self.input.metadata = ConversationMetadata(
            participantProfiles=None,
            tags=tags,
            vectors=vectors,
        )

    async def _get_vector_embeddings_set(self, llml: LlmLib, tags):
        return llml.get_vector_embeddings_set(tags)
