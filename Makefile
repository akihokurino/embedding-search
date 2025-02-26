run:
	docker-compose up

run-with-build:
	docker-compose up --build

seed:
	poetry run python -m insert_local_pdf
	poetry run python -m insert_dummy_data

types:
	poetry run mypy .

console_postgres:
	docker exec -it postgres-db psql -U postgres -d sample

migrate:
	poetry run alembic upgrade head

reset-migrate:
	poetry run alembic downgrade base && alembic upgrade head

check-migration:
	poetry run alembic check