# Makefile
.PHONY: test coverage coverage-html migrate loaddata initdb docker-up docker-down docker-build docker-init

# Запуск тестов
test:
	python manage.py test questionnaire.tests -v 2

# Запуск тестов с покрытием
coverage:
	coverage run --source='questionnaire' manage.py test questionnaire
	coverage report
	@echo "Подробный отчет: coverage html"

# Генерация HTML отчета покрытия
coverage-html:
	coverage html
	@echo "Отчет доступен в htmlcov/index.html"

# Миграции базы данных
migrate:
	python manage.py makemigrations
	python manage.py migrate

# Загрузка тестовых данных
loaddata:
	python manage.py loaddata datadump.json

# Инициализация базы данных (миграции + загрузка данных)
initdb: migrate loaddata

# Docker команды
docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-build:
	docker compose build

# Полная инициализация проекта с Docker
docker-init: docker-build docker-up
	@echo "Ожидание запуска Django (это может занять до 60 секунд)..."
	@timeout 60 bash -c 'until docker compose logs web | grep "Starting development server"; do sleep 2; done' || \
		(echo "Timeout waiting for Django to start"; docker compose logs web; exit 1)
	@echo "Применение миграций..."
	docker compose exec web python manage.py migrate
	@echo "Загрузка данных..."
	docker compose exec web python manage.py loaddata datadump.json
	@echo "Проект запущен! Доступен по адресу: http://localhost:8000"