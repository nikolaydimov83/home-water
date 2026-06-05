from tortoise.models import Model
from tortoise import fields, Tortoise

import config


class Task(Model):
    id = fields.IntField(pk=True)
    gpio_pin = fields.IntField(default=26)
    hour = fields.IntField(default=23)
    minute = fields.IntField(default=0)
    duration_sec = fields.IntField(default=7)
    enabled = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "tasks"


class Database:
    async def init(self):
        await Tortoise.init(
            db_url=f"sqlite://{config.DB_PATH}",
            modules={"models": [__name__]},
            _enable_global_fallback=True,
        )
        await Tortoise.generate_schemas()

    async def create(self, data: dict) -> dict:
        task = await Task.create(
            gpio_pin=data.get("gpio_pin", 26),
            hour=data.get("hour", 23),
            minute=data.get("minute", 0),
            duration_sec=data.get("duration_sec", 7),
            enabled=data.get("enabled", True),
        )
        return await self._serialize(task)

    async def get(self, task_id: int) -> dict | None:
        task = await Task.get_or_none(id=task_id)
        return await self._serialize(task) if task else None

    async def get_all(self) -> list[dict]:
        tasks = await Task.all().order_by("hour", "minute")
        return [await self._serialize(t) for t in tasks]

    async def update(self, task_id: int, data: dict) -> dict | None:
        task = await Task.get_or_none(id=task_id)
        if not task:
            return None
        allowed = {"gpio_pin", "hour", "minute", "duration_sec", "enabled"}
        for k, v in data.items():
            if k in allowed:
                setattr(task, k, v)
        await task.save()
        return await self._serialize(task)

    async def delete(self, task_id: int) -> bool:
        task = await Task.get_or_none(id=task_id)
        if not task:
            return False
        await task.delete()
        return True

    async def close(self):
        await Tortoise.close_connections()

    async def _serialize(self, task: Task) -> dict:
        return {
            "id": task.id,
            "gpio_pin": task.gpio_pin,
            "hour": task.hour,
            "minute": task.minute,
            "duration_sec": task.duration_sec,
            "enabled": task.enabled,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
        }
