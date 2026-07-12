# csnpk Report Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete, searchable `/nav/` index for all published non-daily investment research reports and make nav registration part of the publishing contract.

**Architecture:** `nav/reports.json` is the explicit source of truth. `nav/index.html` fetches, validates, filters, groups, and renders that manifest. A dependency-free validation script checks schema, uniqueness, category values, dates, local targets, and exclusion rules before deployment.

**Tech Stack:** Static HTML/CSS/JavaScript, JSON, Python 3 standard library, Cloudflare Workers static assets.

## Global Constraints

- Include only publicly published topic, industry, and company analysis reports.
- Exclude `CSN`, `csn2`, A-share flow, U.S. sector flow, tools, and non-research pages.
- Allowed categories are exactly `行业研究`, `主题策略`, and `公司研究`.
- Preserve every existing public report path.
- Verify public URLs with cache-busting query parameters after deployment.

---

### Task 1: Manifest and validation contract

**Files:**
- Create: `nav/reports.json`
- Create: `scripts/validate_report_nav.py`

**Interfaces:**
- Consumes: report directories in the repository root.
- Produces: a JSON array with `id`, `date`, `title`, `url`, `category`, and `tags`; validator exit code `0` for a valid manifest and `1` for violations.

- [ ] **Step 1: Write the manifest validator**

Create `scripts/validate_report_nav.py` with Python standard-library checks for: required fields, `YYYY-MM-DD`, allowed categories, non-empty tag arrays, duplicate IDs, duplicate URLs, forbidden URL prefixes, and local `index.html` existence. Resolve URLs relative to `nav/`, so `../cxl/` maps to `<repo>/cxl/index.html`.

Use these constants:

```python
REQUIRED = {"id", "date", "title", "url", "category", "tags"}
ALLOWED_CATEGORIES = {"行业研究", "主题策略", "公司研究"}
FORBIDDEN_PREFIXES = (
    "../csn/", "../csn2/", "../a-share-flow/",
    "../us-sector-flow/", "../skill-packages/", "../summer-classics/",
)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
```

The script prints one `ERROR: ...` line per violation and ends with `OK: <n> report entries validated` on success.

- [ ] **Step 2: Run the validator before the manifest exists**

Run: `python3 scripts/validate_report_nav.py`

Expected: exit code `1` and `ERROR: nav/reports.json does not exist`.

- [ ] **Step 3: Create the initial report manifest**

Add 11 records, sorted newest first:

```text
ai-compute-gw             2026-07-12  主题策略  ../ai-compute-gw/
commercial-space-2026     2026-07-12  行业研究  ../commercial-space-2026/
helium-2026               2026-07-12  行业研究  ../helium-2026/
innovative-drugs-2026     2026-07-11  行业研究  ../innovative-drugs-2026/
ai-entry                  2026-07-10  主题策略  ../ai-entry/
ai-commercialization-csp  2026-07-08  主题策略  ../ai-commercialization-csp/
tencent-0700              2026-07-08  公司研究  ../stock-reports/tencent-0700/
alibaba-9988              2026-07-08  公司研究  ../stock-reports/alibaba-9988/
robotics                  2026-07-03  行业研究  ../robotics/
ymb                       2026-06-26  行业研究  ../ymb/
cxl                       2026-06-25  行业研究  ../cxl/
```

Titles must match each public page's reader-facing subject. Tags should remain short and specific; each entry needs 4-7 tags.

- [ ] **Step 4: Run validation**

Run: `python3 scripts/validate_report_nav.py`

Expected: `OK: 11 report entries validated`.

- [ ] **Step 5: Commit**

```bash
git add nav/reports.json scripts/validate_report_nav.py
git commit -m "feat: add report navigation manifest"
```

### Task 2: Searchable grouped navigation page

**Files:**
- Modify: `nav/index.html`

**Interfaces:**
- Consumes: `fetch("reports.json", {cache: "no-store"})` returning the Task 1 array.
- Produces: filter buttons, grouped report cards, visible result count, and a readable load-error state.

- [ ] **Step 1: Add static contract checks**

Before editing, run these commands and confirm the old embedded list is detected:

```bash
rg 'const entries = \[' nav/index.html
rg '表姐严选资料清单' nav/index.html
```

Expected: both commands return matches.

- [ ] **Step 2: Replace the embedded-list page**

Update the title and heading to `CSN 投研报告导航`. Add category buttons with `data-category` values `全部`, `行业研究`, `主题策略`, and `公司研究`. Keep the search input and mobile breakpoint.

The script must:

