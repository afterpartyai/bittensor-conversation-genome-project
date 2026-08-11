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

    async def mine(self) -> dict:
        llml = get_llm_backend()

        try:
            seed = self.input.data.seed
            section_map = self.input.data.section_map

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
