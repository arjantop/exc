import time
from pyramid.authentication import BasicAuthAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.config import Configurator
from pyramid.security import ALL_PERMISSIONS, unauthenticated_userid
from pyramid.security import Allow
from pyramid.security import Authenticated
from waitress import serve

import db.create
from db import Engine
from event_persister import BackgroundEventPersister
from models import DBSession, Base, User, ApiKey
# In reality this should be cached, ignore for this implementation
from order_book import Events


def check_credentials(username, password, request):
    session = DBSession()
    key = session.query(ApiKey).filter(ApiKey.id == username).filter(ApiKey.key == password).first()

    if key is not None:
        return []


def get_user(request):
    session = DBSession()

    key_id = unauthenticated_userid(request)
    if key_id is not None:
        return session.query(User).filter(ApiKey.user_id == User.id).filter(ApiKey.id == key_id).first()


class Root:
    # Give all permissions to all authenticated users
    __acl__ = (
        (Allow, Authenticated, ALL_PERMISSIONS),
    )


def main():
    # Stupid workaround to wait for mysql actually starting inside of a container
    time.sleep(15)

    # Just init the database at the start for simplicity
    db.create.init()

    p = BackgroundEventPersister(Events)
    p.start()

    DBSession.configure(bind=Engine)
    Base.metadata.bind = Engine

    with Configurator() as config:
        config.include('pyramid_tm')

        config.add_request_method(get_user, 'user', reify=True)

        config.add_route('place_order', '/orders', request_method='POST')
        config.add_route('list_orders', '/orders', request_method='GET')
        config.add_route('cancel_order', '/order/{orderId}', request_method='DELETE')
        config.scan('views')

        auth_policy = BasicAuthAuthenticationPolicy(check_credentials)
        config.set_authentication_policy(auth_policy)
        config.set_authorization_policy(ACLAuthorizationPolicy())
        config.set_root_factory(lambda request: Root())

        app = config.make_wsgi_app()
    serve(app, host='0.0.0.0', port=8888)


if __name__ == '__main__':
    main()
