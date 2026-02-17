import json
import random
import uuid
from copy import deepcopy
from typing import List
from typing import Literal
from typing import Optional
from typing import Tuple

import bittensor as bt
from pydantic import BaseModel

from conversationgenome.api.models.conversation import Conversation
from conversationgenome.api.models.conversation_metadata import ConversationMetadata
from conversationgenome.api.models.raw_metadata import RawMetadata
from conversationgenome.ConfigLib import c

from conversationgenome.llm.LlmLib import LlmLib
from conversationgenome.llm.llm_factory import get_llm_backend
from conversationgenome.scoring_mechanism.GroundTruthTagSimilarityScoringMechanism import (
    GroundTruthTagSimilarityScoringMechanism,
)
from conversationgenome.task.Task import Task
from conversationgenome.task.WebpageMetadataGenerationTask import (
    WebpageMarkdownTaskInput,
)
from conversationgenome.task.WebpageMetadataGenerationTask import (
    WebpageMarkdownTaskInputData,
)
from conversationgenome.task.WebpageMetadataGenerationTask import (
    WebpageMetadataGenerationTask,
)
from conversationgenome.task_bundle.TaskBundle import TaskBundle
from conversationgenome.utils.types import ForceStr
from conversationgenome.utils.Utils import Utils


class WebpageMarkdownInputData(BaseModel):
    lines: List[Tuple[int, str]]

    total: int
    participants: List[str]
    min_convo_windows: int = 0
    indexed_windows: Optional[List[Tuple[int, List[Tuple[int, str]]]]] = None
    prompt: str = (
        "You are given the content of a webpage inside <markdown>...</markdown> tags. Identify the most relevant high-level topics, entities, and concepts that describe the page. Focus only on the core subject matter and ignore navigation menus, boilerplate, or contact info. Return only a flat list of tags in lowercase, separated by commas, with no explanations, formatting, or extra text. Example of required format: tag1, tag2, tag3"
    )


class WebpageMarkdownInput(BaseModel):
    input_type: Literal["webpage_markdown"]
    guid: ForceStr
    data: WebpageMarkdownInputData
    metadata: Optional[ConversationMetadata] = None

    def trim_input(self) -> None:
        max_lines = Utils._int(c.get('env', 'MAX_CONVO_LINES', 300))

        if max_lines and len(self.data.lines) > max_lines:
            self.data.lines = self.data.lines[:max_lines]
            self.data.total = len(self.data.lines)


