from psycopg2 import sql

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
