import pytest
import time
from app.services.chat.chat_metrics_manager import ChatMetricsManager


@pytest.fixture
def metrics_manager():
    return ChatMetricsManager()


def test_initial_state(metrics_manager):
    assert metrics_manager.total_input_tokens == 0
    assert metrics_manager.total_output_tokens == 0
    assert metrics_manager.ttft == 0.0
    assert metrics_manager.steps == {}
    assert metrics_manager.completed_steps == []
    # Test lazy getitem for standard fields
    assert metrics_manager["input_tokens"] == 0
    assert metrics_manager["output_tokens"] == 0
    assert metrics_manager["ttft"] == 0.0
    assert isinstance(metrics_manager["total_duration"], float)


def test_start_end_span(metrics_manager):
    span_id = metrics_manager.start_span("test_step", "Test Label")
    assert span_id in metrics_manager.steps
    assert metrics_manager.steps[span_id].label == "Test Label"

    # Simulate work
    time.sleep(0.01)

    payload = {"foo": "bar"}
    step = metrics_manager.end_span(span_id, payload=payload, input_tokens=10, output_tokens=20)

    assert step is not None
    assert step.is_completed
    assert step.duration > 0
    assert step.input_tokens == 10
    assert step.output_tokens == 20
    assert step.metadata == payload

    # Verify totals
    assert metrics_manager.total_input_tokens == 10
    assert metrics_manager.total_output_tokens == 20
    assert len(metrics_manager.completed_steps) == 1


def test_end_span_tokens_in_payload(metrics_manager):
    span_id = metrics_manager.start_span("llm_call")
    payload = {"tokens": {"input_tokens": 5, "output_tokens": 5}}

    step = metrics_manager.end_span(span_id, payload=payload)

    assert step.input_tokens == 5
    assert step.output_tokens == 5
    assert metrics_manager.total_input_tokens == 5
    assert metrics_manager.total_output_tokens == 5


def test_missing_span_safe(metrics_manager):
    # Should not raise error
    result = metrics_manager.end_span("non_existent_span")
    assert result is None


def test_manual_record_step(metrics_manager):
    metrics_manager.record_completed_step(
        step_type="manual_step", label="Manual Label", duration=1.5, input_tokens=100, output_tokens=50
    )

    assert len(metrics_manager.completed_steps) == 1
    step = metrics_manager.completed_steps[0]
    assert step.duration == 1.5
    assert step.input_tokens == 100
    assert metrics_manager.total_input_tokens == 100


def test_getitem_metrics(metrics_manager):
    metrics_manager.ttft = 0.5
    metrics_manager["custom_key"] = "custom_value"

    assert metrics_manager["ttft"] == 0.5
    assert metrics_manager["custom_key"] == "custom_value"

    # Test fallback to summary
    metrics_manager.record_completed_step("s1", "l1", 0.1)
    summary = metrics_manager.get_summary()
    assert metrics_manager["step_breakdown"] == summary["step_breakdown"]


def test_get_method(metrics_manager):
    metrics_manager["foo"] = "bar"
    assert metrics_manager.get("foo") == "bar"
    assert metrics_manager.get("missing", "default") == "default"


def test_nesting_sequence(metrics_manager):
    span_id_parent = metrics_manager.start_span("agentic", "Agentic Flow")

    # Nested step
    span_id_child = metrics_manager.start_span("check", "Check")
    metrics_manager.end_span(span_id_child)

    # Another nested step
    span_id_child2 = metrics_manager.start_span("run", "Run")
    metrics_manager.end_span(span_id_child2)

    metrics_manager.end_span(span_id_parent)

    # We expect completion order: Check, Run, Agentic Flow
    # But sequence order: Agentic Flow (0), Check (1), Run (2)
    s1 = metrics_manager.completed_steps[0]  # Check
    s2 = metrics_manager.completed_steps[1]  # Run
    s3 = metrics_manager.completed_steps[2]  # Agentic Flow

    assert s1.label == "Check"
    assert s2.label == "Run"
    assert s3.label == "Agentic Flow"

    assert s3.sequence < s1.sequence
    assert s3.sequence < s2.sequence
    assert s3.sequence == 0
    assert s1.sequence == 1
    assert s2.sequence == 2


def test_increment_total_false(metrics_manager):
    # 1. Test record_completed_step
    metrics_manager.record_completed_step("step1", "Label 1", 1.0, 10, 20, increment_total=False)
    assert metrics_manager.total_input_tokens == 0
    assert metrics_manager.total_output_tokens == 0
    assert len(metrics_manager.completed_steps) == 1
    assert metrics_manager.completed_steps[0].input_tokens == 10
    assert metrics_manager.completed_steps[0].output_tokens == 20

    # 2. Test end_span
    span_id = metrics_manager.start_span("step2")
    metrics_manager.end_span(span_id, input_tokens=30, output_tokens=40, increment_total=False)
    assert metrics_manager.total_input_tokens == 0
    assert metrics_manager.total_output_tokens == 0
    assert len(metrics_manager.completed_steps) == 2
    assert metrics_manager.completed_steps[1].input_tokens == 30
    assert metrics_manager.completed_steps[1].output_tokens == 40

    # 3. Test mixed
    metrics_manager.record_completed_step("step3", "Label 3", 1.0, 5, 5, increment_total=True)
    assert metrics_manager.total_input_tokens == 5
    assert metrics_manager.total_output_tokens == 5
