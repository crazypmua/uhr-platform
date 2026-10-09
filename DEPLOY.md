# UHR + Ukrwerkspot: первичная настройка и автодеплой

Оба домена обслуживает одно Python-приложение из `/home/uhr/app`.

- `https://uhrbv.nl/` — заглушка или полный UHR-фронтенд.
- `https://ukrwerkspot.nl/` — заглушка или полный Ukrwerkspot-фронтенд.
- `https://uhrbv.nl/admin/` — общая админка.
- `/api/v1/` на обоих доменах — общее API.

Публичного `/preview/` нет. Если сайт закрыт, посетитель видит заглушку. Администратор
открывает полный интерфейс кнопкой из раздела «Налаштування».

## 1. Создание приватного репозитория GitHub

### 1.1. SSH-ключ рабочего компьютера для GitHub

В PowerShell:

```powershell
ssh-keygen -t ed25519 -C "your-email@example.com" -f "$env:USERPROFILE\.ssh\github_uhr"
```

Пароль на ключ рекомендуется установить. Затем запустите `ssh-agent` от имени
администратора:

```powershell
Get-Service ssh-agent | Set-Service -StartupType Automatic
Start-Service ssh-agent
ssh-add "$env:USERPROFILE\.ssh\github_uhr"
```

Создайте или дополните файл `$env:USERPROFILE\.ssh\config`:

```text
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/github_uhr
    IdentitiesOnly yes
```

Скопируйте публичную часть:

```powershell
Get-Content "$env:USERPROFILE\.ssh\github_uhr.pub"
```

GitHub → **Settings → SSH and GPG keys → New SSH key**. Вставьте содержимое
`.pub`, затем проверьте:

```powershell
ssh -T git@github.com
```

### 1.2. Создание репозитория

GitHub → **New repository**:

- имя, например `uhr-platform`;
- видимость `Private`;
- не добавлять README, `.gitignore` и лицензию — файлы уже есть локально.

В папке проекта:

```powershell
cd "D:\Projects\Нидерланды"
git init
git branch -M main
git config user.name "Ваше имя"
git config user.email "your-email@example.com"
git add .
git commit -m "Initial UHR platform"
git remote add origin git@github.com:OWNER/uhr-platform.git
git push -u origin main
```

Замените `OWNER` на имя пользователя или организации GitHub.

Если `origin` уже существует:

```powershell
git remote set-url origin git@github.com:OWNER/uhr-platform.git
```

## 2. Подготовка сервера

Команды ниже рассчитаны на Ubuntu 22.04/24.04. Вход первоначально выполняется
пользователем с `sudo`.
    
```bash
sudo apt update
sudo apt install -y git nginx postgresql postgresql-contrib \
  python3 python3-venv python3-pip certbot python3-certbot-nginx
```

Создайте системного пользователя проекта:

```bash
sudo adduser --disabled-password --gecos "" uhr
sudo install -d -o uhr -g uhr -m 750 /home/uhr/app
```

Проект, виртуальное окружение, `.env` и загрузки будут находиться в `/home/uhr/app`.
`/var/www` не используется.

## 3. SSH-ключ сервера для чтения приватного GitHub-репозитория

Это отдельный ключ. Он нужен серверу для `git fetch`.

```bash
sudo -iu uhr
mkdir -p ~/.ssh
chmod 700 ~/.ssh
ssh-keygen -t ed25519 -C "uhr-server-deploy" -f ~/.ssh/github_deploy
cat ~/.ssh/github_deploy.pub 
```

В GitHub откройте репозиторий → **Settings → Deploy keys → Add deploy key**:

- Title: `uhr production server`;
- Key: содержимое `github_deploy.pub`;
- `Allow write access` не включать.

На сервере создайте `/home/uhr/.ssh/config`:

```text
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/github_deploy
    IdentitiesOnly yes
```

Задайте права и проверьте соединение:

```bash
chmod 600 ~/.ssh/config
ssh-keyscan github.com >> ~/.ssh/known_hosts
chmod 600 ~/.ssh/known_hosts
ssh -T git@github.com
```

Клонируйте репозиторий:

```bash
git clone git@github.com:OWNER/uhr-platform.git /home/uhr/app
exit
```

Если каталог `/home/uhr/app` уже непустой, сначала клонируйте во временный каталог
и перенесите файлы либо настройте существующий каталог:

```bash
sudo -iu uhr
cd /home/uhr/app
git init
git remote add origin git@github.com:OWNER/uhr-platform.git
git fetch origin main
git checkout -B main origin/main
exit
```

## 4. PostgreSQL

Создайте пользователя и базу. Укажите собственный длинный пароль:

```bash
sudo -u postgres psql
```

```sql
CREATE USER uhr WITH PASSWORD 'ЗАМЕНИТЕ_НА_СЛОЖНЫЙ_ПАРОЛЬ';
CREATE DATABASE uhr OWNER uhr;
\q
```

