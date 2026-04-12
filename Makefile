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