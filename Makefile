.PHONY: reviewer-demo verify benchmark-smoke audit public-boundary test lint typecheck

test:
	uv run pytest -q

lint:
	uv run ruff check .

typecheck:
	uv run mypy

reviewer-demo:
	uv run python -c "from datetime import UTC, datetime; from pathlib import Path; from forge_qsparx.reviewer import build_reviewer_site; result = build_reviewer_site(Path('site'), seed=577, generated_at=datetime(2026, 7, 21, tzinfo=UTC)); print(result.bundle_digest)"

verify: test
	uv run forge-qsparx verify --runs 3 --seed 577

benchmark-smoke:
	uv run forge-qsparx benchmark --repetitions 3 --seed 577

public-boundary:
	uv run python scripts/check_public_boundary.py

audit: lint typecheck test public-boundary
	uv pip check
	uv run pip-audit
