#!/usr/bin/env python3
"""
Minimal client for NVIDIA Omniverse OmniUI MCP server.

Default endpoint:
    http://localhost:9901/mcp
"""

from __future__ import annotations

import argparse
import os
import sys

from mcp_http_client import McpError, call_tool, list_tools, print_result

DEFAULT_URL = "http://localhost:9901/mcp"
CLIENT_NAME = "room-map-rnd-omni-ui-mcp-client"


def run_tool(url: str, tool_name: str, arguments: dict[str, str]) -> None:
    result = call_tool(url, tool_name, arguments, client_name=CLIENT_NAME)
    print_result(result)


def search_code(url: str, query: str) -> None:
    run_tool(url, "search_ui_code_examples", {"query": query})


def window_examples(url: str, query: str) -> None:
    run_tool(url, "search_ui_window_examples", {"query": query})


def list_classes(url: str) -> None:
    run_tool(url, "list_ui_classes", {})


def list_modules(url: str) -> None:
    run_tool(url, "list_ui_modules", {})


def class_detail(url: str, class_names: str) -> None:
    run_tool(url, "get_ui_class_detail", {"class_names": class_names})


def module_detail(url: str, module_names: str) -> None:
    run_tool(url, "get_ui_module_detail", {"module_names": module_names})


def method_detail(url: str, method_names: str) -> None:
    run_tool(url, "get_ui_method_detail", {"method_names": method_names})


def instructions(url: str, name: str) -> None:
    arguments = {"name": name} if name else {}
    run_tool(url, "get_ui_instructions", arguments)


def class_instructions(url: str, class_names: str) -> None:
    run_tool(
        url,
        "get_ui_class_instructions",
        {"class_names": class_names},
    )


def style_docs(url: str, sections: str) -> None:
    run_tool(url, "get_ui_style_docs", {"sections": sections})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        default=os.environ.get("OMNI_UI_MCP_URL", DEFAULT_URL),
        help=f"MCP endpoint URL. Default: {DEFAULT_URL}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list-tools")
    subparsers.add_parser("list-classes")
    subparsers.add_parser("list-modules")

    search_code_parser = subparsers.add_parser("search-code")
    search_code_parser.add_argument("query")

    window_examples_parser = subparsers.add_parser("window-examples")
    window_examples_parser.add_argument("query")

    class_detail_parser = subparsers.add_parser("class-detail")
    class_detail_parser.add_argument("class_names")

    module_detail_parser = subparsers.add_parser("module-detail")
    module_detail_parser.add_argument("module_names")

    method_detail_parser = subparsers.add_parser("method-detail")
    method_detail_parser.add_argument("method_names")

    instructions_parser = subparsers.add_parser("instructions")
    instructions_parser.add_argument("name", nargs="?", default="")

    class_instructions_parser = subparsers.add_parser("class-instructions")
    class_instructions_parser.add_argument("class_names")

    style_docs_parser = subparsers.add_parser("style-docs")
    style_docs_parser.add_argument("sections")

    args = parser.parse_args()

    try:
        if args.command == "list-tools":
            list_tools(args.url, client_name=CLIENT_NAME)
        elif args.command == "search-code":
            search_code(args.url, args.query)
        elif args.command == "window-examples":
            window_examples(args.url, args.query)
        elif args.command == "list-classes":
            list_classes(args.url)
        elif args.command == "list-modules":
            list_modules(args.url)
        elif args.command == "class-detail":
            class_detail(args.url, args.class_names)
        elif args.command == "module-detail":
            module_detail(args.url, args.module_names)
        elif args.command == "method-detail":
            method_detail(args.url, args.method_names)
        elif args.command == "instructions":
            instructions(args.url, args.name)
        elif args.command == "class-instructions":
            class_instructions(args.url, args.class_names)
        elif args.command == "style-docs":
            style_docs(args.url, args.sections)
        else:
            raise McpError(f"Unknown command: {args.command}")

    except McpError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
