# Smart Keyboard Layout Corrector

Легковесный, умный и молниеносный корректор опечаток и раскладки клавиатуры для Linux (X11). Утилита автоматически или принудительно исправляет текст, набранный в неверной раскладке (аналог Punto Switcher, Caramba Switcher).

## 🚀 Архитектура проекта

Проект разделен на две независимые части по канонам системного программирования Linux:
1. **Сервер (`layout_service.py`)** — фоновый веб-сервис на FastAPI. Держит в оперативной памяти тяжелые словари, выполняет токенизацию, каскад лингвистических проверок и исправление текста. Работает как глобальный системный демон `systemd`.
2. **Клиент (`layout_client.py`)** — легковесный перехватчик горячих клавиш (`pynput`), работающий в фоне на чистом нажатии (`on_press`) в контексте графической сессии пользователя. Автоматически захватывает выделенный текст через `xclip/xdotool`, отправляет его локальному серверу по сети и мгновенно возвращает исправленный результат на экран.

---

## 📦 1. Системные зависимости

Для работы захвата экрана, эмуляции ввода и лингвистического анализа установите системные пакеты в вашей ОС (Ubuntu/Debian):

```bash
sudo apt update
sudo apt install python3-pip python3-venv xclip xdotool -y
```

---

## 🐍 2. Настройка виртуального окружения Python

Создайте изолированное виртуальное окружение в домашней директории и установите необходимые библиотеки:

```bash
# Создание venv (замените "user" на имя вашего пользователя в Linux)
python3 -m venv /home/user/venv

# Обновление pip и установка пакетов
/home/user/venv/bin/pip install --upgrade pip
/home/user/venv/bin/pip install fastapi uvicorn pyspellchecker pymorphy3 pynput
```

---

## ⚙️ 3. Развертывание Сервера (`layout_service.py`)

Сервер преобразований работает независимо на порту `18888`.

1. Разместите код сервера в файле `/home/user/layout_service.py`.
2. Создайте файл глобального системного сервиса:
   ```bash
   sudo nano /etc/systemd/system/smart-switcher.service
   ```
3. Вставьте следующую конфигурацию (замените `user` в путях на ваше реальное имя пользователя):
   ```ini
   [Unit]
   Description=Smart Keyboard Layout Corrector Service (API Backend)
   After=network.target

   [Service]
   User=root
   WorkingDirectory=/home/user
   ExecStart=/home/user/venv/bin/uvicorn layout_service:app --host 0.0.0.0 --port 18888
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
4. Активируйте и запустите сервер:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable smart-switcher.service
   sudo systemctl start smart-switcher.service
   ```

---

## ⌨️ 4. Linux-клиент (`layout_client.py`)

Клиент должен запускаться строго внутри вашей пользовательской сессии (не под `root`!), чтобы иметь легитимный доступ к сокетам оконного менеджера X11.

1. Разместите код клиента в файле `/home/user/layout_client.py`.
2. Создайте файл пользовательской службы автозапуска (**без sudo**):
   ```bash
   mkdir -p ~/.config/systemd/user/
   nano ~/.config/systemd/user/smart-switcher-client.service
   ```
3. Вставьте конфигурацию (замените `user` в путях на ваше имя пользователя). Флаг `Nice=-5` сообщает планировщику задач ядра Linux, что процесс является интерактивной утилитой, гарантируя моментальный отклик графики без рандомных микрозадержек:
   ```ini
   [Unit]
   Description=Smart Keyboard Layout Client (High Priority Hook)
   After=graphical-session.target

   [Service]
   Type=simple
   WorkingDirectory=/home/user
   ExecStart=/home/user/venv/bin/python3 /home/user/layout_client.py
   Restart=always

   # Стабильно высокий приоритет планировщика ОС для мгновенной эмуляции клавиш
   Nice=-5

   [Install]
   WantedBy=default.target
   ```
4. Активируйте и запустите клиент в контексте текущего пользователя (**без sudo**):
   ```bash
   systemctl --user daemon-reload
   systemctl --user enable smart-switcher-client.service
   systemctl --user start smart-switcher-client.service
   ```

---

## ⌨️ 5. Windows-клиент (`layout_win.pyw`)

#### Шаг 1. Установка Python
Если у вас еще не установлен Python:
1. Скачайте актуальную версию Python для Windows с [официального сайта](https://python.org).
2. При установке **обязательно отметьте галочку "Add python.exe to PATH"** (Добавить Python в переменные среды).

#### Шаг 2. Установка зависимостей
Откройте командную строку (нажмите `Win + R`, введите `cmd` и нажмите Enter) и выполните следующую команду для установки необходимых библиотек:

```bash
pip install keyboard pyperclip uiautomation
```

#### Шаг 3. Подготовка скрипта
1. Создайте текстовый файл и назовите его, например, `layout_fixer.pyw` (расширение `.pyw` важно, чтобы скрипт работал скрытно).
2. Вставьте в него код вашего клиента.
3. Убедитесь, что в начале файла указаны корректные IP-адреса вашего FastAPI сервера:
   ```python
   API_URL_FIX = "http://127.0.0.1:18888/fix"
   API_URL_INVERT = "http://127.0.0.1:18888/invert"
   ```

#### Шаг 4. Добавление в автозапуск Windows

Чтобы скрипт автоматически запускался в фоновом режиме при каждом включении компьютера:

1. Нажмите комбинацию клавиш **Win + R**.
2. Введите команду `shell:startup` и нажмите **Enter**. Откроется системная папка автозагрузки.
3. Перетащите в эту папку ваш файл `layout_fixer.pyw` (или создайте на него ярлык).

*Готово! Теперь при следующем входе в Windows скрипт запустится сам без лишних окон и запросов.*

---

## 🎮 6. Использование и горячие клавиши

Служба полностью автономна, висит в RAM и срабатывает **мгновенно в момент утапливания клавиш (on_press)**. Защита от дребезга и аппаратного автоповтора ОС реализована нативно: при удержании клавиш повторные вызовы натыкаются на снятое выделение текста, буфер обмена оказывается пустым и ложные потоки тихо завершаются.

*   **`Scroll Lock`** — принудительная инверсия раскладки выделенного текста (из RU в EN или наоборот).
*   **`Pause / Break`** — умное исправление опечаток и раскладки на основе словарей `pyspellchecker` и `pymorphy3`.

## 📊 Диагностика логов

Если что-то пошло не так, вы всегда можете проверить состояние компонентов через встроенный журнал `systemd`:

*   Просмотр логов бэкенда (сервера словарей):
    ```bash
    journalctl -u smart-switcher.service -n 30 --no-pager
    ```
*   Просмотр логов перехватчика горячих клавиш (клиента):
    ```bash
    systemctl --user status smart-switcher-client.service
    ```

