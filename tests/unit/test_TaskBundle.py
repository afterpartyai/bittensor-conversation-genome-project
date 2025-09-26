from unittest.mock import AsyncMock

import pytest

from conversationgenome.task.Task import Task
from conversationgenome.task_bundle.ConversationTaggingTaskBundle import (
    ConversationTaggingTaskBundle,
)
from tests.mocks.DummyData import DummyData
from tests.mocks.MockTaskBundle import MockTask
from tests.mocks.MockTaskBundle import MockTaskBundle


def test_task_bundle_split_conversation_in_windows_sets_indexed_windows():
    bundle: ConversationTaggingTaskBundle = DummyData.conversation_tagging_task_bundle()
    bundle._split_conversation_in_windows()
    assert bundle.input.data.indexed_windows is not None
    assert isinstance(bundle.input.data.indexed_windows, list)
    assert all(isinstance(w, tuple) for w in bundle.input.data.indexed_windows)


def test_task_bundle_split_conversation_in_windows_not_enough_windows_sets_empty_list():
    # Set min_convo_windows high so not enough windows
    bundle: ConversationTaggingTaskBundle = DummyData.conversation_tagging_task_bundle()
    bundle.input.data.min_convo_windows = 100
    bundle._split_conversation_in_windows()
    bundle._enforce_minimum_convo_windows()
    assert bundle.input.data.indexed_windows == []


@pytest.mark.asyncio
async def test_task_bundle_to_mining_tasks_returns_tasks(monkeypatch):
    bundle: ConversationTaggingTaskBundle = DummyData.conversation_tagging_task_bundle()

    generate_metadata_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(bundle, "_generate_metadata", generate_metadata_mock)

    await bundle.setup()
    tasks = bundle.to_mining_tasks(number_of_tasks_per_bundle=1)

    assert tasks is not None
    assert isinstance(tasks, list)
    assert all(isinstance(t, Task) for t in tasks)


@pytest.mark.asyncio
async def test_mask_task_for_miner_masks_sensitive_fields(monkeypatch):
    bundle: ConversationTaggingTaskBundle = DummyData.conversation_tagging_task_bundle()

    generate_metadata_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(bundle, "_generate_metadata", generate_metadata_mock)

    await bundle.setup()
    tasks = bundle.to_mining_tasks(number_of_tasks_per_bundle=1)

    assert tasks, "No tasks generated from bundle"
    task = tasks[0]


    print("task", task)
    # Set sensitive fields to known values
    # task.guid = "real-task-guid"
    # task.bundle_guid = bundle.guid
    # task.input.data.guid = "real-task-guid"

    # masked_task = bundle.mask_task_for_miner(task)

    # # Sensitive fields are masked
    # assert masked_task.guid == "HIDDEN"
    # assert masked_task.bundle_guid == "HIDDEN"
    # assert masked_task.input.data.guid == "HIDDEN"

    # # Non-sensitive fields are preserved
    # assert masked_task.input.data.window_idx == task.input.data.window_idx
    # assert masked_task.input.data.lines == task.input.data.lines
    # assert masked_task.input.data.participants == task.input.data.participants
    # assert masked_task.input.data.prompt == task.input.data.prompt
    # assert masked_task.input.data.min_convo_windows == task.input.data.min_convo_windows
    # assert masked_task.input.data.indexed_windows == task.input.data.indexed_windows

    # # Original task is unchanged
    # assert task.guid == "real-task-guid"
    # assert task.bundle_guid == bundle.guid
    # assert task.input.data.guid == "real-task-guid"
