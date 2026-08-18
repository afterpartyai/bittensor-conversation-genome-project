from typing import Literal

TaskType = Literal["conversation_tagging", "webpage_metadata_generation", "survey_tagging", "skill_generation", "skill_coverage_evaluation"]
ScoringMechanismType = Literal["ground_truth_tag_similarity_scoring", "skill_coverage_scoring"]
PENALTIES = {
    "no_both_tags": {
        "penalty": 0.9,
    },
    "all_junk_tags": {
        "threshold": 0.2,
        "penalty": 0.5,
    },
    "too_few_tags": {
        "threshold": 2,
        "penalty": 0.2,
    },
    "num_unique_tags": {
        "less_than_1": {
            "penalty": 0.85,
        },
        "less_than_2": {
            "penalty": 0.9,
        },
        "less_than_3": {
            "penalty": 0.95,
        },
    },
    # skill_coverage_evaluation penalties
    "too_few_tests": {
        "threshold": 5,
        "penalty": 0.5,
    },
    "near_duplicate_tests": {
        "threshold": 0.95,
        "penalty": 0.5,
    },
    "low_assertion_accuracy": {
        "threshold": 0.5,
        "penalty": 0.7,
    },
    # threshold = max tests per section that get embedded/judged and count
    # towards scoring; also the count above which a section is "flooded".
    "test_flooding": {
        "threshold": 6,
        "penalty": 0.6,
    },
}
