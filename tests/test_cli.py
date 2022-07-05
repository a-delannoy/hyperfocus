from datetime import datetime

import pytest
from click.testing import CliRunner

from hyperfocus import __app_name__, __version__
from hyperfocus.cli import cli
from hyperfocus.config import Config
from hyperfocus.models import Task, TaskStatus
from tests.conftest import pytest_regex

runner = CliRunner()


def test_main_cmd_version():
    result = runner.invoke(cli, ["--version"])

    expected = f"{__app_name__}, version {__version__}\n"
    assert expected == result.stdout


def test_init_cmd(mocker, tmp_test_dir):
    db_path = tmp_test_dir / "test_db.sqlite"
    config = Config(db_path=db_path, dir_path=tmp_test_dir)
    mocker.patch("hyperfocus.cli.Config", return_value=config)

    result = runner.invoke(cli, ["init"], input=f"{db_path}\n")

    pattern = pytest_regex(
        r"\? Database location \[(.*)\]: (.*)\n"
        r"ℹ\(init\) Config file created successfully in (.*)\n"
        r"ℹ\(init\) Database initialized successfully in (.*)\n"
    )
    assert pattern == result.stdout
    assert result.exit_code == 0


def test_status_cmd_without_tasks(cli_session):
    cli_session.daily_tracker.new_day = True
    cli_session.daily_tracker.date = datetime(2012, 12, 21, 0, 0)
    cli_session.daily_tracker.get_tasks.return_value = []

    result = runner.invoke(cli, ["status"])

    expected = (
        "✨ Fri, 21 December 2012\n"
        "✨ A new day starts, good luck!\n\n"
        "No tasks for today...\n"
    )
    assert expected == result.stdout
    assert result.exit_code == 0


def test_status_cmd_without_task(cli_session):
    cli_session.daily_tracker.get_tasks.return_value = []

    result = runner.invoke(cli, ["status"])

    expected = "No tasks for today...\n"
    assert expected == result.stdout
    assert result.exit_code == 0


def test_status_cmd_with_tasks(cli_session):
    task = Task(id=1, title="Test", details="Test")
    cli_session.daily_tracker.get_tasks.return_value = [task]

    result = runner.invoke(cli, ["status"])

    expected = "  #  tasks\n---  --------\n  1  ⬢ Test ⊕ \n\n"
    assert result.stdout == expected
    assert result.exit_code == 0


def test_add_cmd_task_without_details(cli_session):
    task = Task(id=1, title="Test")
    cli_session.daily_tracker.add_task.return_value = task

    result = runner.invoke(cli, ["add", "Test"])

    expected = "✔(created) Task: #1 ⬢ Test ◌\n"
    assert expected == result.stdout
    assert result.exit_code == 0


def test_add_cmd_task_with_details(cli_session):
    task = Task(id=1, title="Test", details="Test")
    cli_session.daily_tracker.add_task.return_value = task

    result = runner.invoke(cli, ["add", "Test", "-d"], input="Test\n")

    expected = "? Task details: Test\n" "✔(created) Task: #1 ⬢ Test ⊕\n"
    assert expected == result.stdout
    assert result.exit_code == 0


@pytest.mark.parametrize(
    "command",
    [
        "delete",
        "done",
        "block",
        "reset",
        "show",
    ],
)
def test_done_cmd_non_existing_task(cli_session, command):
    cli_session.daily_tracker.get_task.return_value = None

    result = runner.invoke(cli, [command, "9"])

    expected = "✘(not found) Task 9 does not exist\n"
    assert expected == result.stdout
    assert result.exit_code == 1
    cli_session.daily_tracker.update_task.assert_not_called()


def test_reset_cmd_task(cli_session):
    task = Task(id=1, title="Test", details="Test", status=TaskStatus.DONE)
    cli_session.daily_tracker.get_task.return_value = task

    result = runner.invoke(cli, ["reset", "1"])

    expected = "✔(updated) Task: #1 ⬢ Test ⊕\n"
    assert expected == result.stdout
    assert result.exit_code == 0
    cli_session.daily_tracker.get_task.assert_called_once_with(task_id=1)
    cli_session.daily_tracker.update_task.assert_called_once_with(
        status=TaskStatus.TODO, task=task
    )


def test_reset_cmd_task_on_already_reset_task(cli_session):
    task = Task(id=1, title="Test", details="Test")
    cli_session.daily_tracker.get_task.return_value = task

    result = runner.invoke(cli, ["reset", "1"])

    expected = "▼(no change) Task: #1 ⬢ Test ⊕\n"
    assert expected == result.stdout
    assert result.exit_code == 0
    cli_session.daily_tracker.get_task.assert_called_once_with(task_id=1)
    cli_session.daily_tracker.update_task.assert_not_called()


