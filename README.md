# Intro to Coverage

## Assignment

You are given a Flask banking service with a test suite that is **incomplete** — some tests have been removed. Your job is to find which parts of the code are not covered and write the missing tests until you reach **100% test coverage**.

## Goal

The CI pipeline measures coverage on every push. When your coverage reaches 100%, the GitHub Actions summary will show:

> ✅ Coverage: 100% — All tests written. Assignment complete!

Until then, it shows which percentage you're at and you need to keep going.

## How to find missing tests

Run the coverage report locally:

```bash
make db       # start the test database (first time only)
make coverage # run tests and show coverage report
```

The report will show you exactly which lines are not covered:

```
Name                              Stmts   Miss  Cover   Missing
app/services/account_service.py     110     12    89%   45-48, 67, 82-90
```

The `Missing` column tells you the line numbers that no test exercises. Open that file, read the code at those lines, and write a test that triggers that code path.

## Workflow

1. Run `make coverage` — read the report
2. Open the file listed under `Missing`
3. Understand what that code does (what conditions lead to it)
4. Write a test in the corresponding `tests/test_<module>.py` file
5. Run `make coverage` again — verify the number went up
6. Repeat until coverage is 100%
7. Push to GitHub — check the Actions tab for the result

## Project structure

```
app/
  models.py          — database models (User, Account, Transaction, Card, Loan)
  exceptions.py      — custom exceptions
  utils.py           — pure utility functions
  services/          — business logic
  routes/            — HTTP endpoints (Flask Blueprints)
tests/
  conftest.py        — shared pytest fixtures
  test_*.py          — test files (some tests are missing here)
```

## Running the service

```bash
make up      # start the app on http://localhost:8080
make down    # stop
```

## Running tests

```bash
make db        # start test database (keep it running)
make test      # run tests
make db-stop   # stop test database when done
```

## Tips

- Each service file has a corresponding test file: `services/user_service.py` → `tests/test_users.py`
- Look at existing tests to understand the pattern before writing new ones
- A "missing" line is often an error case — think about what bad input would trigger it
- `pytest -k test_name` runs a single test so you can iterate quickly
