from unittest.mock import Mock

import pytest

from conversationgenome.llm.llm_factory import get_llm_backend

# Full tests
def test_validate_tags_real_prompt():
    tags = ['apple', 'banana', 'carrot']
    llml = get_llm_backend()
    result = llml.validate_tag_set(tags)
    assert set(result) == {'apple', 'banana', 'carrot'}

def test_prompt_rejects_garbled_words():
    tags = ['apple','caskldoij', 'banana', 'bananacakeinonesingleword', 'carrot']
    llml = get_llm_backend()
    result = llml.validate_tag_set(tags)
    print(result)
    assert set(result) == {'apple', 'banana', 'carrot'}

def test_prompt_no_words_raises():
    tags = ['']
    llml = get_llm_backend()
    with pytest.raises(ValueError):
        res = llml.validate_tag_set(tags)

def test_tags_has_only_garbled_words():
    tags = ['asdf;lkjsfd', 'wowthisisasingleverylongword']
    llml = get_llm_backend()
    res = llml.validate_tag_set(tags)
    assert res == []


# Unit tests
def test_validate_tag_set_normal_tags_returns_all_tags():
    llml = get_llm_backend()
    to_return = lambda x: "good english keywords: apple,banana,carrot\nmalformed keywords: "
    llml.basic_prompt = Mock(side_effect=to_return)
    tags = ['apple', 'banana', 'carrot']
    result = llml.validate_tag_set(tags)
    assert set(result) == {'apple', 'banana', 'carrot'}

def test_validate_tag_set_more_than_20_tags_returns_a_subset_of_tags(monkeypatch):
    tags = [f'tag{i}' for i in range(25)]
    to_return = lambda x: 'good english keywords: ' + ','.join(tags[:20]) + '\nmalformed keywords: '

    llml = get_llm_backend()
    llml.basic_prompt = Mock(side_effect=to_return)

    result = llml.validate_tag_set(tags)
    assert len(result) <= 20
    for tag in result:
        assert tag in tags

def test_validate_tag_set_empty_response():
    tags = ['apple', 'banana']
    to_return = lambda x: ''

    llml = get_llm_backend()
    llml.basic_prompt = Mock(side_effect=to_return)

    result = llml.validate_tag_set(tags)
    assert result is None

def test_validate_tag_set_malformed_tags_removes_invalid_tags():
    tags = ['apple', 'ban@na', 'carrot']
    to_return = lambda x: 'good english keywords: apple,carrot\nmalformed keywords: ban@na'

    llml = get_llm_backend()
    llml.basic_prompt = Mock(side_effect=to_return)

    result = llml.validate_tag_set( tags)
    assert set(result) == {'apple', 'carrot'}
