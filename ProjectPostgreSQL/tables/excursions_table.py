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
        query = ("SELECT e.name, e.description, e.cost FROM " + self.table_name() +
                 " AS e JOIN " + ExcursionCityTable().table_name() +
                 " AS ec ON ec.excursion = e.id WHERE ec.city = %s ORDER BY e.name, e.id")
        with self.dbconn.conn:
            with self.dbconn.conn.cursor() as cur:
                cur.execute(query, (city,))
                return cur.fetchall()

    def insert_one(self, vals):
        if len(vals) != 3:
            raise ValueError("Нужны название, описание и стоимость экскурсии!")
        name, description, cost = vals
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Название экскурсии не может быть пустым!")
        if not (description is None or isinstance(description, str)):
            raise ValueError("Описание должно быть текстом!")
        if '\x00' in name or description is not None and '\x00' in description:
            raise ValueError("Текст содержит недопустимый нулевой символ!")
        try:
            cost = Decimal(str(cost).replace(',', '.'))
        except InvalidOperation:
            raise ValueError("Стоимость должна быть числом!")
        if not cost.is_finite() or not Decimal('0') < cost <= Decimal('99999999.99'):
            raise ValueError("Стоимость должна быть больше нуля и не больше 99999999.99!")
        if cost != cost.quantize(Decimal('0.01')):
            raise ValueError("Укажите стоимость с точностью до копеек!")
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
        return excursion_id
