import random
from typing import List, Optional, Tuple
import uuid

from pydantic import BaseModel

from conversationgenome.ConfigLib import c
from conversationgenome.api.models.conversation_metadata import ConversationMetadata
from conversationgenome.task.Task import Task
from conversationgenome.task.SurveyTaggingTask import SurveyTaggingTask, SurveyTaggingTaskInput
from conversationgenome.task_bundle.TaskBundle import TaskBundle
from conversationgenome.utils.Utils import Utils
from conversationgenome.utils.constants import TaskType


class SurveyTaggingTaskInputData(BaseModel):
    comment: str
    possible_reasons: List[str]
    prompt: str = (
        """Analyze a participant's free-form survey comment to identify all reasons substantiated by the text.
        The comment may be in any language. From the provided list of all possible reasons, return a comma-delimited list of the ones mentioned or strongly implied.
        The data is given in JSON format where the "comment" field contains the free form comment to tag and the "possible_choices" contains a list of possible reasons.
        Only return the tags without any English commentary.
        Example data: {
            "comment": "I primarily stick with them because their mobile app is fantastic for transfers, and the branch is conveniently located right next to my office.",
            "possible_reasons": ["Good mobile application", "Low fees", "Good interest rates", "Helpful in-branch staff", "Tradition/Family habit", "Proximity/Convenience"]
            }
        Example response: ["Good mobile application", "Proximity/Convenience"]
        """
    )


class SurveyTaggingInput(BaseModel):
    input_type: str = "survey_tagging"
    guid: str
    data: SurveyTaggingTaskInputData
    real_reasons: List[str]

class SurveyTaggingTaskBundle(TaskBundle):
    type: TaskType = "survey_tagging"
    input: Optional[SurveyTaggingInput] = None

    def is_ready(self) -> bool:
        return self.input is not None

    async def setup(self) -> None:
        self._split_into_windows()
        self._enforce_minimum_windows()
        await self._generate_metadata()


    def to_mining_tasks(self, number_of_tasks_per_bundle: int) -> List[Task]:
        tasks = []
        
        if len(self.input.data.indexed_windows) > number_of_tasks_per_bundle:
            indexed_windows_subset = random.sample(self.input.data.indexed_windows, number_of_tasks_per_bundle)
        else:
            indexed_windows_subset = self.input.data.indexed_windows

        for _, indexed_window in enumerate(indexed_windows_subset):
            random_id = str(uuid.uuid4())
            task = SurveyTaggingTask(
                mode=self.mode,
                api_version=self.api_version,
                guid=random_id,
                bundle_guid=self.guid,
                type=self.type,
                scoring_mechanism=self.scoring_mechanism,
                input=SurveyTaggingTaskInput(
                    input_type=self.input.input_type,
                    guid=self.input.guid,
                    data=SurveyTaggingTaskInputData(
                        window=indexed_window[1],
                        participants=[]
                    ),
                ),
                prompt_chain=self.prompt_chain,
                example_output=self.example_output,
            )
            tasks.append(task)

        return tasks
    
    
