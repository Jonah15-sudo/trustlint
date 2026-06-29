import unittest

from spl_v7.causal import OnlineCausalGraphLearner


class CausalTests(unittest.TestCase):
    def test_learning_updates_weights(self) -> None:
        learner = OnlineCausalGraphLearner()
        for _ in range(60):
            learner.update({"tls_expiry_urgency": 1.0, "hsts_missing": 1.0}, True)
        for _ in range(60):
            learner.update({"tls_expiry_urgency": 0.0, "hsts_missing": 0.0}, False)

        snapshot = learner.snapshot()
        self.assertGreater(snapshot["samples_seen"], 0)
        self.assertGreaterEqual(snapshot["accuracy"], 0.5)
        self.assertTrue(any(abs(edge["weight"]) > 0 for edge in snapshot["edges"]))


if __name__ == "__main__":
    unittest.main()
