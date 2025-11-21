from typing import List
import bittensor as bt
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

class PromptManager:
    def __init__(self, prompt_dir: Path):
        if not prompt_dir.is_dir():
            raise FileNotFoundError(f"Prompt directory not found: {prompt_dir}")
        self.env = Environment(loader=FileSystemLoader(prompt_dir))

    def conversation_to_metadata_prompt(self, conversation_to_analyze: str) -> str:
        if not conversation_to_analyze.strip():
            raise ValueError("conversation_to_analyze cannot be empty.")
        return self._get("conversation_to_metadata.j2", conversation_to_analyze=conversation_to_analyze)

    def conversation_quality_prompt(self, transcript_text: str) -> str:
        if not transcript_text:
            raise ValueError("transcript_text cannot be empty.")
        return self._get("conversation_quality.j2", transcript_text=transcript_text)
    
    def survey_tag_prompt(self, survey_question: str, free_form_comment:str) -> str:
        if not survey_question.strip() or not free_form_comment.strip():
            raise ValueError("survey_question and comment cannot be empty.")
        return self._get("survey_tag.j2", survey_question=survey_question, free_form_comment=free_form_comment)
    
    def validate_tags_prompt(self, tags: List[str]) -> str:
        if not tags:
            raise ValueError("tags cannot be empty.")
        return self._get("validate_tags.j2", tags_string=",".join(tags))

    def _get(self, prompt_location: str, **kwargs) -> str:
        try:
            template = self.env.get_template(prompt_location)
            return template.render(**kwargs)
        except Exception as e:
            bt.logging.error(f"Error processing prompt {prompt_location}: {e}")
            raise e


# Create a singleton instance for easy access
prompt_manager = PromptManager(Path(__file__).parent / "prompts")
