import queue
import unittest
from decimal import Decimal

from order_book import OrderBookOrder, OrderBook


class OrderBookTest(unittest.TestCase):

    def setUp(self):
        self.events = queue.Queue()
        self.order_book = OrderBook(self.events)

    def test_sell_order_is_added(self):
        order = OrderBookOrder(1, 'sell', Decimal('500'), Decimal('5'))
        self.order_book.add_order(order)

        self.assertEqual(self.order_book.sell_orders(), [order])
        self.assertEqual(self.order_book.buy_orders(), [])

    def test_buy_order_is_added(self):
        order = OrderBookOrder(1, 'buy', Decimal('500'), Decimal('5'))
        self.order_book.add_order(order)

        self.assertEqual(self.order_book.buy_orders(), [order])
        self.assertEqual(self.order_book.sell_orders(), [])

    def test_sell_and_buy_orders_are_matched(self):
        sell_order = OrderBookOrder(1, 'sell', Decimal('500'), Decimal('5'))
        self.order_book.add_order(sell_order)

        buy_order = OrderBookOrder(2, 'buy', Decimal('500'), Decimal('5'))
        self.order_book.add_order(buy_order)

        self.assertEqual(self.order_book.buy_orders(), [])
        self.assertEqual(self.order_book.sell_orders(), [])

        self.assertEqual({
            'name': 'match',
            'amount': Decimal('500'),
            'order_id': 2,
            'matched_order_id': 1,
        }, self.events.get(block=False))

        self.assertEqual({
            'name': 'complete',
            'order_id': 1,
        }, self.events.get(block=False))

        self.assertEqual({
            'name': 'complete',
            'order_id': 2,
        }, self.events.get(block=False))

    def test_cancelled_order_is_removed_from_the_order_book(self):
        self.order_book.add_order(OrderBookOrder(1, 'sell', Decimal('500'), Decimal('5')))

        self.order_book.cancel_order_by_id(1)

        self.assertEqual(self.order_book.buy_orders(), [])
        self.assertEqual(self.order_book.sell_orders(), [])

        self.assertEqual({
            'name': 'cancelled',
            'order_id': 1,
            'remaining_amount': Decimal('500'),
        }, self.events.get(block=False))

    def test_cancelled_partially_matched_order_has_a_correct_remaining_amount(self):
        self.order_book.add_order(OrderBookOrder(1, 'sell', Decimal('500'), Decimal('5')))
        self.order_book.add_order(OrderBookOrder(2, 'buy', Decimal('300'), Decimal('5')))

        self.order_book.cancel_order_by_id(1)

        self.assertEqual(self.order_book.buy_orders(), [])
        self.assertEqual(self.order_book.sell_orders(), [])

        self.expect_event('match')
        self.expect_event('complete')

        self.assertEqual({
            'name': 'cancelled',
            'order_id': 1,
            'remaining_amount': Decimal('200'),
        }, self.events.get(block=False))

    def test_sell_and_buy_orders_are_matched_incompletely(self):
        self.order_book.add_order(OrderBookOrder(1, 'sell', Decimal('500'), Decimal('5')))

        self.order_book.add_order(OrderBookOrder(2, 'buy', Decimal('300'), Decimal('5')))

        self.assertEqual(self.order_book.buy_orders(), [])
        self.assertEqual(self.order_book.sell_orders(), [
            self.with_matched_amount(OrderBookOrder(1, 'sell', Decimal('500'), Decimal('5')), Decimal('300'))])

        self.assertEqual({
            'name': 'match',
            'amount': Decimal('300'),
            'order_id': 2,
            'matched_order_id': 1,
        }, self.events.get(block=False))

        self.order_book.add_order(OrderBookOrder(3, 'buy', Decimal('500'), Decimal('5')))

        self.assertEqual([self.with_matched_amount(OrderBookOrder(3, 'buy', Decimal('500'), Decimal('5')), Decimal('200'))],
                         self.order_book.buy_orders())
        self.assertEqual(self.order_book.sell_orders(), [])

        self.assertEqual({
            'name': 'complete',
            'order_id': 2,
        }, self.events.get(block=False))

        self.assertEqual({
            'name': 'match',
            'amount': Decimal('200'),
            'order_id': 3,
            'matched_order_id': 1,
        }, self.events.get(block=False))

    def test_orders_are_matched_in_fifo_order(self):
        self.order_book.add_order(OrderBookOrder(1, 'sell', Decimal('10'), Decimal('3.5')))
        self.order_book.add_order(OrderBookOrder(2, 'sell', Decimal('30'), Decimal('3.5')))

        self.order_book.add_order(OrderBookOrder(3, 'buy', Decimal('15'), Decimal('3.5')))

        self.assertEqual([], self.order_book.buy_orders())
        self.assertEqual([self.with_matched_amount(OrderBookOrder(2, 'sell', Decimal('30'), Decimal('3.5')), Decimal('5'))],
                         self.order_book.sell_orders())

    def test_sell_orders_are_matched_until_they_are_filled_up_to_the_price_level(self):
        self.order_book.add_order(OrderBookOrder(1, 'sell', Decimal('10'), Decimal('3.6')))
        self.order_book.add_order(OrderBookOrder(2, 'sell', Decimal('30'), Decimal('3.5')))
        self.order_book.add_order(OrderBookOrder(3, 'sell', Decimal('15'), Decimal('3.5')))
        self.order_book.add_order(OrderBookOrder(4, 'sell', Decimal('5'), Decimal('3.4')))

        self.order_book.add_order(OrderBookOrder(5, 'buy', Decimal('60'), Decimal('3.5')))

        self.assertEqual([self.with_matched_amount(OrderBookOrder(5, 'buy', Decimal('60'), Decimal('3.5')), Decimal('50'))],
                         self.order_book.buy_orders())
        self.assertEqual([self.with_matched_amount(OrderBookOrder(1, 'sell', Decimal('10'), Decimal('3.6')), Decimal('0'))],
                         self.order_book.sell_orders())

    def test_buy_orders_are_matched_until_they_are_filled_up_to_the_price_level(self):
        self.order_book.add_order(OrderBookOrder(1, 'buy', Decimal('10'), Decimal('3.6')))
        self.order_book.add_order(OrderBookOrder(2, 'buy', Decimal('30'), Decimal('3.5')))
        self.order_book.add_order(OrderBookOrder(3, 'buy', Decimal('15'), Decimal('3.5')))
        self.order_book.add_order(OrderBookOrder(4, 'buy', Decimal('5'), Decimal('3.4')))

        self.order_book.add_order(OrderBookOrder(5, 'sell', Decimal('60'), Decimal('3.5')))

        self.assertEqual([self.with_matched_amount(OrderBookOrder(4, 'buy', Decimal('5'), Decimal('3.4')), Decimal('0'))],
                         self.order_book.buy_orders())
        self.assertEqual([self.with_matched_amount(OrderBookOrder(5, 'sell', Decimal('60'), Decimal('3.5')), Decimal('55'))],
                         self.order_book.sell_orders())

    def test_unmatched_buy_and_sell_orders_are_added(self):
        self.order_book.add_order(OrderBookOrder(1, 'buy', Decimal('10'), Decimal('1.0')))
        self.order_book.add_order(OrderBookOrder(2, 'sell', Decimal('20'), Decimal('1.1')))
        self.order_book.add_order(OrderBookOrder(3, 'buy', Decimal('30'), Decimal('0.9')))
        self.order_book.add_order(OrderBookOrder(4, 'sell', Decimal('40'), Decimal('1.2')))

        self.assertEqual([OrderBookOrder(3, 'buy', Decimal('30'), Decimal('0.9')),
                          OrderBookOrder(1, 'buy', Decimal('10'), Decimal('1.0'))], self.order_book.buy_orders())
        self.assertEqual([OrderBookOrder(2, 'sell', Decimal('20'), Decimal('1.1')),
                          OrderBookOrder(4, 'sell', Decimal('40'), Decimal('1.2'))], self.order_book.sell_orders())

    def expect_event(self, event_name):
        self.assertEqual(event_name, self.events.get(block=False)['name'])

    @staticmethod
    def with_matched_amount(order, matcher_amount):
        order.matched_amount = matcher_amount
        return order

