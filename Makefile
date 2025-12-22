.PHONY: build
build:
	docker build \
		--file docker/oda.Dockerfile \
		--build-arg BAK_URL="https://oda.ft.dk/odapublish/oda.bak" \
		--build-arg BAK_USER="ODAwebpublish" \
		--build-arg BAK_PASS="b56ff26a-c19b-4322-a3c4-614de155781d" \
		-t oda-restored .

.PHONY: run
run: build
	docker run -d \
		-e SA_PASSWORD="DefaultStrong!Passw0rd" \
		-p 1433:1433 \
		--name oda-restored \
		oda-restored

.PHONY: format
format:
	ktlint --format