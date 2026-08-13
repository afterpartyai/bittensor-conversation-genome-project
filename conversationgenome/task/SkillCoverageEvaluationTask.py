from typing import ClassVar
from typing import List
from typing import Literal
from typing import Optional

import bittensor as bt
from pydantic import BaseModel

from conversationgenome.api.models.skill_coverage import SectionMapEntry
from conversationgenome.llm.llm_factory import get_llm_backend
from conversationgenome.task.Task import Task


class SkillCoverageTaskInputData(BaseModel):
    seed: str
    section_map: List[SectionMapEntry]


class SkillCoverageTaskInput(BaseModel):
    guid: str
    input_type: Literal["skill_coverage"] = "skill_coverage"
    data: SkillCoverageTaskInputData
    input_categories: Optional[List[str]] = None


class SkillCoverageEvaluationTask(Task):
    type: Literal["skill_coverage_evaluation"] = "skill_coverage_evaluation"
    input: Optional[SkillCoverageTaskInput] = None

    # Switch between the two mining paths below. True (default) runs a single
    # combined call (LlmLib.skill_request_to_skill_bundle) instead of the full
    # 3-step chain -- roughly 3x fewer round trips, tuned further via the
    # model/reasoning_effort/service_tier overrides in LlmOpenAI, and brought
    # back to full judge-pass quality by the traceability requirement added to
    # the generation prompts (tests may only reference identifiers the skill
    # itself defines). False runs the original 3-step chain (skill -> TDD plan
    # -> section tests), which lets the model reason over its own already-
    # fixed skill/plan before writing tests -- still the slower path, kept
    # around as a fallback rather than the default.
    FAST_MODE: ClassVar[bool] = True

    async def mine(self) -> dict:
        llml = get_llm_backend()

        try:
            seed = self.input.data.seed
            section_map = self.input.data.section_map

            if self.FAST_MODE:
                return self._mine_fast(llml, seed, section_map)

            # Step 1: author the skill itself from the request + validator section map
            skill = llml.skill_request_to_skill(seed, section_map)
            if not skill:
                return {"skill": "", "tdd_plan": "", "section_tests": {}}

            # Step 2: derive an overall TDD plan from the generated skill
            tdd_plan = llml.skill_to_tdd_plan(skill, section_map)
            if not tdd_plan:
                return {"skill": skill, "tdd_plan": "", "section_tests": {}}

            # Step 3: derive per-section TDD test methods/descriptions
            section_tests_result = llml.skill_to_section_tests(skill, tdd_plan, section_map)
            section_tests = {}
            if section_tests_result and section_tests_result.section_tests:
                section_tests = {
                    section_id: [test.model_dump() for test in tests]
                    for section_id, tests in section_tests_result.section_tests.items()
                }

            output = {"skill": skill, "tdd_plan": tdd_plan, "section_tests": section_tests}
        except Exception as e:
            bt.logging.error(f"Error during mining: {e}")
            raise e

        return output

    def _mine_fast(self, llml, seed, section_map) -> dict:
        bundle = llml.skill_request_to_skill_bundle(seed, section_map)
        if not bundle:
            return {"skill": "", "tdd_plan": "", "section_tests": {}}

        return {
            "skill": bundle.skill,
            "tdd_plan": bundle.tdd_plan,
            "section_tests": {
                section_id: [test.model_dump() for test in tests]
                for section_id, tests in bundle.section_tests.items()
            },
        }
