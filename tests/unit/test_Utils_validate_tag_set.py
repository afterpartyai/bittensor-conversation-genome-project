import pytest

from conversationgenome.utils.Utils import Utils


class DummyLLML:
    def __init__(self, response_content):
        self.response_content = response_content

    async def prompt_call_csv(self, override_prompt=None):
        return {'content': self.response_content}


@pytest.mark.asyncio
async def test_validate_tag_set_normal_tags_returns_all_tags(monkeypatch):
    tags = ['apple', 'banana', 'carrot']
    llml = DummyLLML('good english keywords: apple,banana,carrot\nmalformed keywords: ')

    result = await Utils.validate_tag_set(llml, tags)
    assert set(result) == {'apple', 'banana', 'carrot'}


@pytest.mark.asyncio
async def test_validate_tag_set_more_than_20_tags_returns_a_subset_of_tags(monkeypatch):
    tags = [f'tag{i}' for i in range(25)]
    llml = DummyLLML('good english keywords: ' + ','.join(tags[:20]) + '\nmalformed keywords: ')

    result = await Utils.validate_tag_set(llml, tags)
    assert len(result) <= 20
    for tag in result:
        assert tag in tags


@pytest.mark.asyncio
async def test_validate_tag_set_empty_response():
    tags = ['apple', 'banana']
    llml = DummyLLML('')

    result = await Utils.validate_tag_set(llml, tags)
    assert result is None


@pytest.mark.asyncio
async def test_validate_tag_set_malformed_tags_removes_invalid_tags():
    tags = ['apple', 'ban@na', 'carrot']

    llml = DummyLLML('good english keywords: apple,carrot\nmalformed keywords: ban@na')

    result = await Utils.validate_tag_set(llml, tags)
    assert set(result) == {'apple', 'carrot'}
