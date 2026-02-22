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
import re
import sys

from aiohttp import ClientSession, ClientTimeout

from bring_api import Bring, BringItemOperation

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

MAX_ITEM_LEN = 256
MAX_SPEC_LEN = 128
HTTP_TIMEOUT = ClientTimeout(total=30)


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"Error: {name} environment variable is required", file=sys.stderr)
        sys.exit(1)
    return value


def _require_list_uuid() -> str:
    uuid = os.environ.get("BRING_LIST", "").strip()
    if not uuid:
        print(
            "Error: BRING_LIST environment variable is required. "
            "Run 'bring lists' to find your list UUID.",
            file=sys.stderr,
        )
        sys.exit(1)
    if not _UUID_RE.match(uuid):
        print(
            "Error: BRING_LIST does not look like a valid UUID.",
            file=sys.stderr,
        )
        sys.exit(1)
    return uuid


def _validate_item(name: str) -> str:
    name = name.strip()
    if not name:
        print("Error: item name must not be empty", file=sys.stderr)
        sys.exit(1)
    if len(name) > MAX_ITEM_LEN:
        print(
            f"Error: item name must be {MAX_ITEM_LEN} characters or fewer",
            file=sys.stderr,
        )
        sys.exit(1)
    return name


def _validate_spec(spec: str) -> str:
    spec = spec.strip()
    if len(spec) > MAX_SPEC_LEN:
        print(
            f"Error: specification must be {MAX_SPEC_LEN} characters or fewer",
            file=sys.stderr,
        )
        sys.exit(1)
    return spec


async def _run(args: argparse.Namespace) -> None:
    email = _require_env("BRING_EMAIL")
    password = _require_env("BRING_PASSWORD")

    async with ClientSession(timeout=HTTP_TIMEOUT) as session:
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
        else:
            print(f"Error: unknown command '{args.command}'", file=sys.stderr)
            sys.exit(1)


async def _cmd_lists(bring: Bring, args: argparse.Namespace) -> None:
    response = await bring.load_lists()
    lists = response.lists if hasattr(response, "lists") else []
    if args.json:
        rows = [{"name": lst.name, "listUuid": lst.listUuid} for lst in lists]
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return
    for lst in lists:
        print(f"{lst.name}\t{lst.listUuid}")


async def _cmd_list(bring: Bring, args: argparse.Namespace) -> None:
    list_uuid = _require_list_uuid()
    response = await bring.get_list(list_uuid)
    purchase = response.items.purchase if hasattr(response, "items") else []
    if args.json:
        rows = [{"name": i.itemId, "spec": i.specification} for i in purchase]
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return
    if not purchase:
        print("(empty list)")
        return
    for item in purchase:
        line = f"  {item.itemId}"
        if item.specification:
            line += f" ({item.specification})"
        print(line)


async def _cmd_add(bring: Bring, args: argparse.Namespace) -> None:
    list_uuid = _require_list_uuid()
    items = [_validate_item(i) for i in args.items]
    spec = _validate_spec(args.spec or "")

    if len(items) > 1 and spec:
        print(
            "Error: --spec cannot be used when adding multiple items",
            file=sys.stderr,
        )
        sys.exit(1)

    if len(items) == 1:
        await bring.save_item(list_uuid, items[0], spec)
        spec_msg = f" ({spec})" if spec else ""
        print(f"Added: {items[0]}{spec_msg}")
    else:
        bring_items = [{"itemId": name, "spec": ""} for name in items]
        await bring.batch_update_list(list_uuid, bring_items, BringItemOperation.ADD)
        print(f"Added {len(items)} items:")
        for name in items:
            print(f"  {name}")


async def _cmd_complete(bring: Bring, args: argparse.Namespace) -> None:
    list_uuid = _require_list_uuid()
    item = _validate_item(args.item)
    await bring.complete_item(list_uuid, item)
    print(f"Completed: {item}")


async def _cmd_remove(bring: Bring, args: argparse.Namespace) -> None:
    list_uuid = _require_list_uuid()
    item = _validate_item(args.item)
    await bring.remove_item(list_uuid, item)
    print(f"Removed: {item}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bring",
        description="Bring! Shopping List CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # bring lists
    lists_parser = sub.add_parser("lists", help="Show all available lists")
    lists_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # bring list
    list_parser = sub.add_parser("list", help="Show items on the default list")
    list_parser.add_argument("--json", action="store_true", help="Output as JSON")

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
    except Exception:
        print(
            "Error: an unexpected error occurred. Check your credentials and network.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
