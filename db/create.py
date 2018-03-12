from decimal import Decimal

from db import Engine
from models import *


def init_blanaces(session, currency, default_amount):
    for i in range(1, 10):
        balance_query = session.query(Balance).\
            filter(Balance.user_id == i).\
            filter(Balance.currency == currency)
        if balance_query.first() is not None:
            continue

        balance = Balance(user_id=i, currency=currency, amount=default_amount)
        session.add(balance)


def init():
    Base.metadata.create_all(Engine)

    session = sessionmaker(bind=Engine)()

    for i in range(1, 10):
        name = 'user-{}'.format(i)
        if session.query(User).filter(User.name == name).first() is not None:
            continue

        user = User(name=name)
        session.add(user)

    session.commit()

    init_blanaces(session, 'EUR', Decimal('5000'))
    init_blanaces(session, 'ETH', Decimal('50'))

    session.commit()

    for i in range(1, 10):
        if session.query(ApiKey).filter(ApiKey.user_id == i).first() is not None:
            continue

        api_key = ApiKey(user_id=i, key='user{}'.format(i))
        session.add(api_key)

    session.commit()


if __name__ == '__main__':
    init()
