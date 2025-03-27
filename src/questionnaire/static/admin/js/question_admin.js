document.addEventListener('DOMContentLoaded', function() {
    function toggleFields() {
        const isNumeric = document.querySelector('#id_is_numeric_input').checked;

        // Скрываем/показываем дополнительные настройки
        document.querySelectorAll('.field-allow_free_text, .field-is_multiple_choice').forEach(el => {
            el.style.display = isNumeric ? 'none' : '';
        });

        // Блокируем конфликтующие поля
        if(isNumeric) {
            document.querySelector('#id_allow_free_text').checked = false;
            document.querySelector('#id_is_multiple_choice').checked = false;
        }
    }

    // Инициализация
    toggleFields();

    // Слушаем изменения
    document.querySelector('#id_is_numeric_input').addEventListener('change', toggleFields);
});