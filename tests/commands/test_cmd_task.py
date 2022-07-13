import pytest

from hyperfocus.commands.cmd_task import (
    AddTaskCommand,
    CopyCommand,
    ShowTaskCommand,
    TaskCommand,
    UpdateTasksCommand,
)
from hyperfocus.database.models import Task, TaskStatus
from hyperfocus.exceptions import HyperfocusExit, TaskError
from hyperfocus.services import DailyTracker


@pytest.fixture
def printer(mocker):
    yield mocker.patch("hyperfocus.commands.cmd_task.printer")


@pytest.fixture
def daily_tracker(mocker):
    daily_tracker = mocker.Mock(spec=DailyTracker, instance=True)
    mocker.patch(
        "hyperfocus.commands.cmd_task.DailyTracker.from_date",
        return_value=daily_tracker,
    )
    return daily_tracker


class TestTackCommand:
    def test_task_command_ask_id(self, mocker, test_session, printer, daily_tracker):
        mocker.patch("hyperfocus.commands.cmd_task.TaskCommand.show_tasks")

        TaskCommand(test_session).ask_task_id(text="foobar")

        printer.ask.assert_called_once_with("foobar", type=int)

    def test_task_command_show_tasks_with_no_tasks(
        self, mocker, test_session, printer, daily_tracker
    ):
        daily_tracker.get_tasks.return_value = []

        with pytest.raises(HyperfocusExit):
            TaskCommand(test_session).show_tasks(exclude=[TaskStatus.DONE])

        daily_tracker.get_tasks.assert_called_once_with(exclude=[TaskStatus.DONE])
        printer.echo.assert_called_once_with("No tasks for today...")
        printer.tasks.assert_not_called()

    def test_task_command_show_tasks(
        self, mocker, test_session, printer, daily_tracker
    ):
        daily_tracker.get_tasks.return_value = [mocker.sentinel.task]

        TaskCommand(test_session).show_tasks()

        daily_tracker.get_tasks.assert_called_once_with(exclude=[])
        printer.echo.assert_not_called()
        printer.tasks.assert_called_once_with(
            tasks=[mocker.sentinel.task], newline=False
        )

    def test_task_command_get_task(self, test_session, daily_tracker):
        daily_tracker.get_task.return_value = Task(id=1, title="foo", details="bar")

        task = TaskCommand(test_session).get_task(task_id=1)

        daily_tracker.get_task.assert_called_once_with(task_id=1)
        assert task.id == 1
        assert task.title == "foo"
        assert task.details == "bar"

    def test_task_command_get_task_fails(self, test_session, daily_tracker):
        daily_tracker.get_task.return_value = None

        with pytest.raises(TaskError, match=r"Task \d does not exist."):
            _ = TaskCommand(test_session).get_task(task_id=1)

    def test_task_command_add_task(self, test_session, daily_tracker):
        TaskCommand(test_session).add_task(title="Test", details="foobar")

        daily_tracker.add_task.assert_called_once_with(title="Test", details="foobar")

    def test_task_command_update_task(self, test_session, daily_tracker):
        task = Task(id=1, title="foo", details="bar")

        TaskCommand(test_session).update_task(task=task, status=TaskStatus.DONE)

        daily_tracker.update_task.assert_called_once_with(
            task=task, status=TaskStatus.DONE
        )


@pytest.fixture
def task_command(mocker):
    task_command = mocker.Mock(spec=TaskCommand, instance=True)
    mocker.patch("hyperfocus.commands.cmd_task.TaskCommand", return_value=task_command)
    return task_command


@pytest.fixture
def pyperclip(mocker):
    yield mocker.patch("hyperfocus.commands.cmd_task.pyperclip")


@pytest.fixture
def formatter(mocker):
    yield mocker.patch("hyperfocus.commands.cmd_task.formatter")


