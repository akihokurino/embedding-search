run-db:
	docker-compose up

run-api:
	source venv/bin/activate && python -m api

seed:
	source venv/bin/activate && python -m seed

types:
	source venv/bin/activate && mypy .

console_postgres:
	docker exec -it postgres-db psql -U postgres -d sample

migrate:
	source venv/bin/activate && alembic upgrade head

reset-migrate:
	source venv/bin/activate && alembic downgrade base && alembic upgrade head

clean:
	docker-compose down
	docker-compose rm