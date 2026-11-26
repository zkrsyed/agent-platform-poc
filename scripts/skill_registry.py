"""Put our skill in Agent Registry and find it again (lesson 10).

  uv run python scripts/skill_registry.py upload            # zip skills/ga4-context and create the skill
  uv run python scripts/skill_registry.py list              # the skills in the registry
  uv run python scripts/skill_registry.py show SKILL_ID     # one skill, with its revisions and state
  uv run python scripts/skill_registry.py activate SKILL_ID REVISION_NAME
  uv run python scripts/skill_registry.py search "QUERY"    # search the way an ADK agent does

Our gcloud has no `agent-registry skills` commands, so this calls the REST API (docs:
docs.cloud.google.com/agent-registry/register-skills and manage-skills; field names checked against the
API's own schema at https://agentregistry.googleapis.com/$discovery/rest?version=v1). The registry stores the skill
as a ZIP with SKILL.md at its root (max 1 MB) and gives it an ID starting with "private-".
"""

import asyncio
import base64
import io
import json
import sys
import zipfile
from pathlib import Path

import google.auth
from google.auth.transport.requests import AuthorizedSession

PROJECT = "kc-okf-poc-261122"
LOCATION = "global"
ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "ga4-context"
API = f"https://agentregistry.googleapis.com/v1/projects/{PROJECT}/locations/{LOCATION}"

creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
http = AuthorizedSession(creds)


def call(method: str, url: str, **kwargs) -> dict:
    r = http.request(method, url, headers={"x-goog-user-project": PROJECT}, timeout=60, **kwargs)
    if not r.ok:
        sys.exit(f"{r.status_code} {r.text[:800]}")
    return r.json() if r.text else {}


def zip_skill() -> bytes:
    """SKILL.md and references/ at the root of the ZIP, as the registry expects."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(SKILL_DIR.rglob("*")):
            if path.is_file():
                z.write(path, path.relative_to(SKILL_DIR).as_posix())
    return buffer.getvalue()


def upload() -> None:
    archive = zip_skill()
    print(f"zipped {SKILL_DIR.relative_to(ROOT)}: {len(archive)} bytes")
    body = {
        "displayName": "GA4 context",
        "description": "Rules and definitions for querying the GA4 merchandise-store table correctly.",
        "type": "SIMPLE",                       # required: one skill (not a COMPOSITE bundle)
        "targetState": "TARGET_STATE_ACTIVE",   # required: agents can download only Active skills
        "scanningConfig": {"policy": "DISABLED"},  # vulnerability scanning is free until 2027, then paid
        "initialRevision": {"archiveUploadSource": {"archiveContent": base64.b64encode(archive).decode()}},
    }
    print(json.dumps(call("POST", f"{API}/skills", params={"skillId": "ga4-context"}, json=body), indent=2))


def show_list() -> None:
    for skill in call("GET", f"{API}/skills").get("skills", []):
        print(f"- {skill['name']}  state={skill.get('state')}  default={skill.get('defaultRevision')}")


def show(skill_id: str) -> None:
    print(json.dumps(call("GET", f"{API}/skills/{skill_id}"), indent=2))
    print(json.dumps(call("GET", f"{API}/skills/{skill_id}/revisions"), indent=2))


def activate(skill_id: str, revision: str) -> None:
    """Make the revision the default and the skill Active, so agents can download it."""
    body = {"defaultRevision": revision, "targetState": "TARGET_STATE_ACTIVE"}
    print(json.dumps(call("PATCH", f"{API}/skills/{skill_id}",
                          params={"updateMask": "defaultRevision,targetState"}, json=body), indent=2))


async def search(query: str) -> None:
    from google.adk.integrations.skill_registry import GCPSkillRegistry
    registry = GCPSkillRegistry(project_id=PROJECT, location=LOCATION)
    for found in await registry.search_skills(query=query):
        print(f"- {found.name}: {found.description[:100]}")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "upload":
        upload()
    elif command == "list":
        show_list()
    elif command == "show":
        show(sys.argv[2])
    elif command == "activate":
        activate(sys.argv[2], sys.argv[3])
    elif command == "search":
        asyncio.run(search(sys.argv[2]))
    else:
        sys.exit(__doc__)
