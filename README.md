# locust-pr

Нагрузочное тестирование магазина «Техномаркет» (проект `EP-1101-django`) с помощью Locust. Тестовые данные (ФИО, адреса, телефоны, логины и пароли) генерирует Faker.

## Структура

```
EP-1101-django/           тестируемый магазин (git submodule)
config/locust.conf        настройки запуска (адрес, пользователи)
src/locust_pr/
  locustfile.py           точка входа, проверка соотношения GET : POST
  web.py                  сценарии веб-интерфейса: GuestUser, BuyerUser
  api.py                  сценарии REST API: ApiUser
  data.py                 генерация тестовых данных (Faker)
scripts/create_api_users.py  создание учётных записей для API-тестов
.env.example              переменные окружения (пароль тестовых учётных записей)
```

## Подготовка

1. Склонировать проект вместе с магазином (он подключён как git submodule, подробности о нём в [его README](https://github.com/zumazoy-college/EP-1101-django/blob/main/README.md)):

```bash
git clone --recurse-submodules https://github.com/zumazoy-college/DOCKER-locust-EP-1101-django.git
```

   Если репозиторий уже склонирован без `--recurse-submodules`, папка `EP-1101-django/` будет пустой. Заполнить её: `git submodule update --init`.

1. Создать файл с переменными окружения: `cp .env.example .env`. Значение `LOCUST_API_PASSWORD` задаёт пароль тестовых учётных записей, менять его необязательно.
2. Запустить магазин (сайт будет на <http://127.0.0.1>):

```bash
docker network create MS
cd EP-1101-django
cp .env.example .env
docker compose up -d --build
cd ..
```

   Сеть `MS` создаётся один раз, если её ещё нет.

4. Установить зависимости: `uv sync`.
5. Создать 30 учётных записей `locust_01`…`locust_30` для API (у новых пользователей нет прав на чтение каталога через API):

### Bash

```bash
docker exec -i --env-file .env django_app python manage.py shell < scripts/create_api_users.py
```

### Powershell

```powershell
Get-Content scripts/create_api_users.py -Raw | docker exec -i --env-file .env django_app python manage.py shell
```

## Запуск

```bash
uv run locust --config config/locust.conf
```

Открыть <http://localhost:8089>, задать число пользователей и нажать Start. Графики (RPS, время ответа, число пользователей) находятся на вкладке Charts.

## Что тестируется

| Класс | Тип | Задачи |
| --- | --- | --- |
| `ShopBrowsing` (`GuestUser`) | TaskSet | главная, карточка товара, товары категории (все GET) |
| `BuyerFlow` (`BuyerUser`) | SequentialTaskSet | регистрация (POST), каталог, товар, категория, добавление в корзину (POST), корзина, оформление заказа (GET и POST), мои заказы, профиль |
| `ApiShopper` (`ApiUser`) | TaskSet | получение токена (POST), список/поиск/фильтр товаров, карточка, категории, корзина, мои заказы, добавление в корзину (POST), создание заказа (POST) |

**TaskSet и SequentialTaskSet.** В `TaskSet` следующая задача выбирается случайно с учётом веса `@task(N)`: так ведёт себя поток разных посетителей. В `SequentialTaskSet` задачи идут строго по порядку определения, вес не учитывается, после последней начинается круг заново: так моделируется сценарий, где шаги зависят друг от друга (нельзя оформить заказ, не положив товар в корзину).

**Соотношение GET : POST.** Достигается весами: гости только читают, в API чтений 33 против 3 записей по весу, покупатель делает 3 записи на 9 чтений, а на гостей приходится больше половины пользователей (`weight` у классов). В конце прогона `locustfile.py` выводит итоговое соотношение и завершается с кодом 1, если оно меньше 5 : 1.

## После тестов

Тест создаёт в базе пользователей (email `…@loadtest.example`), заказы и уменьшает остатки товаров. Удалить тестовые данные:

```sql
DELETE FROM auth_user WHERE email LIKE '%@loadtest.example';
UPDATE ep1101_product SET stock = 100 WHERE stock < 100;
```

Если остатки закончатся, оформление заказа в веб-сценарии будет возвращать ошибку, это сообщение о нехватке товара, а не поломка теста.
