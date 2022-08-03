import unittest
from flask import current_app
from app.app_factory import create_app


class BasicTests(unittest.TestCase):
    def setup(self):
        self.app = create_app()

    def test_app_was_created(self):
        self.assertFalse(current_app is None)
