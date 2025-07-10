import sqlite3

from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from blog.auth import login_required
from blog.db import get_db

bp = Blueprint('blog', __name__)


# Главная
@bp.route('/')
@login_required
def index():
    db = get_db()
    posts = db.execute(
        'SELECT p.id, p.is_private, p.title, p.body, p.created, p.author_id,u.username'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' ORDER BY p.created DESC'
    ).fetchall()

    post_ids = [post['id'] for post in posts]

    tags_dict = {}
    if post_ids:
        tags = db.execute(
            '''SELECT pt.post_id, t.name
               FROM post_tag pt
               JOIN tag t ON pt.tag_id = t.id
               WHERE pt.post_id IN ({seq})'''.format(
                seq=','.join('?' * len(post_ids))
            ),
            post_ids
        ).fetchall()

        for tag in tags:
            tags_dict.setdefault(tag['post_id'], []).append(tag['name'])


    # Получаем подписки текущего пользователя
    following_ids = set()
    if g.user:
        followers = db.execute(
            'SELECT followed_id FROM follower WHERE follower_id = ?',
            (g.user['id'],)
        ).fetchall()
        following_ids = {f['followed_id'] for f in followers}

    access_request_list = db.execute(
        'SELECT user_requesting, post_id, status FROM access_request WHERE user_requesting = ?',
        (g.user['id'],)
    ).fetchall()

    access_dict = {
        (r['user_requesting'], r['post_id']): r['status']
        for r in access_request_list
    }

    return render_template('blog/index.html', posts=posts, follower=following_ids, access_dict=access_dict, tags_dict=tags_dict)


# Создание поста
@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        tags_input = request.form.get('tags', '')
        tags = {t.strip().lower() for t in tags_input.split(',') if t.strip()}
        error = None

        if not title:
            error = 'Название обязательно.'

        if error is not None:
            flash(error)
        else:
            db = get_db()

            # Вставляем пост и сохраняем ID
            cur = db.execute(
                'INSERT INTO post (title, body, author_id)'
                ' VALUES (?, ?, ?)',
                (title, body, g.user['id'])
            )
            post_id = cur.lastrowid

            # Добавляем теги
            for name in tags:
                tag = db.execute('SELECT id FROM tag WHERE name = ?', (name,)).fetchone()
                if tag:
                    tag_id = tag['id']
                else:
                    cur = db.execute('INSERT INTO tag (name) VALUES (?)', (name,))
                    tag_id = cur.lastrowid
                db.execute(
                    'INSERT OR IGNORE INTO post_tag (post_id, tag_id) VALUES (?, ?)',
                    (post_id, tag_id)
                )

            db.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/create.html')


# Получение поста
def get_post(id, check_author=True):
    post = get_db().execute(
        'SELECT p.id, is_private,title, body, created, author_id, username'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' WHERE p.id = ?',
        (id,)
    ).fetchone()

    if post is None:
        abort(404, f"Post id {id} doesn't exist.")

    if check_author and post['author_id'] != g.user['id']:
        abort(403)

    return post


@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    post = get_post(id)

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        tags_input = request.form.get('tags', '')
        tags = {t.strip().lower() for t in tags_input.split(',') if t.strip()}
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE post SET title = ?, body = ?'
                ' WHERE id = ?',
                (title, body, id)
            )
            # Удаляем старые привязки тегов
            db.execute('DELETE FROM post_tag WHERE post_id = ?', (id,))

            # Обновляем теги
            for name in tags:
                tag = db.execute('SELECT id FROM tag WHERE name = ?', (name,)).fetchone()
                if tag:
                    tag_id = tag['id']
                else:
                    cur = db.execute('INSERT INTO tag (name) VALUES (?)', (name,))
                    tag_id = cur.lastrowid
                db.execute(
                    'INSERT OR IGNORE INTO post_tag (post_id, tag_id) VALUES (?, ?)',
                    (id, tag_id)
                )

            db.commit()
            return redirect(url_for('blog.index'))

    # Получаем текущие теги поста
    tags = get_db().execute(
        '''SELECT t.name FROM tag t
           JOIN post_tag pt ON t.id = pt.tag_id
           WHERE pt.post_id = ?''',
        (id,)
    ).fetchall()
    tag_names = ', '.join([t['name'] for t in tags])

    return render_template('blog/update.html', post=post, tags=tag_names)