Первичную схему выполните вручную:

```bash
PGPASSWORD='ЗАМЕНИТЕ_НА_СЛОЖНЫЙ_ПАРОЛЬ' \
  psql -h 127.0.0.1 -U uhr -d uhr -f /home/uhr/app/sql/schema.sql
```

Автодеплой не выполняет миграции. Последующие изменения базы будут передаваться
отдельными SQL `ALTER`-командами для ручного запуска.

## 5. Настройка `.env`

```bash
sudo -iu uhr
cd /home/uhr/app
cp .env.example .env
nano .env
```

Пример:

```dotenv
DATABASE_URL=postgresql+psycopg://uhr:URL_ENCODED_PASSWORD@127.0.0.1:5432/uhr
SECRET_KEY=СЛУЧАЙНАЯ_СТРОКА_НЕ_МЕНЕЕ_64_СИМВОЛОВ
ADMIN_EMAIL=admin@uhrbv.nl
ADMIN_PASSWORD=ПЕРВИЧНЫЙ_СЛОЖНЫЙ_ПАРОЛЬ
COOKIE_SECURE=true
COOKIE_NAME=uhr_session
PREVIEW_COOKIE_NAME=uhr_preview
UHRBV_URL=https://uhrbv.nl
UKRWERKSPOT_URL=https://ukrwerkspot.nl
CORS_ORIGINS=https://uhrbv.nl,https://ukrwerkspot.nl
UPLOAD_DIR=uploads
```

Сгенерировать `SECRET_KEY`:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Если пароль базы содержит `@`, `:`, `/`, `#` или `%`, его необходимо
URL-кодировать. После сохранения:

```bash
chmod 600 .env
mkdir -p uploads
chmod 750 uploads
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
exit
```

При первом запуске приложение создаст администратора из `ADMIN_EMAIL` и
`ADMIN_PASSWORD`, а также начальные тексты и настройки сайтов. Существующий пароль
администратора при последующих запусках не перезаписывается.

## 6. systemd

Файл `deploy/uhr.service` уже рассчитан на `/home/uhr/app`:

```bash
sudo cp /home/uhr/app/deploy/uhr.service /etc/systemd/system/uhr.service
sudo systemctl daemon-reload
sudo systemctl enable --now uhr.service
sudo systemctl status uhr.service
```

Проверка напрямую на сервере:

```bash
curl -i http://127.0.0.1:8000/api/v1/health
```

Логи:

```bash
sudo journalctl -u uhr.service -n 100 --no-pager
sudo journalctl -u uhr.service -f
```

## 7. DNS и HTTPS

Для обоих доменов должны существовать DNS-записи:

- `uhrbv.nl` → A/AAAA сервера;
- `ukrwerkspot.nl` → A/AAAA сервера;

Проверьте:

```bash
dig +short uhrbv.nl
dig +short ukrwerkspot.nl
```

Если сертификаты уже используются текущим nginx, сохраните реальные строки
`ssl_certificate` и `ssl_certificate_key` из существующих конфигураций.

Если сертификатов ещё нет, сначала оставьте рабочие HTTP-блоки nginx и выполните:

```bash
sudo certbot --nginx -d uhrbv.nl
sudo certbot --nginx -d ukrwerkspot.nl
```

Проверка автоматического продления:

```bash
sudo certbot renew --dry-run
```

## 8. nginx: оба домена из `/home/uhr/app`

Сделайте резервную копию текущих конфигураций:

```bash
sudo cp -a /etc/nginx/sites-available /etc/nginx/sites-available.backup
sudo cp -a /etc/nginx/sites-enabled /etc/nginx/sites-enabled.backup
```

Скопируйте шаблон:

```bash
sudo cp /home/uhr/app/deploy/nginx.conf /etc/nginx/sites-available/uhr-platform
sudo nano /etc/nginx/sites-available/uhr-platform
```

В двух HTTPS-блоках проверьте пути сертификатов и при необходимости исправьте:

```nginx
ssl_certificate /etc/letsencrypt/live/ДОМЕН/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/ДОМЕН/privkey.pem;
```

Отключите старые конфигурации именно этих двух доменов, затем включите новую:

```bash
sudo ln -sfn /etc/nginx/sites-available/uhr-platform \
  /etc/nginx/sites-enabled/uhr-platform
sudo nginx -t
sudo systemctl reload nginx
```

Старые symlink-файлы доменов в `sites-enabled` нужно удалить только после проверки,
что они дублируют `server_name`. Другие сайты сервера не трогайте.

Nginx проксирует запросы в `127.0.0.1:8000`. Python выбирает:

1. полный фронтенд, если сайт открыт в админке;
2. полный фронтенд для авторизованного администратора;
3. страницу ожидания для остальных.

Такой вариант не требует давать пользователю `www-data` доступ к домашнему каталогу:
файлы читает процесс `uhr`, запущенный из `/home/uhr/app`.

