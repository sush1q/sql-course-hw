# Базовые действия с таблицами

from dbconnection import *

class DbTable:
    dbconn = None

    def __init__(self):
        return

    def table_name(self):
        return self.dbconn.prefix + "table"

    def columns(self):
        return {"test": ["integer", "PRIMARY KEY"]}

    def column_names(self):
        return sorted(self.columns().keys(), key = lambda x: x)

    def primary_key(self):
        return ['id']

    def column_names_without_id(self):
        res = sorted(self.columns().keys(), key = lambda x: x)
        if 'id' in res:
            res.remove('id')
        return res

    def table_constraints(self):
        return []

    def create(self):
        sql = "CREATE TABLE " + self.table_name() + "("
        arr = [k + " " + " ".join(v) for k, v in sorted(self.columns().items(), key = lambda x: x[0])]
        sql += ", ".join(arr + self.table_constraints())
        sql += ")"
        cur = self.dbconn.conn.cursor()
        cur.execute(sql)
        self.dbconn.conn.commit()
        return

    def drop(self):
        sql = "DROP TABLE IF EXISTS " + self.table_name()
        cur = self.dbconn.conn.cursor()
        cur.execute(sql)
        self.dbconn.conn.commit()
        return

    def insert_one(self, vals):
        for i in range(0, len(vals)):
            if type(vals[i]) == str:
                vals[i] = "'" + vals[i] + "'"
            else:
                vals[i] = str(vals[i])
        sql = "INSERT INTO " + self.table_name() + "("
        sql += ", ".join(self.column_names_without_id()) + ") VALUES("
        sql += ", ".join(vals) + ")"
        cur = self.dbconn.conn.cursor()
        cur.execute(sql)
        self.dbconn.conn.commit()
        return

    def first(self):
        sql = "SELECT * FROM " + self.table_name()
        sql += " ORDER BY "
        sql += ", ".join(self.primary_key())
        cur = self.dbconn.conn.cursor()
        cur.execute(sql)
        return cur.fetchone()        

    def last(self):
        sql = "SELECT * FROM " + self.table_name()
        sql += " ORDER BY "
        sql += ", ".join([x + " DESC" for x in self.primary_key()])
        cur = self.dbconn.conn.cursor()
        cur.execute(sql)
        return cur.fetchone()

    def all(self):
        sql = "SELECT * FROM " + self.table_name()
        sql += " ORDER BY "
        sql += ", ".join(self.primary_key())
        cur = self.dbconn.conn.cursor()
        cur.execute(sql)
        return cur.fetchall()        

    fields = "*"
    sort_order = None

    def insert_query(self, vals, *, columns=None):
        columns = self.column_names_without_id() if columns is None else columns
        if len(vals) != len(columns):
            raise ValueError("Количество значений должно совпадать с количеством столбцов!")
        placeholders = ", ".join(["%s"] * len(columns))
        query = f"INSERT INTO {self.table_name()} ({', '.join(columns)}) VALUES ({placeholders})"
        return query, tuple(vals)

    def insert(self, vals):
        cur = self.dbconn.conn.cursor()
        with self.dbconn.conn as cur:
            cur.execute(*self.insert_query(vals))

    def select(self, fields="*", clause="", params=None):
        """Столбцы и части запроса задаются в коде, значения передаются отдельно."""
        cur = self.dbconn.conn.cursor()
        with self.dbconn.conn as cur:
            cur.execute(f"SELECT {fields} FROM {self.table_name()} {clause}", params)
            return cur.fetchall()

    def list_rows(self, where="", params=(), *, page=None):
        order = self.sort_order or ", ".join(self.primary_key())
        clause = f"{where} ORDER BY {order}"
        if page is not None:
            index, size = page
            if index < 0 or size < 1:
                raise ValueError("Некорректный номер или размер страницы!")
            clause += " LIMIT %s OFFSET %s"
            params += (size, index * size)
        return self.select(self.fields, clause, params)

    def count(self, where="", params=()):
        return self.select("COUNT(*)", where, params)[0][0]

    def page(self, page, page_size, where="", params=()):
        return self.list_rows(where, params, page=(page, page_size))
