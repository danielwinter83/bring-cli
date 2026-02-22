#!/usr/bin/env python3
"""Bring! Shopping List CLI — wraps miaucl/bring-api for shell use.

Requires environment variables:
  BRING_EMAIL    — Bring! account email
  BRING_PASSWORD — Bring! account password
  BRING_LIST     — Default list UUID (optional for 'lists' command)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from aiohttp import ClientSession
from bring_api import Bring, BringItemOperation


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"Error: {name} environment variable is required", file=sys.stderr)
        sys.exit(1)
    return value


def _require_list_uuid() -> str:
    uuid = os.environ.get("BRING_LIST")
    if not uuid:
        print(
            "Error: BRING_LIST environment variable is required. "
            "Run 'bring lists' to find your list UUID.",
            file=sys.stderr,
        )
        sys.exit(1)
    return uuid


async def _run(args: argparse.Namespace) -> None:
    email = _require_env("BRING_EMAIL")
    password = _require_env("BRING_PASSWORD")

    async with ClientSession() as session:
        bring = Bring(session, email, password)
        await bring.login()

        if args.command == "lists":
            await _cmd_lists(bring, args)
        elif args.command == "list":
            await _cmd_list(bring, args)
        elif args.command == "add":
            await _cmd_add(bring, args)
        elif args.command == "complete":
            await _cmd_complete(bring, args)
        elif args.command == "remove":
            await _cmd_remove(bring, args)


async def _cmd_lists(bring: Bring, args: argparse.Namespace) -> None:
    response = await bring.load_lists()
    lists = response.get("lists", [])
    if args.json:
        print(json.dumps(lists, indent=2, ensure_ascii=False))
        return
    for lst in lists:
        name = lst.get("name", "?")
        uuid = lst.get("listUuid", "?")
        print(f"{name}\t{uuid}")


async def _cmd_list(bring: Bring, args: argparse.Namespace) -> None:
    list_uuid = _require_list_uuid()
    response = await bring.get_list(list_uuid)
    items = response.get("purchase", [])
    if args.json:
        print(json.dumps(items, indent=2, ensure_ascii=False))
        return
    if not items:
        print("(empty list)")
        return
    for item in items:
        name = item.get("name", item.get("itemId", "?"))
        spec = item.get("specification", "")
        line = f"  {name}"
        if spec:
            line += f" ({spec})"
        print(line)


async def _cmd_add(bring: Bring, args: argparse.Namespace) -> None:
    list_uuid = _require_list_uuid()
    items = args.items
    if len(items) == 1:
        await bring.save_item(list_uuid, items[0], args.spec or "")
        spec_msg = f" ({args.spec})" if args.spec else ""
        print(f"Added: {items[0]}{spec_msg}")
    else:
        bring_items = [{"itemId": name, "spec": ""} for name in items]
        await bring.batch_update_list(list_uuid, bring_items, BringItemOperation.ADD)
        print(f"Added {len(items)} items:")
        for name in items:
            print(f"  {name}")


async def _cmd_complete(bring: Bring, args: argparse.Namespace) -> None:
    list_uuid = _require_list_uuid()
    await bring.complete_item(list_uuid, args.item)
    print(f"Completed: {args.item}")


async def _cmd_remove(bring: Bring, args: argparse.Namespace) -> None:
    list_uuid = _require_list_uuid()
    await bring.remove_item(list_uuid, args.item)
    print(f"Removed: {args.item}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bring",
        description="Bring! Shopping List CLI",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # bring lists
    sub.add_parser("lists", help="Show all available lists")

    # bring list
    sub.add_parser("list", help="Show items on the default list")

    # bring add "item" [--spec "detail"] or bring add "a" "b" "c"
    add_parser = sub.add_parser("add", help="Add item(s) to the list")
    add_parser.add_argument("items", nargs="+", help="Item name(s) to add")
    add_parser.add_argument(
        "--spec",
        default="",
        help="Specification (quantity, brand, etc.) — only for single item",
    )

    # bring complete "item"
    complete_parser = sub.add_parser("complete", help="Mark an item as purchased")
    complete_parser.add_argument("item", help="Item name to complete")

    # bring remove "item"
    remove_parser = sub.add_parser("remove", help="Remove an item from the list")
    remove_parser.add_argument("item", help="Item name to remove")

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    try:
        asyncio.run(_run(args))
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
