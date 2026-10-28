import os

from django.contrib.auth.models import Group, User

password = os.getenv('LOCUST_API_PASSWORD', 'Locust_pass_123')
customers = Group.objects.get(name='Customers')

for i in range(1, 31):
    user, _ = User.objects.get_or_create(
        username=f'locust_{i:02d}', defaults={'email': f'locust_{i:02d}@loadtest.example'})
    user.set_password(password)
    user.save()
    user.groups.add(customers)

print('Готово: учётных записей locust_*:', User.objects.filter(username__startswith='locust_').count())
