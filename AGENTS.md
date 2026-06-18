# AGENTS.md

## Repository Rules

- Ubuntu deployment uses `.env`; do not create or use `.env.production`.
- Keep runtime settings in code when practical. Use `.env` mainly for secrets such as API keys.
- Before updating an Ubuntu deployment, create a git commit first.
- Avoid fallback behavior unless the user explicitly asks for it. LLM failures should fail clearly.
- Do not open or run a Next.js frontend port from this project.
- Do not revert user changes outside this workspace.
- Read `BLUEPRINT.md` before changing the simulator architecture.

