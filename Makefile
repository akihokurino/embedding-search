run:
	docker-compose up

create_dataset:
	source venv/bin/activate && python -m create_dataset

types:
	source venv/bin/activate && mypy .