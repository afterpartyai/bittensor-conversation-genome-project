import pytest
import conversationgenome as cg
from conversationgenome.utils.Utils import Utils
import unittest

class TemplateUtilsTestCase(unittest.TestCase):
    verbose = True

    def setUp(self):
        pass

    def test_safe_tags(self):
        unsafeTags = [
            "hello  world! @#$%^&*()_+-={}:<>?",
            " St. George's Dragon ",
            " St. George's Dragon ",
        ]
        # Visually spot-check various tags
        for tag in unsafeTags:
            safeTag = Utils.get_safe_tag(tag)
            print("Sample tags (visual check)", tag, safeTag, tag == safeTag)

        truthTag = "tag same"
        identicalTags = [
            "tag same",
            " Tag SaMe                 ",
            " Tag_Same   ",
            " tag !!!!!! same ",
            " Tag"+chr(160)+" same", # Non-breaking space
            " _tag __ same-- ",
        ]

        for tag in identicalTags:
            safeTag = Utils.get_safe_tag(tag)
            print(f"Truth match: {truthTag == safeTag}       safe: {safeTag} truth: {truthTag} original: |{tag}| ")
            assert identicalTags[0] == safeTag

        cleanTagSet = Utils.get_clean_tag_set(identicalTags)
        print(f"Clean tags: {cleanTagSet}")
        assert identicalTags[0] == safeTag
