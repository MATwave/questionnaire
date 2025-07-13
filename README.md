# questionnarie

тест (но надо убедится что миграции произведены)

```bash
python manage.py test questionnaire.tests -v 2
```

покрытие
```bash
coverage run --source='questionnaire' manage.py test questionnaire
```
отчет краткий
```bash
coverage report
```
отчет подробный
```bash
coverage html
```