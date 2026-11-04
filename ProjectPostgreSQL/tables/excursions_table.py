from decimal import Decimal, InvalidOperation

from dbtable import DbTable
from tables.excursion_city_table import ExcursionCityTable


class ExcursionsTable(DbTable):
    def table_name(self):
        return self.dbconn.prefix + "excursions"

    def columns(self):
        return {"id": ["integer", "PRIMARY KEY"],
                "name": ["text", "NOT NULL"],
                "description": ["text"],
                "cost": ["numeric(10,2)", "NOT NULL", "CHECK(cost > 0)"]}

    def all_by_city(self, city):
        query = ("SELECT e.id, e.name, e.description, e.cost FROM " + self.table_name() +
                 " AS e JOIN " + ExcursionCityTable().table_name() +
                 " AS ec ON ec.excursion = e.id WHERE ec.city = %s ORDER BY e.name, e.id")
        with self.dbconn.conn:
            with self.dbconn.conn.cursor() as cur:
                cur.execute(query, (city,))
                return cur.fetchall()

    def all(self):
        with self.dbconn.conn:
            with self.dbconn.conn.cursor() as cur:
                cur.execute("SELECT id, name, description, cost FROM " + self.table_name() +
                            " ORDER BY name, id")
                return cur.fetchall()

    def count(self, city=None):
        query = "SELECT COUNT(*) FROM " + self.table_name() + " AS e"
        params = ()
        if city is not None:
            query += (" JOIN " + ExcursionCityTable().table_name() +
                      " AS ec ON ec.excursion = e.id WHERE ec.city = %s")
            params = (city,)
        with self.dbconn.conn:
            with self.dbconn.conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchone()[0]

    def page(self, page, page_size, city=None):
        if page < 0 or page_size < 1:
            raise ValueError("Некорректный номер или размер страницы!")
        query = "SELECT e.id, e.name, e.description, e.cost FROM " + self.table_name() + " AS e"
        params = []
        if city is not None:
            query += (" JOIN " + ExcursionCityTable().table_name() +
                      " AS ec ON ec.excursion = e.id WHERE ec.city = %s")
            params.append(city)
        query += " ORDER BY e.name, e.id LIMIT %s OFFSET %s"
        params.extend([page_size, page * page_size])
        with self.dbconn.conn:
            with self.dbconn.conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchall()

    @staticmethod
    def validate_cost(value):
        try:
            cost = Decimal(str(value).replace(',', '.'))
        except InvalidOperation:
            raise ValueError("Стоимость должна быть числом!")
        if not cost.is_finite() or not Decimal('0') < cost <= Decimal('99999999.99'):
            raise ValueError("Стоимость должна быть больше нуля и не больше 99999999.99!")
        if cost != cost.quantize(Decimal('0.01')):
            raise ValueError("Укажите стоимость с точностью до копеек!")
        return cost

    def validate_values(self, vals):
        if len(vals) != 3:
            raise ValueError("Нужны название, описание и стоимость экскурсии!")
        name, description, cost = vals
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Название экскурсии не может быть пустым!")
        if not (description is None or isinstance(description, str)):
            raise ValueError("Описание должно быть текстом!")
        if '\x00' in name or description is not None and '\x00' in description:
            raise ValueError("Текст содержит недопустимый нулевой символ!")
        cost = self.validate_cost(cost)
        return name.strip(), description, cost

    def insert_one(self, vals, city=None):
        name, description, cost = self.validate_values(vals)
        with self.dbconn.conn:
            with self.dbconn.conn.cursor() as cur:
                # В исходной схеме id — integer без автоматической генерации, поэтому приходится переусложнять =(
                cur.execute("LOCK TABLE " + self.table_name() + " IN SHARE ROW EXCLUSIVE MODE")
                cur.execute("SELECT COALESCE(MAX(id)::bigint, 0) + 1 FROM " + self.table_name())
                excursion_id = cur.fetchone()[0]
                if excursion_id > 2147483647:
                    raise ValueError("Невозможно создать новую экскурсию: исчерпан диапазон ключей.")
                cur.execute("INSERT INTO " + self.table_name() +
                            " (id, name, description, cost) VALUES (%s, %s, %s, %s)",
                            (excursion_id, name.strip(), description, cost))
                if city is not None:
                    cur.execute("INSERT INTO " + ExcursionCityTable().table_name() +
                                " (city, excursion) VALUES (%s, %s)", (city, excursion_id))
        return excursion_id

    def update_one(self, excursion, city, vals):
        name, description, cost = self.validate_values(vals)
        query = ("UPDATE " + self.table_name() +
                 " AS e SET name = %s, description = %s, cost = %s WHERE e.id = %s "
                 "AND EXISTS (SELECT 1 FROM " + ExcursionCityTable().table_name() +
                 " AS ec WHERE ec.excursion = e.id AND ec.city = %s)")
        with self.dbconn.conn:
            with self.dbconn.conn.cursor() as cur:
                cur.execute(query, (name, description, cost, excursion, city))
                if cur.rowcount == 0:
                    raise ValueError("Экскурсия не связана с выбранным городом. Обновите список!")

    def cities_by_excursion(self, excursion):
        with self.dbconn.conn:
            with self.dbconn.conn.cursor() as cur:
                cur.execute("SELECT city FROM " + ExcursionCityTable().table_name() +
                            " WHERE excursion = %s ORDER BY city", (excursion,))
                return cur.fetchall()

    def delete_one(self, excursion, city):
        with self.dbconn.conn:
            with self.dbconn.conn.cursor() as cur:
                cur.execute("SELECT excursion FROM " + ExcursionCityTable().table_name() +
                            " WHERE excursion = %s AND city = %s", (excursion, city))
                if cur.fetchone() is None:
                    raise ValueError("Экскурсия не связана с выбранным городом. Обновите список!")
                cur.execute("DELETE FROM " + ExcursionCityTable().table_name() +
                            " WHERE excursion = %s", (excursion,))
                cur.execute("DELETE FROM " + self.table_name() + " WHERE id = %s", (excursion,))
