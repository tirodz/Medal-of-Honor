import unittest

from tools.arabic import process, shape_only


class ArabicRenderingModesTests(unittest.TestCase):
    def test_scaleform_keeps_logical_order(self):
        text = "سلام بالعالم"
        logical = shape_only(text)
        visual = process(text)
        self.assertNotEqual(logical, visual)
        self.assertEqual(logical, "ﺳﻼﻡ ﺑﺎﻟﻌﺎﻟﻢ")

    def test_scaleform_preserves_mixed_latin_and_numbers_logically(self):
        text = "2 من 3 دبابات"
        shaped = shape_only(text)
        visual = process(text)
        self.assertIn("2", shaped)
        self.assertIn("3", shaped)
        self.assertNotEqual(shaped, visual)

    def test_control_codes_remain_atomic(self):
        text = "اضغط $ACTION ثم %1"
        for fn in (shape_only, process):
            out = fn(text)
            self.assertIn("$ACTION", out)
            self.assertIn("%1", out)
            self.assertNotIn("NOITCA", out)

    def test_line_separators_are_preserved(self):
        text = "سلام\\nالعالم|مرحبا"
        for fn in (shape_only, process):
            out = fn(text)
            self.assertEqual(out.count("\\n"), 1)
            self.assertEqual(out.count("|"), 1)


if __name__ == "__main__":
    unittest.main()
