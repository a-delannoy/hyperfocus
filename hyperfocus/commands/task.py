from __future__ import annotations

import pyperclip

from hyperfocus import printer
from hyperfocus.commands.core import HyperfocusCommand
from hyperfocus.database.models import Task, TaskStatus
from hyperfocus.exceptions import HyperfocusExit, TaskError
from hyperfocus.services import DailyTrackerService
from hyperfocus.session import Session


class TaskCommand(HyperfocusCommand):
    def __init__(self, session: Session):
        super().__init__(session=session)
        self._daily_tracker = DailyTrackerService.from_date(session.date)

    def check_task_id_or_ask(self, task_id: int | None, text: str) -> int:
        if task_id:
            return task_id

        self.show_tasks(newline=True)

        return printer.ask(text, type=int)

    def show_tasks(
        self, exclude: list[TaskStatus] | None = None, newline=False
    ) -> None:
        exclude = exclude or []
        tasks = self._daily_tracker.get_tasks(exclude=exclude)

        if not tasks:
            printer.echo("No tasks for today...")
            raise HyperfocusExit()

        printer.tasks(tasks=tasks, newline=newline)

    def get_task(self, task_id: int) -> Task:
        task = self._daily_tracker.get_task(task_id=task_id)
        if not task:
            raise TaskError(f"Task {task_id} does not exist.")

        return task


class CopyCommand(HyperfocusCommand):
    def __init__(self, session: Session):
        super().__init__(session=session)
        self._task_command = TaskCommand(session)

    def execute(self, task_id: int | None):
        task_id = self._task_command.check_task_id_or_ask(
            task_id=task_id, text="Copy task details"
        )

        task = self._task_command.get_task(task_id=task_id)
        if not task.details:
            raise TaskError(f"Task {task_id} does not have details.")

        pyperclip.copy(task.details)
        printer.success(f"Task {task_id} details copied to clipboard.", event="success")
