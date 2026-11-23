import unittest

from daikin_g3.capability_assessment import assess, Support
from daikin_g3.preflight import PreflightResult


class CapabilityAssessmentTests(unittest.TestCase):
    def result(self, actions):
        return PreflightResult(True, frozenset(actions), (), ())

    def test_declared_is_not_hardware_verified(self):
        item, = assess(self.result({"screen.page.get"}), {"screen": {"screen.page.get"}})
        self.assertEqual(item.support, Support.DECLARED)
        self.assertFalse(item.hardware_verified)
        self.assertEqual(item.missing_actions, frozenset())

    def test_partial_requirements_are_not_declared(self):
        item, = assess(self.result({"screen.page.get"}), {"screen": {"screen.page.get", "screen.page.set"}})
        self.assertEqual(item.support, Support.NOT_DECLARED)
        self.assertEqual(item.missing_actions, frozenset({"screen.page.set"}))

    def test_empty_capabilities_mean_not_declared(self):
        item, = assess(self.result(set()), {"screen": {"screen.page.get"}})
        self.assertEqual(item.support, Support.NOT_DECLARED)

    def test_no_preflight_is_unverified(self):
        item, = assess(None, {"screen": {"screen.page.get"}})
        self.assertEqual(item.support, Support.UNVERIFIED)
        self.assertEqual(item.missing_actions, frozenset())

    def test_no_requirements_never_imply_support(self):
        item, = assess(self.result({"screen.page.get"}), {"unknown": set()})
        self.assertEqual(item.support, Support.UNVERIFIED)

    def test_invalid_action_rejected(self):
        with self.assertRaises(ValueError):
            assess(self.result(set()), {"screen": {"", "screen.page.get"}})

    def test_no_mutation_of_input(self):
        requirements = {"screen": ["screen.page.get"]}
        assess(self.result({"screen.page.get"}), requirements)
        self.assertEqual(requirements, {"screen": ["screen.page.get"]})

    def test_string_actions_rejected(self):
        for actions in ("screen.page.get", b"screen.page.get"):
            with self.subTest(actions=actions), self.assertRaises(ValueError):
                assess(self.result(set()), {"screen": actions})

    def test_noniterable_actions_rejected(self):
        for actions in (None, 123):
            with self.subTest(actions=actions), self.assertRaises(ValueError):
                assess(self.result(set()), {"screen": actions})

    def test_unhashable_action_rejected(self):
        with self.assertRaises(ValueError):
            assess(self.result(set()), {"screen": [["screen.page.get"]]})

    def test_generator_actions_supported(self):
        actions = (action for action in ("screen.page.get",))
        item, = assess(self.result({"screen.page.get"}), {"screen": actions})
        self.assertEqual(item.support, Support.DECLARED)
