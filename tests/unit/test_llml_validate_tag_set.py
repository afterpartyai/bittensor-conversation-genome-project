from unittest.mock import Mock

from conversationgenome.llm.llm_openai import LlmOpenAI

def test_validate_tag_set_normal_tags_returns_all_tags():
    llml = LlmOpenAI()
    to_return = lambda x: "good english keywords: apple,banana,carrot\nmalformed keywords: "
    llml.basic_prompt = Mock(side_effect=to_return)
    tags = ['apple', 'banana', 'carrot']
    result = llml.validate_tag_set(tags)
    assert set(result) == {'apple', 'banana', 'carrot'}

def test_validate_tag_set_more_than_20_tags_returns_a_subset_of_tags(monkeypatch):
    tags = [f'tag{i}' for i in range(25)]
    to_return = lambda x: 'good english keywords: ' + ','.join(tags[:20]) + '\nmalformed keywords: '

    llml = LlmOpenAI()
    llml.basic_prompt = Mock(side_effect=to_return)

    result = llml.validate_tag_set(tags)
    assert len(result) <= 20
    for tag in result:
        assert tag in tags

def test_validate_tag_set_empty_response():
    tags = ['apple', 'banana']
    to_return = lambda x: ''

    llml = LlmOpenAI()
    llml.basic_prompt = Mock(side_effect=to_return)

    result = llml.validate_tag_set(tags)
    assert result is None

def test_validate_tag_set_malformed_tags_removes_invalid_tags():
    tags = ['apple', 'ban@na', 'carrot']
    to_return = lambda x: 'good english keywords: apple,carrot\nmalformed keywords: ban@na'

    llml = LlmOpenAI()
    llml.basic_prompt = Mock(side_effect=to_return)

    result = llml.validate_tag_set( tags)
    assert set(result) == {'apple', 'carrot'}
