# DevDay full rehearsal

Use a separate event `devday-rehearsal-2026` on the existing platform. This
replaces the earlier separate-infrastructure proposal: API, DB, upload mount
and authentication cookie origin are shared. Only the event's synthetic data
and event-exclusive accounts are separate. Do not claim network/DB isolation.

The application must include plan 0037 and migration `0016_devday_rehearsal`
before seeding; the old version rejects team numbers 26–40 and DevDay judging
for this slug. Its main CI publishes API/web images and updates this repository's
production image tags. Let Argo perform the migration/rollout; do not patch live
Deployments. Verify actual images, successful migration and API/web health.

Before an authorized schema rollout, take and verify a database backup per
`services/hackathon-platform/README.md`. Record fingerprints of existing event,
account, team, submission and judging rows and uploaded files; compare afterward.
The additive migration only extends the range function's explicit slug allowlist.
Never seed or reset the actual `devday-seoul-2026` event.

## Prepare credentials and fixtures

The seed script reads actual event settings and creates only the rehearsal
slug. It refuses an existing rehearsal event, uses one DB transaction, and
creates synthetic teams, individual passwords, independent PDF/ZIP files and
code bindings. Passwords and submission codes must never appear in Git or CI logs.
Run from the Ops checkout only after the application rollout is authorized:

```bash
install -d -m 700 "$HOME/.local/share/hackathon-ops/devday-rehearsal-2026"
umask 077
kubectl -n hackathon-platform exec -i deploy/hackathon-platform-api -- \
  python - seed < scripts/hackathon-platform/rehearsal.py \
  > "$HOME/.local/share/hackathon-ops/devday-rehearsal-2026/credentials.json"
chmod 600 "$HOME/.local/share/hackathon-ops/devday-rehearsal-2026/credentials.json"
```

Deliver individual credentials via the team's existing private password manager
or a private SSH/SCP session to the server. The mode-0600 file is an administrator
bundle: distribute only each judge's own credentials; submission codes go to
assigned test participants. Do not place the bundle on a public download URL.
The thirteen QA accounts are event-exclusive and expire seven days after seeding.

Rehearsal pages:

- `/events/devday-rehearsal-2026/submit`: participant submissions/status.
- `/events/devday-rehearsal-2026/login`: QA administrator and judges.
- `/events/devday-rehearsal-2026/operations/teams`: submissions and PDF preview.
- `/events/devday-rehearsal-2026/judging`: preparation, order, scoring and results.
- `/events/devday-rehearsal-2026/presentations`: redacted public presentation order.

The event name and all its routes show QA status. The seed prepares 40 named
teams, 20 per track, all with synthetic complete repo/PDF/ZIP submissions.
Repo addresses under `example.test` are deliberately synthetic; do not expect
live source repositories. PDF slides and ZIP entries clearly identify QA data.

Three judges are assigned per first-round track; six final judges are common to
both tracks. For testing finalist selection, the QA finalist count is three per
track. Actual first-round assignments/finalist counts remain unchanged. Rubrics
copy saved actual rubrics when available; otherwise the current application's
DevDay workbook template is saved into QA draft sessions. No QA scoring opens at
seed time. No actual event session opens as a side effect.

## Rehearsal sequence

1. Claim/access assigned codes; verify all 40 teams and both track filters.
2. Resubmit repo, PDF and ZIP independently. Retry identical upload IDs/bytes;
   verify authorized downloads and SHA-256, including a replaced PDF's preview.
3. Move only the QA deadline forward/backward. Before presentation freezing,
   validate late-new-bytes rejection and recovery of files received in time.
4. Close the QA submission window, freeze the forty-team presentation order,
   preview PDFs, download track PDF archives and move/exclude/restore a team.
5. With each first-round judge, check only the assigned track is accessible.
   With a common final judge, check both final tracks. Check unrelated accounts
   cannot access the rehearsal event or its scores.
6. Open only QA first-round sessions, score teams and inspect aggregates. Select
   three finalists in each track explicitly, open final sessions and score with
   six common judges. Finalists are never inferred from result sorting.

Change the QA deadline, including relative seconds for boundary tests:

```bash
kubectl -n hackathon-platform exec -i deploy/hackathon-platform-api -- \
  python - deadline --seconds 3600 < scripts/hackathon-platform/rehearsal.py
kubectl -n hackathon-platform exec -i deploy/hackathon-platform-api -- \
  python - deadline --seconds -1 < scripts/hackathon-platform/rehearsal.py
```

The command is hard-bound to the QA slug and records an audit event. Freeze and
open scoring are separate explicit UI actions; preserve snapshots/audit history.
Do not overwrite the rehearsal with the seed script after manual testing starts.
The old two-team QA event and its manual submission fixture remain untouched.
