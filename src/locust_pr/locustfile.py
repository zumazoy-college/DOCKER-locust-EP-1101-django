from locust import events

from locust_pr.api import ApiUser
from locust_pr.web import BuyerUser, GuestUser

__all__ = ['ApiUser', 'BuyerUser', 'GuestUser']

MIN_GET_TO_WRITE_RATIO = 5


@events.quitting.add_listener
def check_get_to_write_ratio(environment, **kwargs):
    """По итогам прогона проверяет, что GET-запросов минимум в 5 раз больше, чем POST."""
    get = write = 0
    for (_, method), stats in environment.stats.entries.items():
        if method == 'GET':
            get += stats.num_requests
        else:
            write += stats.num_requests
    ratio = get / write if write else float('inf')
    print(f'\nGET: {get}, POST and other writes: {write}, ratio {ratio:.1f}:1 (required >= {MIN_GET_TO_WRITE_RATIO}:1)')
    if ratio < MIN_GET_TO_WRITE_RATIO:
        environment.process_exit_code = 1
