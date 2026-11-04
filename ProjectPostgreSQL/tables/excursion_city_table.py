from dbtable import DbTable


class ExcursionCityTable(DbTable):
    def table_name(self):
        return self.dbconn.prefix + "excursion_city"

    def columns(self):
        return {"excursion": ["integer"], "city": ["text"]}

    def primary_key(self):
        return ['excursion', 'city']

    def table_constraints(self):
        from tables.cities_table import CitiesTable
        from tables.excursions_table import ExcursionsTable
        return ["PRIMARY KEY(excursion, city)",
                "FOREIGN KEY(excursion) REFERENCES " + ExcursionsTable().table_name() + "(id)",
                "FOREIGN KEY(city) REFERENCES " + CitiesTable().table_name() + "(name)"]

    def insert_one(self, vals):
        if len(vals) != 2:
            raise ValueError("Нужно указать город и экскурсию!")
        city, excursion = vals
        with self.dbconn.conn:
            with self.dbconn.conn.cursor() as cur:
                cur.execute("INSERT INTO " + self.table_name() + " (city, excursion) VALUES (%s, %s)",
                            (city, excursion))
