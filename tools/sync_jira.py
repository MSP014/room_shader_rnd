import argparse
import os
import random  # nosec
import sys
import textwrap
from base64 import b64encode

import requests
from dotenv import load_dotenv

# Configure stdout for UTF-8 (Windows encoding fix)
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )


def get_jira_session():
    load_dotenv()
    url = os.getenv("JIRA_URL")
    user = os.getenv("JIRA_USER")
    token = os.getenv("JIRA_TOKEN")

    if not all([url, user, token]):
        print("Error: Missing JIRA configuration in .env")
        sys.exit(1)

    auth_str = f"{user}:{token}".encode("ascii")
    auth_b64 = b64encode(auth_str).decode("ascii")

    headers = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    return url.rstrip("/"), headers


def extract_text(node):
    if not node:
        return ""
    texts = []
    if isinstance(node, dict):
        if node.get("type") == "text":
            texts.append(node.get("text", ""))
        elif "content" in node:
            for child in node["content"]:
                texts.extend(extract_text(child))
    elif isinstance(node, list):
        for item in node:
            texts.extend(extract_text(item))
    return "".join(texts)


def fetch_issues(project_key):
    base_url, headers = get_jira_session()
    # Fetch all issues for the project to build the full hierarchy context
    jql = f"project = {project_key} ORDER BY priority DESC, created ASC"
    fields = (
        "summary,status,issuetype,priority,parent,description,timetracking"
    )

    issues = []
    next_page_token = None

    while True:
        payload = {
            "jql": jql,
            "fields": fields.split(","),
            "maxResults": 50,
        }

        if next_page_token:
            payload["nextPageToken"] = next_page_token

        # Use /search/jql endpoint with token pagination
        resp = requests.post(
            f"{base_url}/rest/api/3/search/jql",
            headers=headers,
            json=payload,
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"Error fetching issues: {resp.text}")
            break

        data = resp.json()
        batch = data.get("issues", [])
        if batch:
            issues.extend(batch)

        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break

    return issues


def format_status(status_name):
    s = status_name.lower()
    if s == "done":
        return "✅ Done"
    if s in ["in progress", "in review"]:
        return "🔄 In Progress"
    if s in ["to do", "backlog"]:
        return "⏸️ To Do"
    return status_name


def parse_description(text):
    text = text.strip()
    if not text:
        return "N/A", None

    dod_markers = ["Definition of Done:", "DoD:"]
    objective = text
    dod = None

    for marker in dod_markers:
        if marker in text:
            parts = text.split(marker, 1)
            objective = parts[0].strip()
            dod = parts[1].strip()
            break

    # If objective still has "Objective:" prefix, strip it
    if objective.lower().startswith("objective:"):
        objective = objective[10:].strip()

    return objective, dod


