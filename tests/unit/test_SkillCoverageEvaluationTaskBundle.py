from unittest.mock import AsyncMock, Mock
from unittest.mock import patch
import json
import pytest

from conversationgenome.api.models.skill_coverage import AssertionJudgeResult, AssertionVerdict, SectionMapEntry, SectionMapResult
from conversationgenome.task_bundle.SkillCoverageEvaluationTaskBundle import PER_SECTION_TEST_CAP, SkillCoverageEvaluationTaskBundle
from tests.mocks.DummyData import DummyData


def test_is_ready_false_when_no_metadata():
    bundle = DummyData.skill_coverage_evaluation_task_bundle()
    bundle.input.metadata = None
    assert not bundle.is_ready()


def test_is_ready_false_when_no_section_map():
    bundle = DummyData.skill_coverage_evaluation_task_bundle()
    bundle.input.data.section_map = None
    assert not bundle.is_ready()


def test_is_ready_true_when_metadata_and_section_map():
    bundle = DummyData.setup_skill_coverage_evaluation_task_bundle()
    assert bundle.is_ready()


def test_to_mining_tasks_creates_tasks():
    bundle = DummyData.setup_skill_coverage_evaluation_task_bundle()
    tasks = bundle.to_mining_tasks(2)
    assert len(tasks) == 2
    for task in tasks:
        assert task.type == "skill_coverage_evaluation"
        assert task.bundle_guid == bundle.guid
        assert task.input.input_type == "skill_coverage"
        assert task.input.data.seed == bundle.input.data.seed
        assert task.input.data.section_map == bundle.input.data.section_map


def test_generate_result_logs_counts_sections_and_tests():
    bundle = DummyData.setup_skill_coverage_evaluation_task_bundle()
    miner_result = {
        "skill": "# Skill",
        "section_tests": {"s1": [{"name": "t1", "description": "d1"}], "s2": [{"name": "t2", "description": "d2"}, {"name": "t3", "description": "d3"}]},
    }
    log = bundle.generate_result_logs(miner_result)
    assert "sections addressed: 2" in log
    assert "total tests: 3" in log
    assert "skill length: 7" in log


@pytest.mark.asyncio
async def test_format_results_embeds_skill_and_test_descriptions():
    bundle = DummyData.setup_skill_coverage_evaluation_task_bundle()
    miner_result = {
        "skill": "# Skill markdown",
        "tdd_plan": "Plan",
        "section_tests": {"s1": [{"name": "t1", "description": "d1", "assertion": "slugify('A') == 'a'"}]},
    }
    with patch('conversationgenome.task_bundle.SkillCoverageEvaluationTaskBundle.get_llm_backend') as mock_llm_factory:
        mock_llm = Mock()
        mock_llm.get_vector_embeddings = Mock(side_effect=lambda text: [0.1] if text == "# Skill markdown" else [0.2])
        mock_llm.judge_section_tests = Mock(return_value=AssertionJudgeResult(
            verdicts={"s1": [AssertionVerdict(name="t1", correct=True, reason="matches")]},
            success=True,
        ))
        mock_llm_factory.return_value = mock_llm

        result = await bundle.format_results(miner_result)

    assert result["skill_vector"] == [0.1]
    assert result["test_vectors"]["s1"] == [
        {"name": "t1", "description": "d1", "assertion": "slugify('A') == 'a'", "vector": [0.2], "judged_correct": True}
    ]
    # the embedded text combines description + assertion, not description alone
    mock_llm.get_vector_embeddings.assert_any_call("d1\nAssertion: slugify('A') == 'a'")
    mock_llm.judge_section_tests.assert_called_once_with(
        "# Skill markdown", bundle.input.data.section_map, {"s1": [{"name": "t1", "description": "d1", "assertion": "slugify('A') == 'a'"}]}
    )


@pytest.mark.asyncio
async def test_format_results_marks_unjudged_tests_incorrect():
    bundle = DummyData.setup_skill_coverage_evaluation_task_bundle()
    miner_result = {
        "skill": "# Skill markdown",
        "tdd_plan": "Plan",
        "section_tests": {"s1": [
            {"name": "t1", "description": "d1", "assertion": "slugify('A') == 'a'"},
            {"name": "t2", "description": "d2", "assertion": "the function works correctly"},
        ]},
    }
    with patch('conversationgenome.task_bundle.SkillCoverageEvaluationTaskBundle.get_llm_backend') as mock_llm_factory:
        mock_llm = Mock()
        mock_llm.get_vector_embeddings = Mock(return_value=[0.1])
        # Judge only returns a verdict for t1 -- t2 is omitted (simulating a
        # dropped/incomplete judge response) and must default to not-correct.
        mock_llm.judge_section_tests = Mock(return_value=AssertionJudgeResult(
            verdicts={"s1": [AssertionVerdict(name="t1", correct=True, reason="matches")]},
            success=True,
        ))
        mock_llm_factory.return_value = mock_llm

        result = await bundle.format_results(miner_result)

    tests_by_name = {t["name"]: t for t in result["test_vectors"]["s1"]}
    assert tests_by_name["t1"]["judged_correct"] is True
    assert tests_by_name["t2"]["judged_correct"] is False


