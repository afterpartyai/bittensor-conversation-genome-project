from conversationgenome.llm.prompt_manager import prompt_manager

def test_conversation_quality_prompt():
    conversation_xml = "<conversation><p0>Hello</p0><p1>Hi there!</p1></conversation>"
    prompt = prompt_manager.conversation_quality_prompt(transcript_text=conversation_xml)
    assert conversation_xml in prompt

def test_missing_transcript_text_exception():
    try:
        prompt_manager.conversation_quality_prompt(transcript_text="")
    except Exception as e:
        assert isinstance(e, Exception)

def test_none_transcript_text_exception():
    try:
        prompt_manager.conversation_quality_prompt(transcript_text=None) # type: ignore
    except Exception as e:
        assert isinstance(e, Exception)
