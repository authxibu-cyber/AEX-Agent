"""
Unit Tests for EX Agent Skills Engine.
Verifies dynamic skill discovery and autonomous learning persistence.
"""
import tempfile
from pathlib import Path
from ex_agent.skills.learner import SkillLearner
from ex_agent.skills.manager import SkillManager


def test_dynamic_skill_discovery_and_learning():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        user_skills = tmp_path / "user_skills"
        bundled_skills = tmp_path / "bundled_skills"

        user_skills.mkdir()
        bundled_skills.mkdir()

        manager = SkillManager(user_skills_dir=user_skills, bundled_skills_dir=bundled_skills)
        learner = SkillLearner(skill_manager=manager)
        learner.user_skills_dir = user_skills

        # Learn a new skill
        ok, msg = learner.create_skill(
            name="test-kernel-tuning",
            description="Tuning CUDA kernels for fast associative scan",
            instructions="1. Apply torch.compile max-autotune\n2. Profile with Nsight.",
            triggers=["kernel tuning", "nsight"],
            tools=["terminal", "code_execution"],
        )
        assert ok is True

        # Verify discovery
        skill = manager.get_skill("test-kernel-tuning")
        assert skill is not None
        assert skill.name == "test-kernel-tuning"
        assert skill.is_user_skill is True
        assert "kernel tuning" in skill.triggers
