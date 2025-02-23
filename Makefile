run-db:
	docker-compose up

run-api:
	poetry run python -m api

seed:
	poetry run python -m seed

types:
	poetry run mypy .

console_postgres:
	docker exec -it postgres-db psql -U postgres -d sample

migrate:
	poetry run alembic upgrade head

reset-migrate:
	poetry run alembic downgrade base && alembic upgrade head

clean:
	docker-compose down
	docker-compose rm