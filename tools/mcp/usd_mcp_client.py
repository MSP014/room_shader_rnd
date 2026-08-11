#!/usr/bin/env python3
"""
Minimal client for NVIDIA Omniverse USD Code MCP server.

Default endpoint:
    http://localhost:9903/mcp

Usage:
    python tools/mcp/usd_mcp_client.py list-tools
    python tools/mcp/usd_mcp_client.py list-modules
    python tools/mcp/usd_mcp_client.py search-knowledge "USD variants"
    python tools/mcp/usd_mcp_client.py search-code "UsdStage example"
    python tools/mcp/usd_mcp_client.py module-detail "Usd"
    python tools/mcp/usd_mcp_client.py class-detail "UsdStage"
    python tools/mcp/usd_mcp_client.py method-detail "Open" --class-name "UsdStage"
"""

from __future__ import annotations

import argparse
import os
import sys

from mcp_http_client import McpError, call_tool, list_tools, print_result

DEFAULT_URL = "http://localhost:9903/mcp"
CLIENT_NAME = "room-map-rnd-usd-mcp-client"


def list_modules(url: str) -> None:
    result = call_tool(url, "list_usd_modules", {}, client_name=CLIENT_NAME)
    print_result(result)


def search_knowledge(url: str, query: str) -> None:
    result = call_tool(
        url,
        "search_usd_knowledge",
        {"request": query},
        client_name=CLIENT_NAME,
    )
    print_result(result)


def search_code(url: str, query: str) -> None:
    result = call_tool(
        url,
        "search_usd_code_examples",
        {"request": query},
        client_name=CLIENT_NAME,
    )
    print_result(result)


def module_detail(url: str, module_names: str) -> None:
    result = call_tool(
        url,
        "get_usd_module_detail",
        {"module_names": module_names},
        client_name=CLIENT_NAME,
    )
    print_result(result)


def class_detail(url: str, class_names: str) -> None:
    result = call_tool(
        url,
        "get_usd_class_detail",
        {"class_names": class_names},
        client_name=CLIENT_NAME,
    )
    print_result(result)


def method_detail(
    url: str, method_names: str, class_name: str | None = None
) -> None:
    arguments = {"method_names": method_names}
    if class_name:
        arguments["class_name"] = class_name

    result = call_tool(
        url,
        "get_usd_method_detail",
        arguments,
        client_name=CLIENT_NAME,
    )
    print_result(result)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        default=os.environ.get("USD_MCP_URL", DEFAULT_URL),
        help=f"MCP endpoint URL. Default: {DEFAULT_URL}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list-tools")
    subparsers.add_parser("list-modules")

    search_knowledge_parser = subparsers.add_parser("search-knowledge")
    search_knowledge_parser.add_argument("query")

    search_code_parser = subparsers.add_parser("search-code")
    search_code_parser.add_argument("query")

    module_detail_parser = subparsers.add_parser("module-detail")
    module_detail_parser.add_argument("module_names")

    class_detail_parser = subparsers.add_parser("class-detail")
    class_detail_parser.add_argument("class_names")

    method_detail_parser = subparsers.add_parser("method-detail")
    method_detail_parser.add_argument("method_names")
    method_detail_parser.add_argument("--class-name")

    args = parser.parse_args()

    try:
        if args.command == "list-tools":
            list_tools(args.url, client_name=CLIENT_NAME)
        elif args.command == "list-modules":
            list_modules(args.url)
        elif args.command == "search-knowledge":
            search_knowledge(args.url, args.query)
        elif args.command == "search-code":
            search_code(args.url, args.query)
        elif args.command == "module-detail":
            module_detail(args.url, args.module_names)
        elif args.command == "class-detail":
            class_detail(args.url, args.class_names)
        elif args.command == "method-detail":
            method_detail(args.url, args.method_names, args.class_name)
        else:
            raise McpError(f"Unknown command: {args.command}")

    except McpError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
