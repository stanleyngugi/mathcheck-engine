import unittest

from lean_kernel_verifier.symbolic.geometry_wu import certify_geometry_statement, verify_geometry_statement


class GeometryWuTests(unittest.TestCase):
    def test_thales_semicircle_right_angle(self) -> None:
        hypotheses = [("cx^2 + cy^2", "1")]
        conclusion = "(-1 - cx)*(1 - cx) + (0 - cy)*(0 - cy)"
        result = certify_geometry_statement(
            hypotheses, conclusion, ["cx", "cy"], witness={"cx": 0, "cy": 1}
        )
        self.assertTrue(result["proved"], msg=result["reason"])
        self.assertTrue(result["witness"]["satisfies_hypotheses"])
        self.assertTrue(result["witness"]["satisfies_conclusion"])

    def test_midpoint_theorem_parallel_and_length(self) -> None:
        hypotheses = [
            ("2*mx - u", "0"),
            ("2*my", "0"),
            ("2*nx - v", "0"),
            ("2*ny - w", "0"),
        ]
        parallel_conclusion = "(nx - mx)*w - (ny - my)*(v - u)"
        length_conclusion = "4*(nx - mx)^2 + 4*ny^2 - ((u - v)^2 + w^2)"
        variables = ["u", "v", "w", "mx", "my", "nx", "ny"]
        witness = {"u": 4, "v": 2, "w": 6, "mx": 2, "my": 0, "nx": 1, "ny": 3}

        result_parallel = certify_geometry_statement(
            hypotheses, parallel_conclusion, variables, witness=witness
        )
        self.assertTrue(result_parallel["proved"], msg=result_parallel["reason"])

        result_length = certify_geometry_statement(
            hypotheses, length_conclusion, variables, witness=witness
        )
        self.assertTrue(result_length["proved"], msg=result_length["reason"])

    def test_parallelogram_opposite_sides_equal(self) -> None:
        hypotheses = [
            ("cx - u - v", "0"),
            ("cy - w", "0"),
        ]
        conclusion = "u^2 - (cx - v)^2 - (cy - w)^2"
        variables = ["u", "v", "w", "cx", "cy"]
        result = certify_geometry_statement(
            hypotheses,
            conclusion,
            variables,
            witness={"u": 5, "v": 2, "w": 3, "cx": 7, "cy": 3},
        )
        self.assertTrue(result["proved"], msg=result["reason"])

    def test_bogus_conclusion_refused(self) -> None:
        hypotheses = [
            ("2*mx - u", "0"),
            ("2*nx - v", "0"),
        ]
        bogus = "(nx - mx)^2 - ((u - v)^2 + w^2)"
        result = certify_geometry_statement(
            hypotheses,
            bogus,
            ["u", "v", "w", "mx", "nx"],
            witness={"u": 4, "v": 2, "w": 6, "mx": 2, "nx": 3},
        )
        self.assertFalse(result["proved"])

    def test_witness_contradiction_blocks_certification(self) -> None:
        hypotheses = [("x - 1", "0")]
        conclusion = "x - 1"
        result = certify_geometry_statement(
            hypotheses, conclusion, ["x"], witness={"x": 5}
        )
        self.assertFalse(result["proved"])
        self.assertIn("witness", result["reason"])


if __name__ == "__main__":
    unittest.main()
