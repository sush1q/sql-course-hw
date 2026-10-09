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
