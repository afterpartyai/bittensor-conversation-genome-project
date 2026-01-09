import pytest
from unittest.mock import MagicMock, patch
from conversationgenome.llm.LlmLib import LlmLib
from conversationgenome.api.models.conversation import Conversation
from conversationgenome.api.models.raw_metadata import RawMetadata
from conversationgenome.api.models.conversation_metadata import ConversationQualityMetadata
from conversationgenome.utils.Utils import Utils


class MockLlmLib(LlmLib):
    def __init__(self):
        super().__init__()
        self.basic_prompt_responses = {}
        self.embedding_responses = {}

    def basic_prompt(self, prompt: str, response_format: str = "text") -> str:
        return self.basic_prompt_responses.get(prompt, "mock response")

    def get_vector_embeddings(self, tag: str) -> list[float]:
        return self.embedding_responses.get(tag, [0.1, 0.2, 0.3])


@pytest.fixture
def mock_llm():
    return MockLlmLib()


def test_get_vector_embeddings_set(mock_llm):
    with patch.object(Utils, 'get_clean_tag_set') as mock_clean:
        mock_clean.return_value = ['tag1', 'tag2']
        mock_llm.embedding_responses = {'tag1': [1.0, 2.0], 'tag2': [3.0, 4.0]}
        result = mock_llm.get_vector_embeddings_set(['tag1', 'tag2'])
        expected = {
            'tag1': {'vectors': [1.0, 2.0]},
            'tag2': {'vectors': [3.0, 4.0]}
        }
        assert result == expected


def test_conversation_to_metadata(mock_llm):
    with patch.object(Utils, 'generate_convo_xml') as mock_xml, \
         patch('conversationgenome.llm.prompt_manager.prompt_manager.conversation_to_metadata_prompt') as mock_prompt_mgr, \
         patch.object(Utils, 'clean_tags') as mock_clean_tags, \
         patch.object(Utils, 'empty') as mock_empty:
        
        mock_xml.return_value = ("<xml>", ["p1", "p2"])
        mock_prompt_mgr.return_value = "prompt"
        mock_llm.basic_prompt_responses = {"prompt": "tag1,tag2"}
        mock_clean_tags.return_value = ["tag1", "tag2"]
        mock_empty.return_value = False
        
        conversation = MagicMock(spec=Conversation)
        result = mock_llm.conversation_to_metadata(conversation)
        
        assert isinstance(result, RawMetadata)
        assert result.tags == ["tag1", "tag2"]
        assert result.vectors is None  # since generateEmbeddings=False


def test_conversation_to_metadata_with_embeddings(mock_llm):
    with patch.object(Utils, 'generate_convo_xml') as mock_xml, \
         patch('conversationgenome.llm.prompt_manager.prompt_manager.conversation_to_metadata_prompt') as mock_prompt_mgr, \
         patch.object(Utils, 'clean_tags') as mock_clean_tags, \
         patch.object(Utils, 'empty') as mock_empty, \
         patch.object(Utils, 'get_clean_tag_set') as mock_clean_set:
        
        mock_xml.return_value = ("<xml>", ["p1", "p2"])
        mock_prompt_mgr.return_value = "prompt"
        mock_llm.basic_prompt_responses = {"prompt": "tag1,tag2"}
        mock_clean_tags.return_value = ["tag1", "tag2"]
        mock_empty.return_value = False
        mock_clean_set.return_value = ["tag1", "tag2"]
        mock_llm.embedding_responses = {'tag1': [1.0], 'tag2': [2.0]}
        
        conversation = MagicMock(spec=Conversation)
        result = mock_llm.conversation_to_metadata(conversation, generateEmbeddings=True)
        
        assert isinstance(result, RawMetadata)
        assert result.tags == ["tag1", "tag2"]
        assert result.vectors == {'tag1': {'vectors': [1.0]}, 'tag2': {'vectors': [2.0]}}


def test_conversation_to_metadata_no_tags(mock_llm):
    with patch.object(Utils, 'generate_convo_xml') as mock_xml, \
         patch('conversationgenome.llm.prompt_manager.prompt_manager.conversation_to_metadata_prompt') as mock_prompt_mgr, \
         patch.object(Utils, 'clean_tags') as mock_clean_tags, \
         patch.object(Utils, 'empty') as mock_empty:
        
        mock_xml.return_value = ("<xml>", ["p1", "p2"])
        mock_prompt_mgr.return_value = "prompt"
        mock_llm.basic_prompt_responses = {"prompt": ""}
        mock_clean_tags.return_value = []
        mock_empty.return_value = True
        
        conversation = MagicMock(spec=Conversation)
        result = mock_llm.conversation_to_metadata(conversation)
        
        assert result is None


