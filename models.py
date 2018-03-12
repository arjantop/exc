from datetime import datetime

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, scoped_session, sessionmaker
from sqlalchemy import *
from zope.sqlalchemy import ZopeTransactionExtension

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))

Base = declarative_base()

default_table_args = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8', 'mysql_collate': 'utf8_general_ci'}


class User(Base):
    __tablename__ = 'users'
    __table_args__ = default_table_args

    id = Column(BigInteger, primary_key=True)
    name = Column(String(50, collation='utf8_unicode_ci'), nullable=False)

    def __repr__(self):
        return "<User(id='{}', name='{}')>".format(self.id, self.name)


class ApiKey(Base):
    __tablename__ = 'api_keys'
    __table_args__ = default_table_args

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey(User.id, ondelete="CASCADE"), nullable=False)
    key = Column(String(32, collation='utf8_unicode_ci'), nullable=False)

    user = relationship(User)

    def __repr__(self):
        return "<ApiKey(id='{}', user_id='{}', name='{}')>".format(self.id, self.user_id, self.key)


# TODO: index
class Order(Base):
    __tablename__ = 'orders'
    __table_args__ = default_table_args

    id = Column(BigInteger, primary_key=True)
    status = Column(String(32, collation='utf8_unicode_ci'), nullable=False)
    user_id = Column(BigInteger, ForeignKey(User.id, ondelete="CASCADE"), nullable=False)
    type = Column(String(32, collation='utf8_unicode_ci'), nullable=False)
    amount = Column(Numeric(precision=10, scale=6), nullable=False)
    price = Column(Numeric(precision=10, scale=6), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    user = relationship(User)

    matches = relationship('Match', back_populates='order')

    def required_currency(self):
        if self.type == 'buy':
            return 'EUR'
        else:
            return 'ETH'

    def __repr__(self):
        return "<Order(id='{}', status='{}', user_id='{}', type='{}'," +\
               " amount='{}', price='{}', created_at='{}')>".format(
                self.id, self.status, self.user_id, self.type, self.amount, self.price, self.created_at)


class Match(Base):
    __tablename__ = 'matches'
    __table_args__ = default_table_args

    id = Column(BigInteger, primary_key=True)
    amount = Column(Numeric(precision=10, scale=6), nullable=False)
    order_id = Column(BigInteger, ForeignKey(Order.id, ondelete="CASCADE"), nullable=False)
    matched_order_id = Column(BigInteger, nullable=False)

    order = relationship('Order', back_populates='matches')

    def __repr__(self):
        return "<Match(id='{}', amount='{}', order_id='{}', matched_order_id='{}')>".format(
            self.id, self.amount, self.order_id, self.matched_order_id)


class Balance(Base):
    __tablename__ = 'balances'
    __table_args__ = default_table_args

    id = Column(BigInteger, primary_key=True)
    currency = Column(String(32, collation='utf8_unicode_ci'), nullable=False)
    amount = Column(Numeric(precision=10, scale=6), nullable=False)
    user_id = Column(BigInteger, ForeignKey(User.id, ondelete="CASCADE"), nullable=False)

    user = relationship(User)

    def __repr__(self):
        return "<Balance(id='{}', currency='{}', amount='{}')>".format(
            self.id, self.currency, self.amount)

