import asyncio
from datetime import datetime, timedelta

from database import Database
from relay import Relay


class Scheduler:
    def __init__(self):
        self.db = Database()
        self.relay = Relay()
        self._tasks: dict[int, asyncio.Task] = {}

    async def start(self):
        await self.db.init()
        for t in await self.db.get_all():
            if t["enabled"]:
                self._schedule(t)

    def _schedule(self, task: dict):
        tid = task["id"]
        if tid in self._tasks:
            self._tasks[tid].cancel()
        self._tasks[tid] = asyncio.create_task(self._run(task))

    async def _run(self, task: dict):
        while True:
            now = datetime.now()
            target = now.replace(
                hour=task["hour"], minute=task["minute"], second=0, microsecond=0
            )
            if target <= now:
                target += timedelta(days=1)

            await asyncio.sleep((target - now).total_seconds())

            print(f"[{target}] GPIO {task['gpio_pin']} for {task['duration_sec']}s")
            await self.relay.activate(task["gpio_pin"], task["duration_sec"])

    def _unschedule(self, task_id: int):
        if task_id in self._tasks:
            self._tasks[task_id].cancel()
            del self._tasks[task_id]

    async def add_task(self, data: dict) -> dict:
        task = await self.db.create(data)
        if task["enabled"]:
            self._schedule(task)
        return task

    async def get_task(self, task_id: int) -> dict | None:
        return await self.db.get(task_id)

    async def get_all_tasks(self) -> list[dict]:
        return await self.db.get_all()

    async def update_task(self, task_id: int, data: dict) -> dict | None:
        task = await self.db.update(task_id, data)
        if not task:
            return None
        if task["enabled"]:
            self._schedule(task)
        else:
            self._unschedule(task_id)
        return task
#
    async def delete_task(self, task_id: int) -> bool:
        self._unschedule(task_id)
        return await self.db.delete(task_id)

    async def run_now(self, gpio_pin: int, duration_sec: int) -> dict:
        asyncio.create_task(self.relay.activate(gpio_pin, duration_sec))
        return {"status": "started", "gpio_pin": gpio_pin, "duration_sec": duration_sec}

    async def set_on(self, gpio_pin: int) -> dict:
        await self.relay.on(gpio_pin)
        return {"status": "on", "gpio_pin": gpio_pin}

    async def set_off(self, gpio_pin: int) -> dict:
        await self.relay.off(gpio_pin)
        return {"status": "off", "gpio_pin": gpio_pin}

    async def shutdown(self):
        for t in self._tasks.values():
            t.cancel()
        await self.db.close()
