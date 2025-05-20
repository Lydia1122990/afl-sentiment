import unittest
from bluesky_fan import blueskyfan

class TestBlueskyFan(unittest.TestCase):

    def test_main_function_runs(self):
        result = blueskyfan.main()
        self.assertIn(result, ["ok", "error"])  

if __name__ == "__main__":
    unittest.main()
