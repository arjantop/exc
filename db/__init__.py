from sqlalchemy import create_engine

Engine = create_engine('mysql://root:test@db:3306/exchange?use_unicode=1', encoding='utf8', echo=True)
