/**
 * Skill Market — Registry API Server
 *
 * Minimal zero-dependency API for browsing and installing skills.
 * Start: node registry-server.js [--port 3456]
 *
 * Endpoints:
 *   GET  /api/registry              — full registry dump
 *   GET  /api/skills                 — list all skills (summary)
 *   GET  /api/skills/:name           — single skill detail
 *   GET  /api/skills/:name/install   — install metadata (for CLI)
 *   POST /api/auth/install/:name     — verify token & return source info
 */

const http = require("http");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
const PORT = parseInt(process.argv.find((a) => a.startsWith("--port="))?.split("=")[1] || "3456", 10);
const REGISTRY_PATH = path.join(__dirname, "registry.json");

// Simulated auth tokens (in real world: database)
const PAID_TOKENS = new Map(); // token -> { skill, expires }

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function loadRegistry() {
  const raw = fs.readFileSync(REGISTRY_PATH, "utf-8");
  return JSON.parse(raw);
}

function jsonReply(res, status, data) {
  res.writeHead(status, {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
  });
  res.end(JSON.stringify(data, null, 2));
}

function parseBody(req) {
  return new Promise((resolve) => {
    let body = "";
    req.on("data", (chunk) => (body += chunk));
    req.on("end", () => {
      try {
        resolve(JSON.parse(body || "{}"));
      } catch {
        resolve({});
      }
    });
  });
}

function skillSummary(skill) {
  return {
    name: skill.name,
    display_name: skill.display_name,
    version: skill.version,
    author: skill.author,
    description: skill.description,
    category: skill.category,
    tags: skill.tags,
    platforms: skill.platforms || [],
    pricing: skill.pricing,
    rating: skill.rating,
    downloads: skill.downloads,
    icon_url: skill.icon_url,
  };
}

// ---------------------------------------------------------------------------
// Route handlers
// ---------------------------------------------------------------------------
async function handleGetRegistry(req, res) {
  const registry = loadRegistry();
  jsonReply(res, 200, registry);
}

async function handleListSkills(req, res) {
  const reg = loadRegistry();
  const { category, tag, pricing, search } = Object.fromEntries(
    new URL(req.url, "http://localhost").searchParams
  );

  let skills = reg.skills;

  if (category) {
    skills = skills.filter((s) => s.category === category);
  }
  if (tag) {
    skills = skills.filter((s) => s.tags.includes(tag));
  }
  if (pricing) {
    skills = skills.filter((s) => s.pricing.type === pricing);
  }
  if (search) {
    const q = search.toLowerCase();
    skills = skills.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        s.display_name?.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q) ||
        s.tags.some((t) => t.toLowerCase().includes(q))
    );
  }

  jsonReply(res, 200, {
    total: skills.length,
    skills: skills.map(skillSummary),
  });
}

async function handleGetSkill(req, res, name) {
  const reg = loadRegistry();
  const skill = reg.skills.find((s) => s.name === name);
  if (!skill) {
    return jsonReply(res, 404, { error: `Skill '${name}' not found.` });
  }
  jsonReply(res, 200, skill);
}

async function handleInstallMeta(req, res, name) {
  const reg = loadRegistry();
  const skill = reg.skills.find((s) => s.name === name);
  if (!skill) {
    return jsonReply(res, 404, { error: `Skill '${name}' not found.` });
  }

  // For free skills: return source info directly
  if (skill.pricing.type === "free") {
    return jsonReply(res, 200, {
      skill: skill.name,
      source: skill.source,
      message: "Free skill — install directly.",
    });
  }

  // For paid skills: require auth
  return jsonReply(res, 200, {
    skill: skill.name,
    pricing: skill.pricing,
    auth_required: true,
    message: `This is a ${skill.pricing.type} skill. Purchase first, then call /api/auth/install/:name with your token.`,
  });
}

async function handleAuthInstall(req, res, name) {
  const reg = loadRegistry();
  const skill = reg.skills.find((s) => s.name === name);
  if (!skill) {
    return jsonReply(res, 404, { error: `Skill '${name}' not found.` });
  }

  if (skill.pricing.type === "free") {
    return jsonReply(res, 200, {
      skill: skill.name,
      source: skill.source,
      message: "Free skill — no auth needed. Use /api/skills/:name/install instead.",
    });
  }

  // Check auth token
  const body = await parseBody(req);
  const token = body.token || req.headers["x-skill-token"];

  if (!token) {
    return jsonReply(res, 401, { error: "Missing auth token. Purchase this skill first." });
  }

  const entry = PAID_TOKENS.get(token);
  if (!entry) {
    return jsonReply(res, 403, { error: "Invalid or expired token." });
  }

  if (entry.skill !== name) {
    return jsonReply(res, 403, { error: `Token is for '${entry.skill}', not '${name}'.` });
  }

  if (entry.expires < Date.now()) {
    PAID_TOKENS.delete(token);
    return jsonReply(res, 403, { error: "Token has expired." });
  }

  // Return source info with temporary access
  return jsonReply(res, 200, {
    skill: skill.name,
    source: {
      ...skill.source,
      // In production: generate a temporary GitHub token / signed URL
      temp_token: crypto.randomBytes(16).toString("hex"),
      expires_in: 3600,
    },
    message: "Authenticated. Use the source info to install.",
  });
}

