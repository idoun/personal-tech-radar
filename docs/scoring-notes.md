# Personal Tech Radar Scoring Notes

## Why this document exists

This note captures two things:

1. what is currently reflected in the scoring system
2. what improvements were discussed but intentionally deferred for later review

The goal is to preserve the current thinking without overcommitting to additional scoring complexity before confidence is higher.

## Current reflected scoring method

Relevant files:

- `backend/app/core/scoring.py`
- `backend/app/core/profile.py`
- `config/tech-radar-profile.yaml`

In production, a private deployment can override the checked-in sample by setting `TECH_RADAR_PROFILE_PATH` to a file outside the repository.

### 1. Final score structure

The final score is a weighted sum of six components.

- `interest_score`: `30%`
- `project_score`: `25%`
- `novelty_score`: `15%`
- `actionability_score`: `15%`
- `credibility_score`: `10%`
- `community_score`: `5%`

The implementation currently uses `compute_final_score()` in `backend/app/core/scoring.py`.

### 2. Input text used for scoring

The scorer combines multiple text surfaces instead of relying on title only.

- issue title
- `short_summary`
- `impact_summary`
- `action_items`
- tags
- `radar_category`
- `radar_status`
- parsed markdown body text

This makes project/interest matching less brittle than title-only scoring.

### 3. Interest score

Interest matching is based on the configured interest list in the Tech Radar profile.

- matching is not strict exact-match only
- multi-token phrases can still receive partial credit
- `interest_score` starts from a non-trivial base and increases with cumulative interest hits

Current formula:

- base: `3.8`
- additional gain: `min(interest_hits, 6.0) * 0.9`

### 4. Project score

Project score is currently the most customized part of the scoring logic.

Each configured project contributes a match total based on:

- project keywords
- project name
- project description

The scorer then:

1. ranks all projects by match total
2. uses the best-matching project as the main signal
3. weakly incorporates the second-best project
4. applies a small bonus when multiple projects meaningfully match

Current project score logic:

- base: `3.6`
- `project_signal = best_project_hits + second_project_hits * 0.35 + multi_project_bonus`
- `project_score = 3.6 + min(project_signal, 6.0) * 0.95`

This is intentionally more forgiving than the earlier “single exact project only” behavior.

### 5. Keyword matching behavior

Keyword matching is currently heuristic, not semantic embedding-based.

Rules in `backend/app/core/scoring.py`:

- full normalized phrase match: `1.0`
- all tokens present but phrase not exact: `0.75`
- at least half of tokens present for phrases with 2+ tokens: `0.4`
- otherwise: `0.0`

This means the current system can reward:

- exact phrase matches
- reordered or slightly varied multi-token wording
- partially overlapping technical phrasing

But it still does **not** understand meaning in a truly semantic sense.

### 6. Recent project profile keyword expansion

The project profile was recently broadened to better catch real article phrasing.

#### Workflow Automation Platform

Added examples:

- `multi-agent orchestration`
- `workflow engine`
- `execution graph`
- `task graph`
- `tool routing`
- `agent runtime`
- `agent platform`
- `control plane`
- `planning and execution`

#### Observability and Replay Toolkit

Added examples:

- `llm observability`
- `prompt tracing`
- `execution trace`
- `session replay`
- `tool trace`
- `telemetry`
- `debugging`
- `provenance`

#### Self-hosted Model Serving Stack

Added examples:

- `self-hosted llm`
- `private llm`
- `model serving`
- `local inference`
- `inference engine`
- `gpu serving`
- `quantization`
- `tensor parallel`

#### Technical Content Feed

Added examples:

- `news digest`
- `personalized feed`
- `feed ranking`
- `tech curation`
- `summarization pipeline`
- `content recommendation`
- `telegram delivery`

### 7. Current confidence level

What can be said with reasonable confidence:

- the system is less brittle than the earlier substring-only style
- broader project phrasing is now more likely to be captured
- scoring behavior improved on targeted sample cases

What cannot yet be claimed confidently:

- that the new rules reduce false positives overall
- that the new profile is globally better across recent production issues
- that project-score increases always correspond to human-perceived relevance gains

In short:

- the direction looks better
- the proof is still incomplete

## Verification already done

Recent verification completed during implementation:

- backend tests for profile/scoring logic passed in the backend virtualenv
- a targeted sample case for self-hosted LLM serving matched `Self-hosted Model Serving Stack`
- that sample produced a strong `project_score`, confirming the expanded keywords are active

This is useful evidence, but still closer to regression coverage than full evaluation.

## Deferred ideas discussed

These were discussed as promising next steps, but intentionally **not** implemented yet.

### A. Expose matched keywords in score output

Idea:

- show which keywords or phrases caused a project/interest match
- include them in API output and optionally the UI

Why it helps:

- humans can quickly inspect whether a score increase is legitimate
- makes the system far easier to debug
- improves trust without changing the score formula itself

### B. Build a recent-article evaluation script

Idea:

- collect a recent set of issues
- compute old/new scoring side by side
- produce a comparison table or report

Why it helps:

- surfaces distribution shifts
- makes it easier to identify overfitting
- gives concrete before/after evidence instead of intuition

### C. Create a small golden set

Idea:

- manually label `30-50` recent issues
- annotate which project each issue should map to, and how strongly
- compare the scorer against that reference set

Why it helps:

- highest-confidence way to evaluate future tuning
- converts subjective scoring debates into something inspectable

### D. Add guardrails against inflated project scores

Idea:

- cap score growth when only broad keywords are matched
- require at least one stronger signal before allowing very high project scores

Why it helps:

- reduces risk of over-rewarding generic infrastructure phrasing
- makes “high project relevance” harder to trigger accidentally

### E. Project-specific weighting or negative keywords

Idea:

- allow some keywords to count more than others
- optionally allow “negative” phrases that should suppress overmatching

Why it helps:

- could improve precision for ambiguous domains
- may be useful if project profiles become much larger

Why it is deferred:

- adds tuning complexity quickly
- easy to overfit without a reliable evaluation set

## Recommended next step when revisiting this

When scoring work resumes, the best order is likely:

1. expose matched keywords
2. add a recent-issue comparison script
3. only then consider heavier scoring-rule changes

This order is recommended because it improves observability before adding more heuristics.

## Current stance

For now, the scoring system should be treated as:

- improved
- more expressive
- still heuristic
- not yet fully validated

That is a healthy place to pause until there is time to evaluate it more rigorously.
