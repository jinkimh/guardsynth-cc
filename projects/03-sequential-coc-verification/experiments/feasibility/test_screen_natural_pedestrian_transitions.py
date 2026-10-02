import json

import pandas as pd

from screen_natural_pedestrian_transitions import semantic_phase, transition_candidates


def test_semantic_phase() -> None:
    assert semantic_phase("Yield to the pedestrian crossing the crosswalk") == "HOLD"
    assert semantic_phase("Resume speed after the pedestrian crossed") == "RELEASE"
    assert semantic_phase("Follow the lead vehicle") == "OTHER"


def test_transition_candidates_uses_nearest_release() -> None:
    reasoning = pd.DataFrame(
        [
            {
                "event_cluster": "PED",
                "split": "train",
                "events": json.dumps(
                    [
                        {"event_start_timestamp": 1_000_000, "coc": "Yield to the pedestrian"},
                        {"event_start_timestamp": 2_000_000, "coc": "Follow the lead vehicle"},
                        {"event_start_timestamp": 4_000_000, "coc": "Resume after pedestrian crossed"},
                        {"event_start_timestamp": 5_000_000, "coc": "Proceed after pedestrian crossed"},
                    ]
                ),
            }
        ],
        index=pd.Index(["clip-a"], name="clip_id"),
    )
    records = transition_candidates(reasoning)
    assert len(records) == 1
    assert records[0]["transition_duration_s"] == 3.0
    assert records[0]["release_t0_us"] == 4_000_000
