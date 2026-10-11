.PHONY: dev prod down logs

dev:
	./run-dev.sh

prod:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f