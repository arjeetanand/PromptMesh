import importlib
import sys
import types
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from core.security import (
    CallerJobLimitError,
    JobStore,
    RequestBodyLimitMiddleware,
    RequestRateLimiter,
    ServerJobLimitError,
)
from core.types import render_prompt
from prompts.registry import PromptRegistry
from training import review_packets


# Keep API tests independent of optional model-provider packages and credentials.
_fake_model_registry = types.ModuleType("models.registry")
_fake_model_registry.MODEL_DEFINITIONS = {"safe-test-model": {"type": "test"}}

class _FakeModel:
    def run(self, *args, **kwargs):
        raise AssertionError("model calls are not expected in request-boundary tests")


_fake_model_registry.get_model = lambda name: _FakeModel()
sys.modules["models.registry"] = _fake_model_registry
_fake_scorer = types.ModuleType("evaluation.scorer")
_fake_scorer.evaluate = lambda *args, **kwargs: None
sys.modules["evaluation.scorer"] = _fake_scorer
promptmesh_app = importlib.import_module("app")


class FakeClock:
    def __init__(self):
        self.now = 0

    def __call__(self):
        return self.now


class PromptRenderingTests(unittest.TestCase):
    def test_simple_placeholders_preserve_normal_prompt_use(self):
        self.assertEqual(
            render_prompt("Classify: {{text}} / {{ text }}", {"text": "good"}),
            "Classify: good / good",
        )

    def test_template_expressions_and_control_blocks_are_not_executed(self):
        for template in (
            "{{ 7 * 7 }}",
            "{{ cycler.__init__.__globals__ }}",
            "prefix {{text}} {{ caller.__class__ }}",
            "{% for item in text %}{{ item }}{% endfor %}",
        ):
            with self.subTest(template=template):
                with self.assertRaises(ValueError):
                    render_prompt(template, {"text": "input"})

    def test_rendered_prompt_has_a_hard_output_limit(self):
        with self.assertRaisesRegex(ValueError, "Rendered prompts"):
            render_prompt("{{text}}" * 9, {"text": "x" * 4_000})


class PromptRegistryTests(unittest.TestCase):
    def test_extraction_prompt_defines_organization_as_the_claim_actor(self):
        prompt = PromptRegistry().load("extraction", "v1")
        self.assertEqual(prompt["version"], "1.1.0")
        self.assertIn("actor/subject performing the claim", prompt["template"])
        self.assertIn("not a recipient or beneficiary", prompt["template"])

    def test_loads_a_valid_prompt_and_lists_versions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "versions"
            prompt_dir = root / "classification"
            prompt_dir.mkdir(parents=True)
            (prompt_dir / "v1.yaml").write_text("task: classification\ntemplate: '{{text}}'\n")
            with patch("prompts.registry.PROMPT_BASE_PATH", root):
                registry = PromptRegistry()
                self.assertEqual(registry.load("classification", "v1")["task"], "classification")
                self.assertEqual(registry.list_versions("classification"), ["v1"])

    def test_rejects_traversal_before_cache_lookup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "versions"
            root.mkdir()
            registry = PromptRegistry()
            with patch("prompts.registry.PROMPT_BASE_PATH", root):
                registry._cache["unused"] = {"task": "cached"}
                for task, version in (("../outside", "v1"), ("valid", "../../outside"), ("/tmp", "v1")):
                    with self.subTest(task=task, version=version):
                        with self.assertRaises(FileNotFoundError):
                            registry.load(task, version)
                with self.assertRaises(FileNotFoundError):
                    registry.list_versions("../outside")

    def test_rejects_symlink_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "versions"
            prompt_dir = root / "task"
            prompt_dir.mkdir(parents=True)
            secret = Path(directory) / "outside.yaml"
            secret.write_text("task: outside\n")
            (prompt_dir / "escape.yaml").symlink_to(secret)
            with patch("prompts.registry.PROMPT_BASE_PATH", root):
                with self.assertRaises(FileNotFoundError):
                    PromptRegistry().load("task", "escape")


