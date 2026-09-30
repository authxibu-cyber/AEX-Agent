"""
Unit Tests for Merlin Agent Persistent Memory Subsystem.
Verifies bounded memory constraints and FTS5 search indexing.
"""
import tempfile
from pathlib import Path
from merlin_agent.memory.persistent import MemoryManager
from merlin_agent.memory.store import SessionStore
from merlin_constants import MEMORY_MD_MAX_CHARS, USER_MD_MAX_CHARS


def test_bounded_memory_consolidation():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        mem_file = tmp_path / "MEMORY.md"
        user_file = tmp_path / "USER.md"

        manager = MemoryManager(memory_file=mem_file, user_file=user_file)

        # Append large amount of data exceeding bound
        large_chunk = "A" * 1500
        manager.update_memory(large_chunk)
        manager.update_memory(large_chunk)

        content = manager.read_memory()
        assert len(content) <= MEMORY_MD_MAX_CHARS, f"Memory length {len(content)} exceeded {MEMORY_MD_MAX_CHARS}"
        assert content.startswith("# World & Project Knowledge Base")


def test_fts5_session_store():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_state.db"
        store = SessionStore(db_path=db_path)

        session_id = "test_sess_01"
        store.create_or_update_session(session_id, title="Unit Test Session")
        store.add_message(session_id, "user", "How do I optimize Mamba SSM dt_proj?")
        store.add_message(session_id, "assistant", "Inject fused tensor cores and adapt the cognitive pulse gate.")

        # Test full-text search
        matches = store.search_sessions("Mamba")
        assert len(matches) > 0
        assert "Mamba" in matches[0]["content"]

        matches_pulse = store.search_sessions("cognitive pulse")
        assert len(matches_pulse) > 0
