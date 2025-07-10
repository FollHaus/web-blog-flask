DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS post;

DROP TABLE IF EXISTS comment;
DROP TABLE IF EXISTS follower;

DROP TABLE IF EXISTS access_request;


CREATE TABLE user
(
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT        NOT NULL
);


CREATE TABLE post
(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id  INTEGER   NOT NULL,
    created    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    title      TEXT      NOT NULL,
    body       TEXT      NOT NULL,
    is_private INTEGER            DEFAULT 0,
    FOREIGN KEY (author_id) REFERENCES user (id)
);

CREATE TABLE tag (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL
);

CREATE TABLE post_tag (
  post_id INTEGER NOT NULL,
  tag_id  INTEGER NOT NULL,
  PRIMARY KEY(post_id, tag_id),
  FOREIGN KEY(post_id) REFERENCES post(id),
  FOREIGN KEY(tag_id)  REFERENCES tag(id)
);


create TABLE comment
(
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id   INTEGER   NOT NULL,
    author_id INTEGER   NOT NULL,
    body      TEXT      NOT NULL,
    created   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (author_id) REFERENCES user (id),
    FOREIGN KEY (post_id) REFERENCES post (id)
);

create TABLE follower
(
    -- Кто подписывается
    follower_id INTEGER NOT NULL,
    -- На кого
    followed_id INTEGER NOT NULL,
    -- Гарантирует уникальность пары: кто на кого подписан
    PRIMARY KEY (follower_id, followed_id),
    FOREIGN KEY (follower_id) REFERENCES user (id),
    FOREIGN KEY (followed_id) REFERENCES user (id)
);

create TABLE access_request
(
    -- Кто запрашивает доступ
    user_requesting INTEGER NOT NULL,
    -- У кого
    user_id   INTEGER NOT NULL,
    -- К какой статье открыть доступ
    post_id   INTEGER NOT NULL,
    -- Статус: 0 = не одобрен, 1 = доступ разрешён
    status    INTEGER NOT NULL DEFAULT 0,
    -- Гарантирует уникальность пары: кто на кого подписан
    PRIMARY KEY (user_requesting, user_id),
    FOREIGN KEY (user_requesting) REFERENCES user (id),
    FOREIGN KEY (user_id) REFERENCES user (id),
    FOREIGN KEY (post_id) REFERENCES post (id)
);