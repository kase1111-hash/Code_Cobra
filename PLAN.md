# Code Cobra Refocus Plan

Based on the Concept-Execution Evaluation, this plan strips peripheral infrastructure and redirects effort toward the core multi-model pipeline and guide-driven workflow.

---

## Phase 1: Fix What's Broken (Immediate)

### 1.1 Fix broken test — `tests/test_core.py:110`

The audit fix moved `max_tokens` into `options.num_predict`, but the test still asserts `result["max_tokens"]`. This test has been failing since the audit and CI is broken.

**Change:**
```python
# tests/test_core.py line 110
# FROM:
self.assertEqual(result["max_tokens"], 1000)
# TO:
self.assertEqual(result["options"]["num_predict"], 1000)
```

### 1.2 Verify all tests pass after fix

Run `python -m unittest discover -s tests/ -v` and confirm 18/18 pass in test_core.py.

---

## Phase 2: Remove Over-Engineered Infrastructure

These modules total ~1,100 lines of observability code for a batch CLI tool. The main application already has graceful fallbacks (try/except with no-op replacements) so removal is safe.

### 2.1 Delete `monitoring.py` (452 lines)

- Not imported by any file (not even autonomous_ensemble.py)
- No tests reference it
- Provides: health checks, background sampling threads, uptime monitoring, memory alerts
- None of this applies to a run-and-exit CLI tool

### 2.2 Simplify `telemetry.py` → inline basic timing

- Currently 335 lines with Prometheus export, histogram percentiles, workflow tracking
- Used in autonomous_ensemble.py behind `if collector and TELEMETRY_AVAILABLE:` guards at 5 call sites
- **Replace with:** Remove the external module. Replace the try/except import block in autonomous_ensemble.py with simple inline timing using `time.perf_counter()` and print statements in verbose mode. The existing verbose print statements (`[Model A] Generating creative draft...`, etc.) already cover this use case.

### 2.3 Simplify `logging_config.py` → use stdlib logging

- Currently 307 lines with JSON formatter, ELK-compatible structured logging, CodeCobraLogger class
- Used in autonomous_ensemble.py only via `get_logger(__name__)` fallback
- **Replace with:** Remove the external module. The existing fallback in autonomous_ensemble.py already sets up `logging.basicConfig(level=logging.INFO)` and defines `get_logger()` as `logging.getLogger(name)`. This is sufficient.

### 2.4 Update `pyproject.toml` line 67

Remove deleted modules from the package manifest:
```toml
# FROM:
py-modules = ["autonomous_ensemble", "monitoring", "logging_config", "telemetry"]
# TO:
py-modules = ["autonomous_ensemble"]
```

### 2.5 Simplify `autonomous_ensemble.py` import block

Replace the try/except import block (lines 25-46) with direct stdlib usage:
```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

Remove all `if collector and TELEMETRY_AVAILABLE:` guard blocks (lines 604-605, 647-648, 652-653, 667-668) and the `workflow_id`/`collector` initialization. The verbose mode print statements already provide user-facing progress feedback.

---

## Phase 3: Remove Deployment Scaffolding

### 3.1 Delete `scripts/deploy.sh` (~200 lines)

Docker build with environment-based deployment orchestration. Code Cobra has no server component — users run a CLI command, get a file. The Dockerfile and docker-compose.yml already handle containerized usage.

### 3.2 Delete `scripts/rollback.sh` (~200 lines)

Git-tag and Docker-image rollback mechanism. Same reasoning — no deployment target means no rollback target.

### 3.3 Keep `scripts/backdoor_check.py`

This is referenced by deploy.sh (which is being deleted) but it's a genuinely useful standalone security tool for scanning generated output. Move the reference from deploy.sh context into the README as a manual security step.

### 3.4 Keep `scripts/setup.sh`

Still needed for environment setup.

---

## Phase 4: Trim Documentation to Essentials

### Keep (user-facing, actively useful):
- `README.md` — Project overview, quick start, technical spec
- `CONTRIBUTING.md` — Development guidelines
- `SECURITY.md` — Security policy
- `CHANGELOG.md` — Release notes
- `docs/API.md` — API reference
- `docs/ARCHITECTURE.md` — System architecture
- `docs/FAQ.md` — Troubleshooting and common questions

### Delete (process artifacts, not user-facing):
- `IMPLEMENTATION_GUIDE.md` — All phases marked complete. Historical artifact. Not referenced anywhere.
- `Keywords.md` — SEO keyword list. Not referenced anywhere.
- `Step-by-step.md` — Duplicate of IMPLEMENTATION_GUIDE. Not referenced anywhere.
- `docs/USER_STORIES.md` — Referenced only in a comment in test_acceptance.py. Remove the comment.

### Keep but stop maintaining:
- `SUPPORT.md` — Links to other docs, low maintenance burden
- `docs/SECURITY.md` — Security details, low maintenance burden
- `AUDIT_REPORT.md` — Historical record of the audit. Worth keeping as-is.

### Update after deletions:
- `CONTRIBUTING.md` — Remove references to deleted files from project structure
- `CHANGELOG.md` — No changes needed (historical record)
- `SUPPORT.md` — Verify all doc links still work

---

## Phase 5: Strengthen the Core

### 5.1 Add guide templates for common tasks

Create 2-3 short, focused example guides in a `guides/` directory:
- `guides/rest_api_guide.txt` — 10-step guide for building REST APIs
- `guides/cli_tool_guide.txt` — 10-step guide for building CLI tools

These make the tool immediately usable for the most common use cases without users having to write guides from scratch.

### 5.2 Improve dry-run output

Currently dry-run just lists steps. Enhance to also validate:
- Step numbering is sequential (warn on gaps)
- Step descriptions aren't empty
- Guide file size is reasonable (warn if >50 steps)

This is a small change in `WorkflowEngine.dry_run()` that makes the tool more helpful.

---

## Summary of Changes

| Action | Files | Lines Removed | Lines Added |
|--------|-------|---------------|-------------|
| Fix broken test | tests/test_core.py | 1 | 1 |
| Delete monitoring.py | monitoring.py | ~452 | 0 |
| Delete telemetry.py | telemetry.py | ~335 | 0 |
| Delete logging_config.py | logging_config.py | ~307 | 0 |
| Simplify autonomous_ensemble.py | autonomous_ensemble.py | ~25 | ~5 |
| Update pyproject.toml | pyproject.toml | 1 | 1 |
| Delete deploy.sh | scripts/deploy.sh | ~200 | 0 |
| Delete rollback.sh | scripts/rollback.sh | ~200 | 0 |
| Delete process docs | 4 files | ~700 | 0 |
| Update remaining docs | CONTRIBUTING.md, SUPPORT.md | ~15 | ~5 |
| Add guide templates | 2 new files | 0 | ~60 |
| Improve dry-run | autonomous_ensemble.py | 0 | ~15 |

**Net effect:** ~2,200 lines removed, ~85 lines added. The project shrinks from ~17,000 lines to ~14,800 lines while the core application (autonomous_ensemble.py) stays almost unchanged.

---

## Execution Order

1. Phase 1 first (fix broken test — unblocks CI)
2. Phase 2 next (remove infra modules — biggest cleanup)
3. Phase 3 (remove deploy scripts)
4. Phase 4 (trim docs)
5. Phase 5 last (add guides and improve dry-run — new value)

Each phase is a single commit with a clear scope.