class TestAddTaskCommand:
    def test_update_task_command(self, test_session, task_command, printer, formatter):
        task_command.add_task.return_value = Task(id=1, title="foo", details="bar")

        AddTaskCommand(test_session).execute(title="Test", add_details=False)

        printer.ask.assert_not_called()
        formatter.task.assert_called_once()
        printer.success.assert_called_once()

    def test_update_task_command_with_details(
        self, test_session, task_command, printer, formatter
    ):
        task_command.add_task.return_value = Task(id=1, title="foo", details="bar")

        AddTaskCommand(test_session).execute(title="Test", add_details=True)

        printer.ask.assert_called_once_with("Task details")
        formatter.task.assert_called_once()
        printer.success.assert_called_once()


class TestUpdateTasksCommand:
    def test_update_tasks_command(
        self, mocker, test_session, task_command, printer, formatter
    ):
        task1 = Task(id=1, title="foo", details="bar")
        task2 = Task(id=2, title="oof", details="rab")
        task_command.get_task.side_effect = [task1, task2]

        UpdateTasksCommand(test_session).execute(
            task_ids=(1, 2), status=TaskStatus.DONE, text="Test"
        )

        task_command.ask_task_id.assert_not_called()
        task_command.get_task.call_args_list = [
            mocker.call(task1),
            mocker.call(task2),
        ]
        task_command.update_task.call_args_list = [
            mocker.call(task=task1, status=TaskStatus.DONE),
            mocker.call(task=task2, status=TaskStatus.DONE),
        ]
        assert formatter.task.call_count == 2
        assert printer.success.call_count == 2

    def test_update_tasks_command_ask_id_if_none(
        self, mocker, test_session, task_command, printer, formatter
    ):
        task = Task(id=1, title="foo", details="bar")
        task_command.get_task.return_value = task

        UpdateTasksCommand(test_session).execute(
            task_ids=tuple(), status=TaskStatus.DONE, text="Test"
        )

        task_command.ask_task_id.assert_called_once()

    def test_update_tasks_command_with_same_status(
        self, test_session, task_command, printer, formatter
    ):
        task = Task(id=1, title="foo", details="bar", status=TaskStatus.DELETED)
        task_command.get_task.return_value = task

        UpdateTasksCommand(test_session).execute(
            task_ids=(1,), status=TaskStatus.DELETED, text="Test"
        )

        task_command.ask_task_id.assert_not_called()
        task_command.get_task.assert_called_once_with(task_id=1)
        formatter.task.assert_called_once()
        printer.warning.assert_called_once()
        task_command.update_task.assert_not_called()


class TestShowTaskCommand:
    def test_show_task_command(self, test_session, task_command, printer):
        task = Task(id=1, title="foo", details="bar")
        task_command.get_task.return_value = task
        ShowTaskCommand(test_session).execute(task_id=1)

        task_command.ask_task_id.assert_not_called()
        printer.task.assert_called_once_with(
            task=task, show_details=True, show_prefix=True
        )

    def test_show_task_command_ask_id_if_none(
        self, test_session, task_command, printer
    ):
        task = Task(id=1, title="foo", details="bar")
        task_command.get_task.return_value = task
        ShowTaskCommand(test_session).execute(task_id=None)

        task_command.ask_task_id.assert_called_once()


class TestCopyCommand:
    def test_copy_command(self, test_session, printer, pyperclip, task_command):
        task1 = Task(id=1, title="foo", details="bar")
        task_command.ask_task_id.return_value = task1.id
        task_command.get_task.return_value = task1

        CopyCommand(test_session).execute(task_id=1)

        task_command.ask_task_id.assert_not_called()
        pyperclip.copy.assert_called_once_with("bar")
        printer.success.assert_called_once_with(
            "Task 1 details copied to clipboard.", event="success"
        )

    def test_copy_command_fails(self, test_session, printer, pyperclip, task_command):
        task1 = Task(id=1, title="foo", details="")
        task_command.ask_task_id.return_value = task1.id
        task_command.get_task.return_value = task1

        with pytest.raises(TaskError, match=r"Task \d does not have details."):
            CopyCommand(test_session).execute(task_id=None)

        task_command.ask_task_id.assert_called_once_with(text="Copy task details")
        pyperclip.copy.assert_not_called()
        printer.success.assert_not_called()
