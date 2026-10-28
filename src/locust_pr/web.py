import random
import re

from locust import HttpUser, SequentialTaskSet, TaskSet, between, task

from locust_pr.data import new_account, order_data

PRODUCT_RE = re.compile(r'/products/(\d+)/')
CATEGORY_RE = re.compile(r'/categories/(\d+)/products/')


def csrf(client) -> dict:
    """Django ждёт CSRF-токен из cookie в заголовке X-CSRFToken (токен меняется при входе)."""
    return {'X-CSRFToken': client.cookies.get('csrftoken', '')}


def read_catalog(taskset) -> None:
    """Открывает главную и запоминает id товаров и категорий, которые реально есть в базе."""
    with taskset.client.get('/', name='/', catch_response=True) as r:
        taskset.product_ids = list(dict.fromkeys(PRODUCT_RE.findall(r.text)))
        taskset.category_ids = list(dict.fromkeys(CATEGORY_RE.findall(r.text)))
        if not taskset.product_ids:
            r.failure('на главной нет товаров в наличии')


class ShopBrowsing(TaskSet):
    """Гость просматривает каталог. TaskSet: задача выбирается случайно с учётом веса."""

    def on_start(self):
        read_catalog(self)

    @task(5)
    def open_home(self):
        self.client.get('/', name='/')

    @task(6)
    def open_product(self):
        if self.product_ids:
            self.client.get(f'/products/{random.choice(self.product_ids)}/', name='/products/[id]/')

    @task(3)
    def open_category(self):
        if self.category_ids:
            self.client.get(f'/categories/{random.choice(self.category_ids)}/products/',
                            name='/categories/[id]/products/')


class BuyerFlow(SequentialTaskSet):
    """Путь покупателя. SequentialTaskSet: шаги выполняются строго по порядку, как в сценарии."""

    def on_start(self):
        read_catalog(self)
        self.register()

    def register(self):
        for _ in range(3):
            self.account = new_account()
            self.client.get('/register/', name='/register/')
            with self.client.post('/register/', data=self.account, headers=csrf(self.client),
                                  name='/register/', catch_response=True) as r:
                if 'sessionid' in self.client.cookies:
                    r.success()
                    return
                r.failure('регистрация отклонена формой')
        self.user.stop()

    @task
    def view_catalog(self):
        self.client.get('/', name='/')

    @task
    def view_product(self):
        self.client.get(f'/products/{random.choice(self.product_ids)}/', name='/products/[id]/')

    @task
    def view_category(self):
        if self.category_ids:
            self.client.get(f'/categories/{random.choice(self.category_ids)}/products/',
                            name='/categories/[id]/products/')

    @task
    def add_to_cart(self):
        self.client.post(f'/cart/add/{random.choice(self.product_ids)}/', headers=csrf(self.client),
                         name='/cart/add/[id]/')

    @task
    def view_cart(self):
        self.client.get('/cart/', name='/cart/')

    @task
    def open_checkout(self):
        self.client.get('/checkout/', name='/checkout/')

    @task
    def checkout(self):
        with self.client.post('/checkout/', data=order_data(), headers=csrf(self.client),
                              name='/checkout/', catch_response=True) as r:
            if r.url.rstrip('/').endswith('/my-orders'):
                r.success()
            else:
                r.failure('заказ не оформлен: пустая корзина или товар закончился')

    @task
    def view_my_orders(self):
        self.client.get('/my-orders/', name='/my-orders/')

    @task
    def view_profile(self):
        self.client.get('/profile/', name='/profile/')


class GuestUser(HttpUser):
    weight = 5
    wait_time = between(1, 3)
    tasks = [ShopBrowsing]


class BuyerUser(HttpUser):
    weight = 2
    wait_time = between(1, 3)
    tasks = [BuyerFlow]
