# Contributing

Small, focused improvements are welcome through pull requests.

## Development workflow

1. Create a branch from `main`.
2. Install Python and Node dependencies using the commands in the README.
3. Keep local demo mode explicit; do not claim AWS behavior from mock results.
4. Add or update tests for behavior changes.
5. Run the checks below before opening a pull request.

```bash
pytest
ruff check backend evals
cfn-lint infra/template.yaml
bash -n scripts/*.sh
npm run web:test
npm run web:build
npm run web:e2e
```

Never commit credentials, generated AWS outputs, real customer data, or local
agent configuration. Infrastructure changes must preserve exact-target teardown
and clearly distinguish implemented resources from currently deployed ones.

## Pull requests

Describe the user-visible change, verification performed, AWS cost or security
impact, and any remaining limitations. Keep unrelated formatting or dependency
changes separate so the complete diff remains reviewable.