def main():
    parser = argparse.ArgumentParser(description="Jira to Markdown Sync")
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save output to file (default is dry-run)",
    )
    args = parser.parse_args()

    project_key = "KRM"
    output_file = "docs/plans/rnd - implementation.md"

    issues = fetch_issues(project_key)

    all_map = {}
    priority_order = {
        "Highest": 1,
        "High": 2,
        "Medium": 3,
        "Low": 4,
        "Lowest": 5,
    }

    # Pass 1: Local map
    for issue in issues:
        fields = issue["fields"]
        raw_desc = extract_text(fields.get("description", ""))
        obj, dod = parse_description(raw_desc)

        priority_name = "Medium"  # Default
        if fields.get("priority"):
            priority_name = fields["priority"]["name"]

        all_map[issue["key"]] = {
            "key": issue["key"],
            "summary": fields["summary"],
            "status": fields["status"]["name"],
            "type": fields["issuetype"]["name"],
            "priority": priority_name,
            "priority_val": priority_order.get(priority_name, 99),
            "parent": (
                fields.get("parent", {}).get("key")
                if fields.get("parent")
                else None
            ),
            "objective": obj,
            "dod": dod,
            "estimate": fields.get("timetracking", {}).get("originalEstimate"),
            "logged": fields.get("timetracking", {}).get("timeSpent"),
            "children": [],
        }

    # Pass 2: Build Tree
    epics = []
    standalone = []
    for item in all_map.values():
        if item["type"] == "Epic":
            epics.append(item)
        elif item["parent"]:
            if item["parent"] in all_map:
                all_map[item["parent"]]["children"].append(item)
            else:
                standalone.append(item)
        else:
            standalone.append(item)

    # Sort Epics by priority
    epics.sort(key=lambda x: x["priority_val"])

    output = []
    output.append("# RnD: Room Map Shader (L1) — Implementation Plan")
    output.append("")
    output.append(f"**Jira Project**: {project_key}")
    output.append("**Status**: In Progress")
    output.append("**Last Updated**: 2026-02-04")
    output.append("")
    output.append("---")
    output.append("")

    def render_issue(item, level):
        res = []
        prefix = "#" * level
        status_raw = item["status"].lower()
        icon = (
            "✅"
            if status_raw == "done"
            else "🔄" if status_raw in ["in progress", "in review"] else "⏸️"
        )

        res.append(f"{prefix} {icon} [{item['key']}] {item['summary']}")
        res.append("")

        # Add metadata line
        meta = []
        meta.append(f"**Status**: {format_status(item['status'])}")
        meta.append(f"**Priority**: {item['priority']}")
        if item["estimate"]:
            meta.append(f"**Estimate**: {item['estimate']}")

        res.append(" | ".join(meta))

        # Only show objective if it's not effectively empty
        # or just repeating the summary
        if (
            item["objective"]
            and item["objective"] != "N/A"
            and len(item["objective"]) > 5
        ):
            wrapped_obj = textwrap.fill(
                f"**Objective**: {item['objective']}",
                width=80,
                subsequent_indent="  ",
            )
            res.append(wrapped_obj)

        if item["children"]:
            # Sort children by priority then key
            item["children"].sort(key=lambda x: (x["priority_val"], x["key"]))
            for child in item["children"]:
                res.append("")
                res.append(render_issue(child, level + 1))

        if item["dod"]:
            res.append("")
            res.append("**Definition of Done:**")
            res.append(f"{item['dod']}")

        if item["logged"]:
            res.append(f"**Logged**: {item['logged']}")

        return "\n".join(res)

    # Selection logic: included if active or has active children
    active_statuses = ["to do", "in progress", "done"]
    active_epics = []

    for epic in epics:
        active_children = [
            c
            for c in epic["children"]
            if c["status"].lower() in active_statuses
        ]
        is_active_epic = epic["status"].lower() in active_statuses

        if is_active_epic or active_children:
            epic["active_children"] = active_children
            active_epics.append(epic)

    for epic in active_epics:
        output.append(f"## 🧩 EPIC: {epic['summary']} ({epic['key']})")
        output.append("")
        output.append(
            " | ".join(
                [
                    f"**Status**: {format_status(epic['status'])}",
                    f"**Priority**: {epic['priority']}",
                ]
            )
        )
        output.append("")

        # Sort children
        epic["active_children"].sort(
            key=lambda x: (x["priority_val"], x["key"])
        )
        for task in epic["active_children"]:
            output.append(render_issue(task, 3))
            output.append("")

        output.append("---")
        output.append("")

    # Progress Summary
    output.append("## 📊 Progress Summary")
    output.append("")
    output.append("| Epic | Status | Priority | Completion |")
    output.append("| --- | --- | --- | --- |")
    for epic in active_epics:
        total = len(epic["children"])
        done = len(
            [c for c in epic["children"] if c["status"].lower() == "done"]
        )
        perc = int((done / total) * 100) if total > 0 else 0
        output.append(
            f"| {epic['summary']} | {format_status(epic['status'])} | "
            f"{epic['priority']} | {perc}% ({done}/{total}) |"
        )

    output.append("")
    output.append("---")
    output.append("")

    # Next Priorities
    output.append("## 🎯 Next Priorities")
    output.append("")
    # Highest priority active tasks (To Do / In Progress only for priorities)
    active_tasks = [
        i
        for i in all_map.values()
        if (
            i["type"] != "Epic"
            and i["status"].lower() in ["to do", "in progress"]
        )
    ]
    # Sort by priority val (asc), then by created key (desc/asc)
    active_tasks.sort(key=lambda x: (x["priority_val"], x["key"]))

    for i, task in enumerate(active_tasks[:5]):
        output.append(
            f"{i+1}. **{task['key']}**: {task['summary']} "
            f"(Priority: {task['priority']})"
        )

    if not args.save:
        print(f"[DRY RUN] Generated {len(output)} lines of content.")
        print(
            f"[DRY RUN] Active Epics: {len(active_epics)} | "
            f"Active Tasks: {len(active_tasks)}"
        )
        print("--- SAMPLE OUTPUT START ---")

        # Random Sample
        if active_epics:
            epic = random.choice(active_epics)  # nosec  # nosec
            print(f"## 🧩 EPIC: {epic['summary']} ({epic['key']})")
            if epic.get("active_children"):
                child = random.choice(
                    epic["active_children"]
                )  # nosec  # nosec
                print(render_issue(child, 3))
            else:
                print("(Sample epic has no active children)")
        elif active_tasks:
            task = random.choice(active_tasks)  # nosec
            print(render_issue(task, 1))
        else:
            print("(No active tasks or epics found to sample)")

        print("--- SAMPLE OUTPUT END ---")
        print("[DRY RUN] Run with --save to write to disk.")
        return

    with open(output_file, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(output).strip() + "\n")
    print(f"Done. Wrote to {output_file}")


if __name__ == "__main__":
    main()
