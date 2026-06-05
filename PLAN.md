# План за система за поливане

## Архитектура

```
┌─────────────────┐     HTTP (REST)     ┌──────────────────────────┐
│  Controller      │ ──────────────────→ │  Scheduler (aiohttp)    │
│  (laptop/phone)  │ ←────────────────── │  - event loop           │
│  CLI клиент      │     JSON            │  - in-memory asyncio    │
│  stdlib urllib   │                     │    Task за всяка задача │
└─────────────────┘                     │  - SQLite (aiosqlite)   │
                                         │  - RPi.GPIO             │
                                         └──────────────────────────┘
```

### API

| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/tasks` | Създава задача (всички полета optional) |
| GET | `/tasks` | Списък на всички |
| GET | `/tasks/{id}` | Една задача |
| PUT | `/tasks/{id}` | Partial update |
| DELETE | `/tasks/{id}` | Триене |

### Scheduler логика (asyncio)

- При старт зарежда всички активни задачи от SQLite
- За всяка създава `asyncio.create_task(run_loop(task))`
- `run_loop` → `sleep` до `hour:minute` → пуска релето → след приключване reschedule за следващия ден
- При `POST/PUT/DELETE` → update-ва SQLite + cancel старата asyncio.Task / създава нова
- **Polling = 0**, всичко е event-driven

### Дефолти

- GPIO: 26
- Час: 23:00
- Продължителност: 7 секунди

---

## Файлове

```
home-water/
├── scheduler.py      # aiohttp сървър + asyncio scheduling loop
├── controller.py     # HTTP клиент (CLI, stdlib urllib)
├── database.py       # SQLite CRUD (aiosqlite)
├── relay.py          # GPIO output + mock fallback за dev
├── config.py         # Конфигурация и подразбирания
└── requirements.txt  # dependencies
```

### `config.py`

```python
DEFAULT_GPIO = 26
DEFAULT_HOUR = 23
DEFAULT_MINUTE = 0
DEFAULT_DURATION_SEC = 7

DB_PATH = "/home/nikolay/Documents/homegarden/home-water/schedule.db"

HTTP_HOST = "0.0.0.0"
HTTP_PORT = 8080
```

### `relay.py`

```python
import asyncio

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    _gpio_available = True
except (ImportError, RuntimeError):
    _gpio_available = False


class Relay:
    def __init__(self):
        self._setup = set()

    async def activate(self, pin: int, duration: int) -> None:
        if _gpio_available:
            if pin not in self._setup:
                GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)
                self._setup.add(pin)
            GPIO.output(pin, GPIO.LOW)
            await asyncio.sleep(duration)
            GPIO.output(pin, GPIO.HIGH)
        else:
            print(f"[MOCK] GPIO {pin}: ON for {duration}s")
            await asyncio.sleep(duration)
            print(f"[MOCK] GPIO {pin}: OFF")
```

### `database.py`

```python
import aiosqlite
from config import DEFAULT_GPIO, DEFAULT_HOUR, DEFAULT_MINUTE, DEFAULT_DURATION_SEC


class Database:
    def __init__(self, path: str):
        self.path = path
        self.conn = None

    async def init(self):
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gpio_pin INTEGER NOT NULL DEFAULT 26,
                hour INTEGER NOT NULL DEFAULT 23,
                minute INTEGER NOT NULL DEFAULT 0,
                duration_sec INTEGER NOT NULL DEFAULT 7,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await self.conn.commit()

    async def create(self, data: dict) -> dict:
        gpio = data.get("gpio_pin", DEFAULT_GPIO)
        hour = data.get("hour", DEFAULT_HOUR)
        minute = data.get("minute", DEFAULT_MINUTE)
        duration = data.get("duration_sec", DEFAULT_DURATION_SEC)
        cur = await self.conn.execute(
            "INSERT INTO tasks (gpio_pin, hour, minute, duration_sec) VALUES (?, ?, ?, ?)",
            (gpio, hour, minute, duration),
        )
        await self.conn.commit()
        return await self.get(cur.lastrowid)

    async def get(self, task_id: int) -> dict | None:
        cur = await self.conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = await cur.fetchone()
        return dict(row) if row else None

    async def get_all(self) -> list[dict]:
        cur = await self.conn.execute("SELECT * FROM tasks ORDER BY hour, minute")
        return [dict(r) for r in await cur.fetchall()]

    async def update(self, task_id: int, data: dict) -> dict | None:
        allowed = {"gpio_pin", "hour", "minute", "duration_sec", "enabled"}
        fields = [f"{k} = ?" for k in data if k in allowed]
        values = [data[k] for k in data if k in allowed]
        if not fields:
            return await self.get(task_id)
        fields.append("updated_at = datetime('now')")
        values.append(task_id)
        await self.conn.execute(
            f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?", values
        )
        await self.conn.commit()
        return await self.get(task_id)

    async def delete(self, task_id: int) -> bool:
        cur = await self.conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        await self.conn.commit()
        return cur.rowcount > 0

    async def close(self):
        if self.conn:
            await self.conn.close()
```

### `scheduler.py`

```python
import asyncio
from datetime import datetime, timedelta

from aiohttp import web

from config import DB_PATH, HTTP_HOST, HTTP_PORT
from database import Database
from relay import Relay


