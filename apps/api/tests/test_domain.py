from domain import CloseRoadOperation, SignalProgram, calibration_grade, geh
from services import comparison, validate_closure


def test_geh_and_calibration_gate():
    assert geh(100, 100) == 0
    result = calibration_grade([(101, 100)] * 20, [0.10, -0.12])
    assert result["decision_grade"] is True
    assert result["grade"] == "A"


def test_closure_validation_and_matched_seeds():
    operation = CloseRoadOperation(road_segment_id="seg_kalawad_w", reason="Planned maintenance")
    assert validate_closure(operation)["valid"]
    result = comparison(operation)
    assert result["seed_count"] == 5
    assert result["quality"]["passed"]
    assert result["map_layer"]["closed_segment_id"] == "seg_kalawad_w"


def test_signal_cycle_validation():
    signal = SignalProgram(junction_id="j1", name="Peak", cycle_seconds=90, phases=[{"duration_seconds": 45}, {"duration_seconds": 45}])
    assert signal.cycle_seconds == 90

