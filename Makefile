.PHONY: install test demo dashboard kafka docker-build docker-test docker-validate real-validate compileall

install:
	python -m pip install -e .

test:
	./scripts/run_tests.sh

compileall:
	python -m compileall -q spl_v7 experiments scripts

demo:
	./scripts/run_demo.sh

dashboard:
	./scripts/run_dashboard.sh

kafka:
	./scripts/run_kafka.sh

docker-build:
	docker build -t spl-v7:local .

docker-test:
	@echo "NOTE: Tests are not included in the Docker image (pytest not installed, tests/ not copied)."
	@echo "Run tests natively instead:  make test"
	@echo "Or install with dev extras:   pip install \".[dev]\" && python -m pytest tests/ -v"
	@exit 1

docker-compileall:
	docker run --rm spl-v7:local python -m compileall -q spl_v7 experiments scripts

docker-validate:
	docker run --rm -v "$(PWD)/reports:/app/reports" spl-v7:local python scripts/run_local_tls_validation.py datasets/real_tls_seed_domains.txt

real-validate:
	python scripts/run_local_tls_validation.py datasets/real_tls_seed_domains.txt
