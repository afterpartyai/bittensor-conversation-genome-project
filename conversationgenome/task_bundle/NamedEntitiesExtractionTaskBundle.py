import json
import random
import uuid
from typing import Any, Dict, List
from typing import Literal
from typing import Optional
from typing import Tuple
import requests
from io import BytesIO

from bs4 import BeautifulSoup
try:
    import pypdf
except ImportError:
    pypdf = None
import bittensor as bt
from pydantic import BaseModel

from conversationgenome.api.models.conversation_metadata import ConversationMetadata

from conversationgenome.ConfigLib import c
from conversationgenome.api.models.raw_metadata import RawMetadata
from conversationgenome.llm.llm_factory import get_llm_backend
from conversationgenome.llm.LlmLib import LlmLib
from conversationgenome.scoring_mechanism.NoPenaltyGroundTruthTagSimilarityScoringMechanism import NoPenaltyGroundTruthTagSimilarityScoringMechanism
from conversationgenome.task.NamedEntitiesExtrationTask import NamedEntitiesExtractionTask, NamedEntitiesExtractionTaskInput, NamedEntitiesExtractionTaskInputData
from conversationgenome.task.Task import Task
from conversationgenome.task_bundle.TaskBundle import TaskBundle
from conversationgenome.utils.types import ForceStr
from conversationgenome.utils.Utils import Utils

NAMED_ENTITIES_CATEGORIES = ["people", "organizations", "locations", "laws_statutes", "budgets", "specific_projects"]

class NERMetadata(BaseModel):
    tags: List[str]
    vectors: Dict[str, Dict[str, List[float]]]
    participantProfiles: Optional[List[str]] = None


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

    def is_ready(self) -> bool:
        if self.input.metadata is not None and self.input.data.lines is not None:
            return True
        return False

    async def setup(self) -> None:
        self._generate_metadata()

    def _generate_metadata(self) -> None:
        bt.logging.info(f"Generating metadata for NER recognition")
        parsed_json = json.loads(self.input.data.lines[0][1])
        llml = get_llm_backend()

        # Max 1000 characters
        transcript_text = parsed_json['transcript_text'][:1000]
        transcript_metadata = llml.raw_transcript_to_named_entities(transcript_text)
        tags = [transcript_metadata.tags]

        web_texts = []
        if parsed_json['enrichment']:
            bt.logging.info(f"Generating enrichment metadata for NER")
            for query, results in parsed_json['enrichment']['search_results'].items():
                chosen_res = random.choice(results)
                # Max 1000 characters
                web_text = self.get_webpage_text(chosen_res['url'])[:1000]
                if web_text:
                    web_texts.append((0, web_text))
                    tags.append(llml.raw_webpage_to_named_entities(web_text).tags)
        else:
            bt.logging.info(f"Generating non-enriched metadata for NER")

        result: RawMetadata = llml.combine_named_entities(tags, generateEmbeddings=True)
        self.input.metadata = NERMetadata(
            tags=getattr(result, "tags", []),
            vectors=getattr(result, "vectors", {}),
            participantProfiles = None
        )
        # Give transcript + selected web pages to miner
        self.input.data.lines = [(0, transcript_text)] + web_texts


    def get_webpage_text(self, url):
        try:
            # Fetch the content
            response = requests.get(url)
            response.raise_for_status() # Raise error for bad status (404, 500, etc.)

            # Check if the content is a PDF
            content_type = response.headers.get('content-type', '').lower()
            is_pdf = 'application/pdf' in content_type or url.lower().endswith('.pdf')

            if is_pdf and pypdf:
                bt.logging.info('Extracting enrichment from PDF')
                # Extract text from PDF
                pdf_file = BytesIO(response.content)
                pdf_reader = pypdf.PdfReader(pdf_file)
                text_content = ""
                for page in pdf_reader.pages:
                    text_content += page.extract_text() + " "
                return text_content.strip()
            else:
                bt.logging.info('Extracting enrichment from HTML')
                # Parse the HTML
                soup = BeautifulSoup(response.text, 'html.parser')

                # Extract text, using a space as a separator between HTML tags
                # strip=True removes leading/trailing whitespace
                text_content = soup.get_text(separator=' ', strip=True)
                
                return text_content

        except Exception as e:
            return ''


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
        evaluator = NoPenaltyGroundTruthTagSimilarityScoringMechanism()
        evaluator.min_tags = 1  # NER may result in fewer tags, allowing evaluation with at least 1 tag
        return await evaluator.evaluate(self, miner_responses)

    def mask_task_for_miner(self, task: Task) -> Task:
        masked_task = super().mask_task_for_miner(task)
        HIDDEN_WINDOW_IDX = -1
        masked_task.input.data.window_idx = HIDDEN_WINDOW_IDX
        return masked_task

    async def _get_vector_embeddings_set(self, llml: LlmLib, tags):
        return llml.get_vector_embeddings_set(tags)
