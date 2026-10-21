# Startup task (runs when the agent starts)

Put the prompt below into the public agent's start prompt. The marketplace copies the whole workspace, so the package files, AGENTS.md and skills are already in place; the marketplace copies ALL workspace files (checked 2026-10-16), so the publishing workspace is purged first (`marketplace/pre-publish-check.md`), and `package.py start` recreates `files/leadgen/` from `defaults/` for each new user.

## Prompt

```
A new user has just hired you. Set up the workspace quietly and start onboarding.
1. If python3 is missing, install it (apk add python3).
2. Run: python3 files/scripts/package.py start
3. Your whole reply is the text between "SAY:" and "THEN:" in its output, exactly as printed, with its line breaks and emojis. Do not translate it: it is the language choice. Nothing else: no setup details, file names, commands or check results.
4. When the user answers, do what the "THEN:" line says.
If the command could not run at all, reply only: "Setup isn't finished yet. Write me any message and I'll finish it."
Do not create cron jobs.
```

## Before publishing

Follow `marketplace/pre-publish-check.md`: show `python3 files/scripts/package.py prepublish` to the owner and, on their explicit yes, run `python3 files/scripts/package.py purge --yes` right before the snapshot. Then fill «Исключаемые пути» from `marketplace/publish-exclude.txt` as a second safety net.

## Check after install

- `grep -c "leadgen-addon:v1" AGENTS.md` returns 1, including after a restart.
- `skills_manage list` shows all 15 skills.
