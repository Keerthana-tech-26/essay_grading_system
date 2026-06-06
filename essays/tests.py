from django.test import TestCase
from .utils import grade_text

class GradingTests(TestCase):
    def test_basic_grading(self):
        text = "This is a simple sentence. It has some words. Perhaps it is clear."
        result = grade_text(text)
        self.assertIn('overall', result)
        self.assertGreaterEqual(result['overall'], 0)
        self.assertLessEqual(result['overall'], 100)
