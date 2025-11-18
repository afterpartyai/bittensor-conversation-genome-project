from typing import Literal

TaskType = Literal["conversation_tagging", "webpage_metadata_generation", "survey_tagging"]
ScoringMechanismType = Literal["ground_truth_tag_similarity_scoring"]
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
}
