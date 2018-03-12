import decimal
from decimal import Decimal

from pyramid.httpexceptions import HTTPBadRequest
from pyramid.view import (
    view_config,
    view_defaults
)

from models import DBSession, Order, Balance
from order_book import SharedOrderBook, OrderBookOrder


@view_defaults(renderer='json', permission='trade')
class JsonViews:
    def __init__(self, request):
        self.request = request

    @view_config(route_name='list_orders')
    def list_orders(self):
        orders = DBSession.query(Order).order_by(Order.id).\
            filter(Order.user_id == self.request.user.id).\
            all()
        return [{
            'id': order.id,
            'type': order.type,
            'amount': str(order.amount),
            'price': str(order.price),
            'status': order.status,
            'matches': [{
                'id': match.id,
                'matched_order_id': match.matched_order_id,
                'amount': str(match.amount),
            } for match in order.matches]
        } for order in orders]

    # In practice this should prevent:
    # - negative orders
    # - orders that are too small
    # - self orders
    @view_config(route_name='place_order')
    def place_order(self):
        body = self.request.json_body

        order_type = body.get('type')
        if order_type not in ['buy', 'sell']:
            return HTTPBadRequest(detail='Invalid or missing order type: {}'.format(order_type))

        amount_str = body.get('amount')
        if amount_str is None:
            return HTTPBadRequest(detail='Missing amount parameter')

        try:
            amount = Decimal(amount_str)
        except decimal.InvalidOperation:
            return HTTPBadRequest(detail='Invalid amount parameter: {}'.format(amount_str))

        price_str = body.get('price')
        if price_str is None:
            return HTTPBadRequest(detail='Missing price parameter')

        try:
            price = Decimal(price_str)
        except decimal.InvalidOperation:
            return HTTPBadRequest(detail='Invalid price parameter: {}'.format(price_str))

        session = DBSession

        order = Order(user_id=self.request.user.id, status='pending', type=order_type, amount=amount, price=price)

        balance_currency = order.required_currency()
        balance = self.__balance_for_user(session, balance_currency, 1)

        if order_type == 'sell':
            required_amount = amount
        else:
            required_amount = amount*price

        if balance.amount < required_amount:
            return HTTPBadRequest(detail='Insufficient founds: {}'.format(balance.amount))

        balance.amount = balance.amount - required_amount

        session.add(order)
        session.flush()

        SharedOrderBook.add_order(OrderBookOrder(order.id, order.type, order.amount, order.price))

        return {'id': order.id}

    @staticmethod
    def __balance_for_user(session, currency, user_id):
        balance = session.query(Balance).\
            filter(Balance.currency == currency).\
            filter(Balance.user_id == user_id).with_for_update().first()

        if balance is None:
            return Balance(currency=currency, amount=Decimal(0), user_id=user_id)

        return balance

    @view_config(route_name='cancel_order')
    def cancel_order(self):
        order_id = self.request.matchdict['orderId']

        session = DBSession()
        order = session.query(Order).filter(Order.id == order_id).filter(Order.user_id == self.request.user.id).first()
        if order is None:
            return HTTPBadRequest(detail='Invalid order id: {}'.format(order_id))

        SharedOrderBook.cancel_order_by_id(order.id)

        return {'status': 'success'}
