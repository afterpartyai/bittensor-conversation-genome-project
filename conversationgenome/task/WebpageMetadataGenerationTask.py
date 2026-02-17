from typing import List
from typing import Literal
from typing import Optional
from typing import Tuple

import bittensor as bt
from pydantic import BaseModel

from conversationgenome.api.models.conversation import Conversation
from conversationgenome.llm.llm_factory import get_llm_backend
from conversationgenome.task.Task import Task


class WebpageMarkdownTaskInputData(BaseModel):
    window: List[Tuple[int, str]]
    participants: Optional[List[str]] = None

class WebpageMarkdownTaskInput(BaseModel):
    guid: str
    input_type: Literal["webpage_markdown"]
    data: WebpageMarkdownTaskInputData


class WebpageMetadataGenerationTask(Task):
    type: Literal["webpage_metadata_generation"] = "webpage_metadata_generation"
    input: Optional[WebpageMarkdownTaskInput] = None

    async def mine(self) -> dict[str, list]:
        llml = get_llm_backend()

        try:
            all_tags = []
            
            # Process each line in the window
            for idx, (line_idx, content) in enumerate(self.input.data.window):
                if idx == 0:
                    # First line is always the main webpage content
                    result = llml.website_to_metadata(content, generateEmbeddings=False)
                else:
                    # Subsequent lines are enrichment content
                    result = llml.enrichment_to_metadata(content, generateEmbeddings=False)
                
                if result and result.tags:
                    all_tags.append(result.tags)
            
            # Combine all tags from webpage and enrichment content
            if all_tags:
                combined_result = llml.combine_metadata_tags(all_tags, generateEmbeddings=False)
                output = {"tags": combined_result.tags if combined_result else [], "vectors": combined_result.vectors if combined_result else None}
            else:
                output = {"tags": [], "vectors": None}
                
        except Exception as e:
            bt.logging.error(f"Error during mining: {e}")
            raise e

        return output
