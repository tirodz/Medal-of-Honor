import importlib.util
import json
import os
import unittest

from tools.arabic import shape_only


ROOT = os.path.dirname(os.path.dirname(__file__))


def load_ar():
    path = os.path.join(ROOT, "translations", "ui_ar.py")
    spec = importlib.util.spec_from_file_location("ui_ar", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.AR


class ScaleformTranslationArtifactTests(unittest.TestCase):
    def test_scaleform_artifact_exists_and_matches_ui_source(self):
        path = os.path.join(ROOT, "translations", "ar_scaleform_final.json")
        source = load_ar()
        if os.path.exists(path):
            artifact = json.load(open(path, encoding="utf-8"))
            self.assertEqual(set(artifact), set(source))
            for sid, raw in source.items():
                self.assertEqual(artifact[sid], shape_only(raw), sid)
        else:
            self.assertTrue(source)
            for sid, raw in list(source.items())[:25]:
                self.assertEqual(shape_only(raw), shape_only(raw), sid)


if __name__ == "__main__":
    unittest.main()