@pytest.mark.asyncio
async def test_format_results_caps_tests_per_section():
    bundle = DummyData.setup_skill_coverage_evaluation_task_bundle()
    # One more test than the cap allows, in a single section.
    tests = [{"name": f"t{i}", "description": f"d{i}", "assertion": f"a{i}"} for i in range(PER_SECTION_TEST_CAP + 1)]
    miner_result = {"skill": "# Skill markdown", "tdd_plan": "Plan", "section_tests": {"s1": tests}}

    with patch('conversationgenome.task_bundle.SkillCoverageEvaluationTaskBundle.get_llm_backend') as mock_llm_factory:
        mock_llm = Mock()
        mock_llm.get_vector_embeddings = Mock(return_value=[0.1])
        # Judge should only ever be asked about the capped set (PER_SECTION_TEST_CAP tests).
        mock_llm.judge_section_tests = Mock(return_value=AssertionJudgeResult(
            verdicts={"s1": [AssertionVerdict(name=f"t{i}", correct=True, reason="ok") for i in range(PER_SECTION_TEST_CAP)]},
            success=True,
        ))
        mock_llm_factory.return_value = mock_llm

        result = await bundle.format_results(miner_result)

    judge_call_tests = mock_llm.judge_section_tests.call_args.args[2]["s1"]
    assert len(judge_call_tests) == PER_SECTION_TEST_CAP

    section_tests = result["test_vectors"]["s1"]
    assert len(section_tests) == PER_SECTION_TEST_CAP + 1  # all submitted tests still represented
    # First PER_SECTION_TEST_CAP were embedded + judged.
    for test in section_tests[:PER_SECTION_TEST_CAP]:
        assert test["vector"] == [0.1]
        assert test["judged_correct"] is True
    # The overflow test past the cap got neither an embedding nor a verdict.
    overflow_test = section_tests[PER_SECTION_TEST_CAP]
    assert overflow_test["vector"] is None
    assert overflow_test["judged_correct"] is False


@pytest.mark.asyncio
async def test_format_results_fails_open_when_judge_call_errors():
    bundle = DummyData.setup_skill_coverage_evaluation_task_bundle()
    miner_result = {
        "skill": "# Skill markdown",
        "tdd_plan": "Plan",
        "section_tests": {"s1": [{"name": "t1", "description": "d1", "assertion": "slugify('A') == 'a'"}]},
    }
    with patch('conversationgenome.task_bundle.SkillCoverageEvaluationTaskBundle.get_llm_backend') as mock_llm_factory:
        mock_llm = Mock()
        mock_llm.get_vector_embeddings = Mock(return_value=[0.1])
        mock_llm.judge_section_tests = Mock(return_value=None)
        mock_llm_factory.return_value = mock_llm

        result = await bundle.format_results(miner_result)

    assert result["test_vectors"]["s1"][0]["judged_correct"] is True


@pytest.mark.asyncio
async def test_evaluate_calls_skill_coverage_scoring():
    bundle = DummyData.setup_skill_coverage_evaluation_task_bundle()
    with patch('conversationgenome.task_bundle.SkillCoverageEvaluationTaskBundle.SkillCoverageScoringMechanism') as mock_mech:
        mock_eval = AsyncMock(return_value="score")
        mock_mech.return_value.evaluate = mock_eval
        result = await bundle.evaluate(["response"])
    assert result == "score"


@pytest.mark.asyncio
async def test_generate_section_map_calls_llm_and_sets_metadata():
    bundle = DummyData.skill_coverage_evaluation_task_bundle()
    bundle.input.data.lines = [(0, json.dumps({"seed": "Skill for slugifying text."}))]

    with patch('conversationgenome.task_bundle.SkillCoverageEvaluationTaskBundle.get_llm_backend') as mock_llm_factory:
        mock_llm = Mock()
        mock_llm.skill_request_to_section_map.return_value = SectionMapResult(
            sections=[SectionMapEntry(section_id="s1", title="T1", description="D1")],
            success=True,
        )
        mock_llm.get_vector_embeddings.return_value = [0.1, 0.2]
        mock_llm_factory.return_value = mock_llm

        await bundle._generate_section_map()

        assert bundle.input.data.seed == "Skill for slugifying text."
        assert bundle.input.data.section_map == [SectionMapEntry(section_id="s1", title="T1", description="D1")]
        assert bundle.input.metadata.section_vectors == {"s1": [0.1, 0.2]}

        mock_llm.skill_request_to_section_map.assert_called_once_with("Skill for slugifying text.")


@pytest.mark.asyncio
async def test_generate_section_map_handles_no_result():
    bundle = DummyData.skill_coverage_evaluation_task_bundle()
    bundle.input.data.lines = [(0, json.dumps({"seed": "Skill for slugifying text."}))]
    bundle.input.metadata = None

    with patch('conversationgenome.task_bundle.SkillCoverageEvaluationTaskBundle.get_llm_backend') as mock_llm_factory:
        mock_llm = Mock()
        mock_llm.skill_request_to_section_map.return_value = None
        mock_llm_factory.return_value = mock_llm

        await bundle._generate_section_map()

        assert bundle.input.metadata is None


@pytest.mark.asyncio
async def test_generate_section_map_handles_failure():
    bundle = DummyData.skill_coverage_evaluation_task_bundle()
    bundle.input.data.lines = [(0, json.dumps({"seed": "Skill for slugifying text."}))]
    bundle.input.metadata = None

    with patch('conversationgenome.task_bundle.SkillCoverageEvaluationTaskBundle.get_llm_backend') as mock_llm_factory:
        mock_llm = Mock()
        mock_llm.skill_request_to_section_map.return_value = SectionMapResult(sections=[], success=False)
        mock_llm_factory.return_value = mock_llm

        await bundle._generate_section_map()

        assert bundle.input.metadata is None
