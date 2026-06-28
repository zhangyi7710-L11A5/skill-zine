#!/usr/bin/env python3
"""
Skill Market CLI — smcli
========================
Browse, search, and install skills from the Skill Market registry.

Usage:
  smcli list [--category <cat>] [--tag <tag>] [--search <q>] [--registry <url>]
  smcli show <skill-name> [--registry <url>]
  smcli install <skill-name> [--token <token>] [--registry <url>] [--dest <path>]
  smcli purchase <skill-name> [--registry <url>]

Environment:
  SKILL_MARKET_REGISTRY   Default registry API URL (default: http://localhost:3456)
  CODEX_HOME              Codex home directory (default: ~/.codex)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

DEFAULT_REGISTRY = "http://localhost:3456"

# ── colour helpers ──────────────────────────────────────────────────────────
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RED = "\033[31m"
RESET = "\033[0m"


def bold(s: str) -> str:
    return f"{BOLD}{s}{RESET}"


def dim(s: str) -> str:
    return f"{DIM}{s}{RESET}"


def green(s: str) -> str:
    return f"{GREEN}{s}{RESET}"


def yellow(s: str) -> str:
    return f"{YELLOW}{s}{RESET}"


def cyan(s: str) -> str:
    return f"{CYAN}{s}{RESET}"


def red(s: str) -> str:
    return f"{RED}{s}{RESET}"


# ── helpers ─────────────────────────────────────────────────────────────────


def _codex_home() -> str:
    return os.environ.get("CODEX_HOME", os.path.expanduser("~/.codex"))


def _skills_dir() -> str:
    return os.path.join(_codex_home(), "skills")


def _get_registry_url(args_registry: Optional[str]) -> str:
    return (
        args_registry
        or os.environ.get("SKILL_MARKET_REGISTRY")
        or DEFAULT_REGISTRY
    )


def _api_get(url: str) -> dict:
    """Simple GET returning parsed JSON."""
    req = urllib.request.Request(url, headers={"User-Agent": "smcli/1.0"})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            msg = json.loads(body).get("error", body)
        except json.JSONDecodeError:
            msg = body or str(exc)
        raise SystemExit(f"{red('Error')}: {msg}")
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"{red('Error')}: Cannot reach registry — {exc.reason}\n"
            f"  Is the server running? Try: node registry-server.js"
        )


def _api_post(url: str, data: dict) -> dict:
    """Simple POST returning parsed JSON."""
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"User-Agent": "smcli/1.0", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            msg = json.loads(body).get("error", body)
        except json.JSONDecodeError:
            msg = body or str(exc)
        raise SystemExit(f"{red('Error')}: {msg}")


def _installed_skills() -> set[str]:
    root = _skills_dir()
    if not os.path.isdir(root):
        return set()
    return {
        name
        for name in os.listdir(root)
        if os.path.isdir(os.path.join(root, name))
    }


def _pricing_label(pricing: dict) -> str:
    ptype = pricing.get("type", "free")
    if ptype == "free":
        return green("FREE")
    price = pricing.get("price_usd", 0)
    cycle = pricing.get("billing_cycle", "")
    if ptype == "subscription":
        return yellow(f"${price:.2f}/{cycle}")
    return yellow(f"${price:.2f}")


# ── subcommands ─────────────────────────────────────────────────────────────


def cmd_list(args: argparse.Namespace) -> None:
    """List skills from the registry."""
    registry = _get_registry_url(args.registry)
    params = {}
    if args.category:
        params["category"] = args.category
    if args.tag:
        params["tag"] = args.tag
    if args.search:
        params["search"] = args.search
    if args.pricing:
        params["pricing"] = args.pricing

    qs = urllib.parse.urlencode(params) if params else ""
    url = f"{registry}/api/skills"
    if qs:
        url += f"?{qs}"

    data = _api_get(url)
    skills = data.get("skills", [])
    installed = _installed_skills()

    if not skills:
        filter_desc = ", ".join(f"{k}={v}" for k, v in params.items()) or "all"
        print(f"No skills found ({filter_desc}).")
        return

    print()
    print(f"  {bold('Skill Market')}  —  {len(skills)} skill(s)")
    print(f"  Registry: {dim(registry)}")
    print()
    print(f"  {'Name':<26} {'Author':<18} {'Pricing':<14} {'Status'}")
    print(f"  {'─'*26} {'─'*18} {'─'*14} {'─'*12}")

    for skill in skills:
        name = cyan(skill["name"])
        author = dim(skill["author"][:17])
        price = _pricing_label(skill.get("pricing", {}))
        status = green("✓ installed") if skill["name"] in installed else dim("not installed")
        print(f"  {name:<38} {author:<26} {price:<22} {status}")

    print()
    print(f"  {dim('smcli show <name>')}   — details")
    print(f"  {dim('smcli install <name>')} — install")
    print()


def cmd_show(args: argparse.Namespace) -> None:
    """Show skill details."""
    registry = _get_registry_url(args.registry)
    data = _api_get(f"{registry}/api/skills/{args.skill_name}")
    installed = _installed_skills()

    print()
    print(f"  {bold(data['display_name'])}  ({cyan(data['name'])})")
    print(f"  {dim('─' * 60)}")
    print(f"  Version:     {data['version']}")
    print(f"  Author:      {data['author']}")
    print(f"  Category:    {data['category']}")
    print(f"  Tags:        {', '.join(data['tags'])}")
    print(f"  License:     {data['license']}")
    print(f"  Pricing:     {_pricing_label(data['pricing'])}")
    if data.get("rating"):
        print(f"  Rating:      {'★' * int(data['rating'])}{'☆' * (5 - int(data['rating']))}  ({data['rating']})")
    print(f"  Downloads:   {data['downloads']}")
    print()
    print(f"  {data['description']}")
    print()

    source = data.get("source", {})
    if source.get("type") == "github":
        repo = source.get("repo", "?")
        path_ = source.get("path", "")
        ref = source.get("ref", "main")
        print(f"  Source:       https://github.com/{repo}/tree/{ref}/{path_}")
        if source.get("auth_required"):
            print(f"  Auth:         {yellow('Required')} — purchase first")
    elif source.get("type") == "local":
        print(f"  Source:       {source.get('local_path', '?')} (local)")

    if data["name"] in installed:
        print(f"  Status:       {green('✓ Installed')}")
    else:
        print(f"  Status:       {dim('Not installed')}")
        if data["pricing"]["type"] == "free":
            print(f"  Install:      {dim(f'smcli install {data["name"]}')}")
        else:
            print(f"  Purchase:     {dim(f'smcli purchase {data["name"]}')}")

    if data.get("homepage_url"):
        print(f"  Homepage:     {data['homepage_url']}")
    print()


def cmd_install(args: argparse.Namespace) -> None:
    """Install a skill from the registry."""
    registry = _get_registry_url(args.registry)
    name = args.skill_name

    # Check if already installed
    if name in _installed_skills() and not args.force:
        print(f"{yellow('Warning')}: '{name}' is already installed. Use --force to reinstall.")
        return

    # Get install metadata
    url = f"{registry}/api/skills/{name}/install"
    headers = {}
    if args.token:
        headers["X-Skill-Token"] = args.token

    if args.token:
        # POST to auth endpoint for paid skills
        data = _api_post(f"{registry}/api/auth/install/{name}", {"token": args.token})
    else:
        data = _api_get(url)

    if data.get("auth_required"):
        print(f"{yellow('Auth required')}: {data.get('message')}")
        print(f"  Purchase first: smcli purchase {name}")
        return

    source = data.get("source", {})
    if not source:
        raise SystemExit(f"{red('Error')}: No source info returned from registry.")

    source_type = source.get("type", "github")

    if source_type == "github":
        _install_from_github(name, source, args.dest)
    elif source_type == "local":
        _install_from_local(name, source, args.dest)
    else:
        raise SystemExit(f"{red('Error')}: Unsupported source type: {source_type}")


def _install_from_github(name: str, source: dict, dest: Optional[str]) -> None:
    """Install a skill from a GitHub repo."""
    repo = source["repo"]
    path_in_repo = source["path"]
    ref = source.get("ref", "main")

    dest_root = dest or _skills_dir()
    dest_dir = os.path.join(dest_root, name)

    if os.path.exists(dest_dir):
        print(f"{yellow('Warning')}: Destination exists: {dest_dir}")
        return

    # Use existing skill-installer if available
    installer = os.path.join(
        _codex_home(), "skills", "skill-installer", "scripts", "install-skill-from-github.py"
    )

    if os.path.isfile(installer):
        print(f"{dim('Using skill-installer…')}")
        cmd = [
            sys.executable,
            installer,
            "--repo",
            repo,
            "--path",
            path_in_repo,
            "--ref",
            ref,
        ]
        if dest:
            cmd.extend(["--dest", dest])
        if source.get("temp_token"):
            # Inject temporary token as GITHUB_TOKEN
            env = os.environ.copy()
            env["GITHUB_TOKEN"] = source["temp_token"]
            result = subprocess.run(cmd, env=env)
        else:
            result = subprocess.run(cmd)
        if result.returncode != 0:
            raise SystemExit(f"{red('Error')}: Install failed.")
    else:
        # Fallback: manual download & copy
        print(f"{dim('Downloading from GitHub…')}")
        _manual_github_install(name, repo, path_in_repo, ref, dest_root)

    print(f"{green('✓')} Installed {cyan(name)} to {dim(dest_dir)}")
    print(f"  {yellow('Restart Codex to pick up the new skill.')}")


def _manual_github_install(
    name: str, repo: str, path_in_repo: str, ref: str, dest_root: str
) -> None:
    """Fallback: download repo zip and extract the skill directory."""
    owner, repo_name = repo.split("/", 1)
    zip_url = f"https://codeload.github.com/{owner}/{repo_name}/zip/{ref}"

    tmp_dir = tempfile.mkdtemp(prefix="smcli-")
    zip_path = os.path.join(tmp_dir, "repo.zip")

    try:
        # Download
        urllib.request.urlretrieve(zip_url, zip_path)

        # Extract
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp_dir)
            # GitHub zip top-level dir is <repo>-<ref>
            top_dirs = [
                d
                for d in os.listdir(tmp_dir)
                if os.path.isdir(os.path.join(tmp_dir, d))
            ]
            if not top_dirs:
                raise SystemExit(f"{red('Error')}: Empty archive.")
            repo_root = os.path.join(tmp_dir, top_dirs[0])
            skill_src = os.path.join(repo_root, path_in_repo)

        if not os.path.isdir(skill_src):
            raise SystemExit(
                f"{red('Error')}: Path '{path_in_repo}' not found in repo {repo}."
            )

        # Validate
        if not os.path.isfile(os.path.join(skill_src, "SKILL.md")):
            raise SystemExit(
                f"{red('Error')}: SKILL.md not found in '{path_in_repo}'."
            )

        # Copy
        dest_dir = os.path.join(dest_root, name)
        shutil.copytree(skill_src, dest_dir)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _install_from_local(name: str, source: dict, dest: Optional[str]) -> None:
    """Install a skill from a local directory (symlink or copy)."""
    local_path = source.get("local_path", "")
    if not os.path.isdir(local_path):
        raise SystemExit(f"{red('Error')}: Local path not found: {local_path}")

    dest_root = dest or _skills_dir()
    dest_dir = os.path.join(dest_root, name)

    if os.path.exists(dest_dir):
        print(f"{yellow('Warning')}: Destination exists: {dest_dir}")
        return

    os.makedirs(dest_root, exist_ok=True)

    # Try symlink first, fall back to copy
    try:
        os.symlink(os.path.abspath(local_path), dest_dir, target_is_directory=True)
        print(f"{green('✓')} Linked {cyan(name)} → {dim(local_path)}")
    except OSError:
        shutil.copytree(local_path, dest_dir)
        print(f"{green('✓')} Copied {cyan(name)} to {dim(dest_dir)}")

    print(f"  {yellow('Restart Codex to pick up the new skill.')}")


def cmd_purchase(args: argparse.Namespace) -> None:
    """Simulate purchasing a paid skill."""
    registry = _get_registry_url(args.registry)
    name = args.skill_name

    # Show what we're buying
    data = _api_get(f"{registry}/api/skills/{name}")
    pricing = data.get("pricing", {})

    if pricing.get("type") == "free":
        print(f"{green('This skill is free!')} Just run: smcli install {name}")
        return

    print()
    print(f"  {bold('Purchase')}: {cyan(name)}")
    print(f"  Price: {yellow(f'${pricing.get("price_usd", 0):.2f}')} {dim(f'({pricing.get("billing_cycle", "")})')}")
    print()

    # Simulate purchase
    result = _api_post(f"{registry}/api/purchase", {"skill": name})
    token = result.get("token", "")

    print(f"  {green('✓ Purchase simulated!')}")
    print(f"  Token: {dim(token)}")
    print()
    print(f"  Next step: {bold(f'smcli install {name} --token {token}')}")
    print()


# ── main ────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Skill Market CLI — browse and install skills.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  smcli list                          List all skills
  smcli list --category devtools      Filter by category
  smcli list --search "code review"   Search skills
  smcli show code-review-ai           Show skill details
  smcli install hello-world           Install a free skill
  smcli purchase code-review-ai       Purchase a paid skill
  smcli install code-review-ai --token <token>   Install with token
        """,
    )
    parser.add_argument(
        "--registry",
        help="Registry API URL (default: http://localhost:3456)",
    )

    sub = parser.add_subparsers(dest="command", title="commands")

    # list
    p_list = sub.add_parser("list", help="List skills")
    p_list.add_argument("--category", help="Filter by category")
    p_list.add_argument("--tag", help="Filter by tag")
    p_list.add_argument("--search", help="Search query")
    p_list.add_argument("--pricing", choices=["free", "subscription"], help="Filter by pricing type")

    # show
    p_show = sub.add_parser("show", help="Show skill details")
    p_show.add_argument("skill_name", help="Skill name")

    # install
    p_install = sub.add_parser("install", help="Install a skill")
    p_install.add_argument("skill_name", help="Skill name")
    p_install.add_argument("--token", help="Auth token (for paid skills)")
    p_install.add_argument("--dest", help="Destination directory")
    p_install.add_argument("--force", action="store_true", help="Force reinstall")

    # purchase
    p_purchase = sub.add_parser("purchase", help="Purchase a paid skill")
    p_purchase.add_argument("skill_name", help="Skill name")

    args = parser.parse_args()

    if args.command == "list":
        cmd_list(args)
    elif args.command == "show":
        cmd_show(args)
    elif args.command == "install":
        cmd_install(args)
    elif args.command == "purchase":
        cmd_purchase(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
