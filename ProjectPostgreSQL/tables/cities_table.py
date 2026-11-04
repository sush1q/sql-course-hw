from dbtable import DbTable
from tables.excursion_city_table import ExcursionCityTable


class CitiesTable(DbTable):
    def table_name(self):
        return self.dbconn.prefix + "cities"

    def columns(self):
        return {"name": ["text", "PRIMARY KEY"]}

    def primary_key(self):
        return ['name']

    def all(self):
        with self.dbconn.conn:
            with self.dbconn.conn.cursor() as cur:
                cur.execute("SELECT name FROM " + self.table_name() + " ORDER BY name")
                return cur.fetchall()

    @staticmethod
    def validate_name(name):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Название города не может быть пустым!")
        if '\x00' in name:
            raise ValueError("Название содержит недопустимый нулевой символ!")
        return name.strip()

    def insert_one(self, vals):
        if len(vals) != 1:
            raise ValueError("Для города необходимо указать одно название!")
        name = self.validate_name(vals[0])
        with self.dbconn.conn:
            with self.dbconn.conn.cursor() as cur:
                cur.execute("INSERT INTO " + self.table_name() + " (name) VALUES (%s)", (name,))

    def update_one(self, old_name, new_name):
        new_name = self.validate_name(new_name)
        with self.dbconn.conn:
            with self.dbconn.conn.cursor() as cur:
                cur.execute("SELECT name FROM " + self.table_name() +
                            " WHERE name = %s", (old_name,))
                if cur.fetchone() is None:
                    raise ValueError("Город не найден. Обновите список!")
                if old_name == new_name:
                    return False
                cur.execute("INSERT INTO " + self.table_name() + " (name) VALUES (%s)", (new_name,))
                cur.execute("UPDATE " + ExcursionCityTable().table_name() +
                            " SET city = %s WHERE city = %s", (new_name, old_name))
                cur.execute("DELETE FROM " + self.table_name() + " WHERE name = %s", (old_name,))
        return True

    def delete_one(self, name):
        with self.dbconn.conn:
            with self.dbconn.conn.cursor() as cur:
                cur.execute("SELECT name FROM " + self.table_name() +
                            " WHERE name = %s", (name,))
                if cur.fetchone() is None:
                    raise ValueError("Город не найден. Обновите список!")
                cur.execute("DELETE FROM " + ExcursionCityTable().table_name() +
                            " WHERE city = %s", (name,))
                cur.execute("DELETE FROM " + self.table_name() + " WHERE name = %s", (name,))
