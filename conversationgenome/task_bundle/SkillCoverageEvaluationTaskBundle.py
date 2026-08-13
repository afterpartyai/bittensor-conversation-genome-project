import json
import random
import uuid
from typing import List
from typing import Literal
from typing import Optional
from typing import Tuple

import bittensor as bt
from pydantic import BaseModel

from conversationgenome.api.models.skill_coverage import SectionMapEntry
from conversationgenome.api.models.skill_coverage import SkillCoverageMetadata
from conversationgenome.llm.llm_factory import get_llm_backend
from conversationgenome.scoring_mechanism.SkillCoverageScoringMechanism import (
    SkillCoverageScoringMechanism,
)
from conversationgenome.task.Task import Task
from conversationgenome.task.SkillCoverageEvaluationTask import (
    SkillCoverageEvaluationTask,
)
from conversationgenome.task.SkillCoverageEvaluationTask import (
    SkillCoverageTaskInput,
)
from conversationgenome.task.SkillCoverageEvaluationTask import (
    SkillCoverageTaskInputData,
)
from conversationgenome.task_bundle.TaskBundle import TaskBundle
from conversationgenome.utils.constants import PENALTIES
from conversationgenome.utils.types import ForceStr

# Hard per-section cap on how many submitted tests are embedded, judged, and
# eligible to count towards scoring at all -- shared with PENALTIES["test_flooding"]
# so the cap that saves embedding/judge cost and the threshold that flags a
# section as "flooded" for scoring purposes never drift apart. Tests beyond this,
# per section, are neither embedded nor judged: they get vector=None and
# judged_correct=False, so submitting more than the cap buys nothing, and the
# scoring layer can still see (and penalize) that a section was flooded.
PER_SECTION_TEST_CAP = PENALTIES["test_flooding"]["threshold"]

# Backstop on total tests judged across an entire response (sum over sections),
# on top of the per-section cap -- bounds judge-call cost for skills with an
# unusually large number of sections.
MAX_JUDGED_TESTS = 20

# At most this many sections are actually scored per bundle, chosen at random
# once in _generate_section_map() -- the same subset for every miner mining
# this bundle. Miners still receive the full section map and don't know which
# sections were sampled, so the incentive to cover everything is unchanged;
# this only cuts how much ground-truth embedding and per-response judging/
# embedding work the validator pays for.
MAX_EVALUATED_SECTIONS = 3


class SkillCoverageInputData(BaseModel):
    # Raw envelope as returned by the conversation API: lines[0][1] is a JSON
    # string containing at minimum {"seed": "<skill request>"}.
    lines: List[Tuple[int, str]]

    total: int
    participants: List[str]
    seed: Optional[str] = None
    section_map: Optional[List[SectionMapEntry]] = None


class SkillCoverageInput(BaseModel):
    input_type: Literal["skill_coverage"] = "skill_coverage"
    guid: ForceStr
    data: SkillCoverageInputData
    input_categories: Optional[List[str]] = None
    metadata: Optional[SkillCoverageMetadata] = None