@pytest.mark.parametrize(
    "command, updated",
    [
        ("delete", TaskStatus.DELETED),
        ("done", TaskStatus.DONE),
        ("block", TaskStatus.BLOCKED),
    ],
)
def test_update_status_cmd_task(cli_session, command, updated):
    task = Task(id=1, title="Test", details="Test")
    cli_session.daily_tracker.get_task.return_value = task

    result = runner.invoke(cli, [command, "1"])

    expected = "✔(updated) Task: #1 ⬢ Test ⊕\n"
    assert expected == result.stdout
    assert result.exit_code == 0
    cli_session.daily_tracker.get_task.assert_called_once_with(task_id=1)
    cli_session.daily_tracker.update_task.assert_called_once_with(
        status=updated, task=task
    )


def test_show_cmd_task(cli_session):
    task = Task(id=1, title="Test", details="Test")
    cli_session.daily_tracker.get_task.return_value = task

    result = runner.invoke(cli, ["show", "1"])

    expected = "Task: #1 ⬢ Test\n" "Test\n"
    assert expected == result.stdout
    assert result.exit_code == 0
    cli_session.daily_tracker.get_task.assert_called_once_with(task_id=1)


def test_update_task_with_no_id(cli_session):
    task = Task(id=1, title="Test", details="Test", status=TaskStatus.DONE.value)
    cli_session.daily_tracker.get_tasks.return_value = [task]
    cli_session.daily_tracker.get_task.return_value = task

    result = runner.invoke(cli, ["reset"], input="1")

    expected = (
        "  #  tasks\n"
        "---  --------\n"
        "  1  ⬢ Test ⊕ \n\n"
        "? Reset task: 1\n"
        "✔(updated) Task: #1 ⬢ Test ⊕\n"
    )
    assert expected == result.stdout
    assert result.exit_code == 0
    cli_session.daily_tracker.get_task.assert_called_once_with(task_id=1)
    cli_session.daily_tracker.update_task.assert_called_once_with(
        status=TaskStatus.TODO, task=task
    )


def test_show_cmd_task_with_no_id(cli_session):
    task = Task(id=1, title="Test", details="Test")
    cli_session.daily_tracker.get_tasks.return_value = [task]
    cli_session.daily_tracker.get_task.return_value = task

    result = runner.invoke(cli, ["show"], input="1")

    expected = (
        "  #  tasks\n"
        "---  --------\n"
        "  1  ⬢ Test ⊕ \n\n"
        "? Show task details: 1\n"
        "Task: #1 ⬢ Test\n"
        "Test\n"
    )
    assert expected == result.stdout
    assert result.exit_code == 0
    cli_session.daily_tracker.get_task.assert_called_once_with(task_id=1)


def test_copy_non_existing_task_cmd(mocker, cli_session):
    cli_session.daily_tracker.get_task.return_value = None
    pyperclip = mocker.patch("hyperfocus.cli.pyperclip")

    result = runner.invoke(cli, ["copy", "9"])

    expected = "✘(not found) Task 9 does not exist\n"
    assert expected == result.stdout
    assert result.exit_code == 1
    cli_session.daily_tracker.get_task.assert_called_once_with(task_id=9)
    pyperclip.assert_not_called()


def test_copy_task_without_details_cmd(mocker, cli_session):
    task = Task(id=1, title="Test", details="")
    cli_session.daily_tracker.get_task.return_value = task
    pyperclip = mocker.patch("hyperfocus.cli.pyperclip")

    result = runner.invoke(cli, ["copy", "1"])

    expected = "✘(not found) Task 1 does not have details\n"
    assert expected == result.stdout
    assert result.exit_code == 1
    cli_session.daily_tracker.get_task.assert_called_once_with(task_id=1)
    pyperclip.assert_not_called()


def test_copy_task_with_details_cmd(mocker, cli_session):
    task = Task(id=1, title="Test", details=mocker.sentinel.details)
    cli_session.daily_tracker.get_tasks.return_value = [task]
    cli_session.daily_tracker.get_task.return_value = task
    pyperclip = mocker.patch("hyperfocus.cli.pyperclip")

    result = runner.invoke(cli, ["copy"], input="1\n")

    expected = (
        "  #  tasks\n"
        "---  --------\n"
        "  1  ⬢ Test ⊕ \n\n"
        "? Copy task details: 1\n"
        "✔(copied) Task 1 details copied to clipboard\n"
    )
    assert expected == result.stdout
    assert result.exit_code == 0
    cli_session.daily_tracker.get_task.assert_called_once_with(task_id=1)
    pyperclip.copy.assert_called_once_with(mocker.sentinel.details)