// ---------------------------------------------------------------------------
// Simulate purchase (for demo)
// ---------------------------------------------------------------------------
async function handlePurchase(req, res) {
  const body = await parseBody(req);
  const name = body.skill;
  const reg = loadRegistry();
  const skill = reg.skills.find((s) => s.name === name);

  if (!skill) {
    return jsonReply(res, 404, { error: `Skill '${name}' not found.` });
  }

  if (skill.pricing.type === "free") {
    return jsonReply(res, 400, { error: "This skill is free. No purchase needed." });
  }

  // Simulate: generate a token
  const token = "sm_" + crypto.randomBytes(16).toString("hex");
  PAID_TOKENS.set(token, {
    skill: name,
    expires: Date.now() + 30 * 24 * 3600 * 1000, // 30 days
  });

  jsonReply(res, 200, {
    message: `Purchase simulated! Token valid for 30 days.`,
    token: token,
    skill: name,
    next_step: `Run: smcli install ${name} --token ${token}`,
  });
}

// ---------------------------------------------------------------------------
// Static file serving
// ---------------------------------------------------------------------------
const PUBLIC_DIR = path.join(__dirname, "docs");
const MIME_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json",
  ".png": "image/png",
  ".svg": "image/svg+xml",
};

function serveStatic(req, res, filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const mime = MIME_TYPES[ext] || "application/octet-stream";
  try {
    const content = fs.readFileSync(filePath);
    res.writeHead(200, {
      "Content-Type": mime,
      "Access-Control-Allow-Origin": "*",
    });
    res.end(content);
  } catch (err) {
    if (err.code === "ENOENT") {
      jsonReply(res, 404, { error: "Not found." });
    } else {
      jsonReply(res, 500, { error: err.message });
    }
  }
}

// ---------------------------------------------------------------------------
// Router
// ---------------------------------------------------------------------------
const server = http.createServer(async (req, res) => {
  // CORS preflight
  if (req.method === "OPTIONS") {
    res.writeHead(204, {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, X-Skill-Token",
    });
    return res.end();
  }

  const parsed = new URL(req.url, "http://localhost");
  const route = parsed.pathname;

  try {
    // GET / or /index.html → serve the storefront
    if (req.method === "GET" && (route === "/" || route === "/index.html")) {
      return serveStatic(req, res, path.join(PUBLIC_DIR, "index.html"));
    }

    // GET /api/registry
    if (req.method === "GET" && route === "/api/registry") {
      return handleGetRegistry(req, res);
    }

    // GET /api/skills
    if (req.method === "GET" && route === "/api/skills") {
      return handleListSkills(req, res);
    }

    // GET /api/skills/:name
    const skillMatch = route.match(/^\/api\/skills\/([^\/]+)$/);
    if (req.method === "GET" && skillMatch) {
      return handleGetSkill(req, res, skillMatch[1]);
    }

    // GET /api/skills/:name/install
    const installMatch = route.match(/^\/api\/skills\/([^\/]+)\/install$/);
    if (req.method === "GET" && installMatch) {
      return handleInstallMeta(req, res, installMatch[1]);
    }

    // POST /api/auth/install/:name
    const authMatch = route.match(/^\/api\/auth\/install\/([^\/]+)$/);
    if (req.method === "POST" && authMatch) {
      return handleAuthInstall(req, res, authMatch[1]);
    }

    // POST /api/purchase (demo)
    if (req.method === "POST" && route === "/api/purchase") {
      return handlePurchase(req, res);
    }

    // 404
    jsonReply(res, 404, { error: "Not found." });
  } catch (err) {
    console.error(err);
    jsonReply(res, 500, { error: err.message });
  }
});

server.listen(PORT, () => {
  console.log(`\n  Skill Market Registry API`);
  console.log(`  ────────────────────────`);
  console.log(`  Listening on http://localhost:${PORT}\n`);
  console.log(`  Endpoints:`);
  console.log(`    GET  /api/registry              — Full registry`);
  console.log(`    GET  /api/skills                — List skills`);
  console.log(`    GET  /api/skills/:name          — Skill detail`);
  console.log(`    GET  /api/skills/:name/install  — Install metadata`);
  console.log(`    POST /api/auth/install/:name    — Auth install (paid)`);
  console.log(`    POST /api/purchase              — Simulate purchase`);
  console.log();
});
