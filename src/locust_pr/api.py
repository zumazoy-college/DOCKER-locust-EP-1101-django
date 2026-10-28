import itertools
import math
import os
import random

from locust import HttpUser, TaskSet, between, task

from locust_pr.data import order_data

API_USERS = 30
API_PASSWORD = os.getenv('LOCUST_API_PASSWORD', 'Locust_pass_123')

# Учётные записи locust_01..locust_30 создаёт scripts/create_api_users.py
_accounts = itertools.cycle(range(1, API_USERS + 1))


class ApiShopper(TaskSet):
    """Покупатель работает с API. Вес задач: чтений намного больше, чем записей."""

    def on_start(self):
        self.products = []
        self.category_ids = []
        self.cart = set()
        self.login()
        self.load_products()
        with self.client.get('/api/categories/', name='/api/categories/ [start]', catch_response=True) as r:
            self.category_ids = [c['id'] for c in r.json().get('results', [])]

    def login(self):
        creds = {'username': f'locust_{next(_accounts):02d}', 'password': API_PASSWORD}
        with self.client.post('/api/auth/token/', json=creds, name='/api/auth/token/',
                              catch_response=True) as r:
            if r.status_code == 200:
                self.client.headers['Authorization'] = f"Token {r.json()['token']}"
                r.success()
            else:
                r.failure('не удалось получить токен: создайте учётные записи scripts/create_api_users.py')
                self.user.stop()

    def load_products(self, params=None, name='/api/products/ [start]'):
        with self.client.get('/api/products/', params=params or {'page_size': 100}, name=name,
                             catch_response=True) as r:
            data = r.json()
            self.products = data.get('results', self.products)
            self.pages = max(1, math.ceil(data.get('count', 1) / 10))

    @task(8)
    def list_products(self):
        params = {'page': random.randint(1, self.pages), 'ordering': random.choice(['price', '-price', 'name'])}
        self.load_products(params, name='/api/products/ [list]')

    @task(6)
    def search_products(self):
        word = random.choice(random.choice(self.products)['name'].split())
        self.client.get('/api/products/', params={'search': word}, name='/api/products/ [search]')

    @task(6)
    def product_detail(self):
        self.client.get(f"/api/products/{random.choice(self.products)['id']}/", name='/api/products/[id]/')

    @task(4)
    def products_by_category(self):
        if self.category_ids:
            self.client.get('/api/products/', params={'category': random.choice(self.category_ids)},
                            name='/api/products/ [category]')

    @task(3)
    def list_categories(self):
        self.client.get('/api/categories/', name='/api/categories/')

    @task(3)
    def my_orders(self):
        self.client.get('/api/orders/my/', name='/api/orders/my/')

    @task(3)
    def view_cart(self):
        self.client.get('/api/cart/', name='/api/cart/')

    @task(2)
    def add_to_cart(self):
        in_stock = [p for p in self.products if p['stock'] > 0 and p['id'] not in self.cart]
        if in_stock:
            product = random.choice(in_stock)
            with self.client.post(f"/api/cart/add/{product['id']}/", name='/api/cart/add/[id]/',
                                  catch_response=True) as r:
                if r.status_code == 201:
                    self.cart.add(product['id'])
                    r.success()
                else:
                    r.failure(f'HTTP {r.status_code}')

    @task(1)
    def create_order(self):
        if not self.cart:
            self.add_to_cart()
        if not self.cart:
            return
        with self.client.post('/api/orders/', json=order_data(), name='/api/orders/',
                              catch_response=True) as r:
            if r.status_code == 201:
                self.cart.clear()
                r.success()
            elif r.status_code == 400 and 'not available' in r.text:
                # бизнес-правило: товар закончился на складе, это не ошибка сервера
                r.success()
                self.client.delete('/api/cart/clear/', name='/api/cart/clear/')
                self.cart.clear()
            else:
                r.failure(f'HTTP {r.status_code}')


class ApiUser(HttpUser):
    weight = 3
    wait_time = between(0.5, 2)
    tasks = [ApiShopper]
