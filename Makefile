.PHONY: build
build:
	docker-compose build --no-cache

.PHONY: run
run: build
	docker-compose up -d

.PHONY: stop
stop:
	docker-compose down -v

.PHONY: format
format:
	ktlint --format