## 9. Отдельный SSH-ключ GitHub Actions для входа на сервер

Не используйте приватный ключ GitHub и личный SSH-ключ. Создайте третий,
отдельный ключ на рабочем компьютере:

```powershell
ssh-keygen -t ed25519 -C "github-actions-uhr" `
  -f "$env:USERPROFILE\.ssh\uhr_github_actions"
```

Передайте публичную часть на сервер существующим способом:

```powershell
Get-Content "$env:USERPROFILE\.ssh\uhr_github_actions.pub"
```

Добавьте эту одну строку в `/home/uhr/.ssh/authorized_keys`:

```bash
sudo -iu uhr
nano ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
exit
```

Разрешите пользователю `uhr` только необходимые systemd-команды:

```bash
sudo visudo -f /etc/sudoers.d/uhr-deploy
```

Содержимое:

```text
uhr ALL=(root) NOPASSWD: /bin/systemctl restart uhr.service, /bin/systemctl is-active uhr.service
```

Проверьте путь к `systemctl` командой `command -v systemctl`. Если он отличается,
используйте фактический путь и в sudoers.

## 10. Secrets и Variables в GitHub Actions

GitHub → репозиторий → **Settings → Secrets and variables → Actions**.

Создайте Secrets:

- `SERVER_HOST` — IP или SSH-имя сервера;
- `SERVER_USER` — `uhr`;
- `SERVER_SSH_PORT` — обычно `22`;
- `SERVER_SSH_KEY` — всё содержимое приватного файла
  `uhr_github_actions` вместе со строками `BEGIN/END`;
- `TELEGRAM_BOT_TOKEN` — токен бота;
- `TELEGRAM_CHAT_ID` — ID чата.

Создайте Variables:

- `APP_DIR` = `/home/uhr/app`;
- `HEALTH_URL` = `https://uhrbv.nl/api/v1/health`.

После каждого push в `main` workflow:

1. подключается к серверу;
2. выполняет `git fetch` и синхронизацию с `origin/main`;
3. сохраняет `.env`, `.venv` и `uploads`;
4. обновляет Python-зависимости;
5. перезапускает `uhr.service`;
6. проверяет systemd и health endpoint;
7. отправляет результат в Telegram.

## 11. Первый деплой и проверка

```powershell
cd "D:\Projects\Нидерланды"
git add .
git commit -m "Configure site access and production deploy"
git push origin main
```

Проверьте GitHub → **Actions → Deploy to server**.

После успешного запуска:

1. откройте `https://uhrbv.nl/` в приватном окне — должна быть заглушка;
2. откройте `https://ukrwerkspot.nl/` в приватном окне — должна быть заглушка;
3. откройте `https://uhrbv.nl/admin/` и войдите;
4. перейдите в «Налаштування»;
5. кнопка «Переглянути повний сайт» должна показать полную верстку;
6. включите «Відкрити повний сайт для всіх» и проверьте домен в приватном окне;
7. снова закройте сайт и убедитесь, что в приватном окне вернулась заглушка.

## 12. Важное ограничение двух доменов

Cookie `uhrbv.nl` технически не может передаваться на `ukrwerkspot.nl`. Поэтому
кнопка просмотра в админке создаёт подписанную ссылку на 5 минут. Ukrwerkspot
обменивает её на собственную защищённую HttpOnly-cookie сроком на 1 час.

Эта cookie:

- не открывает админку;
- действует только на конкретном домене;
- не передаётся JavaScript;
- не открывает сайт обычным посетителям;
- автоматически истекает.

## 13. Активация визуального CMS

CMS использует GrapesJS, SCSS и дополнительные таблицы PostgreSQL. Миграции
автоматически не выполняются.

Один раз установите Node.js на сервере:

```bash
sudo apt update
sudo apt install -y nodejs npm
node --version
npm --version
```

После получения версии с CMS вручную выполните SQL:

```bash
sudo -u uhr psql \
  -h 127.0.0.1 \
  -U uhr \
  -d uhr \
  -W \
  -f /home/uhr/app/sql/cms_setup.sql
```

Проверьте таблицы:

```bash
sudo -u uhr psql \
  -h 127.0.0.1 \
  -U uhr \
  -d uhr \
  -W \
  -c '\dt cms_*'
```

Следующий deploy сам выполнит:

```bash
npm install --no-audit --no-fund
npm run build
```

Сборка происходит только на VPS. Она:

- компилирует `frontend/admin/assets/cms.scss` в `cms.css`;
- копирует self-hosted GrapesJS в admin assets;
- устанавливает общий CMS runtime для обоих доменов.

В админке откройте `Редактор сайтів`. Для пустого сайта сначала нажмите
`Створити базові сторінки`, затем откройте страницу, измените её в canvas,
сохраните черновик и опубликуйте. Черновик доступен только через защищённый
администраторский preview; посетители получают последнюю опубликованную версию.
