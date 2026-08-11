from typing import Dict, List

from pydantic import BaseModel


class SectionMapEntry(BaseModel):
    section_id: str
    title: str
    description: str


class SectionMapResult(BaseModel):
    sections: List[SectionMapEntry]
    success: bool


class SectionTestCase(BaseModel):
    name: str
    description: str
    assertion: str


class SectionTestsResult(BaseModel):
    section_tests: Dict[str, List[SectionTestCase]]
    success: bool


class SkillCoverageMetadata(BaseModel):
    sections: List[SectionMapEntry]
    section_vectors: Dict[str, List[float]]


class AssertionVerdict(BaseModel):
    name: str
    correct: bool
    reason: str = ""


class AssertionJudgeResult(BaseModel):
    verdicts: Dict[str, List[AssertionVerdict]]
    success: bool
