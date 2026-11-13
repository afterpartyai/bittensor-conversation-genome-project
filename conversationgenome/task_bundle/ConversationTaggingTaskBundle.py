import math
import random
import uuid
from copy import deepcopy
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional
from typing import Tuple

import bittensor as bt
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import PrivateAttr

from conversationgenome.api.models.conversation import Conversation
from conversationgenome.api.models.conversation_metadata import ConversationMetadata, ConversationQualityMetadata
from conversationgenome.api.models.raw_metadata import RawMetadata
from conversationgenome.ConfigLib import c
from conversationgenome.llm.LlmLib import LlmLib
from conversationgenome.llm.llm_factory import get_llm_backend
from conversationgenome.scoring_mechanism.GroundTruthTagSimilarityScoringMechanism import (
    GroundTruthTagSimilarityScoringMechanism,
)
from conversationgenome.task.ConversationTaggingTask import ConversationTaggingTask
from conversationgenome.task.ConversationTaggingTask import ConversationTaskInput
from conversationgenome.task.ConversationTaggingTask import ConversationTaskInputData
from conversationgenome.task.Task import Task
from conversationgenome.task_bundle.TaskBundle import TaskBundle
from conversationgenome.utils.types import ForceStr
from conversationgenome.utils.Utils import Utils


class EnrichmentSearchResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: Optional[str] = None
    snippet: Optional[str] = None


class Enrichment(BaseModel):
    search_results: Dict[str, List[EnrichmentSearchResult]] = Field(default_factory=dict)


class ConversationInputData(BaseModel):
    participants: List[str]
    lines: List[Tuple[int, str]]
    total: int
    min_convo_windows: int = 1
    indexed_windows: Optional[List[Tuple[int, List[Tuple[int, str]]]]] = None
    enrichment: Optional[Enrichment] = None
    enrichment_lines: Optional[List[Tuple[int, str]]] = None
    prompt: str = (
        "Analyze conversation in terms of topic interests of the participants. Analyze the conversation (provided in structured XML format) where <p0> has the questions and <p1> has the answers. Return comma-delimited tags. Only return the tags without any English commentary."
    )


class ConversationInput(BaseModel):
    input_type: Literal["conversation"]
    guid: ForceStr
    data: ConversationInputData
    input_categories: Optional[List[str]] = None
    metadata: Optional[ConversationMetadata] = None
    quality_score: Optional[int] = None

    def trim_input(self) -> None:
        max_lines = Utils._int(c.get('env', 'MAX_CONVO_LINES', 300))

        if max_lines and len(self.data.lines) > max_lines:
            self.data.lines = self.data.lines[:max_lines]
            self.data.total = len(self.data.lines)


