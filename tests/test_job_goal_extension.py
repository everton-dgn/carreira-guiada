"""Extensão de objetivos com dados sintéticos e armazenamento temporário."""

from concurrent.futures import ThreadPoolExecutor
import json
import subprocess
import sys
from threading import Barrier
import unittest

import test_job_workflow as support
from scripts.job.workflow import Workflow


class GoalExtensionTests(unittest.TestCase):
    setUp = support.WorkflowTests.setUp
    approve_profile = support.WorkflowTests.approve_profile
    approved_resume = support.WorkflowTests.approved_resume
    ready = support.WorkflowTests.ready
    apply = support.WorkflowTests.apply
    done = support.WorkflowTests.done

    def extension(self, actions, version=1):
        return {"goal_version": version, "add_actions": actions, "user_confirmation": "Sim, ampliar o objetivo"}

    def test_confirmed_progress_and_open_action_survive(self):
        for period in (None, 30):
            with self.subTest(period=period):
                # Each scenario uses its own storage and real authorization flow.
                if period:
                    self.tearDown()
                    self.doCleanups()
                    self.setUp()
                goal = {"summary": "Candidaturas", "actions": ["apply"], "target_applications": 2, "period_days": period, "portals": ["portal"]}
                job, resume = self.ready(goal)
                action = self.apply(job, resume)
                before = self.wf.state()["goal"]
                extended = self.wf.extend_goal(self.extension(["research"]))
                self.wf.check(action["action_id"], {"owner": "chat:sessao", "generation": 1})
                self.done(action["action_id"], submitted_at=support.iso(self.clock()))
                self.assertEqual(self.wf.state()["progress"]["confirmed_applications"], 1)
                self.wf.extend_goal(self.extension(["email_read"]))
                state = self.wf.state()
                self.assertEqual(state["progress"]["confirmed_applications"], 1)
                for key in ("version", "created_at", "summary", "profile_version"):
                    self.assertEqual(state["goal"][key], before[key])
                for key in ("period_days", "target_applications", "portals"):
                    self.assertEqual(extended["criteria"][key], before["criteria"][key])
                self.assertEqual(len(state["goal"]["amendments"]), 2)
                self.assertTrue(self.wf.extend_goal(self.extension(["research"]))["unchanged"])
                self.assertEqual(len(self.wf.state()["goal"]["amendments"]), 2)

    def test_invalid_stale_replaced_and_stop(self):
        with self.assertRaises(ValueError):
            self.wf.extend_goal(self.extension(["research"]))
        self.wf.configure_goal({"summary": "Primeiro", "actions": ["research"]})
        for payload in (self.extension([]), self.extension(["invalid"]), self.extension(["apply", "apply"]),
                        {"goal_version": 1, "add_actions": ["apply"]}, self.extension(["apply"], 2)):
            with self.assertRaises(ValueError):
                self.wf.extend_goal(payload)
        self.wf.configure_goal({"summary": "Segundo", "actions": ["research"], "replace_version": 1})
        with self.assertRaises(ValueError):
            self.wf.extend_goal(self.extension(["apply"]))
        self.wf.stop()
        self.wf.extend_goal(self.extension(["apply"], 2))
        self.assertTrue(self.wf.state()["control"]["stopped"])

    def test_legacy_and_concurrent_union(self):
        self.wf.configure_goal({"summary": "Legado", "actions": ["research"]})
        self.wf._store.conn.execute("DROP TABLE wf_goal_amendments")
        self.wf.close()
        self.assertEqual(self.wf.state()["goal"]["amendments"], [])
        barrier = Barrier(2)
        def extend(action):
            wf = Workflow(self.root)
            try:
                wf._writer()
                barrier.wait(timeout=10)
                return wf.extend_goal(self.extension([action]))
            finally:
                wf.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(extend, ["apply", "email_read"]))
        goal = self.wf.state()["goal"]
        self.assertEqual(set(goal["criteria"]["actions"]), {"research", "apply", "email_read"})
        self.assertEqual(len(goal["amendments"]), 2)

    def test_cli_and_permission_remain_separate(self):
        self.approve_profile({"research": "allow"})
        self.wf.configure_goal({"summary": "Pesquisa", "actions": ["research"]})
        proc = subprocess.run([sys.executable, "-m", "scripts.job.cli", "--root", str(self.root), "goal-extend", "--json"],
                              input=json.dumps(self.extension(["apply"])), text=True, capture_output=True, timeout=15)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertEqual(json.loads(proc.stdout)["added_actions"], ["apply"])
        with self.assertRaisesRegex(ValueError, "permissão"):
            self.wf.authorize({"action": "apply", "owner": "chat:sessao", "generation": 1})
