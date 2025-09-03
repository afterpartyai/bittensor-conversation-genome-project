DEFAULT_PROMPTS: dict[str, str] = {
    "conversation_tagging": (
        "Analyze conversation in terms of topic interests of the participants. Analyze the conversation (provided in structured XML format) where <p0> has the questions and <p1> has the answers. Return comma-delimited tags. Only return the tags without any English commentary."
    ),
    "webpage_metadata_generation": (
        "You are given the content of a webpage inside <markdown>...</markdown> tags. Identify the most relevant high-level topics, entities, and concepts that describe the page. Focus only on the core subject matter and ignore navigation menus, boilerplate, or contact info. Return only a flat list of tags in lowercase, separated by commas, with no explanations, formatting, or extra text. Example of required format: tag1, tag2, tag3"
    ),
}

def get_task_default_prompt(task_type: str) -> str | None:
    return DEFAULT_PROMPTS.get(task_type)