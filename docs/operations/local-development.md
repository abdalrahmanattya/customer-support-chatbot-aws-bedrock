# Local development

## Prerequisites

- Python 3.12 or newer
- Node.js 24.15 or newer (use `nvm use` with the included `.nvmrc`)
- AWS CLI v2 only for read-only checks or an explicitly approved deployment

## Setup and checks

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
ruff check backend evals
cfn-lint infra/*.yaml
./scripts/run-eval.sh --mock
npm install
npm run web:build
npm run web:test
npm run web:e2e
```

Run `npm run web:dev` for the browser application, or run
`python -m support_service.cli --mock` for the terminal client.

Generated evaluation JSONL is written to ignored `evals/results/`. AWS
credentials are obtained through an ignored local helper and remain in the
calling shell environment.