class Scheduler:
    def __init__(self):
        self.db = Database(DB_PATH)
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

    async def delete_task(self, task_id: int) -> bool:
        self._unschedule(task_id)
        return await self.db.delete(task_id)


async def create_app() -> web.Application:
    sched = Scheduler()
    await sched.start()

    app = web.Application()
    app["sched"] = sched

    async def add(request):
        s = request.app["sched"]
        data = await request.json() if request.body_exists else {}
        task = await s.add_task(data)
        return web.json_response(task, status=201)

    async def get_all(request):
        s = request.app["sched"]
        tasks = await s.get_all_tasks()
        return web.json_response(tasks)

    async def get_one(request):
        s = request.app["sched"]
        task = await s.get_task(int(request.match_info["id"]))
        if not task:
            return web.json_response({"error": "Not found"}, status=404)
        return web.json_response(task)

    async def update(request):
        s = request.app["sched"]
        data = await request.json()
        task = await s.update_task(int(request.match_info["id"]), data)
        if not task:
            return web.json_response({"error": "Not found"}, status=404)
        return web.json_response(task)

    async def delete(request):
        s = request.app["sched"]
        ok = await s.delete_task(int(request.match_info["id"]))
        if not ok:
            return web.json_response({"error": "Not found"}, status=404)
        return web.json_response({"status": "deleted", "id": int(request.match_info["id"])})

    app.router.add_post("/tasks", add)
    app.router.add_get("/tasks", get_all)
    app.router.add_get("/tasks/{id:\d+}", get_one)
    app.router.add_put("/tasks/{id:\d+}", update)
    app.router.add_delete("/tasks/{id:\d+}", delete)

    return app


if __name__ == "__main__":
    web.run_app(create_app(), host=HTTP_HOST, port=HTTP_PORT)
```

### `controller.py`

```python
#!/usr/bin/env python3
import json
import os
import urllib.request
import urllib.parse
import argparse

SCHEDULER_URL = os.environ.get("SCHEDULER_URL", "http://localhost:8080")


def _req(method, path, data=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(f"{SCHEDULER_URL}{path}", data=body, method=method)
    if body:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def cmd_add(args):
    data = {}
    if args.gpio is not None: data["gpio_pin"] = args.gpio
    if args.hour is not None: data["hour"] = args.hour
    if args.minute is not None: data["minute"] = args.minute
    if args.duration is not None: data["duration_sec"] = args.duration
    print(json.dumps(_req("POST", "/tasks", data), indent=2, ensure_ascii=False))


def cmd_list(_):
    print(json.dumps(_req("GET", "/tasks"), indent=2, ensure_ascii=False))


def cmd_show(args):
    task = _req("GET", f"/tasks/{args.id}")
    print(json.dumps(task, indent=2, ensure_ascii=False))


def cmd_update(args):
    data = {}
    if args.gpio is not None: data["gpio_pin"] = args.gpio
    if args.hour is not None: data["hour"] = args.hour
    if args.minute is not None: data["minute"] = args.minute
    if args.duration is not None: data["duration_sec"] = args.duration
    print(json.dumps(_req("PUT", f"/tasks/{args.id}", data), indent=2, ensure_ascii=False))


def cmd_delete(args):
    print(json.dumps(_req("DELETE", f"/tasks/{args.id}"), indent=2, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser(prog="controller")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("add", help="Нова задача (дефолти: 26, 23:00, 7s)")
    sp.add_argument("--gpio", type=int, help="GPIO пин")
    sp.add_argument("--hour", type=int, help="Час (0-23)")
    sp.add_argument("--minute", type=int, help="Минути (0-59)")
    sp.add_argument("--duration", type=int, help="Секунди работа")

    sp = sub.add_parser("list", help="Списък на всички задачи")
    sp.set_defaults(cmd="list")

    sp = sub.add_parser("show", help="Информация за задача")
    sp.add_argument("id", type=int)

    sp = sub.add_parser("update", help="Промяна на задача")
    sp.add_argument("id", type=int)
    sp.add_argument("--gpio", type=int)
    sp.add_argument("--hour", type=int)
    sp.add_argument("--minute", type=int)
    sp.add_argument("--duration", type=int)

    sp = sub.add_parser("delete", help="Изтриване на задача")
    sp.add_argument("id", type=int)

    args = p.parse_args()
    match args.cmd:
        case "add": cmd_add(args)
        case "list": cmd_list(args)
        case "show": cmd_show(args)
        case "update": cmd_update(args)
        case "delete": cmd_delete(args)


if __name__ == "__main__":
    main()
```

### `requirements.txt`

```
aiohttp>=3.9
aiosqlite>=0.20
RPi.GPIO>=0.7.1
```

---

## Как се използва

**На RPi (scheduler):**
```bash
pip install -r requirements.txt
python scheduler.py   # слуша на 0.0.0.0:8080
```

**От друга машина (controller):**
```bash
export SCHEDULER_URL=http://192.168.1.100:8080

# Създава с дефолти (GPIO 26, 23:00, 7s)
python controller.py add

# Създава с конкретни параметри
python controller.py add --gpio 20 --hour 8 --minute 30 --duration 10

# Променя час на задача 1
python controller.py update 1 --hour 9

# Списък
python controller.py list

# Детайли
python controller.py show 1

# Триене
python controller.py delete 1
```
