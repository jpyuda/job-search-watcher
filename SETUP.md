# Job Search Watcher — setup spec

## What this is

This is a spec for a personal job-search automation. It searches JobsPipe (jobspipe.dev) on a schedule for roles matching a stated set of criteria, scores each result against a resume, removes duplicates and previously-seen postings, and delivers the results two ways: an email digest, and a live dashboard page.

This document is meant to be handed to Claude, in a Cowork session, with the instruction: "Read this spec and follow it." Claude should not skip ahead to building anything before Step 1 is complete — Step 1 is a conversation, not a build step.

## Before starting

The person following this spec needs:

- A JobsPipe account and API key (jobspipe.dev). The free tier allows 1,000 searches a month, which comfortably covers a weekly-plus-monthly cadence at the query volume this spec uses. Use your own key — JobsPipe's acceptable use policy prohibits sharing API keys or circumventing quotas, so this setup is per person, not something two people can run off one account.
- A Cowork account with access to scheduled tasks (sometimes called triggers) and the Artifact tool. Scheduled tasks are what let this run automatically on a cadence without a person starting it each time; the Artifact tool is what publishes the live dashboard page and gives it a small shared database.
- A resume, in any text or document format, to score results against.
- Optionally, a Gmail connection in Cowork, if the digest should be emailed rather than only shown on the dashboard, or if a second job-alert source (see the note near the end) should be folded in.

## Step 1 — the interview

Before writing or configuring anything, Claude should ask the person a series of questions and record the answers. Do not proceed to Step 2 until all of these have real answers (not placeholders). Ask them conversationally, a few at a time, rather than as one long form — but make sure every one gets answered.