class SkillCoverageEvaluationTaskBundle(TaskBundle):
    type: Literal["skill_coverage_evaluation"] = "skill_coverage_evaluation"
    input: Optional[SkillCoverageInput] = None

    def is_ready(self) -> bool:
        if self.input.metadata is not None and self.input.data.section_map is not None:
            return True
        return False

    async def setup(self) -> None:
        await self._generate_section_map()

    def to_mining_tasks(self, number_of_tasks_per_bundle: int) -> List[Task]:
        tasks = []
        for _ in range(number_of_tasks_per_bundle):
            random_id = str(uuid.uuid4())
            task: SkillCoverageEvaluationTask = SkillCoverageEvaluationTask(
                mode=self.mode,
                api_version=self.api_version,
                guid=random_id,
                bundle_guid=self.guid,
                type=self.type,
                scoring_mechanism=self.scoring_mechanism,
                input=SkillCoverageTaskInput(
                    guid=self.input.guid,
                    input_type=self.input.input_type,
                    data=SkillCoverageTaskInputData(
                        seed=self.input.data.seed,
                        section_map=self.input.data.section_map,
                    ),
                    input_categories=self.input.input_categories,
                ),
                prompt_chain=self.prompt_chain,
                example_output=self.example_output,
            )
            tasks.append(task)

        return tasks

    def generate_result_logs(self, miner_result) -> str:
        section_tests = miner_result.get('section_tests', {}) if isinstance(miner_result, dict) else {}
        section_tests = section_tests or {}
        total_tests = sum(len(tests) for tests in section_tests.values())
        skill_len = len(miner_result.get('skill', '') or '') if isinstance(miner_result, dict) else 0
        return f"sections addressed: {len(section_tests)} " f"total tests: {total_tests} " f"skill length: {skill_len}"

    async def format_results(self, miner_result) -> dict:
        llml = get_llm_backend()

        # Only the sections actually sampled for evaluation (see
        # _generate_section_map) can affect the score -- both scoring signals
        # are driven entirely by section_vectors -- so tests submitted for any
        # other section are dropped here before doing any embedding/judging
        # work. `miner_result["section_tests"]` itself is left untouched, so
        # generate_result_logs() still reports the miner's true full submission.
        evaluated_section_ids = set(self.input.metadata.section_vectors.keys())
        evaluated_section_map = [section for section in self.input.data.section_map if section.section_id in evaluated_section_ids]

        skill_text = miner_result.get('skill', '') or ''

        raw_section_tests = miner_result.get('section_tests', {}) or {}
        section_tests = {section_id: tests for section_id, tests in raw_section_tests.items() if section_id in evaluated_section_ids}

        # Per-section cap applied once, up front: everything downstream (judging,
        # embedding) only ever sees the first PER_SECTION_TEST_CAP tests of each
        # section. Tests beyond it are cheap to represent (no LLM/embedding call)
        # and stay visible to scoring as flooding evidence, just with no vector
        # and no verdict -- see _score_sections/_calculate_penalty.
        eligible_tests = {
            section_id: tests[:PER_SECTION_TEST_CAP]
            for section_id, tests in section_tests.items()
        }
        verdict_map = self._judge_section_tests(llml, skill_text, eligible_tests, evaluated_section_map)

        # Collect every embedding we need (skill text + each eligible test's
        # description+assertion) and fetch them all in one batched call instead
        # of one round trip per item.
        embedding_slots = []  # ("skill", None, None) or ("test", section_id, idx)
        embedding_texts = []
        if skill_text.strip():
            embedding_slots.append(("skill", None, None))
            embedding_texts.append(skill_text)

        for section_id, tests in section_tests.items():
            for idx, test in enumerate(tests):
                if idx >= PER_SECTION_TEST_CAP:
                    continue
                description = test.get('description', '') if isinstance(test, dict) else ''
                assertion = test.get('assertion', '') if isinstance(test, dict) else ''
                # The assertion -- not the prose description -- is what should
                # separate miners: a vague description ("handles unicode input
                # correctly") looks the same for every miner once embedded, but
                # a concrete assertion ("slugify('Café') == 'cafe'") only embeds
                # close to a section's ground-truth vector if it actually
                # addresses that section. Embedding both keeps the intent
                # (description) and the concrete check (assertion) together.
                embedding_text = f"{description}\nAssertion: {assertion}".strip() if assertion.strip() else description
                if embedding_text.strip():
                    embedding_slots.append(("test", section_id, idx))
                    embedding_texts.append(embedding_text)

        vectors = llml.get_vector_embeddings_batch(embedding_texts) if embedding_texts else []

        skill_vector = None
        test_vector_lookup = {}
        for (kind, section_id, idx), vector in zip(embedding_slots, vectors):
            if kind == "skill":
                skill_vector = vector
            else:
                test_vector_lookup[(section_id, idx)] = vector
        miner_result['skill_vector'] = skill_vector

        test_vectors = {}
        for section_id, tests in section_tests.items():
            section_test_vectors = []
            for idx, test in enumerate(tests):
                name = test.get('name') if isinstance(test, dict) else None
                description = test.get('description', '') if isinstance(test, dict) else ''
                assertion = test.get('assertion', '') if isinstance(test, dict) else ''
                if idx >= PER_SECTION_TEST_CAP:
                    section_test_vectors.append({
                        "name": name, "description": description, "assertion": assertion,
                        "vector": None, "judged_correct": False,
                    })
                    continue
                section_test_vectors.append({
                    "name": name,
                    "description": description,
                    "assertion": assertion,
                    "vector": test_vector_lookup.get((section_id, idx)),
                    "judged_correct": verdict_map.get((section_id, name), False),
                })
            test_vectors[section_id] = section_test_vectors
        miner_result['test_vectors'] = test_vectors

        return miner_result

    def _judge_section_tests(self, llml, skill_text: str, section_tests: dict, section_map: List[SectionMapEntry]) -> dict:
        """
        Runs the LLM-as-judge correctness pass and returns {(section_id, name): bool}.

        `section_tests` is expected to already be capped to PER_SECTION_TEST_CAP
        per section by the caller, and scoped to only the sections actually
        being evaluated this round. Every test in it is judged, batched into a
        single LLM call, up to MAX_JUDGED_TESTS total as a further backstop for
        skills with many sections (tests past that backstop default to False via
        the .get() fallback in format_results -- unverified gets no credit, same
        as verified-wrong). If the judge call itself fails (LLM/parsing error),
        we fail OPEN -- trust all tests as before this feature existed -- rather
        than zeroing every miner's score during an infra outage.
        """
        if not section_tests or not skill_text.strip():
            return {}

        capped = {}
        remaining = MAX_JUDGED_TESTS
        for section_id, tests in section_tests.items():
            if remaining <= 0:
                break
            take = tests[:remaining]
            if take:
                capped[section_id] = take
            remaining -= len(take)

        if not capped:
            return {}

        judge_result = llml.judge_section_tests(skill_text, section_map, capped)
        if not judge_result:
            bt.logging.error("ERROR:9384723. Assertion judge call failed. Skipping correctness verification for this response.")
            return {
                (section_id, test.get('name') if isinstance(test, dict) else None): True
                for section_id, tests in section_tests.items()
                for test in tests
            }

        return {
            (section_id, verdict.name): verdict.correct
            for section_id, verdicts in judge_result.verdicts.items()
            for verdict in verdicts
        }

    async def evaluate(self, miner_responses):
        evaluator = SkillCoverageScoringMechanism()
        return await evaluator.evaluate(self, miner_responses)

    async def _generate_section_map(self) -> None:
        bt.logging.info(f"Generating section map for skill coverage evaluation")
        parsed_json = json.loads(self.input.data.lines[0][1])
        seed = parsed_json['seed']
        llml = get_llm_backend()

        result = llml.skill_request_to_section_map(seed)

        if not result:
            bt.logging.error(f"ERROR:9384721. No section map returned. Aborting.")
            return

        if not result.success or not result.sections:
            bt.logging.error(f"ERROR:9384722. Section map failed: {result}. Aborting.")
            return

        # Score at most MAX_EVALUATED_SECTIONS sections, chosen at random once
        # here -- the same subset for every miner mining this bundle, since
        # to_mining_tasks() copies the same section_map/metadata to every task.
        evaluated_sections = random.sample(result.sections, min(MAX_EVALUATED_SECTIONS, len(result.sections)))

        section_texts = [f"{section.title}: {section.description}" for section in evaluated_sections]
        vectors = llml.get_vector_embeddings_batch(section_texts) if section_texts else []
        section_vectors = {
            section.section_id: (vector or [])
            for section, vector in zip(evaluated_sections, vectors)
        }

        self.input.data.seed = seed
        self.input.data.section_map = result.sections
        self.input.metadata = SkillCoverageMetadata(sections=result.sections, section_vectors=section_vectors)