class WebpageMetadataGenerationTaskBundle(TaskBundle):
    type: Literal["webpage_metadata_generation"] = "webpage_metadata_generation"
    input: Optional[WebpageMarkdownInput] = None

    def is_ready(self) -> bool:
        if self.input.metadata is not None and self.input.data.indexed_windows is not None:
            return True
        return False

    async def setup(self) -> None:
        self.input.trim_input()
        self._split_conversation_in_windows()
        self._enforce_minimum_convo_windows()
        await self._generate_metadata()

    def to_mining_tasks(self, number_of_tasks_per_bundle: int) -> List[Task]:
        tasks = []
        for _ in range(number_of_tasks_per_bundle):
            random_id = str(uuid.uuid4())
            task: WebpageMetadataGenerationTask = WebpageMetadataGenerationTask(
                mode=self.mode,
                api_version=self.api_version,
                guid=random_id,
                bundle_guid=self.guid,
                type=self.type,
                scoring_mechanism=self.scoring_mechanism,
                input=WebpageMarkdownTaskInput(
                    input_type=self.input.input_type,
                    guid=self.input.guid,
                    data=WebpageMarkdownTaskInputData(
                        window=self.input.data.lines,
                        participants=[]
                    ),
                ),
                prompt_chain=self.prompt_chain,
                example_output=self.example_output,
            )
            tasks.append(task)

        return tasks

    def generate_result_logs(self, miner_result) -> str:
        return (
            f"tags: {len(miner_result.get('tags', [])) if isinstance(miner_result.get('tags'), (list, dict)) else 0} "
            f"vector count: {len(miner_result.get('vectors', [])) if isinstance(miner_result.get('vectors'), (list, dict)) else 0} "
            f"original tags: {len(miner_result.get('original_tags', [])) if isinstance(miner_result.get('original_tags'), (list, dict)) else 0}"
        )

    async def format_results(self, miner_result) -> str:
        miner_result['original_tags'] = miner_result['tags']
        # Clean and validate tags for duplicates or whitespace matches
        llml = get_llm_backend()
        miner_result['tags'] = llml.validate_tag_set(tags=miner_result['original_tags'])
        miner_result['vectors'] = await self._get_vector_embeddings_set(llml=llml, tags=miner_result['tags'])
        return miner_result

    async def evaluate(self, miner_responses):
        evaluator = GroundTruthTagSimilarityScoringMechanism()
        return await evaluator.evaluate(self, miner_responses)

    def _split_conversation_in_windows(self) -> None:
        minLines = c.get("convo_window", "min_lines", 2)
        maxLines = c.get("convo_window", "max_lines", 10)
        overlapLines = c.get("convo_window", "overlap_lines", 2)

        windows = Utils.split_overlap_array(self.input.data.lines, size=maxLines, overlap=overlapLines)
        if len(windows) < 2:
            windows = Utils.split_overlap_array(self.input.data.lines, size=minLines, overlap=overlapLines)

        # TODO: Write convo windows into local database with full convo metadata
        indexed_windows = []

        for idx, window in enumerate(windows):
            indexed_windows.append((idx, window))

        self.input.data.indexed_windows = indexed_windows

    def _enforce_minimum_convo_windows(self) -> None:
        minimum_convo_windows = 1
        if self.input.data.min_convo_windows is not None and self.input.data.min_convo_windows >= 0:
            bt.logging.info(f"Change in minimum required convo windows from API from {minimum_convo_windows} to {self.input.data.min_convo_windows}.")
            minimum_convo_windows = self.input.data.min_convo_windows

        if len(self.input.data.indexed_windows) <= minimum_convo_windows:
            bt.logging.info(f"Not enough convo windows -- only {len(self.input.data.indexed_windows)}. Passing.")
            self.input.data.indexed_windows = []

    async def _generate_metadata(self) -> None:
        bt.logging.info(f"Generating metadata for webpage metadata generation")
        parsed_json = json.loads(self.input.data.lines[0][1])
        llml = get_llm_backend()
        
        # Max 1000 characters from the main website markdown
        website_markdown = parsed_json['website_markdown'][:1000]
        website_metadata = llml.website_to_metadata(website_markdown)
        tags = [website_metadata.tags]
        
        enrichment_lines = []
        if parsed_json.get('enrichment'):
            bt.logging.info(f"Generating enrichment metadata for webpage")
            for query, results in parsed_json['enrichment']['search_results'].items():
                # Randomly select some results instead of all
                num_to_select = random.randint(1, min(3, len(results)))
                selected_results = random.sample(results, num_to_select)
                
                for chosen_res in selected_results:
                    # Use snippet and title directly instead of fetching the page
                    snippet = chosen_res.get('snippet', '')
                    title = chosen_res.get('title', '')
                    enrichment_text = f"{title}\n{snippet}"[:1000]
                    
                    if enrichment_text.strip():
                        enrichment_lines.append((len(enrichment_lines), enrichment_text))
                        enrichment_metadata = llml.enrichment_to_metadata(enrichment_text)
                        tags.append(enrichment_metadata.tags)
        else:
            bt.logging.info(f"Generating non-enriched metadata for webpage")
        
        # Update input data with main website content + selected enrichment results
        self.input.data.lines = [(0, website_markdown)] + enrichment_lines
        
        # Combine all tags from main page and enrichment
        result: RawMetadata = llml.combine_metadata_tags(tags, generateEmbeddings=True)
        
        if not result:
            bt.logging.error(f"ERROR:2873226353. No metadata returned. Aborting.")
            return

        if not result.success:
            bt.logging.error(f"ERROR:2873226354. Metadata failed: {result}. Aborting.")
            return
        
        self.input.metadata = ConversationMetadata(
            tags=getattr(result, "tags", []),
            vectors=getattr(result, "vectors", {}),
        )

    async def _get_vector_embeddings_set(self, llml: LlmLib, tags):
        return llml.get_vector_embeddings_set(tags)
