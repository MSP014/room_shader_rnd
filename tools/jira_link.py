import argparse
import json
import os
import sys
from base64 import b64encode

import requests
from dotenv import load_dotenv


def get_jira_session():
    load_dotenv()
    # Default to the provided URL if not in env, but User/Token must be in env
    url = os.getenv("JIRA_URL", "https://plangreen.atlassian.net")
    user = os.getenv("JIRA_USER")
    token = os.getenv("JIRA_TOKEN")

    if not all([url, user, token]):
        print(
            "Error: Missing JIRA configuration in .env "
            "(Need JIRA_USER and JIRA_TOKEN)"
        )
        sys.exit(1)

    auth_str = f"{user}:{token}".encode("ascii")
    auth_b64 = b64encode(auth_str).decode("ascii")

    headers = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    return url.rstrip("/"), headers


def get_issue(issue_key):
    base_url, headers = get_jira_session()
    # Explicitly request fields including parent and timetracking
    resp = requests.get(
        f"{base_url}/rest/api/3/issue/{issue_key}",
        headers=headers,
        params={"fields": "summary,status,description,parent,timetracking"},
        timeout=30,
    )

    if resp.status_code == 200:
        data = resp.json()
        fields = data["fields"]
        print(f"[{data['key']}] {fields['summary']}")
        print(f"Status: {fields['status']['name']}")

        if (
            "timetracking" in fields
            and "originalEstimate" in fields["timetracking"]
        ):
            print(f"Estimate: {fields['timetracking']['originalEstimate']}")
        else:
            print("Estimate: None")

        if "parent" in fields:
            parent = fields["parent"]
            print(
                f"Parent/Epic: [{parent['key']}] {parent['fields']['summary']}"
            )

        print(f"Link: {base_url}/browse/{data['key']}")

        description = fields.get("description")
        if description:
            # Basic ADF extraction - Flattening all text
            try:

                def extract_text(node):
                    texts = []
                    if node.get("type") == "text":
                        texts.append(node.get("text", ""))
                    elif "content" in node:
                        for child in node["content"]:
                            texts.extend(extract_text(child))
                    return texts

                all_text = extract_text(description)
                print("\nDescription:")
                print("".join(all_text))
            except Exception as e:
                print(f"\n[Error Parsing Rich Text: {e}]")
                print(json.dumps(description, indent=2))
    else:
        print(f"Error {resp.status_code}: {resp.text}")


