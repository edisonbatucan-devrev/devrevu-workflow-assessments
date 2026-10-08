import unittest

from title_validator import validate_bug_title, run, BUG_TITLE_PATTERN


class TestBugTitleValidator(unittest.TestCase):
    def test_valid_title(self):
        r = validate_bug_title("[BUG] Login button does nothing on Safari")
        self.assertTrue(r["is_valid"])
        self.assertEqual(r["pattern"], BUG_TITLE_PATTERN)

    def test_valid_minimum_length(self):
        # exactly 5 chars after the "[BUG] " prefix
        self.assertTrue(validate_bug_title("[BUG] abcde")["is_valid"])

    def test_too_short_body(self):
        self.assertFalse(validate_bug_title("[BUG] abc")["is_valid"])

    def test_missing_prefix(self):
        self.assertFalse(validate_bug_title("Login button broken")["is_valid"])

    def test_wrong_case_prefix(self):
        self.assertFalse(validate_bug_title("[bug] something is broken")["is_valid"])

    def test_empty_string(self):
        r = validate_bug_title("   ")
        self.assertFalse(r["is_valid"])
        self.assertIn("empty", r["reason"].lower())

    def test_none_input(self):
        r = validate_bug_title(None)
        self.assertFalse(r["is_valid"])

    def test_non_string_input(self):
        r = validate_bug_title(12345)
        self.assertFalse(r["is_valid"])

    def test_whitespace_is_trimmed(self):
        r = validate_bug_title("  [BUG] Crash on export  ")
        self.assertTrue(r["is_valid"])
        self.assertEqual(r["normalized_title"], "[BUG] Crash on export")

    def test_too_long_body(self):
        self.assertFalse(validate_bug_title("[BUG] " + "x" * 121)["is_valid"])

    def test_run_entrypoint_shape(self):
        out = run({"title": "[BUG] Valid enough title"}, {})
        self.assertEqual(
            set(out.keys()),
            {"is_valid", "reason", "normalized_title", "pattern"},
        )
        self.assertTrue(out["is_valid"])

    def test_run_handles_missing_inputs(self):
        self.assertFalse(run({}, {})["is_valid"])
        self.assertFalse(run(None, None)["is_valid"])

    def test_newline_in_body_rejected(self):
        # '.' does not match newlines; a multi-line title should fail the single-line format.
        self.assertFalse(validate_bug_title("[BUG] line one\nline two")["is_valid"])

    def test_prefix_only_no_body(self):
        self.assertFalse(validate_bug_title("[BUG] ")["is_valid"])

    def test_prefix_without_space(self):
        self.assertFalse(validate_bug_title("[BUG]crash on export")["is_valid"])

    def test_leading_text_before_prefix(self):
        self.assertFalse(validate_bug_title("urgent [BUG] crash")["is_valid"])

    def test_boundary_120_body_accepted(self):
        self.assertTrue(validate_bug_title("[BUG] " + "x" * 120)["is_valid"])

    def test_result_shape_on_invalid(self):
        r = validate_bug_title("nope")
        self.assertEqual(
            set(r.keys()), {"is_valid", "reason", "normalized_title", "pattern"}
        )
        self.assertIsInstance(r["is_valid"], bool)


if __name__ == "__main__":
    unittest.main()
