from unittest.mock import MagicMock, Mock
from unittest.mock import patch

import pytest

from conversationgenome.api.models.skill_coverage import SectionMapEntry, SectionTestCase, SectionTestsResult, SkillBundleResult
from conversationgenome.prompt_chain.PromptChainStep import PromptChainStep
from conversationgenome.task.SkillCoverageEvaluationTask import (
    SkillCoverageEvaluationTask,
    SkillCoverageTaskInput,
    SkillCoverageTaskInputData,
)


def _section_map():
    return [
        SectionMapEntry(section_id="s1", title="Basic transformation", description="Lowercase and hyphenate."),
        SectionMapEntry(section_id="s2", title="Edge cases", description="Handle empty input."),
    ]


def _make_task(seed="Skill for slugifying text.", section_map=None):
    return SkillCoverageEvaluationTask(
        mode="local",
        api_version=1.4,
        guid="test-guid",
        bundle_guid="bundle-guid",
        type="skill_coverage_evaluation",
        input=SkillCoverageTaskInput(
            guid="input-guid",
            input_type="skill_coverage",
            data=SkillCoverageTaskInputData(
                seed=seed,
                section_map=section_map if section_map is not None else _section_map(),
            ),
        ),
        prompt_chain=[PromptChainStep(
            step=0,
            id="skill_coverage_001",
            crc=12345,
            title="Generate skill and tests",
            name="generate_skill_with_section_tests",
            description="Generates a skill, TDD plan, and per-section tests",
            type="inference",
            input_path="skill_coverage",
            prompt_template="Generate the skill and tests",
            output_variable="final_output",
            output_type="dict"
        )]
    )


@pytest.mark.asyncio
async def test_mine_returns_skill_plan_and_section_tests(monkeypatch):
    monkeypatch.setattr(SkillCoverageEvaluationTask, "FAST_MODE", False)
    task = _make_task()

    mock_llml = MagicMock()
    mock_llml.skill_request_to_skill = Mock(return_value="# Slugify Text\n\nSteps...")
    mock_llml.skill_to_tdd_plan = Mock(return_value="Verify each stage independently.")
    mock_llml.skill_to_section_tests = Mock(return_value=SectionTestsResult(
        section_tests={
            "s1": [SectionTestCase(name="test_lowercases", description="slugify lowercases input", assertion="slugify('Hello World') == 'hello-world'")],
            "s2": [SectionTestCase(name="test_empty_input", description="slugify handles empty input", assertion="slugify('') == 'n-a'")],
        },
        success=True,
    ))

    with patch("conversationgenome.task.SkillCoverageEvaluationTask.get_llm_backend", return_value=mock_llml):
        result = await task.mine()

    assert result["skill"] == "# Slugify Text\n\nSteps..."
    assert result["tdd_plan"] == "Verify each stage independently."
    assert result["section_tests"]["s1"] == [{"name": "test_lowercases", "description": "slugify lowercases input", "assertion": "slugify('Hello World') == 'hello-world'"}]
    assert result["section_tests"]["s2"] == [{"name": "test_empty_input", "description": "slugify handles empty input", "assertion": "slugify('') == 'n-a'"}]

    mock_llml.skill_request_to_skill.assert_called_once_with(task.input.data.seed, task.input.data.section_map)
    mock_llml.skill_to_tdd_plan.assert_called_once_with("# Slugify Text\n\nSteps...", task.input.data.section_map)
    mock_llml.skill_to_section_tests.assert_called_once_with(
        "# Slugify Text\n\nSteps...", "Verify each stage independently.", task.input.data.section_map
    )


@pytest.mark.asyncio
async def test_mine_handles_no_skill_returned(monkeypatch):
    monkeypatch.setattr(SkillCoverageEvaluationTask, "FAST_MODE", False)
    task = _make_task()
    mock_llml = MagicMock()
    mock_llml.skill_request_to_skill = Mock(return_value=None)

    with patch("conversationgenome.task.SkillCoverageEvaluationTask.get_llm_backend", return_value=mock_llml):
        result = await task.mine()

    assert result == {"skill": "", "tdd_plan": "", "section_tests": {}}
    mock_llml.skill_to_tdd_plan.assert_not_called()
    mock_llml.skill_to_section_tests.assert_not_called()


