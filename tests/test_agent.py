"""
Unit Tests for AEX Agent Brain & Parser.
Verifies Hermes XML and thought block parsing, and agent initialization.
"""
from aex_agent.agent.core import EXAgent
from aex_agent.agent.parser import ToolParser
from aex_agent.agent.selective_pulse import CognitivePulseGate


def test_tool_parser_thought_and_xml():
    raw_response = (
        "<thought>\nAnalyzing user request to optimize SSM selectively.\n</thought>\n"
        "I will perform the surgery now.\n"
        '<tool_call>{"name": "file_read", "arguments": {"path": "model.py"}}</tool_call>'
    )

    clean_content, reasoning = ToolParser.extract_thought(raw_response)
    assert "Analyzing user request" in reasoning
    assert "<thought>" not in clean_content

    calls, final_text = ToolParser.parse_tool_calls(native_calls=None, content_text=clean_content)
    assert len(calls) == 1
    assert calls[0]["name"] == "file_read"
    assert calls[0]["arguments"]["path"] == "model.py"
    assert "I will perform the surgery now." in final_text


def test_cognitive_pulse_gate():
    gate = CognitivePulseGate()
    delta, decay = gate.compute_selectivity(token_salience=2.5)
    assert delta > 0.0
    assert 0.0 <= decay <= 1.0

    comp = gate.associative_scan_compression([0.9, 0.8, 0.95, 0.85])
    assert 0.0 < comp <= 1.0


def test_agent_initialization():
    agent = EXAgent()
    assert agent.model is not None
    assert agent.session_id is not None
    system_prompt = agent.assemble_system_message()
    assert "AEX Agent" in system_prompt
    assert "Persistent Memory Cabinet" in system_prompt


def test_skill_activation_on_trigger():
    """Trigger-matched skills inject full instructions into the system prompt."""
    agent = EXAgent()
    prompt = agent.assemble_system_message(
        user_message="gua mau bikin node sensor pakai ESP32, bantu pinout"
    )
    assert "embedded-hardware" in agent.active_skill_names
    assert "Active Skill Protocols" in prompt
    assert "Strapping pins" in prompt


def test_no_skill_leak_on_unrelated_message():
    """Unrelated messages must not activate any skill protocol."""
    agent = EXAgent()
    prompt = agent.assemble_system_message(user_message="halo gimana kabarnya")
    assert agent.active_skill_names == []
    assert "Active Skill Protocols" not in prompt
