# Анализатор зависимостей пакетов Ubuntu

Практика № 2, вариант 5. Этап 1 читает настройки из XML и печатает их
в формате `ключ = значение`.

Нужен Python 3.10 или новее. Сборка и установка библиотек не требуются.

```bash
sh run.sh examples/config.xml
python3 -m unittest discover -s tests -v
```

В Windows PowerShell:

```powershell
.\run.bat examples\config.xml
py -m unittest discover -s tests -v
```

Корень XML — `config`. Каждое поле задаётся один раз.

| Поле | Значение |
| --- | --- |
| `package` | Имя пакета Ubuntu или заглавная латинская буква в тестовом режиме. |
| `repository` | URL HTTP(S) или путь к тестовому файлу относительно XML. |
| `test_mode` | `true` для тестового репозитория, иначе `false`. |
| `version` | Версия выбранного пакета, например `2.10-3`. |
| `output` | Имя файла PNG, например `graph.png`. |
| `ascii` | `true` для вывода ASCII-дерева, иначе `false`. |

На первом этапе программа проверяет настройки. Загрузка зависимостей
и построение графа относятся к следующим этапам.

Пример успешного вывода:

```text
package = hello
repository = https://archive.ubuntu.com/ubuntu/
test_mode = false
version = 2.10-3
output = graph.png
ascii = false
```

Для демонстрации ошибок скопируйте XML и меняйте по одному значению:
`package` → `?`, `repository` → `local`, `test_mode` → `maybe`,
`version` → `unknown`, `output` → `graph.txt`, `ascii` → `maybe`.
Запустите программу с изменённым XML. Ошибка укажет поле, код выхода — 1.
Тесты выполняют эти шесть проверок автоматически.