def test_raw_transcript_to_named_entities(mock_llm):
    with patch('conversationgenome.llm.prompt_manager.prompt_manager.raw_transcript_to_named_entities_prompt') as mock_prompt_mgr, \
         patch.object(Utils, 'clean_tags') as mock_clean_tags, \
         patch.object(Utils, 'empty') as mock_empty:
        
        mock_prompt_mgr.return_value = "prompt"
        mock_llm.basic_prompt_responses = {"prompt": "entity1,entity2"}
        mock_clean_tags.return_value = ["entity1", "entity2"]
        mock_empty.return_value = False
        
        result = mock_llm.raw_transcript_to_named_entities("transcript")
        
        assert isinstance(result, RawMetadata)
        assert result.tags == ["entity1", "entity2"]


def test_survey_to_metadata(mock_llm):
    with patch('conversationgenome.llm.prompt_manager.prompt_manager.survey_tag_prompt') as mock_prompt_mgr, \
         patch.object(Utils, 'clean_tags') as mock_clean_tags:
        
        mock_prompt_mgr.return_value = "prompt"
        mock_llm.basic_prompt_responses = {"prompt": "tag1,tag2"}
        mock_clean_tags.return_value = ["tag1", "tag2"]
        
        result = mock_llm.survey_to_metadata("question", "comment")
        
        assert isinstance(result, RawMetadata)
        assert result.tags == ["tag1", "tag2"]


def test_validate_conversation_quality(mock_llm):
    with patch.object(Utils, 'generate_convo_xml') as mock_xml, \
         patch('conversationgenome.llm.prompt_manager.prompt_manager.conversation_quality_prompt') as mock_prompt_mgr:
        
        mock_xml.return_value = ("<xml>", ["p1", "p2"])
        mock_prompt_mgr.return_value = "prompt"
        mock_llm.basic_prompt_responses = {"prompt": '{"quality_score": 5}'}
        
        conversation = MagicMock(spec=Conversation)
        result = mock_llm.validate_conversation_quality(conversation)
        
        assert isinstance(result, ConversationQualityMetadata)
        assert result.quality_score == 5


def test_validate_conversation_quality_invalid_json(mock_llm):
    with patch.object(Utils, 'generate_convo_xml') as mock_xml, \
         patch('conversationgenome.llm.prompt_manager.prompt_manager.conversation_quality_prompt') as mock_prompt_mgr:
        
        mock_xml.return_value = ("<xml>", ["p1", "p2"])
        mock_prompt_mgr.return_value = "prompt"
        mock_llm.basic_prompt_responses = {"prompt": "invalid json"}
        
        conversation = MagicMock(spec=Conversation)
        result = mock_llm.validate_conversation_quality(conversation)
        
        assert result is None


def test_validate_tag_set(mock_llm):
    with patch.object(Utils, 'get_clean_tag_set') as mock_clean_set, \
         patch('conversationgenome.llm.prompt_manager.prompt_manager.validate_tags_prompt') as mock_prompt_mgr:
        
        mock_clean_set.return_value = ["tag1", "tag2"]
        mock_prompt_mgr.return_value = "prompt"
        mock_llm.basic_prompt_responses = {"prompt": "good english keywords: tag1, tag2\nmalformed: none"}
        
        result = mock_llm.validate_tag_set(["tag1", "tag2"])
        
        assert result == ["tag1", "tag2"]


def test_validate_tag_set_empty_response(mock_llm):
    with patch.object(Utils, 'get_clean_tag_set') as mock_clean_set, \
         patch('conversationgenome.llm.prompt_manager.prompt_manager.validate_tags_prompt') as mock_prompt_mgr:
        
        mock_clean_set.return_value = ["tag1", "tag2"]
        mock_prompt_mgr.return_value = "prompt"
        mock_llm.basic_prompt_responses = {"prompt": ""}
        
        result = mock_llm.validate_tag_set(["tag1", "tag2"])
        
        assert result is None


def test_validate_named_entities_tag_set(mock_llm):
    with patch.object(Utils, 'get_clean_tag_set') as mock_clean_set:
        mock_clean_set.return_value = ["entity1", "entity2"]
        
        result = mock_llm.validate_named_entities_tag_set(["entity1", "entity2"])
        
        assert result == ["entity1", "entity2"]


def test_validate_named_entities_tag_set_large_list(mock_llm):
    with patch.object(Utils, 'get_clean_tag_set') as mock_clean_set:
        large_list = [f"tag{i}" for i in range(25)]
        mock_clean_set.return_value = large_list
        
        result = mock_llm.validate_named_entities_tag_set(large_list)
        
        assert len(result) == 20  # Should sample to 20
