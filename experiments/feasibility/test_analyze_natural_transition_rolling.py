from analyze_natural_transition_rolling import coc_action_phase, release_timing


def test_coc_action_phase() -> None:
    assert coc_action_phase("Stop to yield to pedestrians") == "HOLD"
    assert coc_action_phase("Resume speed after pedestrian crosses") == "RELEASE"
    assert coc_action_phase("Follow the lead vehicle") == "UNSPECIFIED"


def test_release_timing() -> None:
    assert release_timing(None) == "NO_EXPLICIT_RELEASE_WITHIN_WINDOW"
    assert release_timing(2.0) == "EARLY_RELEASE_CANDIDATE"
    assert release_timing(3.5) == "ALIGNED_WITH_HUMAN_EVENT_TOLERANCE"
    assert release_timing(4.0) == "LATE_RELEASE_CANDIDATE"
