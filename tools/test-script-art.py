"""Regression coverage for durable scene-specific portrait selection."""
import copy
import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("script_v2", Path(__file__).with_name("script_v2.py"))
script = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(script)


class SceneArtTests(unittest.TestCase):
    def test_explicit_portrait_overrides_survive_filtering_without_changing_base(self):
        base = {"c1_flat": {"company": ["steve", "iris"], "appearances": {"iris": "iris"}}}
        original = copy.deepcopy(base)
        content = {"scenes": [{"id": "c1_flat", "tasks": []}], "lines": {}}
        selected = {"c1_flat": {"steve": "steve_morning"}}
        result = script.filter_illustrated_campaign(base, content, selected)
        self.assertEqual(result["c1_flat"]["appearances"],
                         {"iris": "iris", "steve": "steve_morning"})
        self.assertEqual(base, original)

    def test_absent_overrides_preserve_original_appearances(self):
        base = {"epilogue": {"company": ["iris"], "appearances": {"iris": "iris_epilogue"}}}
        content = {"scenes": [{"id": "epilogue", "tasks": []}], "lines": {}}
        self.assertEqual(script.filter_illustrated_campaign(base, content), base)


if __name__ == "__main__":
    unittest.main()
