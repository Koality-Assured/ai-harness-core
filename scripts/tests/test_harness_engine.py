"""Unit tests for the embeddable .harness core engine.

tags: [tests, harness, engine, a2a, cache, isolation]
routing_hints: [tests, harness-engine]
"""

import datetime as dt
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parents[2]
HARNESS_ROOT = REPO_ROOT / ".harness"
sys.path.insert(0, str(HARNESS_ROOT))

from a2a.protocol import A2AProtocol, A2ASecurityError
from cache.manager import PromptCacheManager
from config import load_harness_config
from isolation.worktree import WorktreeManager

_harness_init_spec = importlib.util.spec_from_file_location("harness_cli_init", HARNESS_ROOT / "cli" / "harness_init.py")
_harness_init_mod = importlib.util.module_from_spec(_harness_init_spec)
_harness_init_spec.loader.exec_module(_harness_init_mod)
init_harness = _harness_init_mod.init_harness


class TestHarnessEngine(unittest.TestCase):
    def test_config_loading(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "harness.config.json"
            p.write_text(json.dumps({"a2a": {"default_budget": 12}}))
            cfg = load_harness_config(p)
            self.assertEqual(cfg.a2a.default_budget, 12)

    def test_cache_planners(self):
        mgr = PromptCacheManager()
        # anthropic
        msgs = [{"role": "user", "content": "x" * 5000}]
        res = mgr.optimize_anthropic(system_prompt="sys", tools=[], messages=msgs)
        self.assertIn("breakpoints_added", res.to_dict().keys())

    def test_a2a_envelope(self):
        proto = A2AProtocol(signature_key="test_key")

        task_id = "123"
        status = "completed"
        agent_id = "agent-x"
        ts = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        sig = proto._generate_signature(task_id, status, agent_id, ts)

        env = proto.validate_envelope({
            "task_id": task_id,
            "status": status,
            "artifacts": [],
            "handoff_requests": [],
            "metrics": {},
            "agent_id": agent_id,
            "timestamp_utc": ts,
            "signature": sig
        }, strict_security=True)
        self.assertEqual(env.task_id, "123")

        # Tamper
        with self.assertRaises(A2ASecurityError):
            proto.validate_envelope({
                "task_id": task_id,
                "status": status,
                "artifacts": [],
                "handoff_requests": [],
                "metrics": {},
                "agent_id": agent_id,
                "timestamp_utc": ts,
                "signature": "bad_sig"
            }, strict_security=True)

    def test_worktree_isolation(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(["git", "init"], cwd=d, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=d, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=d, check=True)
            (Path(d) / "test.txt").write_text("test")
            subprocess.run(["git", "add", "."], cwd=d, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=d, check=True, capture_output=True)

            cfg = load_harness_config(repo_root=d)
            cfg.paths.worktrees = "wt"
            wm = WorktreeManager(config=cfg)
            claim = wm.create_worktree("test-task", areas=["foo"])
            self.assertTrue(Path(claim.path).exists())
            wm.remove_worktree(claim.slug)
            self.assertFalse(Path(claim.path).exists())

    def test_harness_init_scaffolding(self):
        with tempfile.TemporaryDirectory() as d:
            init_harness(Path(d))
            self.assertTrue((Path(d) / "config" / "harness.config.json").exists())
            self.assertTrue((Path(d) / "ai-tooling" / "skills").exists())
            self.assertTrue((Path(d) / "routing").exists())


if __name__ == '__main__':
    unittest.main()
