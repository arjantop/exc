import logging
import sys
from queue import Queue
from threading import Thread

from sqlalchemy.orm import Session, sessionmaker

from db import Engine
from models import Order, Match, Balance


class BackgroundEventPersister(Thread):

    def __init__(self, events: Queue):
        super().__init__(daemon=True)
        self.logger = logging.getLogger('BackgroundEventPersister')
        self.events = events

    def run(self):
        session = sessionmaker(bind=Engine)()

        p = EventPersister(session, self.events)
        try:
            p.run()
        except Exception:
            self.logger.exception("Persister failed")
            # Do no crash recovery, persister could be restarted n times to try to recover
            sys.exit(1)


class EventPersister:
    def __init__(self, session: Session, events: Queue):
        self.session = session
        self.events = events

    def run(self):
        while True:
            event = self.events.get()
            event_name = event.get('name')

            try:
                self.__handle_event(event_name, event)
            except Exception:
                self.session.rollback()
                raise

    def __handle_event(self, event_name, event):
        if event_name == 'cancelled':
            order = self.session.query(Order).filter(Order.id == event['order_id']).first()
            order.status = 'cancelled'

            self.session.query(Balance).\
                filter(Balance.user_id == order.user_id).\
                filter(Balance.currency == order.required_currency()).\
                update({Balance.amount: Balance.amount + event['remaining_amount']})

            self.session.commit()
        elif event_name == 'complete':
            self.session.query(Order).filter(Order.id == event['order_id']). \
                update({Order.status: 'complete'})
            self.session.commit()
        elif event_name == 'match':
            match = Match(amount=event['amount'],
                          order_id=event['order_id'],
                          matched_order_id=event['matched_order_id'])
            reverse_match = Match(amount=event['amount'],
                                  order_id=event['matched_order_id'],
                                  matched_order_id=event['order_id'])

            self.session.add(match)
            self.session.add(reverse_match)

            self.session.commit()
        else:
            raise Exception('Unrecognized event name: {}'.format(event_name))
