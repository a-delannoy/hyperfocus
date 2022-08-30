import datetime

import pytest

from hyperfocus.database.models import Task, TaskStatus
from hyperfocus.services.history import History
from hyperfocus.termui import formatter, icons, style


def test_formatter_date():
    date = datetime.datetime(2012, 1, 14)

    pretty_date = formatter.date(date=date)

    expected = "Sat, 14 January 2012"
    assert pretty_date == expected


@pytest.mark.parametrize(
    "status, expected",
    [
        (TaskStatus.TODO, f"[{style.DEFAULT}]{icons.TASK_STATUS}[/]"),
        (TaskStatus.DELETED, f"[{style.ERROR}]{icons.TASK_STATUS}[/]"),
        (TaskStatus.DONE, f"[{style.SUCCESS}]{icons.TASK_STATUS}[/]"),
        (TaskStatus.STASHED, f"[{style.STASHED}]{icons.TASK_STATUS}[/]"),
    ],
)
def test_formatter_task_status(status, expected):
    pretty_status = formatter.task_status(status)

    assert pretty_status == expected


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        ({}, f"[{style.DEFAULT}]⬢[/] foo"),
        ({"show_prefix": True}, f"Task: #1 [{style.DEFAULT}]⬢[/] foo"),
    ],
)
def test_task(kwargs, expected):
    task = Task(id=1, title="foo", details="bar")

    formatted_task = formatter.task(task=task, **kwargs)

    assert formatted_task == expected


def test_stashed_task():
    task = Task(id=3, title="foo", details="bar")

    formatted_task = formatter.stashed_task(old_task_id=1, task=task)

    assert formatted_task == f"Task: #1 [{style.DEFAULT}]⬢[/] foo"


def test_config():
    config = {
        "core.database": "/database.sqlite",
        "alias.st": "status",
    }

    result = formatter.config(config)

    expected = (
        f"[{style.INFO}]core.database[/] = /database.sqlite\n"
        f"[{style.INFO}]alias.st[/] = status"
    )
    assert result == expected


def test_history(mocker):
    history = mocker.Mock(
        **{
            "return_value": iter(
                [
                    datetime.date(2022, 1, 1),
                    Task(title="task1"),
                    Task(title="task2"),
                    datetime.date(2022, 1, 2),
                    Task(title="task3"),
                    Task(title="task4"),
                ]
            ),
        },
        spec=History,
    )

    result = [line for line in formatter.history(history)]

    assert result == [
        "\nSat, 01 January 2022\n",
        "  [bright_white]⬢[/] task1\n",
        "  [bright_white]⬢[/] task2\n",
        "\nSun, 02 January 2022\n",
        "  [bright_white]⬢[/] task3\n",
        "  [bright_white]⬢[/] task4\n",
    ]
