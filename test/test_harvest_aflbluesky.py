import unittest
from functions.aflHarvester.harvest_aflbluesky import harvestByKeyword

class TestBlueskyHarvest(unittest.TestCase):

    def test_harvest_keyword(self):
        headers = {
            "Authorization": "Bearer faketoken"
        }

        keyword = "crows"
        result = harvestByKeyword(keyword, headers=headers)

        self.assertNotEqual(result, "error")

if __name__ == "__main__":
    unittest.main()