# Удаляем пост
@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_post(id)
    db = get_db()
    db.execute('DELETE FROM post WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('blog.index'))


# Комментированре поста
@bp.route('/comment', methods=('POST',))
@login_required
def comment():
    post_id = request.form.get('post_id')
    body = request.form.get('body')

    if not post_id or not body:
        flash("Пост или текст комментария не указаны")
        return redirect(url_for('blog.index'))

    db = get_db()

    db.execute(
        ' INSERT INTO comment (post_id, author_id, body)'
        ' VALUES (?,?,?)',
        (post_id, g.user['id'], body)
    )
    db.commit()

    return redirect(url_for('blog.post_detail', id=post_id))


# Все подписки
@bp.route('/subscriptions')
@login_required
def subscriptions():
    db = get_db()

    followers = db.execute(
        'SELECT u.id , u.username '
        ' FROM follower f '
        ' JOIN user u ON f.followed_id = u.id'
        ' WHERE f.follower_id = ?',
        (g.user['id'],)
    ).fetchall()

    return render_template('blog/subscribe.html', followers=followers)


# Подписка на пользователя
@bp.route('/<int:author_id>/subscribe')
@login_required
def subscribe(author_id):
    db = get_db()

    if not author_id:
        flash("Автор не найден")
        return redirect(url_for('blog.index'))

    try:
        db.execute(
            'INSERT INTO follower (follower_id, followed_id) VALUES (?,?)',
            (g.user['id'], author_id)
        )
        db.commit()

    except sqlite3.InternalError:
        flash("Вы уже подписаны")
        return redirect(url_for('blog.index'))

    flash("Подписка оформлена")
    return redirect(url_for('blog.index'))


# Функция отписки
@bp.route('/<int:author_id>/unsubscribe')
@login_required
def unsubscribe(author_id):
    db = get_db()

    if not author_id:
        flash("Автор не найден")
        return redirect(url_for('blog.index'))

    # Удаляем подписку
    db.execute(
        'DELETE FROM follower WHERE follower_id = ? AND followed_id = ?',
        (g.user['id'], author_id)
    )
    db.commit()

    flash("Вы успешно отписаны")
    return redirect(url_for('blog.index'))


# Функция просмотра поста
@bp.route('/<int:id>/post')
@login_required
def post_detail(id):
    db = get_db()

    post = db.execute(
        'SELECT p.*, u.username FROM post p JOIN user u ON p.author_id = u.id WHERE p.id = ?',
        (id,)
    ).fetchone()

    if post is None:
        abort(404, "Пост не найден.")

    # Проверка приватности
    if post['is_private']:
        if g.user is None:
            flash('Для доступа нужно войти.')
            return redirect(url_for('auth.login'))

        if g.user['id'] != post['author_id']:
            access = db.execute(
                'SELECT status FROM access_request WHERE user_requesting = ? AND post_id = ?',
                (g.user['id'], id)
            ).fetchone()

            if not access or access['status'] != 1:
                flash('У вас нет доступа к этому посту.')
                return redirect(url_for('blog.index'))

    # Получаем теги поста
    tags = db.execute(
        '''SELECT t.name FROM tag t
           JOIN post_tag pt ON t.id = pt.tag_id
           WHERE pt.post_id = ?''',
        (id,)
    ).fetchall()

    tag_names = [t['name'] for t in tags]

    return render_template('blog/post_detail.html', post=post, tags=tag_names)



# Скрывает пост
@bp.route('/hide', methods=('POST',))
@login_required
def toggle_hide_post():
    if request.method == 'POST':
        post_id = request.form.get('post_id')
        is_private = request.form.get('toggle')
        post = get_post(post_id)

        if not post_id:
            flash('Пост не найден')
            return redirect(url_for('blog.index'))

        try:
            is_private = int(is_private)
        except ValueError:
            flash('Ошибка: значение не является числом')
        else:
            if is_private in (0, 1):
                db = get_db()
                db.execute(
                    'UPDATE post SET is_private = ?'
                    ' WHERE id = ?',
                    (is_private, post_id)
                )
                db.commit()
                flash('Статус приватности изменён')
                return redirect(url_for('blog.index'))
    return redirect(url_for('blog.index'))


# Отправка запроса на доступ к статье
@bp.route('/access_request', methods=('POST',))
@login_required
def access_request():
    if request.method == 'POST':
        # Кто
        user_requesting = request.form.get('user_id')
        # У кого
        author_id = request.form.get('author_id')
        post_id = request.form.get('post_id')

        if not user_requesting or not author_id:
            flash('Пользователя не существует')
            return redirect(url_for('blog.index'))

        db = get_db()
        try:
            db.execute(
                'INSERT INTO access_request (user_requesting, user_id, post_id, status) '
                'VALUES (?, ?, ?, ?)',
                (user_requesting, author_id, post_id, 0)
            )
            db.commit()
        except db.IntegrityError:
            # Запись уже существует
            flash("Запрос уже отправлен")
        else:
            flash("Запрос на доступ отправлен")
        db.commit()


# Получаем все запросы на доступ к статьям
@bp.route('/access_requests')
@login_required
def access_requests():
    db = get_db()

    access_request_list = db.execute(
        'SELECT a.user_requesting, a.user_id, a.post_id, a.status, p.title AS post_title, u.username AS username'
        ' FROM access_request a '
        ' JOIN post p ON a.post_id = p.id'
        ' JOIN user u ON a.user_requesting = u.id'
        ' WHERE a.user_id = ?',
        (g.user['id'],)
    ).fetchall()

    access = db.execute(
        'SELECT user_requesting, post_id, status FROM access_request WHERE user_id = ?',
        (g.user['id'],)
    ).fetchall()

    access_dict = {
        (r['user_requesting'], r['post_id']): r['status']
        for r in access
    }

    return render_template('blog/access_request.html', access_request=access_request_list, access_dict=access_dict)


# Даем доступ к статье
@bp.route('/give_access', methods=('POST',))
@login_required
def give_access():
    user_requesting = request.form.get('user_requesting')
    post_id = request.form.get('post_id')

    if not user_requesting or not post_id:
        flash('Пользователь или пост не найден')
        return redirect(url_for('blog.access_requests'))

    db = get_db()
    try:
        # Правильно ищем существующую запись по запрашивающему и посту
        existing_request = db.execute(
            'SELECT * FROM access_request WHERE user_requesting = ? AND post_id = ?',
            (user_requesting, post_id)
        ).fetchone()

        if existing_request:
            current_status = existing_request['status']
            new_status = 0 if current_status == 1 else 1
            db.execute(
                'UPDATE access_request SET status = ? WHERE user_requesting = ? AND post_id = ?',
                (new_status, user_requesting, post_id)
            )
        else:
            db.execute(
                'INSERT INTO access_request (user_id, user_requesting, post_id, status) VALUES (?, ?, ?, ?)',
                (g.user.id, user_requesting, post_id, 1)
            )

        db.commit()
        flash("Доступ предоставлен")
        return redirect(url_for('blog.access_requests'))
    except Exception as e:
        flash(f"Произошла ошибка: {str(e)}")
    finally:
        return redirect(url_for('blog.access_requests'))


@bp.route('/tag/<tag_name>')
@login_required
def posts_by_tag(tag_name):
    db = get_db()

    posts = db.execute(
        '''
        SELECT p.id, p.is_private, p.title, p.body, p.created, p.author_id, u.username
        FROM post p
        JOIN user u ON p.author_id = u.id
        JOIN post_tag pt ON pt.post_id = p.id
        JOIN tag t ON pt.tag_id = t.id
        WHERE t.name = ?
        ORDER BY p.created DESC
        ''',
        (tag_name,)
    ).fetchall()

    # Подписки
    followers = db.execute(
        'SELECT followed_id FROM follower WHERE follower_id = ?',
        (g.user['id'],)
    ).fetchall()
    following_ids = {f['followed_id'] for f in followers}

    # Доступы
    access_request_list = db.execute(
        'SELECT user_requesting, post_id, status FROM access_request WHERE user_requesting = ?',
        (g.user['id'],)
    ).fetchall()

    access_dict = {
        (r['user_requesting'], r['post_id']): r['status']
        for r in access_request_list
    }

    # Теги к постам
    post_ids = [post['id'] for post in posts]
    tags_dict = {}
    if post_ids:
        tags = db.execute(
            '''SELECT pt.post_id, t.name
               FROM post_tag pt
               JOIN tag t ON pt.tag_id = t.id
               WHERE pt.post_id IN ({seq})'''.format(seq=','.join('?' * len(post_ids))),
            post_ids
        ).fetchall()

        for tag in tags:
            tags_dict.setdefault(tag['post_id'], []).append(tag['name'])

    return render_template(
        'blog/index.html',
        posts=posts,
        follower=following_ids,
        access_dict=access_dict,
        tags_dict=tags_dict,
        current_tag=tag_name  # можно использовать в заголовке
    )
