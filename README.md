# Опросник здоровья

Django-приложение для оценки состояния здоровья пользователя через анкетирование.

## Особенности проекта

- Современный стек: Django 4.2, PostgreSQL, Poetry
- Полностью контейнеризованная среда разработки
- Автоматизированные тесты и анализ покрытия кода
- Готовые фикстуры для быстрого старта

## Технический стек

- **Бэкенд**: Django 4.2
- **База данных**: PostgreSQL
- **Управление зависимостями**: Poetry
- **Контейнеризация**: Docker Compose
- **Тестирование**: встроенный тестовый фреймворк Django + Coverage

## Быстрый старт

### Предварительные требования

- Docker и Docker Compose
- Make (опционально, но рекомендуется)

### Запуск с помощью Docker Compose

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/your-username/questionnaire.git
   cd questionnaire/src
   ```

2. Запустите инициализацию проекта:
   ```bash
   make docker-init
   ```
   Приложение будет доступно по адресу: http://localhost:8000

Основные команды Makefile
```bash
# Запуск проекта (сборка + инициализация БД)
make docker-init

# Запуск контейнеров
make docker-up

# Остановка контейнеров
make docker-down

# Пересборка Docker образов
make docker-build

# Запуск тестов
make test

# Запуск тестов с отчетом о покрытии
make coverage

# Генерация HTML отчета о покрытии
make coverage-html

# Применение миграций
make migrate

# Загрузка тестовых данных
make loaddata
```


запрос к базе, чтобы посмотреть ответы:

```sql
-- Создаем функцию для извлечения ответов на вопросы
CREATE OR REPLACE FUNCTION get_question_answer(responses_data JSONB, question_id INT)
RETURNS TEXT AS $$
DECLARE
    question_record JSONB;
    answer_text TEXT := '';
BEGIN
    -- Находим вопрос по question_id
    SELECT response INTO question_record
    FROM jsonb_array_elements(responses_data->'questions') AS response
    WHERE (response->>'question_id')::int = question_id
    LIMIT 1;
    
    IF question_record IS NULL THEN
        RETURN NULL;
    END IF;
    
    -- Проверяем тип ответа и извлекаем данные
    IF question_record->>'numeric_answer' IS NOT NULL AND question_record->>'numeric_answer' != 'null' THEN
        -- Числовой ответ
        answer_text := question_record->>'numeric_answer';
    ELSIF question_record->>'free_text_answer' IS NOT NULL AND question_record->>'free_text_answer' != '' THEN
        -- Свободный текст
        answer_text := question_record->>'free_text_answer';
    ELSIF jsonb_array_length(question_record->'selected_answers') > 0 THEN
        -- Выбранные варианты ответов
        SELECT string_agg(a->>'answer_text', ', ') INTO answer_text
        FROM jsonb_array_elements(question_record->'selected_answers') AS a;
    END IF;
    
    RETURN answer_text;
END;
$$ LANGUAGE plpgsql;

-- Генерируем и выполняем полный запрос с использованием поля text и ID для уникальности
DO $$
DECLARE
    column_list TEXT := '';
    query_text TEXT;
BEGIN
    -- Собираем список всех вопросов из таблицы questionnaire_question
    -- Используем поле text и добавляем ID для уникальности
    SELECT string_agg(
        format('get_question_answer(responses_data, %s) as "Q%s_%s"', 
               q.id,
               q.order,  -- ID вопроса для уникальности
               regexp_replace(substring(q.text from 1 for 50), '[\n\r]+', ' ', 'g')  -- Первые 50 символов текста
        )
    , E',\n    ' ORDER BY q."order")
    INTO column_list
    FROM questionnaire_question q;
    
    -- Строим финальный запрос со всеми колонками
    query_text := format('
        SELECT 
            sr.created_at as "Отметка времени",
            up.gender as "Пол",
            up.age as "Возраст",
            up.height as "Рост (см)",
            up.weight as "Вес (кг)",
            ROUND((up.weight::numeric / ((up.height::numeric/100)^2)), 1) as "ИМТ",
            %s,
            -- Специальные рейтинговые колонки
            COALESCE((sr.calculated_rating->>''medico_biological_avg'')::numeric, 0) as "Медико-биологические факторы",
            COALESCE((sr.calculated_rating->>''lifestyle_avg'')::numeric, 0) as "Двигательная активность, режим дня",
            COALESCE((sr.calculated_rating->>''work_assessment_avg'')::numeric, 0) as "Самооценка трудового процесса",
            COALESCE((sr.calculated_rating->>''nutrition_avg'')::numeric, 0) as "Питание",
            COALESCE((sr.calculated_rating->>''eating_behavior_avg'')::numeric, 0) as "Пищевые привычки",
            COALESCE((sr.calculated_rating->>''stress_avg'')::numeric, 0) as "Стрессоустойчивость",
            COALESCE((sr.calculated_rating->>''total_score'')::numeric, 0) as "ИТОГО",
            COALESCE(sr.calculated_rating->>''rating'', ''Нет оценки'') as "Оценка соответствия"
        FROM questionnaire_surveyresult sr
        JOIN questionnaire_anonymoususerprofile up ON sr.user_profile_id = up.id
        ORDER BY sr.created_at
    ', column_list);
    
    -- Создаем временную таблицу с результатами
    EXECUTE 'DROP TABLE IF EXISTS temp_survey_export;';
    EXECUTE 'CREATE TEMP TABLE temp_survey_export AS ' || query_text;
    
    RAISE NOTICE 'Временная таблица temp_survey_export создана успешно';
END;
$$;

-- Просмотр результатов
SELECT * FROM temp_survey_export LIMIT 5;
```