.PHONY: up down db db-stop test coverage

export DATABASE_URL=postgresql://bank:bank@localhost:5433/testdb

up:
	docker compose up --build

down:
	docker compose down -v

db:
	docker compose -p intro-to-coverage-testdb -f docker-compose.db.yml up -d --wait

db-stop:
	docker compose -p intro-to-coverage-testdb -f docker-compose.db.yml down -v

test: db
	pytest

