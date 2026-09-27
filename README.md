# Job Search Watcher

A personal job-search automation built on the [JobsPipe](https://jobspipe.dev) API and Claude (Cowork). It searches on a schedule, scores each result against a resume, removes duplicates and postings already seen, and delivers the results as an email digest and a live dashboard page.

This repository holds a spec and two templates, not a program you install and run. The intended use is to hand `SETUP.md` to Claude in a Cowork session and let it walk you through configuring your own copy.

## What it does

Each scheduled run does the following: queries JobsPipe for postings matching your titles, salary floor, and location rule; reads your stored criteria and resume; drops postings already surfaced in an earlier run; scores every remaining posting against your resume with a fit tier and a one-line rationale; records the results in a small database attached to your dashboard page; and delivers a digest by email, on the dashboard, or both.

Two cadences are typical: a short-lookback weekly run, and a longer-lookback monthly run that catches older listings the weekly window would otherwise miss.

## Prerequisites

You need your own JobsPipe API key, a Cowork account with access to scheduled tasks and the Artifact tool, and a resume in any text or document format. See `SETUP.md` for the full list, including an optional Gmail connection.

## Quick start

Open a new Cowork session, attach or paste the contents of `SETUP.md`, and tell Claude to read it and follow it. Claude will interview you for your criteria before building anything — do not skip ahead.

## Repository structure

- `SETUP.md` — the full setup spec: the interview questions, the dashboard and database design, the fetch-and-score design, and how to configure the scheduled tasks.
- `templates/jobspipe_fetch_template.py` — a fetch script with placeholder sections for your titles, salary floor, curated and excluded employers, and location rule.
- `templates/job_search_watcher_template.html` — a dashboard page with no personal data baked in; all criteria live in its attached database, filled in during setup.
- `LICENSE` — MIT license.

## A note on JobsPipe's acceptable use policy

This setup requires each person to use their own JobsPipe API key rather than sharing one, does not redistribute JobsPipe's data in bulk, and every posting shown on the dashboard or in a digest links back to the original listing. Review [JobsPipe's acceptable use policy](https://jobspipe.dev/acceptable-use) yourself before relying on this, since it may change.

## License

MIT — see `LICENSE`.
