import bittensor as bt
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

class PromptManager:
    def __init__(self, prompt_dir: Path):
        if not prompt_dir.is_dir():
            raise FileNotFoundError(f"Prompt directory not found: {prompt_dir}")
        self.env = Environment(loader=FileSystemLoader(prompt_dir))

    def conversation_quality_prompt(self, transcript_text: str) -> str:
        if not transcript_text:
            raise ValueError("transcript_text cannot be empty.")
        return self._get("conversation_quality.j2", transcript_text=transcript_text)

    def _get(self, prompt_location: str, **kwargs) -> str:
        try:
            template = self.env.get_template(prompt_location)
            return template.render(**kwargs)
        except Exception as e:
            bt.logging.error(f"Error processing prompt {prompt_location}: {e}")
            raise e


# Create a singleton instance for easy access
prompt_manager = PromptManager(Path(__file__).parent / "prompts")
