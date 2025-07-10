import sqlite3
from datetime import datetime

import click
from flask import current_app, g


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            # путь к базе данных
            current_app.config['DATABASE'],
            # авто определение типов
            detect_types=sqlite3.PARSE_DECLTYPES
        )

        #Для, обращение по имени столбцов.
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()


def init_db():
    db = get_db()

    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

# CLI для инициализации базы
@click.command('init-db')
def init_db_command():
    init_db()
    click.echo('База данных инициализирована')


# Конвертер для типа данных timestamp так, как изначально SQL не понимает это.
sqlite3.register_converter(
    "timestamp", lambda v: datetime.fromisoformat(v.decode())
)


''''
    app.teardown_appcontext() указывает Flask на вызов этой функции при очистке после возврата ответа.
    app.cli.add_command() добавляет новую команду, которая может быть вызвана с помощью команды flask. 
    '''''
def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)