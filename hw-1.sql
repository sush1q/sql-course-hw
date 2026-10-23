-- Сироткин П.И.
-- Вариант 18
-- Описание предметной области
-- Описание экскурсионных туров. 
-- Включает в себя: маршруты, экскурсии, туры. 
-- Маршрут характеризуется названием, городом отправления, описанием маршрута, базовой ценой (без экскурсий) в рублях, указанием списка всех возможных для посещения городов и количеством дней пребывания в них. 
-- Экскурсия характеризуется: указанием города (в каждом городе может быть несколько экскурсий), названием, описанием и ценой в рублях. 
-- Тур характеризуется: указанием маршрута, датой отъезда, количеством дней тура, дополнительными взносами, дополнительным описанием.
-- Одна и та же экскурсия может быть связана с несколькими городами.

DROP TABLE IF EXISTS cities CASCADE;
CREATE TABLE cities (
    name text PRIMARY KEY
);

DROP TABLE IF EXISTS routes CASCADE;
CREATE TABLE routes (
    id integer PRIMARY KEY,
    name text NOT NULL,
    start_city text NOT NULL REFERENCES cities(name),
    description text,
    base_cost numeric(10, 2) CONSTRAINT base_cost_not_negative NOT NULL CHECK(base_cost >= 0)
);

DROP TABLE IF EXISTS route_city CASCADE;
CREATE TABLE route_city (
    id integer PRIMARY KEY,
    route integer NOT NULL REFERENCES routes(id),
    city text NOT NULL REFERENCES cities(name),
    days_count integer CONSTRAINT days_not_negative NOT NULL CHECK(days_count >= 0),
    visit_order integer CONSTRAINT order_not_negative NOT NULL CHECK(visit_order > 0),

    UNIQUE (route, visit_order)
);

DROP TABLE IF EXISTS excursions CASCADE;
CREATE TABLE excursions (
    id integer PRIMARY KEY,
    name text NOT NULL,
    description text,
    cost numeric(10,2) CONSTRAINT cost_not_negative NOT NULL CHECK(cost > 0)
);

DROP TABLE IF EXISTS excursion_city CASCADE;
CREATE TABLE excursion_city (
    excursion integer REFERENCES excursions(id),
    city text REFERENCES cities(name),
    PRIMARY KEY(excursion, city)
);

DROP TABLE IF EXISTS tours CASCADE;
CREATE TABLE tours (
    id integer PRIMARY KEY,
    route integer NOT NULL REFERENCES routes(id),
    departure_date date NOT NULL,
    days_count integer CONSTRAINT days_not_negative NOT NULL CHECK(days_count > 0),
    description text
);

DROP TABLE IF EXISTS fees CASCADE;
CREATE TABLE fees (
    id integer PRIMARY KEY,
    tour integer NOT NULL REFERENCES tours(id),
    cost numeric(10,2) CONSTRAINT cost_not_negative NOT NULL CHECK(cost > 0)
);

-- ================================= hw 2 prep =======================================
INSERT INTO cities (name) VALUES
    ('Токио'),
    ('Киото'),
    ('Осака'),
    ('Нара'),
    ('Ито');

INSERT INTO routes (id, name, start_city, description, base_cost) VALUES
    (1, 'Токио и Ито', 'Токио',
     'Маршрут из Токио в курортный город Ито.',
     70000.00),

    (2, 'Классическая Япония', 'Токио',
     'Маршрут через Токио, Киото и Осаку.',
     120000.00),

    (3, 'Киото и Нара', 'Киото',
     'Культурный маршрут по историческим городам Киото и Нара.',
     65000.00),

    (4, 'Осака и Нара', 'Осака',
     'Короткий маршрут по Осаке и Наре.',
     55000.00),

    (5, 'Большое путешествие по Японии', 'Токио',
     'Маршрут через Токио, Ито, Киото, Нару и Осаку.',
     160000.00);


INSERT INTO route_city
    (id, route, city, days_count, visit_order)
VALUES
    (1, 1, 'Токио', 2, 1),
    (2, 1, 'Ито', 2, 2),

    (3, 2, 'Токио', 3, 1),
    (4, 2, 'Киото', 3, 2),
    (5, 2, 'Осака', 2, 3),

    (6, 3, 'Киото', 3, 1),
    (7, 3, 'Нара', 1, 2),

    (8, 4, 'Осака', 2, 1),
    (9, 4, 'Нара', 1, 2),

    (10, 5, 'Токио', 3, 1),
    (11, 5, 'Ито', 2, 2),
    (12, 5, 'Киото', 3, 3),
    (13, 5, 'Нара', 1, 4),
    (14, 5, 'Осака', 2, 5);

INSERT INTO excursions (id, name, description, cost) VALUES
    (1, 'Обзорная экскурсия по Токио',
     'Посещение Асакусы, Сибуи и Синдзюку.',
     8500.00),

    (2, 'Храмы Киото',
     'Экскурсия по известным храмам и историческим районам Киото.',
     9000.00),

    (3, 'Замок Осака',
     'Посещение замка Осака и прогулка по центральной части города.',
     7000.00),

    (4, 'Историческая Нара',
     'Посещение парка Нара и храма Тодай-дзи.',
     7500.00),

    (5, 'Традиционная Япония',
     'Знакомство с традиционной японской архитектурой и культурой.',
     8000.00);

INSERT INTO excursion_city (excursion, city) VALUES
    (1, 'Токио'),
    (2, 'Киото'),
    (3, 'Осака'),
    (4, 'Нара'),
    (5, 'Киото'),
    (5, 'Нара'),
    (5, 'Ито');

INSERT INTO tours
    (id, route, departure_date, days_count, description)
VALUES
    (1, 1, '2027-03-20', 4,
     'Весенний тур из Токио в Ито.'),

    (2, 2, '2027-04-05', 8,
     'Тур по Токио, Киото и Осаке.'),

    (3, 3, '2027-05-10', 4,
     'Культурный тур по Киото и Наре.'),

    (4, 4, '2027-09-15', 3,
     'Короткий тур по Осаке и Наре.'),

    (5, 5, '2027-11-01', 11,
     'Большое путешествие по пяти городам Японии.');

INSERT INTO fees (id, tour, cost) VALUES
    (1, 1, 3000.00),
    (2, 2, 5000.00),
    (3, 3, 2500.00),
    (4, 4, 2000.00),
    (5, 5, 6000.00);


-- ================================= hw 2 =======================================
-- Вариант 18
-- Выберите экскурсии (все поля таблицы), пересчитав их цену из рублей в доллары по текущему курсу ЦБ РФ и округлив её в большую сторону до доллара. 
SELECT *, CEIL(cost / 81.12) AS dollar_cost
FROM excursions;

-- Выберите для каждого номера или идентификатора тура, число городов, через которые он проходит, отсортировав по этому числу и исключив туры  с 2 городами.
SELECT tours.id, COUNT(route_city.city) city_count
FROM tours
JOIN route_city ON tours.route = route_city.route
GROUP BY tours.id
HAVING COUNT(route_city.city) != 2
ORDER BY city_count;
