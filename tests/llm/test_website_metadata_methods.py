from unittest.mock import Mock, patch
import pytest
from conversationgenome.api.models.raw_metadata import RawMetadata
from conversationgenome.llm.llm_factory import get_llm_backend


def test_website_to_metadata_produces_RawMetadata():
    llml = get_llm_backend()
    website_content = "This is a webpage about artificial intelligence and machine learning."
    res = llml.website_to_metadata(website_content)
    assert res is not None
    assert type(res) == RawMetadata


def test_website_to_metadata_does_not_produce_embeds():
    llml = get_llm_backend()
    website_content = "This is a webpage about artificial intelligence and machine learning."
    res = llml.website_to_metadata(website_content, False)
    assert res is not None
    assert len(res.tags)
    assert res.success == True
    assert res.vectors is None


def test_website_to_metadata_produces_embeds_if_specified():
    llml = get_llm_backend()
    website_content = "This is a webpage about artificial intelligence and machine learning."
    res = llml.website_to_metadata(website_content, True)
    assert res is not None
    assert len(res.tags)
    assert res.success == True
    assert len(res.vectors)
    assert len(res.tags) == len(res.vectors)


def test_website_to_metadata_returns_none_on_empty_content():
    llml = get_llm_backend()
    with pytest.raises(ValueError, match="website_content cannot be empty"):
        llml.website_to_metadata("")


def test_website_to_metadata_cleans_tags():
    llml = get_llm_backend()
    llml.basic_prompt = Mock(side_effect=lambda x: 'artificial intelligence          , machine learning,\n data science, \tdeep learning')
    res = llml.website_to_metadata("test content")
    assert res is not None
    assert len(res.tags) == 4
    assert 'artificial intelligence' in res.tags
    assert 'machine learning' in res.tags
    assert 'data science' in res.tags
    assert 'deep learning' in res.tags


def test_enrichment_to_metadata_produces_RawMetadata():
    llml = get_llm_backend()
    enrichment_content = "AI Research Breakthrough\nNew developments in artificial intelligence research show promising results."
    res = llml.enrichment_to_metadata(enrichment_content)
    assert res is not None
    assert type(res) == RawMetadata


def test_enrichment_to_metadata_does_not_produce_embeds():
    llml = get_llm_backend()
    enrichment_content = "AI Research Breakthrough\nNew developments in artificial intelligence research show promising results."
    res = llml.enrichment_to_metadata(enrichment_content, False)
    assert res is not None
    assert len(res.tags)
    assert res.success == True
    assert res.vectors is None


def test_enrichment_to_metadata_produces_embeds_if_specified():
    llml = get_llm_backend()
    enrichment_content = "AI Research Breakthrough\nNew developments in artificial intelligence research show promising results."
    res = llml.enrichment_to_metadata(enrichment_content, True)
    assert res is not None
    assert len(res.tags)
    assert res.success == True
    assert len(res.vectors)
    assert len(res.tags) == len(res.vectors)


def test_enrichment_to_metadata_returns_none_on_empty_content():
    llml = get_llm_backend()
    with pytest.raises(ValueError, match="enrichment_content cannot be empty"):
        llml.enrichment_to_metadata("")


def test_enrichment_to_metadata_cleans_tags():
    llml = get_llm_backend()
    llml.basic_prompt = Mock(side_effect=lambda x: 'climate change          , environmental policy,\n carbon emissions, \tsustainable development')
    res = llml.enrichment_to_metadata("test content")
    assert res is not None
    assert len(res.tags) == 4
    assert 'climate change' in res.tags
    assert 'environmental policy' in res.tags
    assert 'carbon emissions' in res.tags
    assert 'sustainable development' in res.tags


def test_combine_metadata_tags_produces_RawMetadata():
    llml = get_llm_backend()
    metadata_tags = [["artificial intelligence", "machine learning"], ["data science", "deep learning"]]
    res = llml.combine_metadata_tags(metadata_tags)
    assert res is not None
    assert type(res) == RawMetadata


def test_combine_metadata_tags_does_not_produce_embeds():
    llml = get_llm_backend()
    metadata_tags = [["artificial intelligence", "machine learning"], ["data science", "deep learning"]]
    res = llml.combine_metadata_tags(metadata_tags, False)
    assert res is not None
    assert len(res.tags)
    assert res.success == True
    assert res.vectors is None


def test_combine_metadata_tags_produces_embeds_if_specified():
    llml = get_llm_backend()
    metadata_tags = [["artificial intelligence", "machine learning"], ["data science", "deep learning"]]
    res = llml.combine_metadata_tags(metadata_tags, True)
    assert res is not None
    assert len(res.tags)
    assert res.success == True
    assert len(res.vectors)
    assert len(res.tags) == len(res.vectors)


def test_combine_metadata_tags_returns_none_on_empty_tags():
    llml = get_llm_backend()
    res = llml.combine_metadata_tags([])
    assert res is None


def test_combine_metadata_tags_cleans_tags():
    llml = get_llm_backend()
    llml.basic_prompt = Mock(side_effect=lambda x: 'artificial intelligence          , machine learning,\n data science, \tdeep learning')
    res = llml.combine_metadata_tags([["ai", "ml"], ["ds", "dl"]])
    assert res is not None
    assert len(res.tags) == 4
    assert 'artificial intelligence' in res.tags
    assert 'machine learning' in res.tags
    assert 'data science' in res.tags
    assert 'deep learning' in res.tags