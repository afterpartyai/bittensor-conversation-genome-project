import pytest
from conversationgenome.llm.prompt_manager import prompt_manager


def test_conversation_quality_prompt():
    conversation_xml = "<conversation><p0>Hello</p0><p1>Hi there!</p1></conversation>"
    prompt = prompt_manager.conversation_quality_prompt(transcript_text=conversation_xml)
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert conversation_xml in prompt


def test_conversation_quality_prompt_empty_transcript():
    with pytest.raises(ValueError, match="transcript_text cannot be empty"):
        prompt_manager.conversation_quality_prompt(transcript_text="")


def test_conversation_quality_prompt_none_transcript():
    with pytest.raises(ValueError, match="transcript_text cannot be empty"):
        prompt_manager.conversation_quality_prompt(transcript_text=None)  # type: ignore


def test_conversation_to_metadata_prompt():
    conversation_xml = "<conversation><p0>Hello</p0><p1>Hi there!</p1></conversation>"
    prompt = prompt_manager.conversation_to_metadata_prompt(conversation_to_analyze=conversation_xml)
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert conversation_xml in prompt


def test_conversation_to_metadata_prompt_empty():
    with pytest.raises(ValueError, match="conversation_to_analyze cannot be empty"):
        prompt_manager.conversation_to_metadata_prompt(conversation_to_analyze="")


def test_raw_transcript_to_named_entities_prompt():
    transcript = "Hello, my name is John. I live in New York."
    prompt = prompt_manager.raw_transcript_to_named_entities_prompt(raw_transcript=transcript)
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert transcript in prompt


def test_raw_transcript_to_named_entities_prompt_empty():
    with pytest.raises(ValueError, match="raw_transcript cannot be empty"):
        prompt_manager.raw_transcript_to_named_entities_prompt(raw_transcript="")


def test_survey_tag_prompt():
    question = "What is your favorite color?"
    comment = "I like blue because it's calming."
    prompt = prompt_manager.survey_tag_prompt(survey_question=question, free_form_comment=comment)
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert question in prompt
    assert comment in prompt


def test_survey_tag_prompt_empty_question():
    with pytest.raises(ValueError, match="survey_question and comment cannot be empty"):
        prompt_manager.survey_tag_prompt(survey_question="", free_form_comment="comment")


def test_survey_tag_prompt_empty_comment():
    with pytest.raises(ValueError, match="survey_question and comment cannot be empty"):
        prompt_manager.survey_tag_prompt(survey_question="question", free_form_comment="")


def test_validate_tags_prompt():
    tags = ["tag1", "tag2", "tag3"]
    prompt = prompt_manager.validate_tags_prompt(tags=tags)
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert "tag1,tag2,tag3" in prompt


def test_validate_tags_prompt_empty_list():
    with pytest.raises(ValueError, match="tags cannot be empty"):
        prompt_manager.validate_tags_prompt(tags=[])


def test_validate_tags_prompt_single_tag():
    tags = ["single_tag"]
    prompt = prompt_manager.validate_tags_prompt(tags=tags)
    assert isinstance(prompt, str)
    assert "single_tag" in prompt
