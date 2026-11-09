from decimal import Decimal, InvalidOperation

from dbtable import DbTable
from tables.excursion_city_table import ExcursionCityTable


class ExcursionsTable(DbTable):
    fields = "id, name, description, cost"
    sort_order = "name, id"
    missing_link = "Экскурсия не связана с выбранным городом. Обновите список!"

    def table_name(self):
        return self.dbconn.prefix + "excursions"

    def columns(self):
        return {"id": ["integer", "PRIMARY KEY"],
                "name": ["text", "NOT NULL"],
                "description": ["text"],
                "cost": ["numeric(10,2)", "NOT NULL", "CHECK(cost > 0)"]}

    def _city_filter(self, city):
        if city is None:
            return "", ()
        links = ExcursionCityTable().table_name()
        return f"WHERE id IN (SELECT excursion FROM {links} WHERE city = %s)", (city,)

    def all(self):
        return self.list_rows()

    def all_by_city(self, city):
        return [] if city is None else self.list_rows(*self._city_filter(city))

    def count(self, city=None):
        return super().count(*self._city_filter(city))

    def page(self, page, page_size, city=None):
        return super().page(page, page_size, *self._city_filter(city))

    @staticmethod
    def validate_name(name):
        if not isinstance(name, str) or not name.strip() or '\x00' in name:
            raise ValueError("Введите непустое название экскурсии без нулевых символов!")
        return name.strip()

    @staticmethod
    def validate_description(value):
        if value is not None and (not isinstance(value, str) or '\x00' in value):
            raise ValueError("Описание должно быть текстом без нулевых символов!")
        return value

    @staticmethod
    def validate_cost(value):
        try:
            cost = Decimal(str(value).replace(',', '.'))
            if not 0 < cost <= Decimal('99999999.99'):
                raise ValueError("Стоимость должна быть больше нуля и не больше 99999999.99!")
        except InvalidOperation:
            raise ValueError("Стоимость должна быть числом!") from None
        if cost != cost.quantize(Decimal('0.01')):
            raise ValueError("Укажите стоимость с точностью до копеек!")
        return cost

    def validate_values(self, vals):
        if len(vals) != 3:
            raise ValueError("Нужны название, описание и стоимость экскурсии!")
        name, description, cost = vals
        return self.validate_name(name), self.validate_description(description), self.validate_cost(cost)

    def insert_one(self, vals, city=None):
        data = self.validate_values(vals)
        with self.dbconn.conn:
            with self.dbconn.conn.cursor() as cur:
                cur.execute(f"SELECT COALESCE(MAX(id)::bigint, 0) + 1 FROM {self.table_name()}")
                excursion = cur.fetchone()[0]
                if excursion > 2147483647:
                    raise ValueError("Невозможно создать экскурсию: исчерпан диапазон ключей.")
                columns = ("id", "name", "description", "cost")
                cur.execute(*self.insert_query((excursion, *data), columns=columns))
                if city is not None:
                    cur.execute(*ExcursionCityTable().insert_query([city, excursion]))
        return excursion

    def update_one(self, excursion, city, vals):
        data = self.validate_values(vals)
        links = ExcursionCityTable().table_name()
        with self.dbconn.conn:
            with self.dbconn.conn.cursor() as cur:
                cur.execute(
                    f"UPDATE {self.table_name()} SET name = %s, description = %s, cost = %s "
                    f"WHERE id = %s AND id IN (SELECT excursion FROM {links} WHERE city = %s)",
                    (*data, excursion, city),
                )
                if cur.rowcount == 0:
                    raise ValueError(self.missing_link)

    def cities_by_excursion(self, excursion):
        return ExcursionCityTable().select("city", "WHERE excursion = %s ORDER BY city", (excursion,))

    def delete_one(self, excursion, city):
        links = ExcursionCityTable().table_name()
        with self.dbconn.conn:
            with self.dbconn.conn.cursor() as cur:
                cur.execute(f"SELECT 1 FROM {links} WHERE excursion = %s AND city = %s", (excursion, city))
                if cur.fetchone() is None:
                    raise ValueError(self.missing_link)
                cur.execute(f"DELETE FROM {links} WHERE excursion = %s", (excursion,))
                cur.execute(f"DELETE FROM {self.table_name()} WHERE id = %s", (excursion,))
                if cur.rowcount == 0:
                    raise ValueError(self.missing_link)
