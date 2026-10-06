# GridironIQ

Rule-grounded penalty determination for football officiating review.

Submit a structured play description; the system parses it into machine-checkable facts,
evaluates those facts against a rule library, and returns a determination **with the rule
citation that produced it**.

The determination comes from a deterministic rule engine, not from a language model. The
same description always yields the same call, and every call carries a citation. A language
model sits at the periphery in an advisory role only — if it is unreachable or unconfigured,
the system still returns a complete, citable answer.

---

## Quick start

```bash
pip install -r requirements.txt
python run.py
# open http://127.0.0.1:8000
```

Optional advisory notes:

```bash
export ANTHROPIC_API_KEY=...   # omit and everything else works identically
```

## Architecture

Four layers. Dependencies point one direction only, enforced by a rule checkable with a
text search: **no service module imports FastAPI, and no API module issues an ORM query.**

| Layer | Modules | Responsibility |
|---|---|---|
| Presentation | `app/main.py` (embedded template) | Reviewer interface |
| API | `app/api/routes.py`, `schemas.py`, `dependencies.py` | Validate, delegate, shape responses |
| Service | `play_parser`, `rule_engine`, `rule_library`, `advisor`, `analysis_service` | All business logic |
| Data | `app/data/models.py`, `repositories.py`, `db.py` | Persistence |

```
POST /api/plays
   -> PlaySubmission schema (validation)
   -> AnalysisService.analyze()
        -> play_parser.parse()      -> PlayFacts
        -> RuleEngine.evaluate()    -> PenaltyDecision   [decision is complete here]
        -> PenaltyAdvisor.review()  -> optional note     [failure degrades to ""]
        -> CallRepository.save()    -> call_id
   -> AnalysisOut
```

## Core features

1. **Play analysis** — `POST /api/plays`
2. **Rule citation and search** — `GET /api/rules`, `GET /api/rules/{code}`
3. **Call history and audit log** — `GET /api/history`, `GET /api/history/{id}`

Interactive API docs at `/docs` once running.

## Testing

```bash
pip install -r requirements-dev.txt
pytest --cov=app --cov-report=term-missing
ruff check .
```

| Tier | Tests | Dependencies |
|---|---|---|
| Unit | 27 | none |
| Integration | 17 | temp SQLite, fake advisor |
| System | 6 | temp SQLite, fake advisor |
| **Total** | **50** | ~1.1s, 95% coverage |

The only nondeterministic dependency is isolated behind the `PenaltyAdvisor` protocol.
Every test substitutes `FakePenaltyAdvisor`, so the suite needs no network and is
reproducible on any machine.

The 21 uncovered statements are the live HTTP path in `ClaudeAdvisor` and the production
wiring in `dependencies.py` — both uncovered by design. Covering them would mean either
reintroducing nondeterminism or asserting that a mock behaves as configured.

## Adding a rule

Append a `Rule` to `RULES` in `app/services/rule_library.py`. The engine needs no change.

```python
Rule(
    code="XYZ", name="...", citation="Rule N, Section N, Article N",
    summary="...", yards=10, automatic_first_down=False,
    penalized_side="offense", predicate=lambda f: f.some_fact,
    rationale="...", priority=45,
)
```

Add unit tests covering both the firing and non-firing conditions.

## Project layout

```
app/
  api/          routers, pydantic schemas, dependency wiring
  services/     parser, rule engine, rule library, advisor seam, orchestration
  data/         ORM models, repositories, session factory
tests/
  unit/         parser and engine in isolation
  integration/  routes through the ORM to a real database
  system/       known play scenarios, full stack
docs/uml/       use case, class, sequence, deployment diagrams (Mermaid)
```

## Scope boundaries

Deliberately out of scope: video ingestion, live game feeds, multi-user accounts,
exhaustive rule coverage. Eight rules span the pre-snap, passing, contact, and blocking
categories; the library is designed for extension.