class ConversationTaggingTaskBundle(TaskBundle):
    type: Literal["conversation_tagging"] = "conversation_tagging"
    input: Optional[ConversationInput] = None
    _QUALITY_THRESHOLD = Utils._int(c.get('env', 'CONVO_QUALITY_THRESHOLD', 5))
    # Min index distance between windows that share no lines
    _window_min_gap: int = PrivateAttr(default=1)

    def is_ready(self) -> bool:
        if self.input.metadata is None or self.input.data.indexed_windows is None:
            return False
        if self.is_user_request:
            return True
        return self._check_conversation_quality()

    async def setup(self) -> None:
        self.input.trim_input()
        self._split_conversation_in_windows()

        if self.is_user_request:
            await self._generate_metadata()
            return

        self._enforce_minimum_convo_windows()
        if not self.input.data.indexed_windows:
            return

        await self._get_conversation_quality()
        # Only generate metadata and make bundle ready for conversations that pass quality threshold
        if self._check_conversation_quality():
            await self._generate_metadata()
        else:
            bt.logging.info(f"Conversation did not pass quality check or could not be validated. Skipping metadata generation.")

    async def _get_conversation_quality(self) -> None:
        bt.logging.info(f"Validating conversation quality")
        llml = get_llm_backend()
        conversation = Conversation(
            guid=self.input.guid,
            lines=self.input.data.lines,
            participants=self.input.data.participants,
            miner_task_prompt=self.input.data.prompt,
        )
        result: ConversationQualityMetadata|None = llml.validate_conversation_quality(conversation=conversation)
        if result:
            # For now, only store quality score, down the line we can expand to store more detailed metadata if we want to use it
            self.input.quality_score = result.quality_score
        else:
            bt.logging.error(f"ERROR - No conversation quality metadata returned. Aborting.")
    
    def _check_conversation_quality(self) -> bool:
        if self.input.quality_score is not None:
            return self.input.quality_score >= self._QUALITY_THRESHOLD
        return False

    def to_mining_tasks(self, number_of_tasks_per_bundle: int) -> List[Task]:
        tasks = []

        indexed_windows_subset = self._select_windows(number_of_tasks_per_bundle)
        enrichment_per_window = self._partition_enrichment_lines(len(indexed_windows_subset))

        for indexed_window, window_enrichment_lines in zip(indexed_windows_subset, enrichment_per_window):
            random_id = str(uuid.uuid4())
            task: ConversationTaggingTask = ConversationTaggingTask(
                mode=self.mode,
                api_version=self.api_version,
                guid=random_id,
                bundle_guid=self.guid,
                type=self.type,
                scoring_mechanism=self.scoring_mechanism,
                input=ConversationTaskInput(
                    input_type=self.input.input_type,
                    guid=self.input.guid,
                    data=ConversationTaskInputData(
                        window_idx=indexed_window[0],
                        window=indexed_window[1],
                        participants=[],
                        enrichment_lines=window_enrichment_lines,
                    ),
                    input_categories=self.input.input_categories
                ),
                prompt_chain=self.prompt_chain,
                example_output=self.example_output,
            )
            tasks.append(task)

        return tasks

    def _max_windows_to_send(self, number_of_tasks_per_bundle: int) -> int:
        """Max windows of this conversation that may be sent to miners."""
        num_windows = len(self.input.data.indexed_windows or [])
        if num_windows == 0:
            return 0

        limit = number_of_tasks_per_bundle

        if not self.is_user_request:
            max_per_convo = c.get("convo_window", "max_windows_per_conversation", 2)
            max_fraction = c.get("convo_window", "max_window_fraction", 0.25)
            limit = min(limit, max_per_convo, max(1, math.floor(num_windows * max_fraction)))

        gap = max(1, self._window_min_gap)
        max_non_overlapping = (num_windows - 1) // gap + 1
        return max(0, min(limit, max_non_overlapping))

    def _select_windows(self, number_of_tasks_per_bundle: int) -> List[Tuple[int, List[Tuple[int, str]]]]:
        """Randomly pick windows that share no lines with each other."""
        windows = self.input.data.indexed_windows or []
        k = self._max_windows_to_send(number_of_tasks_per_bundle)
        if k == 0:
            return []

        gap = max(1, self._window_min_gap)
        compressed_range = len(windows) - (k - 1) * (gap - 1)
        positions = sorted(random.sample(range(compressed_range), k))
        selected = [windows[pos + rank * (gap - 1)] for rank, pos in enumerate(positions)]
        random.shuffle(selected)
        return selected

    def _partition_enrichment_lines(self, num_windows: int) -> List[Optional[List[Tuple[int, str]]]]:
        """Split enrichment snippets across windows so no two windows share one."""
        if num_windows <= 0:
            return []

        enrichment_lines = list(self.input.data.enrichment_lines or [])
        if not enrichment_lines:
            return [None] * num_windows

        random.shuffle(enrichment_lines)
        buckets: List[List[str]] = [[] for _ in range(num_windows)]
        for i, (_, content) in enumerate(enrichment_lines):
            buckets[i % num_windows].append(content)

        return [[(idx, content) for idx, content in enumerate(bucket)] or None for bucket in buckets]

    async def format_results(self, miner_result) -> str:
        miner_result['original_tags'] = miner_result['tags']
        # Clean and validate tags for duplicates or whitespace matches
        llml = get_llm_backend()
        miner_result['tags'] = llml.validate_tag_set(miner_result['original_tags'])
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

    def _split_conversation_in_windows(self) -> None:
        minLines = c.get("convo_window", "min_lines", 2)
        maxLines = c.get("convo_window", "max_lines", 10)
        overlapLines = c.get("convo_window", "overlap_lines", 2)

        window_size = maxLines
        windows = Utils.split_overlap_array(self.input.data.lines, size=maxLines, overlap=overlapLines)
        if len(windows) < 2:
            window_size = minLines
            windows = Utils.split_overlap_array(self.input.data.lines, size=minLines, overlap=overlapLines)

        # Windows i and i+g share no lines when g * step >= size.
        step = window_size - overlapLines
        self._window_min_gap = math.ceil(window_size / step) if step > 0 else 1

        # TODO: Write convo windows into local database with full convo metadata
        indexed_windows = []

        for idx, window in enumerate(windows):
            indexed_windows.append((idx, window))

        self.input.data.indexed_windows = indexed_windows

    def _enforce_minimum_convo_windows(self) -> None:
        minimum_convo_windows = c.get("convo_window", "min_convo_windows_floor", 3)
        if self.input.data.min_convo_windows is not None and self.input.data.min_convo_windows > minimum_convo_windows:
            bt.logging.info(f"Change in minimum required convo windows from API from {minimum_convo_windows} to {self.input.data.min_convo_windows}.")
            minimum_convo_windows = self.input.data.min_convo_windows

        if len(self.input.data.indexed_windows) <= minimum_convo_windows:
            bt.logging.info(f"Not enough convo windows -- only {len(self.input.data.indexed_windows)}. Passing.")
            self.input.data.indexed_windows = []

    async def _generate_metadata(self) -> None:
        bt.logging.info(f"Generating metadata")
        llml = get_llm_backend()
        conversation = Conversation(
            guid=self.input.guid,
            lines=self.input.data.lines,
            participants=self.input.data.participants,
            miner_task_prompt=self.input.data.prompt,
            input_categories=self.input.input_categories
        )
        conversation_metadata: RawMetadata = llml.conversation_to_metadata(conversation=conversation, generateEmbeddings=False)

        if not conversation_metadata:
            bt.logging.error(f"ERROR:2873226353. No conversation metadata returned. Aborting.")
            return

        if not conversation_metadata.success:
            bt.logging.error(f"ERROR:2873226354. Conversation metadata failed: {conversation_metadata}. Aborting.")
            return

        all_tags = [conversation_metadata.tags]
        enrichment_lines = self._build_enrichment_lines_and_tags(llml=llml, all_tags=all_tags)
        self.input.data.enrichment_lines = enrichment_lines

        if len(all_tags) > 1:
            result: RawMetadata = llml.combine_metadata_tags(all_tags, generateEmbeddings=True)
            if not result or not result.success:
                bt.logging.error(f"ERROR:2873226355. Combined conversation+enrichment metadata failed. Aborting.")
                return
        else:
            result = RawMetadata(
                tags=conversation_metadata.tags,
                vectors=llml.get_vector_embeddings_set(conversation_metadata.tags),
                success=True,
            )

        self.input.metadata = ConversationMetadata(
            participantProfiles=self.input.data.participants,
            tags=getattr(result, "tags", []),
            vectors=getattr(result, "vectors", {}),
        )

    def _build_enrichment_lines_and_tags(self, llml: LlmLib, all_tags: List[List[str]]) -> List[Tuple[int, str]]:
        enrichment_lines: List[Tuple[int, str]] = []
        enrichment = self.input.data.enrichment
        if not enrichment or not enrichment.search_results:
            bt.logging.info(f"Generating non-enriched metadata for conversation")
            return enrichment_lines

        bt.logging.info(f"Generating enrichment metadata for conversation")
        for query, results in enrichment.search_results.items():
            if not results:
                continue
            num_to_select = random.randint(1, min(3, len(results)))
            selected_results = random.sample(results, num_to_select)

            for chosen_res in selected_results:
                snippet = chosen_res.snippet or ''
                title = chosen_res.title or ''
                enrichment_text = f"{title}\n{snippet}"[:1000]

                if not enrichment_text.strip():
                    continue

                enrichment_lines.append((len(enrichment_lines), enrichment_text))
                enrichment_metadata = llml.enrichment_to_metadata(
                    enrichment_text, input_categories=self.input.input_categories
                )
                if enrichment_metadata and enrichment_metadata.tags:
                    all_tags.append(enrichment_metadata.tags)

        return enrichment_lines

    async def _get_vector_embeddings_set(self, llml: LlmLib, tags):
        return llml.get_vector_embeddings_set(tags)