def list_issues(project_key):
    base_url, headers = get_jira_session()
    # JQL to get open issues
    jql = (
        f"project = {project_key} AND statusCategory != Done "
        "ORDER BY created DESC"
    )
    payload = {"jql": jql, "fields": ["summary", "status"], "maxResults": 20}

    resp = requests.post(
        f"{base_url}/rest/api/3/search/jql",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if resp.status_code == 200:
        issues = resp.json().get("issues", [])
        for issue in issues:
            print(
                f"{issue['key']}: {issue['fields']['summary']} "
                f"({issue['fields']['status']['name']})"
            )
    else:
        print(f"Error {resp.status_code}: {resp.text}")


def add_comment(issue_key, comment_text):
    base_url, headers = get_jira_session()
    # Atlassian Document Format (ADF) required for v3 API
    payload = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"text": comment_text, "type": "text"}],
                }
            ],
        }
    }

    resp = requests.post(
        f"{base_url}/rest/api/3/issue/{issue_key}/comment",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if resp.status_code == 201:
        print(f"Comment added to {issue_key}")
    else:
        print(f"Error {resp.status_code}: {resp.text}")


def set_status(issue_key, status_name):
    base_url, headers = get_jira_session()

    # 1. Get available transitions
    resp = requests.get(
        f"{base_url}/rest/api/3/issue/{issue_key}/transitions",
        headers=headers,
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"Error getting transitions: {resp.text}")
        return

    transitions = resp.json().get("transitions", [])
    target_transition = None

    # Try exact match first, then case-insensitive
    for t in transitions:
        if t["to"]["name"] == status_name:
            target_transition = t
            break

    if not target_transition:
        for t in transitions:
            if t["to"]["name"].lower() == status_name.lower():
                target_transition = t
                break

    if not target_transition:
        print(
            f"Status '{status_name}' not available. Available: "
            f"{', '.join([t['to']['name'] for t in transitions])}"
        )
        return

    # 2. Perform transition
    payload = {"transition": {"id": target_transition["id"]}}

    resp = requests.post(
        f"{base_url}/rest/api/3/issue/{issue_key}/transitions",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if resp.status_code == 204:
        print(
            f"Issue {issue_key} moved to '{target_transition['to']['name']}'"
        )
    else:
        print(f"Error {resp.status_code}: {resp.text}")


def add_worklog(issue_key, time_spent):
    print(f"DEBUG: Attempting to log {time_spent} for {issue_key}...")
    base_url, headers = get_jira_session()
    url = f"{base_url}/rest/api/3/issue/{issue_key}/worklog"
    payload = {"timeSpent": time_spent}
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code == 201:
        print(f"Worklog '{time_spent}' added to {issue_key}")
    else:
        print(f"Error {resp.status_code}: {resp.text}")


def update_issue(
    issue_key, summary=None, description=None, assignee_id=None, estimate=None
):
    base_url, headers = get_jira_session()

    fields = {}
    if summary:
        fields["summary"] = summary
    if description:
        # Simple ADF wrapper for description if it's just text
        fields["description"] = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"text": description, "type": "text"}],
                }
            ],
        }

    if assignee_id:
        fields["assignee"] = {"id": assignee_id}

    if estimate:
        fields["timetracking"] = {
            "originalEstimate": estimate,
            "remainingEstimate": estimate,
        }

    if not fields:
        print("Nothing to update.")
        return

    payload = {"fields": fields}

    resp = requests.put(
        f"{base_url}/rest/api/3/issue/{issue_key}",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if resp.status_code == 204:
        print(f"Issue {issue_key} updated.")
    else:
        print(f"Error {resp.status_code}: {resp.text}")


def create_issue(
    project_key,
    summary,
    description,
    issue_type="Task",
    parent_key=None,
    assignee_id=None,
    estimate="1h",
):
    base_url, headers = get_jira_session()

    fields = {
        "project": {"key": project_key},
        "summary": summary,
        "issuetype": {"name": issue_type},
        "description": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"text": description, "type": "text"}],
                }
            ],
        },
    }

    # 1. Assignment
    if assignee_id:
        fields["assignee"] = {"id": assignee_id}

    # 2. Time Tracking
    if estimate:
        fields["timetracking"] = {
            "originalEstimate": estimate,
            "remainingEstimate": estimate,
        }

    if parent_key:
        fields["parent"] = {"key": parent_key}

    payload = {"fields": fields}

    resp = requests.post(
        f"{base_url}/rest/api/3/issue",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if resp.status_code == 201:
        data = resp.json()
        print(f"Created {data['key']}")
        return data["key"]
    else:
        print(f"Error {resp.status_code}: {resp.text}")
        return None


def get_myself():
    base_url, headers = get_jira_session()
    resp = requests.get(
        f"{base_url}/rest/api/3/myself", headers=headers, timeout=30
    )
    if resp.status_code == 200:
        return resp.json()["accountId"]


def list_transitions(issue_key):
    base_url, headers = get_jira_session()
    resp = requests.get(
        f"{base_url}/rest/api/3/issue/{issue_key}/transitions",
        headers=headers,
        timeout=30,
    )
    if resp.status_code == 200:
        transitions = resp.json().get("transitions", [])
        print(f"Transitions for {issue_key}:")
        for t in transitions:
            print(f" - {t['name']} (id: {t['id']}) -> {t['to']['name']}")
    else:
        print(f"Error {resp.status_code}: {resp.text}")


def main():
    parser = argparse.ArgumentParser(
        description="Simple Jira CLI (Quentin - KRM)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Get Issue
    p_get = subparsers.add_parser("get", help="Get issue details")
    p_get.add_argument("key", help="Issue Key (e.g. KRM-123)")

    # List Issues
    p_list = subparsers.add_parser("list", help="List open issues for project")
    p_list.add_argument(
        "project", help="Project Key (e.g. KRM)", nargs="?", default="KRM"
    )

    # Transitions
    p_trans = subparsers.add_parser(
        "transitions", help="List available transitions"
    )
    p_trans.add_argument("key", help="Issue Key")

    # Comment
    p_comment = subparsers.add_parser("comment", help="Add comment to issue")
    p_comment.add_argument("key", help="Issue Key")
    p_comment.add_argument("text", help="Comment text")

    # Status
    p_status = subparsers.add_parser("status", help="Change issue status")
    p_status.add_argument("key", help="Issue Key")
    p_status.add_argument(
        "status", help="Target status (e.g. 'Done', 'In Progress')"
    )

    # Worklog
    p_worklog = subparsers.add_parser("worklog", help="Log work time")
    p_worklog.add_argument("key", help="Issue Key")
    p_worklog.add_argument("time", help="Time spent (e.g. 1h 30m, 2h, 15m)")

    # Edit
    p_edit = subparsers.add_parser("edit", help="Edit issue fields")
    p_edit.add_argument("key", help="Issue Key")
    p_edit.add_argument("--summary", help="New summary/title")
    p_edit.add_argument("--description", help="New description")
    p_edit.add_argument(
        "--assign-me", help="Assign to current user?", action="store_true"
    )
    p_edit.add_argument("--estimate", help="Original Estimate (e.g. 1h)")

    # Create
    p_create = subparsers.add_parser("create", help="Create new issue")
    p_create.add_argument(
        "project", help="Project Key", nargs="?", default="KRM"
    )
    p_create.add_argument("summary", help="Issue Summary")
    p_create.add_argument(
        "--description", help="Issue Description", default=""
    )
    p_create.add_argument(
        "--type", help="Issue Type (Task, Epic, Bug)", default="Task"
    )
    p_create.add_argument(
        "--parent",
        help="Parent Issue Key (for Subtasks or Hierarchy)",
        default=None,
    )
    p_create.add_argument(
        "--assign-me",
        help="Assign to current user?",
        action="store_true",
        default=True,
    )
    p_create.add_argument(
        "--estimate", help="Original Estimate (e.g. 1h)", default="1h"
    )

    args = parser.parse_args()

    try:
        myself_id = None
        if hasattr(args, "assign_me") and args.assign_me:
            myself_id = get_myself()
            if not myself_id:
                print("Warning: Could not fetch user ID for assignment.")

        if args.command == "get":
            get_issue(args.key)
        elif args.command == "list":
            list_issues(args.project)
        elif args.command == "transitions":
            list_transitions(args.key)
        elif args.command == "comment":
            add_comment(args.key, args.text)
        elif args.command == "status":
            set_status(args.key, args.status)
        elif args.command == "worklog":
            add_worklog(args.key, args.time)
        elif args.command == "edit":
            update_issue(
                args.key,
                summary=args.summary,
                description=(
                    args.description.replace("\\n", "\n")
                    if args.description
                    else None
                ),
                assignee_id=myself_id,
                estimate=args.estimate,
            )
        elif args.command == "create":
            create_issue(
                args.project,
                args.summary,
                (
                    args.description.replace("\\n", "\n")
                    if args.description
                    else ""
                ),
                args.type,
                args.parent,
                assignee_id=myself_id,
                estimate=args.estimate,
            )
    except Exception as e:
        print(f"Execution failed: {e}")


if __name__ == "__main__":
    main()
