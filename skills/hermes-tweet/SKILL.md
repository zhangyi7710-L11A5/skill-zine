---
name: hermes-tweet
description: Native Hermes Agent X/Twitter plugin guidance for Xquik read-first workflows and approval-gated account actions.
metadata:
  short-description: Hermes Agent X/Twitter plugin guidance
  category: productivity
  tags: [hermes-agent, x, twitter, social-media, automation]
  license: MIT
---

# Hermes Tweet

Hermes Tweet is a native Hermes Agent plugin for X/Twitter automation through
Xquik. Use it for social listening, account reads, trend research, giveaway
audits, creator research, support triage, and controlled publishing workflows.

## Install

```bash
hermes plugins install Xquik-dev/hermes-tweet --enable
```

Configure `XQUIK_API_KEY` in the Hermes runtime environment or
`~/.hermes/.env` before calling read endpoints.

## Tool Flow

1. Use `tweet_explore` to find the exact catalog-listed `/api/v1/...` route.
2. Use `tweet_read` for read-only account, search, trend, monitor, media, draw,
   extraction, and export routes.
3. Keep `tweet_action` disabled unless the session explicitly sets
   `HERMES_TWEET_ENABLE_ACTIONS=true`.
4. Treat posting, replies, DMs, follows, monitor changes, media uploads, and
   webhook changes as approval-gated actions.
5. Never place API keys, cookies, account credentials, or private tokens in
   prompts, issues, PR comments, or tool arguments.

## Source

- Repository: https://github.com/Xquik-dev/hermes-tweet
- Package: https://pypi.org/project/hermes-tweet/
- License: MIT

