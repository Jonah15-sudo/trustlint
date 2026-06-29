import unittest

from spl_v7.dsl import compile_feature_dsl


class DSLTests(unittest.TestCase):
    def test_parse_and_eval(self) -> None:
        dsl = """
        feature a = data.valid
        feature b = normalize(30 - data.expiry_days, 0, 30)
        feature c = not data.headers.hsts
        feature d = clamp(0.0, 1.0, 0.3 * b + 0.7 * c)
        """
        program = compile_feature_dsl(dsl)
        context = {
            "data": {
                "valid": True,
                "expiry_days": 5,
                "headers": {"hsts": False},
            }
        }
        result = program.evaluate(context)
        self.assertTrue(result["a"])
        self.assertGreater(result["b"], 0.5)
        self.assertTrue(result["c"])
        self.assertGreaterEqual(result["d"], 0.0)
        self.assertLessEqual(result["d"], 1.0)


if __name__ == "__main__":
    unittest.main()
