import pytest
from conversationgenome.api.models.raw_metadata import RawMetadata
from conversationgenome.llm.LlmLib import LlmLib

@pytest.mark.asyncio
async def test_prompt_produces_list():
    question = 'Why are you staying with Poutine Inc. Bank?'
    comment = "They're kinda nice I guess. Sometimes they have good deals when transfering cash."
    llml = LlmLib()
    res = await llml.survey_to_metadata(question, comment)
    assert isinstance(res, RawMetadata)
    assert isinstance(res.tags, list)
    assert isinstance(res.vectors, dict)
    assert len(res.tags) > 0

@pytest.mark.asyncio
async def test_prompt_with_clear_multi_concept_comment():
    question = "Why do you prefer our airline for your travel needs?"
    comment = "The flight attendants are always so friendly and professional, and I find that your boarding process is much more organized than other airlines."
    llml = LlmLib()
    res = await llml.survey_to_metadata(question, comment)
    
    assert isinstance(res, RawMetadata)
    assert isinstance(res.tags, list)
    assert isinstance(res.vectors, dict)
    assert len(res.tags) >= 2, "Should extract at least two distinct concepts"

@pytest.mark.asyncio
async def test_prompt_with_mixed_sentiment_comment():
    question = "Why did you choose our internet service?"
    comment = "The download speed is incredible for the price, which is why I signed up. I do wish your customer support was a bit faster to respond, though."
    llml = LlmLib()
    res = await llml.survey_to_metadata(question, comment)
    
    assert isinstance(res, RawMetadata)
    assert isinstance(res.tags, list)
    assert isinstance(res.vectors, dict)
    assert len(res.tags) > 0, "Should extract the positive reason"

@pytest.mark.asyncio
async def test_prompt_with_conceptual_comment():
    question = "What makes our software a valuable tool for your team?"
    comment = "I can get a new employee up and running on the system in less than an hour, which is a huge time-saver for me."
    llml = LlmLib()
    res = await llml.survey_to_metadata(question, comment)
    
    assert isinstance(res, RawMetadata)
    assert isinstance(res.tags, list)
    assert isinstance(res.vectors, dict)
    assert len(res.tags) > 0, "Should distill the comment"

@pytest.mark.asyncio
async def test_prompt_with_non_english_comment():

    question = "P9. ¿Por qué razones prefiere ese banco?"
    comment = "Tienen sucursales por toda la ciudad, así que siempre hay una cerca. Además, mis padres usaban este banco, así que es una costumbre."
    llml = LlmLib()
    res = await llml.survey_to_metadata(question, comment)
    
    assert isinstance(res, RawMetadata)
    assert isinstance(res.tags, list)
    assert isinstance(res.vectors, dict)
    assert len(res.tags) >= 2, "Should extract two concepts from the Spanish comment"
    
@pytest.mark.asyncio
async def test_empty_comment_raises_value_error():
    question = "Why do you use our delivery service?"
    comment = ""
    llml = LlmLib()

    with pytest.raises(ValueError) as excinfo:
        await llml.survey_to_metadata(question, comment)
    assert "survey_question and comment cannot be empty" in str(excinfo.value)

@pytest.mark.asyncio
async def test_whitespace_question_raises_value_error():
    question = "   "
    comment = "This is a valid comment."
    llml = LlmLib()

    with pytest.raises(ValueError) as excinfo:
        await llml.survey_to_metadata(question, comment)
    assert "survey_question and comment cannot be empty" in str(excinfo.value)
