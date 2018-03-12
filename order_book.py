import threading

from decimal import Decimal
from queue import Queue

from sortedcontainers import SortedDict


class OrderBookOrder:
    def __init__(self, id, type, amount, price):
        self.id = id
        self.type = type
        self.amount = amount
        self.price = price
        self.matched_amount = Decimal(0)

    def transfer_amount(self, order):
        to_transfer = min(self.amount_to_match(), order.amount_to_match())

        self.matched_amount += to_transfer
        order.matched_amount += to_transfer

        return to_transfer

    def amount_to_match(self):
        return self.amount - self.matched_amount

    def is_matched(self):
        return self.amount == self.matched_amount

    def __repr__(self):
        return "<Order(id='{}', type='{}', amount='{}', price='{}', matched_amount='{}')>".format(
            self.id, self.type, self.amount, self.price, self.matched_amount)

    def __eq__(self, other):
        return self.id == other.id and self.type == other.type \
            and self.amount == other.amount and self.price == other.price \
            and self.matched_amount == other.matched_amount


class OrderBookSide:
    def __init__(self, asc, events: Queue):
        self.asc = asc
        self.events = events
        self.orders_map = {}
        self.levels_map = SortedDict()

    def add_order(self, order):
        self.levels_map.setdefault(order.price, []).append(order)
        self.orders_map[order.id] = order

    def match_order(self, order):
        remove_list = []
        for level in self.__iterate_levels():
            if self.__compare_price(order.price, level):
                self.__match_orders(order, self.levels_map[level], remove_list)
                if order.is_matched():
                    self.events.put({
                        'name': 'complete',
                        'order_id': order.id,
                    })
                    break
            else:
                break

        # Remove orders after the iteration is complete (so we do not modify the list while iterating over)
        for o in remove_list:
            self.__remove_order(o)

        return order

    def __match_orders(self, order, orders, remove_list):
        for o in orders:
            transferred_amount = o.transfer_amount(order)
            self.events.put({
                'name': 'match',
                'amount': transferred_amount,
                'order_id': order.id,
                'matched_order_id': o.id,
            })

            if o.is_matched():
                remove_list.append(o)
                self.events.put({
                    'name': 'complete',
                    'order_id': o.id,
                })

            if order.is_matched():
                break

    def __remove_order(self, order):
        level = self.levels_map[order.price]
        level.remove(order)

        if len(level) == 0:
            self.levels_map.pop(order.price)

    def __compare_price(self, order_price, book_price):
        if self.asc:
            return order_price >= book_price
        else:
            return order_price <= book_price

    def __iterate_levels(self):
        if self.asc:
            return iter(self.levels_map)
        else:
            return reversed(self.levels_map)

    def cancel_order_by_id(self, order_id):
        order = self.orders_map.get(order_id)
        if order is None:
            return

        self.__remove_order(order)

        self.events.put({
            'name': 'cancelled',
            'order_id': order.id,
            'remaining_amount': order.amount_to_match(),
        })

    def orders(self):
        return [o for l in self.levels_map for o in self.levels_map[l]]


class OrderBook:
    def __init__(self, events: Queue):
        # This will not allow any parallelism but is correct. Theoretically orders of the same type could execute in
        # parallel while walking the order book. More threads contending for locks could just make things worse.
        self.lock = threading.Lock()

        self.buy_side = OrderBookSide(asc=False, events=events)
        self.sell_side = OrderBookSide(asc=True, events=events)

    def add_order(self, order):
        if order.type == 'buy':
            with self.lock:
                self.sell_side.match_order(order)
                if not order.is_matched():
                    self.buy_side.add_order(order)
        elif order.type == 'sell':
            with self.lock:
                self.buy_side.match_order(order)
                if not order.is_matched():
                    self.sell_side.add_order(order)
        else:
            raise Exception('Invalid order type: {}'.format(order.kind))

    def cancel_order_by_id(self, order_id):
        with self.lock:
            self.buy_side.cancel_order_by_id(order_id)
            self.sell_side.cancel_order_by_id(order_id)

    def buy_orders(self):
        return self.buy_side.orders()

    def sell_orders(self):
        return self.sell_side.orders()


Events = Queue()
SharedOrderBook = OrderBook(Events)