class WorkLimitTests(unittest.TestCase):
    def test_jobs_enforce_global_and_per_caller_active_caps(self):
        store = JobStore(max_active=2, max_active_per_caller=1, max_retained=4)
        first = store.create("alice")
        with self.assertRaises(CallerJobLimitError):
            store.create("alice")
        second = store.create("bob")
        with self.assertRaises(ServerJobLimitError):
            store.reserve("carol")
        store.update(first, {"status": "completed", "results": ["ok"]})
        self.assertIsNone(store.get(first, "bob"))
        self.assertEqual(store.get(first, "alice")["results"], ["ok"])
        self.assertIsNotNone(store.get(second, "bob"))

    def test_completed_jobs_expire_and_retention_is_bounded(self):
        clock = FakeClock()
        store = JobStore(
            max_active=3,
            max_active_per_caller=3,
            max_retained=2,
            retention_seconds=10,
            clock=clock,
        )
        first = store.create("alice")
        store.update(first, {"status": "completed"})
        second = store.create("alice")
        store.update(second, {"status": "failed"})
        third = store.create("alice")
        self.assertIsNone(store.get(first, "alice"))
        self.assertIsNotNone(store.get(second, "alice"))
        clock.now = 11
        self.assertIsNone(store.get(second, "alice"))
        self.assertIsNotNone(store.get(third, "alice"))

    def test_rate_limit_expires_and_caps_caller_tracking(self):
        clock = FakeClock()
        limiter = RequestRateLimiter(limit=2, window_seconds=60, max_callers=2, clock=clock)
        self.assertTrue(limiter.allow("alice"))
        self.assertTrue(limiter.allow("alice"))
        self.assertFalse(limiter.allow("alice"))
        clock.now = 61
        self.assertTrue(limiter.allow("alice"))
        self.assertLessEqual(len(limiter._requests), 2)

    def test_request_body_middleware_rejects_oversized_requests(self):
        async def accept(request):
            return JSONResponse({"size": len(await request.body())})

        app = Starlette(routes=[Route("/api/test", accept, methods=["POST"])])
        app.add_middleware(RequestBodyLimitMiddleware, max_bytes=4)
        with TestClient(app) as client:
            response = client.post("/api/test", content=b"12345")
        self.assertEqual(response.status_code, 413)


class ApiBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.previous_api_key = promptmesh_app.API_KEY
        self.previous_allowed_origins = promptmesh_app.ALLOWED_ORIGINS
        self.previous_jobs = promptmesh_app.jobs
        promptmesh_app.API_KEY = "security-test-key-that-is-at-least-32-chars"
        promptmesh_app.jobs = JobStore()
        self.client = TestClient(promptmesh_app.app)

    def tearDown(self):
        self.client.close()
        promptmesh_app.API_KEY = self.previous_api_key
        promptmesh_app.ALLOWED_ORIGINS = self.previous_allowed_origins
        promptmesh_app.jobs = self.previous_jobs

    def test_remote_api_requests_require_the_bearer_key(self):
        self.assertEqual(self.client.get("/api/tasks").status_code, 401)
        response = self.client.get(
            "/api/tasks",
            headers={"Authorization": f"Bearer {promptmesh_app.API_KEY}"},
        )
        self.assertEqual(response.status_code, 200)

    def test_server_rejects_excessive_work_before_queueing(self):
        headers = {"Authorization": f"Bearer {promptmesh_app.API_KEY}"}
        payload = {
            "task": "generation",
            "version": "v1",
            "models": ["model"] * 6,
            "custom_prompt": "Hello {{text}}",
        }
        response = self.client.post("/api/evaluate", json=payload, headers=headers)
        self.assertEqual(response.status_code, 422)

    def test_server_caps_custom_provider_output_tokens(self):
        headers = {"Authorization": f"Bearer {promptmesh_app.API_KEY}"}
        payload = {
            "task": "generation",
            "version": "v1",
            "models": ["model"],
            "test_inputs": ["hello"],
            "custom_prompt": "Hello {{text}}",
            "custom_constraints": {"max_tokens": 2049},
        }
        response = self.client.post("/api/evaluate", json=payload, headers=headers)
        self.assertEqual(response.status_code, 422)

    def test_prompt_selection_requires_a_text_placeholder_and_reviewed_data(self):
        headers = {"Authorization": f"Bearer {promptmesh_app.API_KEY}"}
        base = {"dataset_id": "entity_extraction_demo", "adapter_run_id": "a" * 32}
        missing_placeholder = self.client.post(
            "/api/training/prompt-selections",
            json={**base, "candidate_prompts": ["Extract the requested fields."]},
            headers=headers,
        )
        synthetic_data = self.client.post(
            "/api/training/prompt-selections",
            json={**base, "candidate_prompts": ["Extract {{text}} as JSON."]},
            headers=headers,
        )
        self.assertEqual(missing_placeholder.status_code, 422)
        self.assertEqual(synthetic_data.status_code, 422)

    def test_prompt_selection_queues_as_a_local_model_job(self):
        headers = {"Authorization": f"Bearer {promptmesh_app.API_KEY}"}
        rows = [{"group_id": "source-1", "input": "source", "output": {"organization": None, "year": None, "claim": None}}]
        card = {
            "card_ready": True,
            "validation_ready": True,
            "final_test_ready": True,
            "card_sha256": "b" * 64,
        }

        def complete(job_id, _request, jobs):
            jobs.update(job_id, {"status": "completed", "progress": 100, "result": {"selection_id": "c" * 32}})

        with patch.object(promptmesh_app, "load_dataset_snapshot", return_value=(rows, "a" * 64)), \
             patch.object(promptmesh_app, "benchmark_card_status", return_value=card), \
             patch.object(promptmesh_app, "get_benchmark_adapter", return_value=(Path("/adapter"), {})), \
             patch.object(promptmesh_app, "training_runtime", return_value={"available": True, "missing": []}), \
             patch.object(promptmesh_app, "run_prompt_selection", side_effect=complete):
            response = self.client.post(
                "/api/training/prompt-selections",
                json={"dataset_id": "reviewed", "adapter_run_id": "d" * 32, "candidate_prompts": ["Extract {{text}} as JSON."]},
                headers=headers,
            )

        self.assertEqual(response.status_code, 200)
        job = self.client.get("/api/jobs/" + response.json()["job_id"], headers=headers)
        self.assertEqual(job.status_code, 200)
        self.assertEqual(job.json()["result"]["selection_id"], "c" * 32)

    def test_prompt_selection_rejects_a_reviewed_dataset_below_benchmark_floors(self):
        headers = {"Authorization": f"Bearer {promptmesh_app.API_KEY}"}
        rows = [{"group_id": "source-1", "input": "source", "output": {"organization": None, "year": None, "claim": None}}]
        card = {"card_ready": True, "validation_ready": False, "final_test_ready": False}

        with patch.object(promptmesh_app, "load_dataset_snapshot", return_value=(rows, "a" * 64)), \
             patch.object(promptmesh_app, "benchmark_card_status", return_value=card), \
             patch.object(promptmesh_app, "get_benchmark_adapter") as get_adapter, \
             patch.object(promptmesh_app, "run_prompt_selection") as run_selection:
            response = self.client.post(
                "/api/training/prompt-selections",
                json={"dataset_id": "reviewed", "adapter_run_id": "d" * 32, "candidate_prompts": ["Extract {{text}} as JSON."]},
                headers=headers,
            )

        self.assertEqual(response.status_code, 422)
        self.assertIn("30 examples across 10 source groups", response.json()["detail"])
        get_adapter.assert_not_called()
        run_selection.assert_not_called()

    def test_frozen_benchmark_requires_the_selected_adapter_and_queues_locally(self):
        headers = {"Authorization": f"Bearer {promptmesh_app.API_KEY}"}
        selection_id = "c" * 32
        adapter_id = "d" * 32
        dataset_digest = "a" * 64
        card_digest = "b" * 64
        selection = {
            "selection_id": selection_id,
            "adapter_run_id": adapter_id,
            "dataset_id": "reviewed",
            "dataset_sha256": dataset_digest,
            "benchmark_card_sha256": card_digest,
        }
        rows = [{"group_id": "source-1", "input": "source", "output": {"organization": None, "year": None, "claim": None}}]
        card = {
            "card_ready": True,
            "validation_ready": True,
            "final_test_ready": True,
            "card_sha256": card_digest,
        }

        def complete(job_id, _request, jobs):
            jobs.update(job_id, {"status": "completed", "progress": 100, "result": {"report": {"metrics_split": "test"}}})

        quant_runtime = {"available": True, "methods": [{"id": "bnb_nf4"}]}
        with patch.object(promptmesh_app, "load_prompt_selection", return_value=selection), \
             patch.object(promptmesh_app, "load_dataset_snapshot", return_value=(rows, dataset_digest)), \
             patch.object(promptmesh_app, "benchmark_card_status", return_value=card), \
             patch.object(promptmesh_app, "get_benchmark_adapter", return_value=(Path("/adapter"), {})), \
             patch.object(promptmesh_app, "quantization_runtime", return_value=quant_runtime), \
             patch.object(promptmesh_app, "training_runtime", return_value={"available": True, "missing": []}), \
             patch.object(promptmesh_app, "run_frozen_benchmark", side_effect=complete) as run_benchmark:
            mismatched = self.client.post(
                "/api/training/benchmarks",
                json={"selection_id": selection_id, "adapter_run_id": "e" * 32},
                headers=headers,
            )
            self.assertEqual(mismatched.status_code, 422)
            run_benchmark.assert_not_called()

            response = self.client.post(
                "/api/training/benchmarks",
                json={"selection_id": selection_id, "adapter_run_id": adapter_id, "quantization_methods": ["bnb_nf4"]},
                headers=headers,
            )

        self.assertEqual(response.status_code, 200)
        job = self.client.get("/api/jobs/" + response.json()["job_id"], headers=headers)
        self.assertEqual(job.status_code, 200)
        self.assertEqual(job.json()["result"]["report"]["metrics_split"], "test")
        run_benchmark.assert_called_once()
        self.assertEqual(run_benchmark.call_args.args[1].quantization_methods, ["bnb_nf4"])

    def test_frozen_benchmark_rejects_duplicate_or_unavailable_quantization_methods(self):
        headers = {"Authorization": f"Bearer {promptmesh_app.API_KEY}"}
        payload = {"selection_id": "c" * 32, "adapter_run_id": "d" * 32}
        unavailable = {"available": False, "methods": [], "reason": "bitsandbytes unavailable"}
        with patch.object(promptmesh_app, "quantization_runtime", return_value=unavailable), \
             patch.object(promptmesh_app, "run_frozen_benchmark") as run_benchmark:
            unavailable_response = self.client.post(
                "/api/training/benchmarks",
                json={**payload, "quantization_methods": ["bnb_nf4"]},
                headers=headers,
            )
            duplicate_response = self.client.post(
                "/api/training/benchmarks",
                json={**payload, "quantization_methods": ["bnb_nf4", "bnb_nf4"]},
                headers=headers,
            )

        self.assertEqual(unavailable_response.status_code, 503)
        self.assertEqual(duplicate_response.status_code, 422)
        run_benchmark.assert_not_called()

    def test_training_dataset_listing_exposes_optional_quantization_runtime(self):
        headers = {"Authorization": f"Bearer {promptmesh_app.API_KEY}"}
        runtime = {"available": True, "backend": "bitsandbytes", "version": "0.50.0", "device": "mps", "methods": []}
        with patch.object(promptmesh_app, "list_datasets", return_value=[]), \
             patch.object(promptmesh_app, "training_runtime", return_value={"available": True, "device": "mps"}), \
             patch.object(promptmesh_app, "quantization_runtime", return_value=runtime):
            response = self.client.get("/api/training/datasets", headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["quantization"], runtime)

    def test_review_packet_is_loopback_only_even_with_a_valid_api_key(self):
        headers = {"Authorization": f"Bearer {promptmesh_app.API_KEY}"}
        with TestClient(promptmesh_app.app, base_url="http://remote.example") as remote:
            response = remote.get("/api/training/review-packet", headers=headers)
            saved = remote.post(
                "/api/training/review-packet",
                json={
                    "group_id": "source-1",
                    "rows": [{"row_index": 0, "review_status": "NEEDS_HUMAN_REVIEW"}],
                    "reuse_status": "permission_unconfirmed",
                },
                headers=headers,
            )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(saved.status_code, 403)

    def test_loopback_client_can_read_and_save_a_private_review_group(self):
        import csv

        columns = list(review_packets.REQUIRED_COLUMNS)
        with tempfile.TemporaryDirectory() as directory:
            packet_path = Path(directory) / "review.csv"
            with packet_path.open("w", encoding="utf-8", newline="") as output:
                writer = csv.DictWriter(output, fieldnames=columns)
                writer.writeheader()
                for index in range(3):
                    writer.writerow({
                        "group_id": "source-1", "input": f"Input {index}",
                        "proposed_organization": "Actor Org", "proposed_year": "2024",
                        "proposed_claim": "opened a lab", "review_status": "NEEDS_HUMAN_REVIEW",
                        "source_title": "Source", "source_url": "https://example.org/source",
                        "source_date": "2024-01-01", "reuse_status": "permission_unconfirmed",
                    })
            with patch.object(review_packets, "REVIEW_PACKET_DIR", Path(directory)), \
                 patch.object(review_packets, "REVIEW_PACKET_PATH", packet_path), \
                 TestClient(
                     promptmesh_app.app,
                     base_url="http://localhost:8000",
                     client=("127.0.0.1", 49152),
                 ) as local:
                headers = {"Authorization": f"Bearer {promptmesh_app.API_KEY}"}
                loaded = local.get("/api/training/review-packet", headers=headers)
                rows = [
                    {
                        "row_index": row["row_index"],
                        "review_status": "REVIEWED",
                        "reviewed_organization": "Actor Org",
                        "reviewed_year": 2024,
                        "reviewed_claim": "opened a lab",
                        "review_notes": "Checked against linked source",
                    }
                    for row in loaded.json()["groups"][0]["rows"]
                ]
                saved = local.post(
                    "/api/training/review-packet",
                    json={
                        "group_id": "source-1", "rows": rows,
                        "reuse_status": "permission_unconfirmed", "reuse_evidence": "",
                    },
                    headers=headers,
                )

        self.assertEqual(loaded.status_code, 200)
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json()["reviewed_rows"], 3)

    def test_valid_evaluation_job_can_be_submitted_and_polled(self):
        headers = {"Authorization": f"Bearer {promptmesh_app.API_KEY}"}
        original_runner = promptmesh_app.run_evaluation_job

        def finish_without_provider(job_id, request):
            promptmesh_app.jobs.update(
                job_id,
                {"status": "completed", "progress": 100, "results": []},
            )

        promptmesh_app.run_evaluation_job = finish_without_provider
        try:
            response = self.client.post(
                "/api/evaluate",
                json={
                    "task": "generation",
                    "version": "v1",
                    "models": ["safe-test-model"],
                    "test_inputs": ["hello"],
                    "generate_test_cases": False,
                    "custom_prompt": "Hello {{text}}",
                },
                headers=headers,
            )
            self.assertEqual(response.status_code, 200)
            job_id = response.json()["job_id"]
            job = self.client.get(f"/api/jobs/{job_id}", headers=headers)
            self.assertEqual(job.status_code, 200)
            self.assertEqual(job.json()["status"], "completed")
        finally:
            promptmesh_app.run_evaluation_job = original_runner

    def test_test_case_generation_runs_in_a_worker_thread(self):
        headers = {"Authorization": f"Bearer {promptmesh_app.API_KEY}"}
        cases = ["hello", "hello, with a detail"]
        with patch.object(
            promptmesh_app, "run_in_threadpool", new=AsyncMock(return_value=cases)
        ) as worker:
            response = self.client.post(
                "/api/test-cases/generate",
                json={"task_type": "generation", "base_inputs": ["hello"], "count": 2},
                headers=headers,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["test_cases"], cases)
        worker.assert_awaited_once_with(
            promptmesh_app.generate_test_cases,
            task_type="generation",
            input_variables=["text"],
            base_inputs=["hello"],
            schema_fields=None,
            n=2,
        )

    def test_unconfigured_remote_api_is_denied(self):
        promptmesh_app.API_KEY = None
        with TestClient(promptmesh_app.app, base_url="http://remote.example") as remote:
            response = remote.get("/api/tasks")
        self.assertEqual(response.status_code, 403)

    def test_loopback_api_rejects_cross_site_browser_requests(self):
        promptmesh_app.API_KEY = None
        promptmesh_app.ALLOWED_ORIGINS = ["https://attacker.example"]
        with TestClient(
            promptmesh_app.app,
            base_url="http://localhost:8000",
            client=("127.0.0.1", 49152),
        ) as local:
            blocked = local.get("/api/tasks", headers={"Origin": "https://attacker.example"})
            allowed = local.get("/api/tasks", headers={"Origin": "http://localhost:8000"})
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(allowed.status_code, 200)


class TestCaseGenerationTests(unittest.TestCase):
    def test_empty_input_fallback_cannot_loop_forever(self):
        # Avoid importing external model adapters; the empty-input guard runs first.
        fake_registry = types.ModuleType("models.registry")
        fake_registry.get_model = lambda name: self.fail("model access should not occur")
        with patch.dict(sys.modules, {"models.registry": fake_registry}):
            from optimization.testcase_generator import create_smart_variations, generate_test_cases

            self.assertEqual(create_smart_variations([], 3, "generation"), [])
            with self.assertRaises(ValueError):
                generate_test_cases("generation", ["text"], [], n=3)


if __name__ == "__main__":
    unittest.main()
