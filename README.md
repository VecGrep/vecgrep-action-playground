# VecGrep Action Playground

A test repository for the [VecGrep GitHub Action](https://github.com/VecGrep/action).
Contains a realistic Python application and workflows that exercise every action mode.

## Application structure

```
src/
  auth/
    authentication.py   — password hashing, token generation, session management
    middleware.py       — auth middleware, rate limiting
  database/
    connection.py       — connection pool, parameterized query helpers
    repository.py       — user and order data access layer
  payments/
    processor.py        — payment intent, charge, refund
    invoice.py          — invoice creation and lifecycle
  api/
    routes.py           — HTTP route handlers wired to domain logic
```

`processor.py` and `invoice.py` are intentionally structurally similar
to validate that the `duplicate` mode detects them.

## Workflows

| Workflow | Mode tested | What it verifies |
|---|---|---|
| `test-index.yml` | `index` | Codebase is indexed; stats are reported |
| `test-search.yml` | `search` | Auth, payment, and DB code is found semantically |
| `test-validate.yml` | `validate` | No raw SQL, no hardcoded credentials; auth + payment logic exists |
| `test-comment.yml` | `comment` | Related code is posted as a PR comment |
| `test-duplicate.yml` | `duplicate` | Intentional duplicates detected; near-identical code blocks the build |

## Using VecGrep Action in your project

```yaml
- uses: VecGrep/action@v0.1.0
  with:
    mode: validate
    query: "raw SQL string concatenation"
    min_score: "0.80"
    fail_on_match: "true"
```

See the [VecGrep Action README](https://github.com/VecGrep/action#readme) for full documentation.
