.PHONY: build
build:
	docker-compose build

.PHONY: run
run: build
	docker-compose up -d

.PHONY: stop
stop:
	docker-compose down -v

.PHONY: format
format:
	ktlint --format

.PHONY: test-vector
test-vector:
	bash scripts/test-vector.sh