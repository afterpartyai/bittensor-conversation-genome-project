import random

from conversationgenome import __version__ as CGP_VERSION
from conversationgenome.api.ApiLib import ApiLib
from conversationgenome.task_bundle.NamedEntitiesExtractionTaskBundle import NamedEntitiesExtractionTaskBundle
from conversationgenome.task_bundle.TaskBundle import TaskBundle


class TaskBundleLib:
    async def get_task_bundle(self, hotkey, api_key=None) -> TaskBundle:
        if random.random() > 0.66:
            # For now we build this task locally - Eventually will be moved to the API
            task_bundle: TaskBundle = NamedEntitiesExtractionTaskBundle()
        else:
            api = ApiLib()
            task_bundle: TaskBundle = await api.reserve_task_bundle(hotkey, api_key=api_key)
        
        await task_bundle.setup()

        return task_bundle
