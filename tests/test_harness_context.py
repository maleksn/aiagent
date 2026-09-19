from harness.context import ObservationTrimmer


def test_trimmer_under_limit():
    trimmer = ObservationTrimmer(max_chars=100)
    short_text = "Hello world! This is a test."
    assert trimmer.trim(short_text) == short_text


def test_trimmer_head_and_tail_preservation():
    trimmer = ObservationTrimmer(max_chars=100, head_lines=2, tail_lines=2)
    lines = [f"Line {i}\n" for i in range(1, 21)]
    text = "".join(lines)
    trimmed = trimmer.trim(text, label="Log")

    assert "Line 1" in trimmed
    assert "Line 2" in trimmed
    assert "Line 19" in trimmed
    assert "Line 20" in trimmed
    assert "[... Log truncated: omitted 16 lines" in trimmed


def test_estimate_tokens():
    assert ObservationTrimmer.estimate_tokens("") == 0
    assert ObservationTrimmer.estimate_tokens("abcd") == 1
    assert ObservationTrimmer.estimate_tokens("a" * 400) == 100


def test_compact_messages():
    messages = [
        {"role": "user", "content": "Initial prompt"},
        {"role": "tool", "content": "x" * 2000, "name": "big_tool"},
        {"role": "assistant", "content": "Working on it..."},
        {"role": "tool", "content": "Recent output", "name": "recent_tool"},
    ]
    compacted = ObservationTrimmer.compact_messages(messages, max_total_chars=1000, keep_recent_turns=2)
    assert len(compacted) == 4
    assert compacted[0]["content"] == "Initial prompt"
    assert "Archived observation truncated" in compacted[1]["content"]
    assert compacted[3]["content"] == "Recent output"
