import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch


class EvolutionJobTests(unittest.TestCase):
    def test_result_records_judge_score_and_optimization_input_provenance(self):
        import app

        history = [
            {"iteration": 0, "prompt": "initial", "score": 0.4},
            {"iteration": 1, "prompt": "revised", "score": 0.6},
        ]
        request = SimpleNamespace(
            custom_prompt="starting prompt",
            custom_constraints={},
            test_inputs=["case one", "case two"],
            test_case_count=0,
            optimizer_model="optimizer",
            model="executor",
            max_iterations=1,
            min_delta=0.3,
        )
        job_store = Mock()

        with (
            patch.object(app, "jobs", job_store),
            patch.object(app, "get_model", return_value=object()),
            patch.object(app, "evolve_prompt", return_value=history),
        ):
            app.run_evolution_job("job-1", request)

        result = job_store.update.call_args_list[-1].args[1]["results"]
        self.assertEqual(result["score_method"], "llm_judge_heuristic")
        self.assertEqual(result["selection_data_role"], "optimization_inputs")
        self.assertEqual(result["optimization_input_count"], 2)


if __name__ == "__main__":
    unittest.main()
