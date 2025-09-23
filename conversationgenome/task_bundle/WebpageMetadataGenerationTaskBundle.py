import random
import uuid
from typing import Any, List, Literal, Optional, Tuple

import bittensor as bt
from pydantic import BaseModel

from conversationgenome.api.models.conversation import Conversation
from conversationgenome.api.models.conversation_metadata import ConversationMetadata
from conversationgenome.api.models.raw_metadata import RawMetadata
from conversationgenome.ConfigLib import c
from conversationgenome.llm.LlmLib import LlmLib
from conversationgenome.scoring_mechanism.GroundTruthTagSimilarityScoringMechanism import GroundTruthTagSimilarityScoringMechanism
from conversationgenome.task.Task import Task
from conversationgenome.task.WebpageMetadataGenerationTask import WebpageMarkdownTaskInput, WebpageMarkdownTaskInputData, WebpageMetadataGenerationTask
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

        if len(self.input.data.indexed_windows) > number_of_tasks_per_bundle:
            indexed_windows_subset = random.sample(self.input.data.indexed_windows, number_of_tasks_per_bundle)
        else:
            indexed_windows_subset = self.input.data.indexed_windows

        for _, indexed_window in enumerate(indexed_windows_subset):
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
                    data=WebpageMarkdownTaskInputData(
                        min_convo_windows=self.input.data.min_convo_windows,
                        prompt=self.input.data.prompt,
                        participants=self.input.data.participants,
                        window=indexed_window[1],
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
        llml = LlmLib()
        miner_result['tags'] = await Utils.validate_tag_set(llml=llml, tags=miner_result['original_tags'])
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
        bt.logging.info(f"Generating metadata")

        llml = LlmLib()

        conversation = Conversation(
            guid=self.input.guid,
            lines=self.input.data.lines,
            participants=self.input.data.participants,
            miner_task_prompt=self.input.data.prompt,
        )

        result: RawMetadata = await llml.conversation_to_metadata(conversation=conversation, generateEmbeddings=True)

        if not result:
            bt.logging.error(f"ERROR:2873226353. No metadata returned. Aborting.")
            return None

        if not result.success:
            bt.logging.error(f"ERROR:2873226354. Metadata failed: {result}. Aborting.")
            return None

        self.input.metadata = ConversationMetadata(
            tags=getattr(result, "tags", []),
            vectors=getattr(result, "vectors", {}),
        )

    async def _get_vector_embeddings_set(self, llml: LlmLib, tags):
        response = await llml.get_vector_embeddings_set(tags)
        return response
