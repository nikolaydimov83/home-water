from aiohttp import web

from config import HTTP_HOST, HTTP_PORT
from scheduler import Scheduler


async def create_app() -> web.Application:
    sched = Scheduler()
    await sched.start()

    app = web.Application()
    app["sched"] = sched

    async def on_cleanup(app):
        await sched.shutdown()

    app.on_cleanup.append(on_cleanup)

    async def add(request):
        s = request.app["sched"]
        try:
            data = await request.json()
        except Exception:
            data = {}
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
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON body"}, status=400)
        task = await s.update_task(int(request.match_info["id"]), data)
        if not task:
            return web.json_response({"error": "Not found"}, status=404)
        return web.json_response(task)

    async def delete(request):
        s = request.app["sched"]
        ok = await s.delete_task(int(request.match_info["id"]))
        if not ok:
            return web.json_response({"error": "Not found"}, status=404)
        return web.json_response(
            {"status": "deleted", "id": int(request.match_info["id"])}
        )

    async def run_now(request):
        s = request.app["sched"]
        try:
            data = await request.json()
        except Exception:
            data = {}
        gpio = data.get("gpio_pin", 26)
        duration = data.get("duration_sec", 7)
        result = await s.run_now(gpio, duration)
        return web.json_response(result, status=202)

    async def set_on(request):
        s = request.app["sched"]
        try:
            data = await request.json()
        except Exception:
            data = {}
        gpio = data.get("gpio_pin", 26)
        result = await s.set_on(gpio)
        return web.json_response(result)

    async def set_off(request):
        s = request.app["sched"]
        try:
            data = await request.json()
        except Exception:
            data = {}
        gpio = data.get("gpio_pin", 26)
        result = await s.set_off(gpio)
        return web.json_response(result)

    app.router.add_post("/tasks", add)
    app.router.add_get("/tasks", get_all)
    app.router.add_post("/tasks/run", run_now)
    app.router.add_post("/tasks/on", set_on)
    app.router.add_post("/tasks/off", set_off)
    app.router.add_get("/tasks/{id:\\d+}", get_one)
    app.router.add_put("/tasks/{id:\\d+}", update)
    app.router.add_delete("/tasks/{id:\\d+}", delete)

    return app


if __name__ == "__main__":
    web.run_app(create_app(), host=HTTP_HOST, port=HTTP_PORT)
