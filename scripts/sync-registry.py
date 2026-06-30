#!/usr/bin/env python3
"""
Sync skill registry from openai/skills and community sources.

Run locally or in GitHub Actions:
  python scripts/sync-registry.py

Output: Updated registry.json with the latest skills.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "registry.json"

GITHUB_API = "https://api.github.com"
CURATED_REPO = "openai/skills"
CURATED_PATH = "skills/.curated"
CURATED_REF = "main"

# ── Known community skills (manually curated, checked periodically) ──
COMMUNITY_SKILLS = [
    {
        "name": "power-automate-helper",
        "display_name": "Power Automate Helper",
        "version": "1.0.0",
        "author": "community",
        "description": "Power Automate 云流开发助手。解决步骤名引用、动态内容、Dataverse 列名、Adaptive Card 语法等常见痛点。",
        "category": "productivity",
        "tags": ["power-automate", "microsoft", "low-code", "workflow"],
        "platforms": ["codex", "zcode"],
        "license": "MIT",
        "pricing": {"type": "free", "price_usd": 0},
        "source": {"type": "github", "repo": "openai/skills", "path": "skills/.curated/power-automate-helper", "ref": "main"},
    },
    {
        "name": "frontend-design",
        "display_name": "Frontend Design",
        "version": "1.0.0",
        "author": "community",
        "description": "Build frontends with deliberate visual direction — 8 aesthetic anchors (Swiss, Brutalist, Lo-Fi, etc.), each locked to specific CSS tokens.",
        "category": "design",
        "tags": ["frontend", "design", "css", "ui", "design-system"],
        "platforms": ["codex", "zcode", "claude-code"],
        "license": "MIT",
        "pricing": {"type": "free", "price_usd": 0},
        "source": {"type": "github", "repo": "openai/skills", "path": "skills/.curated/frontend-design", "ref": "main"},
    },
    {
        "name": "hermes-tweet",
        "display_name": "Hermes Tweet",
        "version": "0.1.6",
        "author": "Xquik",
        "description": "Native Hermes Agent X/Twitter plugin guidance for Xquik read-first workflows and approval-gated account actions.",
        "category": "productivity",
        "tags": ["hermes-agent", "x", "twitter", "social-media", "automation"],
        "platforms": ["codex", "zcode", "claude-code"],
        "license": "MIT",
        "pricing": {"type": "free", "price_usd": 0},
        "source": {"type": "github", "repo": "Xquik-dev/hermes-tweet", "path": "SKILL.md", "ref": "main"},
        "homepage_url": "https://github.com/Xquik-dev/hermes-tweet",
    },
    {
        "name": "hue",
        "display_name": "Hue — Design Skill Generator",
        "version": "1.2.0",
        "author": "community",
        "description": "Meta-skill that generates new design language skills. Create custom aesthetic systems for AI coding assistants.",
        "category": "design",
        "tags": ["design", "meta-skill", "design-system", "generator"],
        "platforms": ["codex", "zcode", "claude-code"],
        "license": "MIT",
        "pricing": {"type": "free", "price_usd": 0},
        "source": {"type": "github", "repo": "openai/skills", "path": "skills/.curated/hue", "ref": "main"},
    },
    {
        "name": "plugin-creator",
        "display_name": "Plugin Creator",
        "version": "1.0.0",
        "author": "community",
        "description": "Scaffold Codex plugin directories — valid manifest defaults, plugin folder structure, and marketplace entries.",
        "category": "devtools",
        "tags": ["plugins", "scaffolding", "codex", "marketplace"],
        "platforms": ["codex", "zcode"],
        "license": "MIT",
        "pricing": {"type": "free", "price_usd": 0},
        "source": {"type": "github", "repo": "openai/skills", "path": "skills/.curated/plugin-creator", "ref": "main"},
    },
    {
        "name": "imagegen",
        "display_name": "Image Generation",
        "version": "1.0.0",
        "author": "community",
        "description": "Generate and edit raster images — photos, illustrations, textures, sprites, mockups, and background removal.",
        "category": "media",
        "tags": ["image", "generation", "design", "media", "ai"],
        "platforms": ["codex", "zcode", "claude-code"],
        "license": "MIT",
        "pricing": {"type": "free", "price_usd": 0},
        "source": {"type": "github", "repo": "openai/skills", "path": "skills/.curated/imagegen", "ref": "main"},
    },
    {
        "name": "skill-installer",
        "display_name": "Skill Installer",
        "version": "1.0.0",
        "author": "community",
        "description": "Install Codex skills from GitHub — browse curated and experimental skills, install from any repo with one command.",
        "category": "devtools",
        "tags": ["skills", "installer", "package-management", "codex"],
        "platforms": ["codex", "zcode"],
        "license": "MIT",
        "pricing": {"type": "free", "price_usd": 0},
        "source": {"type": "github", "repo": "openai/skills", "path": "skills/.curated/skill-installer", "ref": "main"},
    },
    {
        "name": "skill-creator",
        "display_name": "Skill Creator",
        "version": "1.0.0",
        "author": "community",
        "description": "Create new skills for Codex — scaffolding, best practices, SKILL.md authoring, and workflow packaging.",
        "category": "devtools",
        "tags": ["skills", "authoring", "scaffolding", "codex"],
        "platforms": ["codex", "zcode"],
        "license": "MIT",
        "pricing": {"type": "free", "price_usd": 0},
        "source": {"type": "github", "repo": "openai/skills", "path": "skills/.curated/skill-creator", "ref": "main"},
    },
    {
        "name": "docx",
        "display_name": "DOCX — Word Documents",
        "version": "1.0.0",
        "author": "community",
        "description": "Complete DOCX creation, editing, and analysis — track changes, comments, formatting preservation, and text extraction.",
        "category": "documentation",
        "tags": ["docx", "word", "documents", "office"],
        "platforms": ["codex", "zcode", "claude-code"],
        "license": "MIT",
        "pricing": {"type": "free", "price_usd": 0},
        "source": {"type": "github", "repo": "openai/skills", "path": "skills/.curated/docx", "ref": "main"},
    },
]

# ── Platform constants ──
P_CODEX = ["codex", "zcode"]               # Codex-native skills (ZCode compatible)
P_UNIVERSAL = ["codex", "zcode", "claude-code"]  # Works everywhere
P_CLAUDE = ["claude-code"]                   # Claude Code only

# ── Skill metadata that can't be derived from directory name ──
SKILL_METADATA: dict[str, dict] = {
    "aspnet-core": {"category": "framework", "display_name": "ASP.NET Core", "tags": ["aspnet", "dotnet", "csharp", "web-api", "backend"], "platforms": P_UNIVERSAL, "description": "Build and maintain ASP.NET Core applications — controllers, middleware, Entity Framework, and best practices."},
    "chatgpt-apps": {"category": "framework", "display_name": "ChatGPT Apps", "tags": ["chatgpt", "openai", "ai", "gpt"], "platforms": P_UNIVERSAL, "description": "Build applications that integrate with ChatGPT — custom GPTs, plugin systems, and conversation APIs."},
    "cli-creator": {"category": "devtools", "display_name": "CLI Creator", "tags": ["cli", "developer-tools", "scaffolding"], "platforms": P_UNIVERSAL, "description": "Scaffold production-ready CLI tools — argument parsing, subcommands, colored output, and shell completions."},
    "cloudflare-deploy": {"category": "deployment", "display_name": "Cloudflare — Deploy", "tags": ["cloudflare", "deploy", "edge", "workers"], "platforms": P_UNIVERSAL, "description": "Deploy to Cloudflare Workers and Pages — edge computing, KV storage, D1 databases at global scale."},
    "define-goal": {"category": "devtools", "display_name": "Define Goal", "tags": ["planning", "project-management", "requirements"], "platforms": P_CODEX, "description": "Clarify project goals before coding — structured discovery to align on scope, constraints, and success criteria."},
    "figma": {"category": "design", "display_name": "Figma — Core", "tags": ["figma", "design", "design-to-code"], "platforms": P_CODEX, "description": "Core Figma integration: read designs, inspect layers, extract tokens, and bridge design to code."},
    "figma-use": {"category": "design", "display_name": "Figma — Use", "tags": ["figma", "design", "workflow"], "platforms": P_CODEX, "description": "Smart Figma file selector — pick the right design file, page, and frame for your task."},
    "figma-create-new-file": {"category": "design", "display_name": "Figma — Create New File", "tags": ["figma", "design", "automation"], "platforms": P_CODEX, "description": "Create new Figma design files programmatically — set up canvases, frames, and starter layouts."},
    "figma-create-design-system-rules": {"category": "design", "display_name": "Figma — Design System Rules", "tags": ["figma", "design-system", "tokens"], "platforms": P_CODEX, "description": "Extract design system rules from Figma — tokens, spacing, typography scales, and color palettes."},
    "figma-generate-design": {"category": "design", "display_name": "Figma — Generate Design", "tags": ["figma", "design", "ai-generation"], "platforms": P_CODEX, "description": "Generate complete UI designs in Figma from text descriptions — layout, components, styles, all auto-created."},
    "figma-generate-library": {"category": "design", "display_name": "Figma — Generate Library", "tags": ["figma", "design", "component-library"], "platforms": P_CODEX, "description": "Generate Figma component libraries — build reusable component sets with variants and properties."},
    "figma-implement-design": {"category": "design", "display_name": "Figma — Implement Design", "tags": ["figma", "design", "code-generation", "design-to-code"], "platforms": P_CODEX, "description": "Turn Figma designs into production code. Reads frames, auto-generates components with matching styles."},
    "figma-code-connect-components": {"category": "design", "display_name": "Figma — Code Connect", "tags": ["figma", "design", "code-connect", "dev-handoff"], "platforms": P_CODEX, "description": "Connect Figma components to code — map design components to their code counterparts for bi-directional sync."},
    "gh-address-comments": {"category": "devtools", "display_name": "GitHub — Address Comments", "tags": ["github", "code-review", "pull-requests", "workflow"], "platforms": P_UNIVERSAL, "description": "Process GitHub PR review comments — triage, respond, and resolve review feedback systematically."},
    "gh-fix-ci": {"category": "devtools", "display_name": "GitHub — Fix CI", "tags": ["github", "ci-cd", "devops", "debugging"], "platforms": P_UNIVERSAL, "description": "Diagnose and fix failing CI/CD pipelines — read logs, identify root cause, apply fixes, and re-run."},
    "hatch-pet": {"category": "fun", "display_name": "Hatch Pet", "tags": ["pet", "fun", "terminal", "tamagotchi"], "platforms": P_UNIVERSAL, "description": "A virtual pet for your terminal — hatch, feed, and play with a creature that grows as you code."},
    "jupyter-notebook": {"category": "devtools", "display_name": "Jupyter Notebook", "tags": ["jupyter", "notebook", "data-science", "python"], "platforms": P_UNIVERSAL, "description": "Create, edit, and execute Jupyter notebooks — data analysis, visualization, and reproducible research."},
    "linear": {"category": "devtools", "display_name": "Linear — Issue Tracking", "tags": ["linear", "project-management", "issues", "workflow"], "platforms": P_CODEX, "description": "Manage Linear issues — create, triage, and track tasks with the Linear project management API."},
    "migrate-to-codex": {"category": "migration", "display_name": "Migrate to Codex", "tags": ["migration", "codex", "onboarding", "setup"], "platforms": P_CODEX, "description": "Migrate projects and workflows from other AI coding tools to Codex — config conversion, setup, and onboarding."},
    "netlify-deploy": {"category": "deployment", "display_name": "Netlify — Deploy", "tags": ["netlify", "deploy", "frontend", "serverless"], "platforms": P_UNIVERSAL, "description": "Deploy to Netlify with a single command — static sites, serverless functions, forms, and edge functions."},
    "notion-knowledge-capture": {"category": "productivity", "display_name": "Notion — Knowledge Capture", "tags": ["notion", "knowledge-management", "notes"], "platforms": P_CODEX, "description": "Capture meeting notes, research, and ideas into structured Notion pages automatically."},
    "notion-meeting-intelligence": {"category": "productivity", "display_name": "Notion — Meeting Intelligence", "tags": ["notion", "meetings", "productivity"], "platforms": P_CODEX, "description": "Prepare agendas, take structured notes, and extract action items into Notion databases."},
    "notion-research-documentation": {"category": "productivity", "display_name": "Notion — Research Documentation", "tags": ["notion", "research", "documentation"], "platforms": P_CODEX, "description": "Transform research notes and references into polished Notion documentation with proper structure."},
    "notion-spec-to-implementation": {"category": "productivity", "display_name": "Notion — Spec to Implementation", "tags": ["notion", "project-management", "specs"], "platforms": P_CODEX, "description": "Turn Notion product specs into implementation plans — break down features, estimate work, create tasks."},
    "openai-docs": {"category": "documentation", "display_name": "OpenAI — Docs", "tags": ["openai", "api", "docs", "reference"], "platforms": P_UNIVERSAL, "description": "Access up-to-date OpenAI API documentation — model guidance, migration guides, and best practices with citations."},
    "pdf": {"category": "documentation", "display_name": "PDF Toolkit", "tags": ["pdf", "documents", "latex", "reports", "forms"], "platforms": P_UNIVERSAL, "description": "Professional PDF toolkit — create reports, posters, forms, LaTeX docs, merge, split, extract, and convert."},
    "playwright": {"category": "testing", "display_name": "Playwright — Browser Automation", "tags": ["playwright", "browser", "testing", "automation", "e2e"], "platforms": P_UNIVERSAL, "description": "Full browser automation with Playwright — navigate, click, fill forms, take screenshots, run assertions."},
    "playwright-interactive": {"category": "testing", "display_name": "Playwright — Interactive", "tags": ["playwright", "browser", "interactive", "debugging"], "platforms": P_UNIVERSAL, "description": "Interactive browser sessions — explore, debug, and interact with web pages in real-time during development."},
    "render-deploy": {"category": "deployment", "display_name": "Render — Deploy", "tags": ["render", "deploy", "cloud", "backend"], "platforms": P_UNIVERSAL, "description": "Deploy to Render — web services, background workers, cron jobs, and managed databases."},
    "screenshot": {"category": "media", "display_name": "Screenshot", "tags": ["screenshot", "browser", "media", "capture"], "platforms": P_UNIVERSAL, "description": "Capture screenshots of web pages — full page, viewport, or specific elements with multiple output formats."},
    "security-best-practices": {"category": "security", "display_name": "Security — Best Practices", "tags": ["security", "owasp", "code-review", "best-practices"], "platforms": P_UNIVERSAL, "description": "Apply OWASP-aligned security best practices during code review and development — catch vulnerabilities before they ship."},
    "security-ownership-map": {"category": "security", "display_name": "Security — Ownership Map", "tags": ["security", "ownership", "governance"], "platforms": P_UNIVERSAL, "description": "Map security ownership across your codebase — identify who owns what and track security responsibilities."},
    "security-threat-model": {"category": "security", "display_name": "Security — Threat Model", "tags": ["security", "threat-modeling", "stride", "architecture"], "platforms": P_UNIVERSAL, "description": "Generate threat models for your application — identify attack surfaces, threats, and mitigations using STRIDE."},
    "sentry": {"category": "devtools", "display_name": "Sentry — Error Monitoring", "tags": ["sentry", "monitoring", "error-tracking", "observability"], "platforms": P_CODEX, "description": "Integrate Sentry for error monitoring — set up projects, configure SDKs, and triage production errors."},
    "speech": {"category": "media", "display_name": "Speech — Text to Speech", "tags": ["speech", "tts", "audio", "openai"], "platforms": P_CODEX, "description": "Convert text to natural-sounding speech using OpenAI TTS models — multiple voices and formats."},
    "transcribe": {"category": "media", "display_name": "Transcribe — Speech to Text", "tags": ["transcription", "whisper", "audio", "speech-to-text", "openai"], "platforms": P_CODEX, "description": "Transcribe audio and video files to text using Whisper — supports multiple languages and formats."},
    "vercel-deploy": {"category": "deployment", "display_name": "Vercel — Deploy", "tags": ["vercel", "deploy", "frontend", "cloud"], "platforms": P_UNIVERSAL, "description": "One-command deployment to Vercel — ship frontends, APIs, and full-stack apps to production instantly."},
    "winui-app": {"category": "framework", "display_name": "WinUI App", "tags": ["winui", "windows", "dotnet", "desktop", "xaml"], "platforms": P_UNIVERSAL, "description": "Build native Windows applications with WinUI 3 — XAML, MVVM, and Windows App SDK integration."},
    "yeet": {"category": "devtools", "display_name": "Yeet", "tags": ["utility", "cleanup", "fun"], "platforms": P_UNIVERSAL, "description": "Quickly discard or archive — yeet files, branches, or configs you no longer need with style."},
}


def gh_request(path: str, raw: bool = False) -> bytes:
    """Make a GitHub API or raw request."""
    if raw:
        url = f"https://raw.githubusercontent.com/{path}"
    else:
        url = f"{GITHUB_API}{path}"
    headers = {"User-Agent": "skill-zine-sync/1.0"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def fetch_curated_skills() -> list[str]:
    """Return list of skill directory names from openai/skills curated."""
    data = gh_request(
        f"/repos/{CURATED_REPO}/contents/{CURATED_PATH}?ref={CURATED_REF}"
    )
    items = json.loads(data.decode("utf-8"))
    return sorted(
        item["name"] for item in items if item.get("type") == "dir"
    )


def try_fetch_description(name: str) -> Optional[str]:
    """Try to fetch the SKILL.md description for a curated skill."""
    try:
        raw = gh_request(
            f"{CURATED_REPO}/{CURATED_REF}/{CURATED_PATH}/{name}/SKILL.md",
            raw=True,
        ).decode("utf-8")
        for line in raw.splitlines():
            if line.startswith("description:"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return None


def build_registry(curated_names: list[str]) -> dict:
    """Build the full registry.json structure."""
    existing = {}
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            old = json.load(f)
            for s in old.get("skills", []):
                existing[s["name"]] = s

    skills = []

    # ── Curated skills ──
    for name in curated_names:
        meta = SKILL_METADATA.get(name, {})
        old_entry = existing.get(name, {})

        category = meta.get("category") or _guess_category(name)
        display_name = meta.get("display_name") or name.replace("-", " ").title()
        tags = meta.get("tags") or []
        platforms = meta.get("platforms") or P_CODEX
        description = meta.get("description") or old_entry.get("description") or ""

        # Try to enrich description from live SKILL.md if missing
        if not description:
            live_desc = try_fetch_description(name)
            if live_desc:
                description = live_desc

        if not description:
            description = f"Skill: {name}"

        skills.append({
            "name": name,
            "display_name": display_name,
            "version": old_entry.get("version", "1.0.0"),
            "author": "openai",
            "description": description,
            "category": category,
            "tags": tags,
            "platforms": platforms,
            "license": "MIT",
            "pricing": {"type": "free", "price_usd": 0},
            "source": {
                "type": "github",
                "repo": CURATED_REPO,
                "path": f"{CURATED_PATH}/{name}",
                "ref": CURATED_REF,
            },
            "downloads": old_entry.get("downloads", 0),
        })

    # ── Community skills (keep existing if not in curated) ──
    curated_set = set(curated_names)
    for cs in COMMUNITY_SKILLS:
        if cs["name"] in curated_set:
            continue  # Already covered as curated
        old_entry = existing.get(cs["name"], {})
        skills.append({
            **cs,
            "downloads": old_entry.get("downloads", 0),
        })

    # ── Any existing community skills not in our hardcoded list ──
    for old_skill in existing.values():
        if old_skill["name"] not in {s["name"] for s in skills}:
            if old_skill.get("author") != "openai":
                skills.append(old_skill)

    # Sort: openai skills first, then community, alphabetical
    skills.sort(key=lambda s: (0 if s.get("author") == "openai" else 1, s["name"]))

    return {
        "version": "2.0.0",
        "updated": _utc_now(),
        "source": "openai/skills + community (auto-synced)",
        "skills": skills,
    }


def _guess_category(name: str) -> str:
    """Guess category from skill name when metadata is missing."""
    name_lower = name.lower()
    if any(k in name_lower for k in ["figma", "design", "ui", "css", "style"]):
        return "design"
    if any(k in name_lower for k in ["deploy", "cloudflare", "vercel", "netlify", "render"]):
        return "deployment"
    if any(k in name_lower for k in ["security", "threat", "auth"]):
        return "security"
    if any(k in name_lower for k in ["playwright", "test", "browser"]):
        return "testing"
    if any(k in name_lower for k in ["notion", "linear", "sentry", "productivity"]):
        return "productivity"
    if any(k in name_lower for k in ["pdf", "doc", "document", "docs"]):
        return "documentation"
    if any(k in name_lower for k in ["speech", "transcrib", "audio", "image", "screenshot", "media"]):
        return "media"
    if any(k in name_lower for k in ["github", "gh-", "cli", "git"]):
        return "devtools"
    if any(k in name_lower for k in ["aspnet", "winui", "chatgpt", "api", "sdk"]):
        return "framework"
    return "devtools"


def _utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    print("🔍 Fetching curated skills from openai/skills…")
    try:
        curated_names = fetch_curated_skills()
        print(f"   Found {len(curated_names)} curated skills.")
    except Exception as e:
        print(f"   ⚠️  Failed to fetch: {e}")
        print("   Falling back to existing registry…")
        if REGISTRY_PATH.exists():
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                old = json.load(f)
            curated_names = [
                s["name"] for s in old.get("skills", [])
                if s.get("author") == "openai"
            ]
            print(f"   Using {len(curated_names)} cached skill names.")
        else:
            curated_names = []

    print("📦 Building registry…")
    registry = build_registry(curated_names)
    total = len(registry["skills"])
    categories = sorted(set(s["category"] for s in registry["skills"]))

    print(f"   {total} skills across {len(categories)} categories: {', '.join(categories)}")

    # ── Detect changes ──
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            old = json.load(f)
        old_names = {s["name"] for s in old.get("skills", [])}
        new_names = {s["name"] for s in registry["skills"]}
        added = new_names - old_names
        removed = old_names - new_names
        if added:
            print(f"   🆕 New skills: {', '.join(sorted(added))}")
        if removed:
            print(f"   ❌ Removed skills: {', '.join(sorted(removed))}")
        if not added and not removed:
            print("   ✅ No changes — registry is up to date.")

    print(f"💾 Writing {REGISTRY_PATH}…")
    json_str = json.dumps(registry, indent=2, ensure_ascii=False) + "\n"
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        f.write(json_str)

    # Also write to docs/ for GitHub Pages
    public_registry = ROOT / "docs" / "registry.json"
    public_registry.parent.mkdir(parents=True, exist_ok=True)
    with open(public_registry, "w", encoding="utf-8") as f:
        f.write(json_str)
    print(f"   Also wrote {public_registry}")

    print("✔ Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
