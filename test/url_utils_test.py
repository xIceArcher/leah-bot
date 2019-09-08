import unittest
from utils.url_utils import get_tweet_ids


class GetTweetIdsTest(unittest.TestCase):
    def test_single_url(self):
        ids = get_tweet_ids('https://twitter.com/TVTOKYO_PR/status/1169955731430227968')
        self.assertIsNotNone(ids)
        self.assertEqual(len(ids), 1)
        self.assertIn('1169955731430227968', ids)

    def test_single_url_with_question_mark(self):
        ids = get_tweet_ids('https://twitter.com/TVTOKYO_PR/status/1169955731430227968?s=20')
        self.assertIsNotNone(ids)
        self.assertEqual(len(ids), 1)
        self.assertIn('1169955731430227968', ids)

    def test_multiple_urls(self):
        ids = get_tweet_ids('https://twitter.com/TVTOKYO_PR/status/1169955731430227968\n'
                            'https://twitter.com/box_komiyaarisa/status/1169970460521484288')
        self.assertIsNotNone(ids)
        self.assertEqual(len(ids), 2)
        self.assertIn('1169955731430227968', ids)
        self.assertIn('1169970460521484288', ids)

    def test_duplicates(self):
        ids = get_tweet_ids('https://twitter.com/TVTOKYO_PR/status/1169955731430227968\n'
                            'https://twitter.com/TVTOKYO_PR/status/1169955731430227968')
        self.assertIsNotNone(ids)
        self.assertEqual(len(ids), 1)
        self.assertIn('1169955731430227968', ids)


if __name__ == '__main__':
    unittest.main()
