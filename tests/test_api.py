import pytest


@pytest.fixture
async def client(aiohttp_client, app):
    return await aiohttp_client(app)


async def test_create_task_with_defaults(client):
    resp = await client.post("/tasks")
    assert resp.status == 201
    data = await resp.json()
    assert data["gpio_pin"] == 26
    assert data["hour"] == 23
    assert data["minute"] == 0
    assert data["duration_sec"] == 7
    assert data["enabled"] is True


async def test_create_task_custom(client):
    resp = await client.post(
        "/tasks", json={"gpio_pin": 20, "hour": 8, "minute": 30, "duration_sec": 10}
    )
    assert resp.status == 201
    data = await resp.json()
    assert data["gpio_pin"] == 20
    assert data["hour"] == 8
    assert data["minute"] == 30
    assert data["duration_sec"] == 10


async def test_get_all_tasks(client):
    await client.post("/tasks", json={"gpio_pin": 20})
    await client.post("/tasks", json={"gpio_pin": 21})
    resp = await client.get("/tasks")
    assert resp.status == 200
    data = await resp.json()
    assert len(data) == 2


async def test_get_one_task(client):
    await client.post("/tasks")
    resp = await client.get("/tasks/1")
    assert resp.status == 200
    data = await resp.json()
    assert data["id"] == 1


async def test_get_one_task_not_found(client):
    resp = await client.get("/tasks/999")
    assert resp.status == 404
    data = await resp.json()
    assert data["error"] == "Not found"


async def test_update_task(client):
    await client.post("/tasks")
    resp = await client.put("/tasks/1", json={"hour": 9, "duration_sec": 5})
    assert resp.status == 200
    data = await resp.json()
    assert data["hour"] == 9
    assert data["duration_sec"] == 5
    assert data["gpio_pin"] == 26


async def test_update_task_partial(client):
    await client.post("/tasks", json={"gpio_pin": 20})
    resp = await client.put("/tasks/1", json={"gpio_pin": 21})
    assert resp.status == 200
    data = await resp.json()
    assert data["gpio_pin"] == 21


async def test_update_task_not_found(client):
    resp = await client.put("/tasks/999", json={"hour": 9})
    assert resp.status == 404


async def test_delete_task(client):
    await client.post("/tasks")
    resp = await client.delete("/tasks/1")
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "deleted"

    resp = await client.get("/tasks/1")
    assert resp.status == 404


async def test_delete_task_not_found(client):
    resp = await client.delete("/tasks/999")
    assert resp.status == 404


async def test_run_now(client):
    resp = await client.post(
        "/tasks/run", json={"gpio_pin": 26, "duration_sec": 3}
    )
    assert resp.status == 202
    data = await resp.json()
    assert data["status"] == "started"
    assert data["gpio_pin"] == 26
    assert data["duration_sec"] == 3


async def test_run_now_with_defaults(client):
    resp = await client.post("/tasks/run", json={})
    assert resp.status == 202
    data = await resp.json()
    assert data["gpio_pin"] == 26
    assert data["duration_sec"] == 7


async def test_set_on(client):
    resp = await client.post("/tasks/on", json={"gpio_pin": 20})
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "on"
    assert data["gpio_pin"] == 20


async def test_set_off(client):
    await client.post("/tasks/on", json={"gpio_pin": 20})
    resp = await client.post("/tasks/off", json={"gpio_pin": 20})
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "off"
    assert data["gpio_pin"] == 20


async def test_set_off_when_already_off(client):
    resp = await client.post("/tasks/off", json={"gpio_pin": 20})
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "off"


async def test_set_on_with_defaults(client):
    resp = await client.post("/tasks/on", json={})
    assert resp.status == 200
    data = await resp.json()
    assert data["gpio_pin"] == 26


async def test_set_off_with_defaults(client):
    resp = await client.post("/tasks/off", json={})
    assert resp.status == 200
    data = await resp.json()
    assert data["gpio_pin"] == 26


async def test_empty_body_creates_with_defaults(client):
    resp = await client.post("/tasks")
    assert resp.status == 201
    data = await resp.json()
    assert data["gpio_pin"] == 26
    assert data["hour"] == 23
    assert data["minute"] == 0
    assert data["duration_sec"] == 7


async def test_update_with_invalid_json(client):
    resp = await client.put("/tasks/1")
    assert resp.status == 400
