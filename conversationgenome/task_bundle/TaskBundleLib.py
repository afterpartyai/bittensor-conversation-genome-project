from conversationgenome import __version__ as CGP_VERSION
from conversationgenome.api.ApiLib import ApiLib
from conversationgenome.ConfigLib import c
from conversationgenome.task_bundle.TaskBundle import TaskBundle
from conversationgenome.utils.Utils import Utils


class TaskBundleLib:
    async def get_task_bundle(self, hotkey, api_key=None) -> TaskBundle:
        api = ApiLib()
        task_bundle: TaskBundle = await api.reserve_task_bundle(hotkey, api_key=api_key)
        await task_bundle.setup()

        return task_bundle
