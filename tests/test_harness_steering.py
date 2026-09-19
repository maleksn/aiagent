from harness.steering import LoopDetector


def test_loop_detector_triggers_on_repetition():
    detector = LoopDetector(repetition_threshold=3)

    # 1st call
    alert1 = detector.record_and_check("get_file_content", {"file_path": "main.py"}, "content")
    assert alert1 is None

    # 2nd call
    alert2 = detector.record_and_check("get_file_content", {"file_path": "main.py"}, "content")
    assert alert2 is None

    # 3rd call with same args -> trigger loop alert
    alert3 = detector.record_and_check("get_file_content", {"file_path": "main.py"}, "content")
    assert alert3 is not None
    assert "HARNESS STEERING INTERVENTION" in alert3
    assert "3 times" in alert3


def test_loop_detector_resets_on_different_call():
    detector = LoopDetector(repetition_threshold=3)

    detector.record_and_check("get_file_content", {"file_path": "a.py"}, "content a")
    detector.record_and_check("get_file_content", {"file_path": "a.py"}, "content a")
    # Different call
    detector.record_and_check("get_file_content", {"file_path": "b.py"}, "content b")

    # One more call to a.py should not trigger 3-consecutive alert
    alert = detector.record_and_check("get_file_content", {"file_path": "a.py"}, "content a")
    assert alert is None


def test_enrich_error():
    err1 = LoopDetector.enrich_error("get_file_content", 'Error: "foo.py" does not exist')
    assert "Harness Hint" in err1
    assert "get_files_info" in err1

    err2 = LoopDetector.enrich_error("edit_file", "Error: target_content not found in calc.py")
    assert "get_file_content" in err2

    err3 = LoopDetector.enrich_error("edit_file", "Error: target_content appears 2 times")
    assert "surrounding lines" in err3