1. **Salary floor.** The single hard minimum salary to search for, in USD. (Optional refinement: some people want a rule where jobs closer to the floor are held to a stricter employer-type or mission-fit standard than jobs well above it — for example, "under $X, only nonprofits and government; above $X, anything goes." Ask if they want this. If yes, get the exact bands and rules; if no, skip it — a single flat floor is simpler and works fine.)
2. **Job titles / roles.** The exact titles or role families to search for (e.g. "Product Manager," "Product Lead," "Director of Product"). Ask whether to include adjacent seniority levels (Director, VP, Head of) and whether any of those title words are known to produce false positives in their field (for product roles, "Head of Product Marketing" is a marketing title that JobsPipe's substring search will incorrectly match on "Head of Product" — ask if their target titles have an equivalent trap, since if so this needs to be screened at the scoring step, not the search step).
3. **Location and work arrangement.** Ask separately about: remote (yes/no — almost always yes, since it costs nothing to include), onsite (which specific place or places are acceptable, and at what radius or named-area precision), and hybrid (same question). If multiple locations or arrangements have different acceptability, get the specifics for each rather than a single blended answer. Also ask whether they want to personally triage borderline location matches themselves (accept broadly and let them filter by eye on the dashboard) or whether they want the system to narrow automatically by keyword-matching city/area names in each listing's location field — JobsPipe's location filter is state/region-level only, with no radius or distance filter, so anything more precise than a whole state has to be done as a keyword check against the listing's location text after the fact.
4. **Curated employers.** A list of employers to weight higher in scoring — companies they already have a specific interest in.
5. **Excluded employers.** A list of employers to exclude outright, and ask whether there are any employer *categories* (an industry, business model, or type of company) they want excluded as a standing rule, not just specific named companies — since new companies in an excluded category will keep appearing over time and can't all be listed by name up front. If yes, this becomes a scoring-time text screen (see Step 3), not a name-based filter.
6. **Resume.** Get the resume itself — pasted text, an uploaded file, or a link. Confirm whether it needs any editing or updating before use, and ask them to flag when it later goes stale so scoring doesn't quietly run against an outdated version.
7. **Other working preferences or screens.** Ask directly: "Is there anything about a job posting that would make you skip it even if the salary, title, and location all matched?" This is where things like "not really interested in [X industry]," "avoid pure sales/growth roles," or "this kind of stated responsibility is a dealbreaker" surface. Each one becomes a standing scoring rule.
8. **Delivery.** Where should the digest go — email (get the address), the dashboard, or both? If email, confirm Gmail is connected in this Cowork account.
9. **Cadence.** How often should this run? A common pattern is a weekly digest (short lookback window, e.g. 7 days) plus a monthly "backfill" run with a longer lookback (e.g. 45 days) to catch older-but-still-open postings the weekly window would otherwise miss. Ask for a preferred day and time (and time zone) for each.
10. **The API key.** Get the JobsPipe API key. Tell them plainly it will never be shown back to them, written into the dashboard, or included in any digest or email — it is stored only in a local secret file that gets recreated at the start of each scheduled run (scheduled runs start from a completely empty environment each time, so nothing persists between them except what's explicitly rebuilt or stored in the artifact database).

If anything above still needs to be revisited later, that's fine and expected — the config lives in the dashboard's own database (see Step 2), so it can be edited at any time without touching the scheduled tasks' code.

## Step 2 — build the dashboard and its database

Use the Artifact tool to publish a single-file HTML page with a small live database attached (the `db` capability). This page is the dashboard: it shows the latest digest, lets the person flag postings as interested or not interested, and reads its data live rather than needing to be republished every time new results come in.

The database needs three collections:

- **`config`** — two documents: `resume` (the resume text, plus an `updated` date and a short `version_label` so staleness is visible at a glance) and `filters` (everything gathered in Step 1: salary rule, titles, location rule, curated employers, excluded employers, any category-level exclusion rules, any other scoring screens, and freeform notes explaining each one — future scoring runs read this document fresh every time, so it is the single source of truth for the person's criteria, not the fetch script).
- **`digests`** — one document per run, keyed by date, holding the full list of postings that run surfaced (title, company, url, salary range, location, work arrangement, fit tier, and a one-line rationale for each) plus summary counts.
- **`seen_jobs`** — one document per posting id, recording at minimum its fit tier and interested/not-interested status, so a posting already shown once is never shown again.

A template dashboard page (`templates/job_search_watcher_template.html`) is included in this repo — start from it rather than from scratch. It already implements: a latest-digest view grouped by fit tier, an "interested" aggregate view that pulls full posting details across all past digests, and interested/not-interested flag buttons on every card. Every posting card links back to the original listing, which JobsPipe's acceptable use policy requires when a posting is displayed. It has no employer names or personal criteria baked in — all of that lives in the database, not the page — so it can be published as-is and will pick up whatever goes into `config`.

Once published, note the artifact's URL — every scheduled task will need it to read and write the database.

## Step 3 — build the fetch-and-score logic

A template fetch script (`templates/jobspipe_fetch_template.py`) is included in this repo. It queries JobsPipe with the title list, salary floor, and location rule from Step 1, merges and de-duplicates results by JobsPipe's posting id, and writes them to a local file for scoring. Fill in its placeholders (`TITLES`, `MIN_SALARY_USD`, `CURATED_COMPANIES`, `EXCLUDED_COMPANIES`, and the location/region section) from the Step 1 answers before using it.

Two things belong in scoring (done by Claude reading the fetched postings and the resume, not in the fetch script itself), because they need judgment a static filter can't apply:

- **Title-substring false positives** (if any were identified in Step 1) — flag rather than present these as genuine matches.
- **Any category-level exclusion or other screen** from Step 1 (an industry, business model, or responsibility pattern to avoid) — read each posting's company and description text for it, and tier a match down (or exclude it, per the person's preference) with a rationale explaining why, rather than silently dropping it. Keeping a downgraded posting visible with an explanation, instead of hiding it outright, tends to be more useful — it lets the person catch a screening rule that's too aggressive.

Score every remaining posting Strong / Good / Moderate / Low against the resume, weighting curated employers higher, with a one-line rationale for each.

## Step 4 — set up the scheduled tasks

Create two scheduled tasks (in Cowork, these are called scheduled tasks — the underlying mechanism is sometimes referred to as a trigger, but that's internal terminology, not something the person needs to know). Each one's stored instructions need to be fully self-contained: **a scheduled task starts a brand-new, empty session every time it fires — nothing from a previous run, and nothing from the session that created it, carries over.** That means the full fetch script, the JobsPipe API key, and every step of the process must be written directly into the scheduled task's own prompt text, not left as "run the file from last time," because there is no "last time" from that session's point of view.

**Weekly digest** — cadence and time from Step 1. Its prompt should, in order: (1) recreate the API key file and set restrictive permissions on it; (2) recreate and run the fetch script with a short lookback (e.g. 7 days); (3) if a second alert source was set up (see the note below), check it too; (4) read `config/resume` and `config/filters` from the dashboard's database; (5) read `seen_jobs` and drop anything already surfaced; (6) score survivors, applying every rule from `config/filters`; (7) write a new `digests` document and batch-write the newly-seen postings into `seen_jobs`; (8) deliver the digest per the Step 1 delivery preference; (9) flag it if JobsPipe's monthly credit usage looks close to its limit.

**Monthly backfill** — same shape, but with a longer lookback (e.g. 45 days) to catch older listings the weekly window missed, and it should skip sending anything if there's nothing new that run.

## A note on a second alert source

If the person already gets, or sets up, an email-based job alert from some other site (a saved search that emails new listings), that can be folded in without building a scraper for that site: each scheduled run searches Gmail for messages from that sender within its lookback window, reads the body, extracts each listing (title, company, link, and salary/location when stated), and merges them into the candidate pool with a synthetic id (a short hash of the listing's link) so they're tracked in `seen_jobs` the same way. Since the other site's own saved search already applied its filters, these candidates skip JobsPipe's title/salary/region filters — but if a listing doesn't state salary or location, it shouldn't be scored above Moderate, since neither of the hard requirements can actually be verified from it. This is meaningfully cheaper to build than scraping a site directly, and worth doing only if that site actually has real, relevant inventory for the search — check that first rather than assuming.

## Operational notes worth knowing going in

- JobsPipe's posting id is not always consistent across cross-posted sources — the same listing can appear twice under two different ids. There's no fully reliable fix; just note likely duplicates when company, title, and salary all match.
- JobsPipe's `work_arrangement` tag (remote/onsite/hybrid) is not always accurate — spot-check the description text against the tag when it materially affects whether a posting is acceptable.
- JobsPipe has a `max_ghost_score` filter (0–100, a likelihood-of-being-expired-or-fake score) — setting it around 50 cuts down on stale listings without being so aggressive it drops real ones, since unscored postings always pass through regardless of the threshold.
- Everything in `config/filters` and `config/resume` can be edited at any time by writing to the database directly — none of it requires touching or republishing the fetch script or the scheduled tasks, except the scoring step's own reasoning, which reads `config/filters` fresh every run.
