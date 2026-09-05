import unittest
from lean_kernel_verifier.symbolic.geometry_wu import certify_geometry_statement, verify_geometry_statement


class GeometryParserTests(unittest.TestCase):
    def test_python_expression_is_rejected(self):
        result = verify_geometry_statement(
            [('x', '0')], '__import__("builtins").sum([1, 2])', ['x'],
        )
        self.assertFalse(result['proved'])
        self.assertIn('parse/poly failure', result['reason'])

    def test_missing_witness_coordinate_is_not_certified(self):
        result = certify_geometry_statement([('x', 'x')], 'x-x', ['x'], {})
        self.assertFalse(result['proved'])

    def test_nearby_rational_is_not_rounded_to_equal(self):
        result = certify_geometry_statement([('x', '1')], 'x-1', ['x'],
                                            {'x': '1.0000000000000000000000000000000000000001'})
        self.assertFalse(result['proved'])
