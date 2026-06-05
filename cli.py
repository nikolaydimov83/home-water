#!/usr/bin/env python3
import json
import os
import urllib.request
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
    if args.gpio is not None:
        data["gpio_pin"] = args.gpio
    if args.hour is not None:
        data["hour"] = args.hour
    if args.minute is not None:
        data["minute"] = args.minute
    if args.duration is not None:
        data["duration_sec"] = args.duration
    print(json.dumps(_req("POST", "/tasks", data), indent=2, ensure_ascii=False))


def cmd_list(_):
    print(json.dumps(_req("GET", "/tasks"), indent=2, ensure_ascii=False))


def cmd_show(args):
    print(json.dumps(_req("GET", f"/tasks/{args.id}"), indent=2, ensure_ascii=False))


def cmd_update(args):
    data = {}
    if args.gpio is not None:
        data["gpio_pin"] = args.gpio
    if args.hour is not None:
        data["hour"] = args.hour
    if args.minute is not None:
        data["minute"] = args.minute
    if args.duration is not None:
        data["duration_sec"] = args.duration
    print(
        json.dumps(
            _req("PUT", f"/tasks/{args.id}", data), indent=2, ensure_ascii=False
        )
    )


def cmd_delete(args):
    print(
        json.dumps(
            _req("DELETE", f"/tasks/{args.id}"), indent=2, ensure_ascii=False
        )
    )


def main():
    p = argparse.ArgumentParser(prog="cli")
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
        case "add":
            cmd_add(args)
        case "list":
            cmd_list(args)
        case "show":
            cmd_show(args)
        case "update":
            cmd_update(args)
        case "delete":
            cmd_delete(args)


if __name__ == "__main__":
    main()