```javascript
const CATEGORY_ORDER = ["主题策略", "行业研究", "公司研究"];
let entries = [];
let activeCategory = "全部";

async function loadReports() {
  const response = await fetch("reports.json", { cache: "no-store" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  entries = await response.json();
  entries.sort((a, b) => b.date.localeCompare(a.date));
  render();
}
```

`render()` filters on title, category, and tags; then emits one section per non-empty category in `CATEGORY_ORDER`. Error handling displays `报告清单加载失败，请稍后刷新。` and sets the visible count to `0`.

- [ ] **Step 3: Verify static contract changed**

Run:

```bash
! rg 'const entries = \[' nav/index.html
rg 'fetch\("reports.json"' nav/index.html
rg 'CSN 投研报告导航' nav/index.html
```

Expected: all three shell checks succeed.

- [ ] **Step 4: Run local browser-independent validation**

Run: `python3 scripts/validate_report_nav.py`

Expected: `OK: 11 report entries validated`.

Serve with `python3 -m http.server 8765`, then request:

```bash
curl -fsS http://127.0.0.1:8765/nav/
curl -fsS http://127.0.0.1:8765/nav/reports.json
```

Expected: both requests succeed; JSON contains 11 entries.

- [ ] **Step 5: Commit**

```bash
git add nav/index.html
git commit -m "feat: group all research reports in nav"
```

### Task 3: Durable project publishing rules

**Files:**
- Create: `AGENTS.md`
- Create: `docs/report-nav-policy.md`
- Create outside repository by explicit user request: `/Users/lingliang/.codex/memories/extensions/ad_hoc/notes/2026-07-12-csnpk-report-nav-rule.md`

**Interfaces:**
- Consumes: the manifest and validator from Task 1.
- Produces: instructions future publishing tasks can follow without reconstructing this decision.

- [ ] **Step 1: Add the short project rule**

Create `AGENTS.md` with a `csnpk 分析报告导航` section stating that publishing a non-daily topic, industry, or company report requires updating `nav/reports.json`, running the validator, and verifying both the report URL and `/nav/` publicly. Explicitly list daily pages and dynamic flow pages as excluded.

- [ ] **Step 2: Add the detailed maintenance policy**

Create `docs/report-nav-policy.md` documenting field definitions, allowed categories, exclusions, the exact validator command, cache-busting acceptance checks, and deletion/path-change handling.

- [ ] **Step 3: Add the memory routing note**

Create the timestamped ad-hoc note requested by the user. It should point to the repository `AGENTS.md`, `docs/report-nav-policy.md`, and `nav/reports.json`; it must not duplicate the entire manifest.

- [ ] **Step 4: Validate policy references**

Run:

```bash
rg 'nav/reports.json' AGENTS.md docs/report-nav-policy.md
rg '每日|动态' AGENTS.md docs/report-nav-policy.md
python3 scripts/validate_report_nav.py
```

Expected: policy references are found and manifest validation reports 11 entries.

- [ ] **Step 5: Commit repository rules**

```bash
git add AGENTS.md docs/report-nav-policy.md
git commit -m "docs: require nav registration for research reports"
```

### Task 4: Deployment and public acceptance

**Files:**
- No new source files.

**Interfaces:**
- Consumes: committed repository state from Tasks 1-3 and the existing Cloudflare deployment workflow.
- Produces: publicly readable `/nav/`, `/nav/reports.json`, and 11 working report URLs.

- [ ] **Step 1: Run the full local gate**

Run:

```bash
python3 scripts/validate_report_nav.py
git status --short
```

Expected: validator reports 11 entries; only the intentionally untracked memory note exists outside the repository; repository status is clean.

- [ ] **Step 2: Push the publishing branch**

Run: `git push origin cloudflare/workers-autoconfig`

Expected: remote accepts the new commits. If the branch is behind, fetch and integrate without discarding unrelated remote changes, rerun validation, and push again.

- [ ] **Step 3: Verify public nav assets with cache busting**

Use a timestamp value `<ts>` and request:

```text
https://csnpk.com/nav/?v=<ts>
https://csnpk.com/nav/reports.json?v=<ts>
```

Expected: HTTP 200; page title is `CSN 投研报告导航`; JSON parses to 11 entries.

- [ ] **Step 4: Verify every public report target**

Resolve all 11 `url` values against `https://csnpk.com/nav/` and request them with `?v=<ts>`.

Expected: every URL returns HTTP 200. Any non-200 response blocks completion.

- [ ] **Step 5: Confirm exclusions and counts**

Confirm the public JSON contains none of `csn`, `csn2`, `a-share-flow`, or `us-sector-flow`, and that the public entry count is 11.

- [ ] **Step 6: Record final deployment commit**

Run: `git log -1 --oneline`

Expected: final commit hash is included in the user handoff alongside the public nav URL.
