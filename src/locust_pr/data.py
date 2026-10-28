import re

from faker import Faker

fake_ru = Faker('ru_RU')
fake_en = Faker('en_US')

TEST_EMAIL_DOMAIN = 'loadtest.example'


def new_account() -> dict:
    """Данные для регистрации нового покупателя."""
    username = f'{fake_en.user_name()}_{fake_en.random_int(1000, 99999)}'
    password = fake_en.password(length=14, special_chars=False)
    return {
        'username': username,
        'email': f'{username}@{TEST_EMAIL_DOMAIN}',
        'password1': password,
        'password2': password,
    }


def order_data() -> dict:
    """Данные для оформления заказа: ФИО, телефон, email и адрес доставки."""
    return {
        'customer_name': fake_ru.name(),
        'phone': '+7' + fake_ru.numerify('9#########'),
        'email': fake_en.email(),
        'shipping_address': re.sub(r'\s*\n\s*', ', ', fake_ru.address()),
    }
