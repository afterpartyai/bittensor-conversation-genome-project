import pytest
import conversationgenome as cg
from conversationgenome.Skeleton import Skeleton
import unittest

class TemplateCgTestCase(unittest.TestCase):
    verbose = True

    def setUp(self):
        pass

    def test_run_single_step(self):
        s = Skeleton()
        response = s.get_skeleton()
        if self.verbose:
            print("Skeleton response: ", response)
        assert response == "Skeleton"

    def test_safe_tags(self):
        unsafeTags = [
            "hello  world! @#$%^&*()_+-={}:<>?",
            " Tag SaMe                 ",
            " Tag_Same   ",
            " tag !!!!!! same ",
            " St. Michael's Dragon ",
            " Tag"+chr(160)+" same",
        ]

