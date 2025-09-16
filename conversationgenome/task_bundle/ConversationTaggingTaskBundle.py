import random
import uuid
from typing import List, Literal, Optional, Tuple

import bittensor as bt
from pydantic import BaseModel

from conversationgenome.api.models.conversation import Conversation
from conversationgenome.api.models.conversation_metadata import ConversationMetadata
from conversationgenome.api.models.raw_metadata import RawMetadata
from conversationgenome.ConfigLib import c
from conversationgenome.llm.LlmLib import LlmLib
from conversationgenome.scoring_mechanism.GroundTruthTagSimilarityScoringMechanism import GroundTruthTagSimilarityScoringMechanism
from conversationgenome.task.ConversationTaggingTask import ConversationTaggingTask, ConversationTaskInput, ConversationTaskInputData
from conversationgenome.task.Task import Task
from conversationgenome.task_bundle.TaskBundle import TaskBundle
from conversationgenome.utils.types import ForceStr
from conversationgenome.utils.Utils import Utils


class ConversationInputData(BaseModel):
    participants: List[str]
    lines: List[Tuple[int, str]]
    total: int
    min_convo_windows: int = 1
    indexed_windows: Optional[List[Tuple[int, List[Tuple[int, str]]]]] = None
    prompt: str = (
        "Analyze conversation in terms of topic interests of the participants. Analyze the conversation (provided in structured XML format) where <p0> has the questions and <p1> has the answers. Return comma-delimited tags. Only return the tags without any English commentary."
    )


class ConversationInput(BaseModel):
    input_type: Literal["conversation"]
    guid: ForceStr
    data: ConversationInputData
    metadata: Optional[ConversationMetadata] = None

    def trim_input(self) -> None:
        max_lines = Utils._int(c.get('env', 'MAX_CONVO_LINES', 300))

        if max_lines and len(self.data.lines) > max_lines:
            self.data.lines = self.data.lines[:max_lines]
            self.data.total = len(self.data.lines)


class ConversationTaggingTaskBundle(TaskBundle):
    type: Literal["conversation_tagging"] = "conversation_tagging"
    input: Optional[ConversationInput] = None

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
            task: ConversationTaggingTask = ConversationTaggingTask(
                mode=self.mode,
                api_version=self.api_version,
                guid=random_id,
                bundle_guid=self.guid,
                type=self.type,
                scoring_mechanism=self.scoring_mechanism,
                input=ConversationTaskInput(
                    input_type=self.input.input_type,
                    data=ConversationTaskInputData(
                        min_convo_windows=self.input.data.min_convo_windows,
                        participants=self.input.data.participants,
                        window_idx=indexed_window[0],
                        window=indexed_window[1],
                        prompt=self.input.data.prompt,
                    ),
                ),
                prompt_chain=self.prompt_chain,
                example_output=self.example_output,
            )
            tasks.append(task)

        return tasks

    async def format_results(self, miner_result) -> str:
        miner_result['original_tags'] = miner_result['tags']

        # Clean and validate tags for duplicates or whitespace matches
        llml = LlmLib()

        miner_result['tags'] = await Utils.validate_tag_set(llml=llml, tags=miner_result['original_tags'])
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
        bt.logging.info(f"Execute generating metadata for conversation")

        llml = LlmLib()

        conversation = Conversation(
            guid=self.input.guid,
            lines=self.input.data.lines,
            participants=self.input.data.participants,
            miner_task_prompt=self.input.data.prompt,
        )

        result: RawMetadata = await llml.conversation_to_metadata(conversation=conversation, generateEmbeddings=True)

        if not result:
            bt.logging.error(f"ERROR:2873226353. No conversation metadata returned. Aborting.")
            return None

        if not result.success:
            bt.logging.error(f"ERROR:2873226354. Conversation metadata failed: {result}. Aborting.")
            return None

        self.input.metadata = ConversationMetadata(
            participantProfiles=self.input.data.participants,
            tags=getattr(result, "tags", []),
            vectors=getattr(result, "vectors", {}),
        )

    async def _get_vector_embeddings_set(self, llml: LlmLib, tags):
        response = await llml.get_vector_embeddings_set(tags)
        return response
