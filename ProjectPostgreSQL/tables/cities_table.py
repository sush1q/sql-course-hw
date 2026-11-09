from dbtable import DbTable
from tables.excursion_city_table import ExcursionCityTable


class CitiesTable(DbTable):
    def table_name(self):
        return self.dbconn.prefix + "cities"

    def columns(self):
        return {"name": ["text", "PRIMARY KEY"]}

    def primary_key(self):
        return ["name"]

    @staticmethod
    def validate_name(name):
        if not isinstance(name, str) or not name.strip() or '\x00' in name:
            raise ValueError("Введите непустое название города без нулевых символов!")
        return name.strip()

    def find_by_name(self, name):
        rows = self.select("name", "WHERE name = %s", (name,))
        return rows[0] if rows else None

    def insert_one(self, vals):
        if len(vals) != 1:
            raise ValueError("Для города необходимо указать одно название!")
        self.insert([self.validate_name(vals[0])])

    def update_one(self, old_name, new_name):
        new_name = self.validate_name(new_name)
        table = self.table_name()
        with self.dbconn.conn, self.dbconn.conn.cursor() as cur:
            cur.execute(f"SELECT 1 FROM {table} WHERE name = %s", (old_name,))
            if cur.fetchone() is None:
                raise ValueError("Город не найден. Обновите список!")
            if old_name == new_name:
                return False

            cur.execute(*self.insert_query([new_name]))
            links = ExcursionCityTable().table_name()
            cur.execute(f"UPDATE {links} SET city = %s WHERE city = %s", (new_name, old_name))
            cur.execute(f"DELETE FROM {table} WHERE name = %s", (old_name,))
            if cur.rowcount == 0:
                raise ValueError("Город не найден. Обновите список!")
        return True

    def delete_one(self, name):
        with self.dbconn.conn, self.dbconn.conn.cursor() as cur:
            links = ExcursionCityTable().table_name()
            cur.execute(f"DELETE FROM {links} WHERE city = %s", (name,))
            cur.execute(f"DELETE FROM {self.table_name()} WHERE name = %s", (name,))
            if cur.rowcount == 0:
                raise ValueError("Город не найден. Обновите список!")
