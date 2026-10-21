# Pre-publish check

Run in the workspace you publish from, right before pressing Publish. The marketplace copies ALL workspace files (checked 2026-10-16), including test leads, outbox batches, the do-not-contact list, reports and logs, so the data must be purged first.

1. `python3 files/scripts/package.py check` → `clean: true` (if not, run `tidy` and reinstall from GitHub as needed).
2. `python3 files/scripts/package.py prepublish` (read-only): show the owner what would be deleted.
3. On the owner's explicit yes: `python3 files/scripts/package.py purge --yes` right before the snapshot. It deletes `files/leadgen/` (test leads, outbox, sequences, do-not-contact list, reports, logs, archives), tool dumps and every other non-package file, then recreates fresh data from `defaults/`. Check `clean_now: true` and that `USER.md` holds nothing about the owner.
4. No Kevin cron tasks in the publishing workspace (`cron list`: no `kevin-lead-batch`, `kevin-followups`, `kevin-weekly-report`, `kevin-signal-watch`).
5. Shared memory holds no test leads or prospects (wipe test entries).
6. Soul field deployed from `marketplace/soul-intro.md` (name Kevin); it must contain the read-first line.
7. Start prompt from `marketplace/startup-task.md`; exclude paths from `marketplace/publish-exclude.txt` (with `workspace/` prefix in the form) as a second safety net.
8. Secrets: none required and none present in the publishing workspace (`AMO_*`, `BITRIX_WEBHOOK_URL`, `HUNTER_API_KEY`, `APOLLO_API_KEY`, `DADATA_API_KEY`, `HH_APP_TOKEN` are added by each buyer in Settings → Secrets).
