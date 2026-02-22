"""Tests for bring_cli.main."""

from __future__ import annotations

import argparse
import json
from unittest.mock import AsyncMock, patch

import pytest

from bring_cli.main import (
    MAX_ITEM_LEN,
    MAX_SPEC_LEN,
    _build_parser,
    _cmd_add,
    _cmd_complete,
    _cmd_list,
    _cmd_lists,
    _cmd_remove,
    _require_env,
    _require_list_uuid,
    _validate_item,
    _validate_spec,
    main,
)


# ---------------------------------------------------------------------------
# _require_env
# ---------------------------------------------------------------------------


class TestRequireEnv:
    def test_returns_value_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_VAR", "hello")
        assert _require_env("TEST_VAR") == "hello"

    def test_exits_when_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TEST_VAR", raising=False)
        with pytest.raises(SystemExit, match="1"):
            _require_env("TEST_VAR")

    def test_exits_when_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_VAR", "")
        with pytest.raises(SystemExit, match="1"):
            _require_env("TEST_VAR")


# ---------------------------------------------------------------------------
# _require_list_uuid
# ---------------------------------------------------------------------------


class TestRequireListUuid:
    def test_returns_valid_uuid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BRING_LIST", "12345678-1234-1234-1234-123456789abc")
        assert _require_list_uuid() == "12345678-1234-1234-1234-123456789abc"

    def test_exits_when_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("BRING_LIST", raising=False)
        with pytest.raises(SystemExit, match="1"):
            _require_list_uuid()

    def test_exits_when_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BRING_LIST", "")
        with pytest.raises(SystemExit, match="1"):
            _require_list_uuid()

    def test_exits_when_invalid_uuid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BRING_LIST", "not-a-uuid")
        with pytest.raises(SystemExit, match="1"):
            _require_list_uuid()

    def test_strips_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BRING_LIST", "  12345678-1234-1234-1234-123456789abc  ")
        assert _require_list_uuid() == "12345678-1234-1234-1234-123456789abc"


# ---------------------------------------------------------------------------
# _validate_item
# ---------------------------------------------------------------------------


class TestValidateItem:
    def test_returns_stripped_name(self) -> None:
        assert _validate_item("  Milk  ") == "Milk"

    def test_exits_when_empty(self) -> None:
        with pytest.raises(SystemExit, match="1"):
            _validate_item("")

    def test_exits_when_whitespace_only(self) -> None:
        with pytest.raises(SystemExit, match="1"):
            _validate_item("   ")

    def test_exits_when_too_long(self) -> None:
        with pytest.raises(SystemExit, match="1"):
            _validate_item("x" * (MAX_ITEM_LEN + 1))

    def test_accepts_max_length(self) -> None:
        name = "x" * MAX_ITEM_LEN
        assert _validate_item(name) == name


# ---------------------------------------------------------------------------
# _validate_spec
# ---------------------------------------------------------------------------


class TestValidateSpec:
    def test_returns_stripped_spec(self) -> None:
        assert _validate_spec("  2 kg  ") == "2 kg"

    def test_allows_empty(self) -> None:
        assert _validate_spec("") == ""

    def test_exits_when_too_long(self) -> None:
        with pytest.raises(SystemExit, match="1"):
            _validate_spec("x" * (MAX_SPEC_LEN + 1))

    def test_accepts_max_length(self) -> None:
        spec = "x" * MAX_SPEC_LEN
        assert _validate_spec(spec) == spec


# ---------------------------------------------------------------------------
# _build_parser
# ---------------------------------------------------------------------------


class TestBuildParser:
    def test_lists_command(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["lists"])
        assert args.command == "lists"

    def test_lists_with_json(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["lists", "--json"])
        assert args.command == "lists"
        assert args.json is True

    def test_list_command(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["list"])
        assert args.command == "list"

    def test_list_with_json(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["list", "--json"])
        assert args.json is True

    def test_add_single_item(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["add", "Milk"])
        assert args.command == "add"
        assert args.items == ["Milk"]

    def test_add_multiple_items(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["add", "Milk", "Eggs", "Butter"])
        assert args.items == ["Milk", "Eggs", "Butter"]

    def test_add_with_spec(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["add", "Apples", "--spec", "2 kg bio"])
        assert args.spec == "2 kg bio"

    def test_complete_command(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["complete", "Milk"])
        assert args.command == "complete"
        assert args.item == "Milk"

    def test_remove_command(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["remove", "Cheese"])
        assert args.command == "remove"
        assert args.item == "Cheese"

    def test_no_global_json_flag(self) -> None:
        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--json", "add", "Milk"])

    def test_requires_command(self) -> None:
        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])


# ---------------------------------------------------------------------------
# _cmd_lists
# ---------------------------------------------------------------------------


