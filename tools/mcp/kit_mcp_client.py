#!/usr/bin/env python3
"""
Minimal client for NVIDIA Omniverse Kit MCP server.

Default endpoint:
    http://localhost:9902/mcp
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from mcp_http_client import McpError, call_tool, list_tools, print_result

DEFAULT_URL = "http://localhost:9902/mcp"
CLIENT_NAME = "room-map-rnd-kit-mcp-client"


def run_tool(url: str, tool_name: str, arguments: dict[str, Any]) -> None:
    """Call one Kit MCP tool and print its reader-facing result."""

    result = call_tool(url, tool_name, arguments, client_name=CLIENT_NAME)
    print_result(result)


def instructions(url: str, instruction_sets: str) -> None:
    """Print the requested Kit instruction sets."""

    run_tool(
        url,
        "get_kit_instructions",
        {"instruction_sets": instruction_sets},
    )


def search_knowledge(url: str, query: str) -> None:
    """Search the local Kit knowledge index."""

    run_tool(
        url,
        "search_kit_knowledge",
        {"request": query},
    )


def search_extensions(url: str, query: str, top_k: int) -> None:
    """Find Kit extensions matching a capability query."""

    run_tool(
        url,
        "search_kit_extensions",
        {"query": query, "top_k": top_k},
    )


def extension_detail(url: str, extension_ids: str) -> None:
    """Print metadata for selected Kit extension identifiers."""

    run_tool(
        url,
        "get_kit_extension_details",
        {"extension_ids": extension_ids},
    )


def extension_deps(
    url: str,
    extension_id: str,
    depth: int,
    include_optional: bool,
) -> None:
    """Resolve the bounded dependency graph of one Kit extension."""

    run_tool(
        url,
        "get_kit_extension_dependencies",
        {
            "extension_id": extension_id,
            "depth": depth,
            "include_optional": include_optional,
        },
    )


def extension_apis(url: str, extension_ids: str) -> None:
    """List APIs exposed by selected Kit extensions."""

    run_tool(
        url,
        "get_kit_extension_apis",
        {"extension_ids": extension_ids},
    )


def api_detail(url: str, api_references: str) -> None:
    """Print details for selected Kit API references."""

    run_tool(
        url,
        "get_kit_api_details",
        {"api_references": api_references},
    )


def search_code(url: str, query: str, top_k: int) -> None:
    """Search indexed Kit implementation examples."""

    run_tool(
        url,
        "search_kit_code_examples",
        {"query": query, "top_k": top_k},
    )


def search_tests(url: str, query: str, top_k: int) -> None:
    """Search indexed Kit test examples."""

    run_tool(
        url,
        "search_kit_test_examples",
        {"query": query, "top_k": top_k},
    )


def search_settings(
    url: str,
    query: str,
    top_k: int,
    prefix_filter: str,
    type_filter: str,
) -> None:
    """Search Kit settings with optional namespace and type filters."""

    arguments: dict[str, Any] = {"query": query, "top_k": top_k}
    if prefix_filter:
        arguments["prefix_filter"] = prefix_filter
    if type_filter:
        arguments["type_filter"] = type_filter

    run_tool(url, "search_kit_settings", arguments)


def search_app_templates(
    url: str,
    query: str,
    top_k: int,
    category_filter: str,
) -> None:
    """Search Kit application templates with an optional category filter."""

    arguments: dict[str, Any] = {"query": query, "top_k": top_k}
    if category_filter:
        arguments["category_filter"] = category_filter

    run_tool(url, "search_kit_app_templates", arguments)


def app_template_detail(url: str, template_ids: str) -> None:
    """Print details for selected Kit application templates."""

    run_tool(
        url,
        "get_kit_app_template_details",
        {"template_ids": template_ids},
    )


def main() -> int:
    """Parse one Kit research command and report transport errors cleanly."""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        default=os.environ.get("KIT_MCP_URL", DEFAULT_URL),
        help=f"MCP endpoint URL. Default: {DEFAULT_URL}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list-tools")

    instructions_parser = subparsers.add_parser("instructions")
    instructions_parser.add_argument("instruction_sets")

    search_knowledge_parser = subparsers.add_parser("search-knowledge")
    search_knowledge_parser.add_argument("query")

    search_extensions_parser = subparsers.add_parser("search-extensions")
    search_extensions_parser.add_argument("query")
    search_extensions_parser.add_argument("--top-k", type=int, default=10)

    extension_detail_parser = subparsers.add_parser("extension-detail")
    extension_detail_parser.add_argument("extension_ids")

    extension_deps_parser = subparsers.add_parser("extension-deps")
    extension_deps_parser.add_argument("extension_id")
    extension_deps_parser.add_argument("--depth", type=int, default=2)
    extension_deps_parser.add_argument(
        "--include-optional", action="store_true"
    )

    extension_apis_parser = subparsers.add_parser("extension-apis")
    extension_apis_parser.add_argument("extension_ids")

    api_detail_parser = subparsers.add_parser("api-detail")
    api_detail_parser.add_argument("api_references")

    search_code_parser = subparsers.add_parser("search-code")
    search_code_parser.add_argument("query")
    search_code_parser.add_argument("--top-k", type=int, default=10)

    search_tests_parser = subparsers.add_parser("search-tests")
    search_tests_parser.add_argument("query")
    search_tests_parser.add_argument("--top-k", type=int, default=10)

    search_settings_parser = subparsers.add_parser("search-settings")
    search_settings_parser.add_argument("query")
    search_settings_parser.add_argument("--top-k", type=int, default=20)
    search_settings_parser.add_argument("--prefix-filter", default="")
    search_settings_parser.add_argument("--type-filter", default="")

    search_templates_parser = subparsers.add_parser("search-app-templates")
    search_templates_parser.add_argument("query")
    search_templates_parser.add_argument("--top-k", type=int, default=5)
    search_templates_parser.add_argument("--category-filter", default="")

    app_template_detail_parser = subparsers.add_parser("app-template-detail")
    app_template_detail_parser.add_argument("template_ids")

    args = parser.parse_args()

    try:
        if args.command == "list-tools":
            list_tools(args.url, client_name=CLIENT_NAME)
        elif args.command == "instructions":
            instructions(args.url, args.instruction_sets)
        elif args.command == "search-knowledge":
            search_knowledge(args.url, args.query)
        elif args.command == "search-extensions":
            search_extensions(args.url, args.query, args.top_k)
        elif args.command == "extension-detail":
            extension_detail(args.url, args.extension_ids)
        elif args.command == "extension-deps":
            extension_deps(
                args.url,
                args.extension_id,
                args.depth,
                args.include_optional,
            )
        elif args.command == "extension-apis":
            extension_apis(args.url, args.extension_ids)
        elif args.command == "api-detail":
            api_detail(args.url, args.api_references)
        elif args.command == "search-code":
            search_code(args.url, args.query, args.top_k)
        elif args.command == "search-tests":
            search_tests(args.url, args.query, args.top_k)
        elif args.command == "search-settings":
            search_settings(
                args.url,
                args.query,
                args.top_k,
                args.prefix_filter,
                args.type_filter,
            )
        elif args.command == "search-app-templates":
            search_app_templates(
                args.url,
                args.query,
                args.top_k,
                args.category_filter,
            )
        elif args.command == "app-template-detail":
            app_template_detail(args.url, args.template_ids)
        else:
            raise McpError(f"Unknown command: {args.command}")

    except McpError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