@pytest.mark.asyncio
async def test_mine_handles_no_tdd_plan_returned(monkeypatch):
    monkeypatch.setattr(SkillCoverageEvaluationTask, "FAST_MODE", False)
    task = _make_task()
    mock_llml = MagicMock()
    mock_llml.skill_request_to_skill = Mock(return_value="# Slugify Text")
    mock_llml.skill_to_tdd_plan = Mock(return_value=None)

    with patch("conversationgenome.task.SkillCoverageEvaluationTask.get_llm_backend", return_value=mock_llml):
        result = await task.mine()

    assert result == {"skill": "# Slugify Text", "tdd_plan": "", "section_tests": {}}
    mock_llml.skill_to_section_tests.assert_not_called()


@pytest.mark.asyncio
async def test_mine_handles_no_section_tests_returned(monkeypatch):
    monkeypatch.setattr(SkillCoverageEvaluationTask, "FAST_MODE", False)
    task = _make_task()
    mock_llml = MagicMock()
    mock_llml.skill_request_to_skill = Mock(return_value="# Slugify Text")
    mock_llml.skill_to_tdd_plan = Mock(return_value="Plan text")
    mock_llml.skill_to_section_tests = Mock(return_value=None)

    with patch("conversationgenome.task.SkillCoverageEvaluationTask.get_llm_backend", return_value=mock_llml):
        result = await task.mine()

    assert result == {"skill": "# Slugify Text", "tdd_plan": "Plan text", "section_tests": {}}


@pytest.mark.asyncio
async def test_mine_raises_on_llm_exception(monkeypatch):
    monkeypatch.setattr(SkillCoverageEvaluationTask, "FAST_MODE", False)
    task = _make_task()
    mock_llml = MagicMock()
    mock_llml.skill_request_to_skill = Mock(side_effect=Exception("LLM Error"))

    with patch("conversationgenome.task.SkillCoverageEvaluationTask.get_llm_backend", return_value=mock_llml):
        with pytest.raises(Exception, match="LLM Error"):
            await task.mine()


@pytest.mark.asyncio
async def test_mine_fast_mode_returns_skill_plan_and_section_tests(monkeypatch):
    monkeypatch.setattr(SkillCoverageEvaluationTask, "FAST_MODE", True)
    task = _make_task()

    mock_llml = MagicMock()
    mock_llml.skill_request_to_skill_bundle = Mock(return_value=SkillBundleResult(
        skill="# Slugify Text\n\nSteps...",
        tdd_plan="Verify each stage independently.",
        section_tests={
            "s1": [SectionTestCase(name="test_lowercases", description="slugify lowercases input", assertion="slugify('Hello World') == 'hello-world'")],
            "s2": [SectionTestCase(name="test_empty_input", description="slugify handles empty input", assertion="slugify('') == 'n-a'")],
        },
        success=True,
    ))

    with patch("conversationgenome.task.SkillCoverageEvaluationTask.get_llm_backend", return_value=mock_llml):
        result = await task.mine()

    assert result["skill"] == "# Slugify Text\n\nSteps..."
    assert result["tdd_plan"] == "Verify each stage independently."
    assert result["section_tests"]["s1"] == [{"name": "test_lowercases", "description": "slugify lowercases input", "assertion": "slugify('Hello World') == 'hello-world'"}]
    assert result["section_tests"]["s2"] == [{"name": "test_empty_input", "description": "slugify handles empty input", "assertion": "slugify('') == 'n-a'"}]

    mock_llml.skill_request_to_skill_bundle.assert_called_once_with(task.input.data.seed, task.input.data.section_map)
    mock_llml.skill_request_to_skill.assert_not_called()
    mock_llml.skill_to_tdd_plan.assert_not_called()
    mock_llml.skill_to_section_tests.assert_not_called()


@pytest.mark.asyncio
async def test_mine_fast_mode_handles_no_bundle_returned(monkeypatch):
    monkeypatch.setattr(SkillCoverageEvaluationTask, "FAST_MODE", True)
    task = _make_task()

    mock_llml = MagicMock()
    mock_llml.skill_request_to_skill_bundle = Mock(return_value=None)

    with patch("conversationgenome.task.SkillCoverageEvaluationTask.get_llm_backend", return_value=mock_llml):
        result = await task.mine()

    assert result == {"skill": "", "tdd_plan": "", "section_tests": {}}


def test_fast_mode_defaults_to_true():
    assert SkillCoverageEvaluationTask.FAST_MODE is True