class TestCmdLists:
    @pytest.fixture()
    def mock_bring(self) -> AsyncMock:
        bring = AsyncMock()
        bring.load_lists.return_value = {
            "lists": [
                {"name": "Groceries", "listUuid": "uuid-1"},
                {"name": "Hardware", "listUuid": "uuid-2"},
            ]
        }
        return bring

    async def test_plain_output(
        self, mock_bring: AsyncMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        args = argparse.Namespace(json=False)
        await _cmd_lists(mock_bring, args)
        output = capsys.readouterr().out
        assert "Groceries\tuuid-1" in output
        assert "Hardware\tuuid-2" in output

    async def test_json_output(
        self, mock_bring: AsyncMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        args = argparse.Namespace(json=True)
        await _cmd_lists(mock_bring, args)
        data = json.loads(capsys.readouterr().out)
        assert len(data) == 2
        assert data[0]["name"] == "Groceries"


# ---------------------------------------------------------------------------
# _cmd_list
# ---------------------------------------------------------------------------


class TestCmdList:
    @pytest.fixture()
    def mock_bring(self) -> AsyncMock:
        bring = AsyncMock()
        bring.get_list.return_value = {
            "purchase": [
                {"name": "Milk", "specification": "1L"},
                {"name": "Eggs", "specification": ""},
            ]
        }
        return bring

    async def test_plain_output(
        self,
        mock_bring: AsyncMock,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("BRING_LIST", "12345678-1234-1234-1234-123456789abc")
        args = argparse.Namespace(json=False)
        await _cmd_list(mock_bring, args)
        output = capsys.readouterr().out
        assert "Milk (1L)" in output
        assert "Eggs" in output

    async def test_json_output(
        self,
        mock_bring: AsyncMock,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("BRING_LIST", "12345678-1234-1234-1234-123456789abc")
        args = argparse.Namespace(json=True)
        await _cmd_list(mock_bring, args)
        data = json.loads(capsys.readouterr().out)
        assert len(data) == 2

    async def test_empty_list(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("BRING_LIST", "12345678-1234-1234-1234-123456789abc")
        bring = AsyncMock()
        bring.get_list.return_value = {"purchase": []}
        args = argparse.Namespace(json=False)
        await _cmd_list(bring, args)
        assert "(empty list)" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# _cmd_add
# ---------------------------------------------------------------------------


class TestCmdAdd:
    @pytest.fixture()
    def mock_bring(self) -> AsyncMock:
        return AsyncMock()

    async def test_add_single_item(
        self,
        mock_bring: AsyncMock,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("BRING_LIST", "12345678-1234-1234-1234-123456789abc")
        args = argparse.Namespace(items=["Milk"], spec="")
        await _cmd_add(mock_bring, args)
        mock_bring.save_item.assert_called_once_with(
            "12345678-1234-1234-1234-123456789abc", "Milk", ""
        )
        assert "Added: Milk" in capsys.readouterr().out

    async def test_add_single_with_spec(
        self,
        mock_bring: AsyncMock,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("BRING_LIST", "12345678-1234-1234-1234-123456789abc")
        args = argparse.Namespace(items=["Apples"], spec="2 kg bio")
        await _cmd_add(mock_bring, args)
        mock_bring.save_item.assert_called_once_with(
            "12345678-1234-1234-1234-123456789abc", "Apples", "2 kg bio"
        )
        assert "(2 kg bio)" in capsys.readouterr().out

    async def test_add_multiple_items(
        self,
        mock_bring: AsyncMock,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("BRING_LIST", "12345678-1234-1234-1234-123456789abc")
        args = argparse.Namespace(items=["Milk", "Eggs"], spec="")
        await _cmd_add(mock_bring, args)
        mock_bring.batch_update_list.assert_called_once()
        output = capsys.readouterr().out
        assert "Added 2 items" in output

    async def test_add_multiple_with_spec_errors(
        self,
        mock_bring: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("BRING_LIST", "12345678-1234-1234-1234-123456789abc")
        args = argparse.Namespace(items=["Milk", "Eggs"], spec="organic")
        with pytest.raises(SystemExit, match="1"):
            await _cmd_add(mock_bring, args)


# ---------------------------------------------------------------------------
# _cmd_complete
# ---------------------------------------------------------------------------


class TestCmdComplete:
    async def test_completes_item(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("BRING_LIST", "12345678-1234-1234-1234-123456789abc")
        bring = AsyncMock()
        args = argparse.Namespace(item="Milk")
        await _cmd_complete(bring, args)
        bring.complete_item.assert_called_once_with(
            "12345678-1234-1234-1234-123456789abc", "Milk"
        )
        assert "Completed: Milk" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# _cmd_remove
# ---------------------------------------------------------------------------


class TestCmdRemove:
    async def test_removes_item(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("BRING_LIST", "12345678-1234-1234-1234-123456789abc")
        bring = AsyncMock()
        args = argparse.Namespace(item="Cheese")
        await _cmd_remove(bring, args)
        bring.remove_item.assert_called_once_with(
            "12345678-1234-1234-1234-123456789abc", "Cheese"
        )
        assert "Removed: Cheese" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


class TestMain:
    def test_keyboard_interrupt_exits_130(self) -> None:
        with (
            patch("bring_cli.main._build_parser") as mock_parser,
            patch("bring_cli.main.asyncio") as mock_asyncio,
        ):
            mock_parser.return_value.parse_args.return_value = argparse.Namespace(
                command="lists"
            )
            mock_asyncio.run.side_effect = KeyboardInterrupt
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 130

    def test_generic_exception_exits_1(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with (
            patch("bring_cli.main._build_parser") as mock_parser,
            patch("bring_cli.main.asyncio") as mock_asyncio,
        ):
            mock_parser.return_value.parse_args.return_value = argparse.Namespace(
                command="lists"
            )
            mock_asyncio.run.side_effect = RuntimeError("secret-token-leaked")
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
            stderr = capsys.readouterr().err
            assert "unexpected error" in stderr
            assert "secret-token-leaked" not in stderr
