import shlex
import sys

import psycopg2
import yaml
from psycopg2 import sql

from dbconnection import DbConnection
from dbtable import DbTable
from project_config import ProjectConfig
from tables.cities_table import CitiesTable
from tables.excursion_city_table import ExcursionCityTable
from tables.excursions_table import ExcursionsTable


class InputCancelled(Exception):
    pass


class Menu:
    page_size = 5

    @staticmethod
    def read_next_step(prompt="=> "):
        try:
            tokens = shlex.split(input(prompt).strip())
        except ValueError:
            return ""
        return tokens[0].lower() if len(tokens) == 1 else ""

    def last_page(self, count):
        return max(0, (count - 1) // self.page_size)

    def load_page(self, table, page, *filters):
        count = table.count(*filters)
        last = self.last_page(count)
        page = min(page, last)
        rows = table.page(page, self.page_size, *filters)
        print(f"Страница {page + 1} из {last + 1}")
        if not rows:
            print("Список пуст.")
        return page, count, rows

    def move_page(self, page, count, step):
        target = page + (1 if step == "n" else -1)
        if 0 <= target <= self.last_page(count):
            return target
        print("Следующей страницы нет." if step == "n" else "Предыдущей страницы нет.")
        return page

    @staticmethod
    def row_at(rows, value):
        try:
            number = int(value)
        except ValueError:
            raise ValueError("Введите целый номер строки.") from None
        if not 0 <= number <= len(rows):
            raise ValueError("На этой странице такой строки нет.")
        return rows[number - 1] if number else None

    def choose_row(self, rows, prompt):
        if not rows:
            print("Список пуст.")
            return None
        while True:
            try:
                return self.row_at(rows, self.read_next_step(f"{prompt} (0 - отмена): "))
            except ValueError as error:
                print(error)

    @staticmethod
    def read_field(prompt, validate, default="", *, clear=False):
        while True:
            value = input(f"{prompt} (/отмена - вернуться): ").strip()
            if value == "/отмена":
                raise InputCancelled
            if clear and value == "/очистить":
                value = None
            elif not value:
                value = default
            try:
                return validate(value)
            except ValueError as error:
                print(error)

    @staticmethod
    def confirm(prompt):
        while True:
            answer = input(f"{prompt} (да/нет): ").strip().lower()
            if answer in ("да", "д"):
                return True
            if answer in ("нет", "н", ""):
                return False
            print("Введите «да» или «нет».")

    @staticmethod
    def show_db_error(error):
        messages = {
            psycopg2.errors.UniqueViolation: "Запись с такими значениями уже существует.",
            psycopg2.errors.ForeignKeyViolation: "Операция нарушает связь между записями.",
            psycopg2.errors.DependentObjectsStillExist: "Удаление заблокировано зависимыми объектами базы.",
            psycopg2.errors.UndefinedTable: "Таблица не найдена. Выполните инициализацию в главном меню или проверьте префикс таблиц.",
            psycopg2.errors.InsufficientPrivilege: "Недостаточно прав для этой операции.",
        }
        print(messages.get(type(error), "Не удалось выполнить запрос к базе данных."))


class CitiesMenu(Menu):
    def __init__(self, cities, excursions_menu):
        self.cities = cities
        self.excursions_menu = excursions_menu
        self.city_page = 0
        self.city_count = 0
        self.city_rows = []

    def run(self):
        self.city_page = 0
        while True:
            self.show_cities()
            try:
                destination = self.after_show_cities(self.read_next_step())
            except psycopg2.Error as error:
                self.show_db_error(error)
            except ValueError as error:
                print(error)
            else:
                if destination != "1":
                    return destination

    def show_cities(self):
        self.city_count = 0
        self.city_rows = []
        print("Города:\n№\tНазвание")
        try:
            self.city_page, self.city_count, self.city_rows = self.load_page(self.cities, self.city_page)
        except psycopg2.Error as error:
            self.show_db_error(error)
        for number, (name,) in enumerate(self.city_rows, 1):
            print(f"{number}\t{name}")
        print("""    0 - главное меню
    3 - добавление города
    4 - удаление города
    5 - экскурсии города
    8 - переименование города
    n / p - следующая / предыдущая страница
    9 - выход""")

    def after_show_cities(self, step):
        if step in ("0", "1", "9"):
            return step
        if step in ("n", "p"):
            self.city_page = self.move_page(self.city_page, self.city_count, step)
        elif step == "3":
            self.show_add_city()
        elif step == "4":
            self.show_delete_city()
        elif step == "8":
            self.show_edit_city()
        elif step == "5":
            city = self.choose_city()
            if city is not None:
                return self.excursions_menu.run(city)
        else:
            print("Выберите команду из меню.")
        return "1"

    def read_city_name(self, prompt):
        try:
            return self.read_field(prompt, self.cities.validate_name)
        except InputCancelled:
            return None

    def choose_city(self):
        row = self.choose_row(self.city_rows, "Номер строки города")
        return row[0] if row is not None else None

    def show_add_city(self):
        name = self.read_city_name("Название города")
        if name is None:
            return
        try:
            self.cities.insert_one([name])
            print(f"Город «{name}» добавлен.")
        except psycopg2.errors.UniqueViolation:
            print("Город с таким названием уже существует. Добавление отменено.")

    def show_edit_city(self):
        name = self.choose_city()
        if name is None:
            return
        new_name = self.read_city_name(f"Новое название города «{name}»")
        if new_name is not None:
            changed = self.cities.update_one(name, new_name)
            print("Город переименован." if changed else "Название осталось прежним.")

    def show_delete_city(self):
        name = self.choose_city()
        if name is not None and self.confirm(f"Удалить город «{name}» и его связи с экскурсиями?"):
            self.cities.delete_one(name)
            print("Город удалён. Экскурсии сохранены.")


class ExcursionsMenu(Menu):
    def __init__(self, cities, excursions, links):
        self.cities = cities
        self.excursions = excursions
        self.links = links
        self.city_name = None
        self.excursion_page = 0
        self.excursion_rows = []

    def run(self, city):
        self.city_name = city
        self.excursion_page = 0
        actions = {
            "6": self.show_add_excursion,
            "7": self.show_delete_excursion,
            "10": self.show_attach_excursion,
            "11": self.show_edit_excursion,
        }
        while True:
            step = self.show_excursions_by_city()
            if step in actions:
                actions[step]()
            elif step != "5":
                return step

    def show_excursions_by_city(self):
        if self.city_name is None:
            return "1"
        if self.cities.find_by_name(self.city_name) is None:
            print("Выбранный город не существует. Обновите список.")
            return "1"

        print(f"Экскурсии города «{self.city_name}»")
        self.excursion_page, count, self.excursion_rows = self.show_excursion_page(
            self.excursion_page, self.city_name
        )
        print("""    0 - главное меню
    1 - список городов
    6 - создание экскурсии
    7 - удаление экскурсии
    10 - добавление существующей экскурсии в город
    11 - изменение экскурсии
    n / p - следующая / предыдущая страница
    9 - выход""")
        while True:
            step = self.read_next_step()
            if step in ("0", "1", "6", "7", "9", "10", "11"):
                return step
            if step in ("n", "p"):
                page = self.move_page(self.excursion_page, count, step)
                if page != self.excursion_page:
                    self.excursion_page = page
                    return "5"
            else:
                print("Выберите команду из меню.")

    def show_excursion_page(self, page, *filters):
        print("№\tНазвание\tСтоимость, руб.\tОписание")
        page, count, rows = self.load_page(self.excursions, page, *filters)
        for number, (_, name, description, cost) in enumerate(rows, 1):
            print(f"{number}\t{name}\t{cost:.2f}\t{description or '—'}")
        return page, count, rows

    def read_excursion_data(self, current=None):
        if current is None:
            name = ""
            description = None
            cost = ""
        else:
            name, description, cost = current
            print("Enter сохраняет прежнее значение. /очистить удаляет описание.")
        try:
            name = self.read_field("Название экскурсии", self.excursions.validate_name, name)
            description = self.read_field("Описание", self.excursions.validate_description, description, clear=True)
            cost = self.read_field("Стоимость в рублях", self.excursions.validate_cost, cost)
        except InputCancelled:
            return None
        return [name, description, cost]

    def show_add_excursion(self):
        data = self.read_excursion_data()
        if data is None:
            return
        try:
            self.excursions.insert_one(data, self.city_name)
            print("Экскурсия создана и добавлена в выбранный город.")
        except psycopg2.errors.UniqueViolation:
            print("Возник конфликт при добавлении экскурсии. Повторите ввод.")

    def choose_excursion(self, rows):
        return self.choose_row(rows, "Номер строки экскурсии")

    def show_edit_excursion(self):
        row = self.choose_excursion(self.excursion_rows)
        if row is not None:
            self.show_excursion_details(row)
            print("Изменения применятся во всех связанных городах.")
            data = self.read_excursion_data(row[1:])
            if data is not None:
                self.excursions.update_one(row[0], self.city_name, data)
                print("Экскурсия обновлена.")

    def show_delete_excursion(self):
        row = self.choose_excursion(self.excursion_rows)
        if row is not None:
            self.show_excursion_details(row)
            if self.confirm(f"Удалить экскурсию «{row[1]}» и все её связи?"):
                self.excursions.delete_one(row[0], self.city_name)
                print("Экскурсия удалена.")

    def show_excursion_details(self, row):
        excursion, name, description, cost = row
        print(f"«{name}», {cost:.2f} руб. Описание: {description or '—'}")
        cities = self.excursions.cities_by_excursion(excursion)
        print("Связанные города: " + ", ".join(city for city, in cities))

    def show_attach_excursion(self):
        page = 0
        while True:
            page, count, rows = self.show_excursion_page(page)
            if not rows:
                return
            step = self.read_next_step("Номер строки (n / p - страницы, 0 - отмена): ")
            if step in ("n", "p"):
                page = self.move_page(page, count, step)
                continue
            try:
                row = self.row_at(rows, step)
            except ValueError as error:
                print(error)
                continue
            if row is not None:
                try:
                    self.links.insert_one([self.city_name, row[0]])
                    print("Экскурсия добавлена в выбранный город.")
                except psycopg2.errors.UniqueViolation:
                    print("Экскурсия уже добавлена в выбранный город.")
            return


class Main(Menu):
    connection = None

    def __init__(self):
        if self.connection is None:
            self.connection = DbConnection(ProjectConfig())
        DbTable.dbconn = self.connection
        self.cities = CitiesTable()
        self.excursions = ExcursionsTable()
        self.links = ExcursionCityTable()
        self.excursions_menu = ExcursionsMenu(self.cities, self.excursions, self.links)
        self.cities_menu = CitiesMenu(self.cities, self.excursions_menu)

    def show_main_menu(self):
        print("""Добро пожаловать!
    1 - просмотр городов
    2 - сброс и инициализация таблиц
    9 - выход""")

    def sample_data(self):
        cities = (
            ("Токио",), ("Киото",), ("Осака",), ("Нара",), ("Ито",),
        )
        excursions = (
            (1, "Обзорная экскурсия по Токио", "Посещение Асакусы, Сибуи и Синдзюку.", "8500.00"),
            (2, "Храмы Киото", "Экскурсия по известным храмам и историческим районам Киото.", "9000.00"),
            (3, "Замок Осака", "Посещение замка Осака и прогулка по центральной части города.", "7000.00"),
            (4, "Историческая Нара", "Посещение парка Нара и храма Тодай-дзи.", "7500.00"),
            (5, "Традиционная Япония", "Знакомство с традиционной японской архитектурой и культурой.", "8000.00"),
        )
        links = (
            (1, "Токио"), (2, "Киото"), (3, "Осака"), (4, "Нара"),
            (5, "Киото"), (5, "Нара"), (5, "Ито"),
        )
        return (
            (self.cities, ("name",), cities),
            (self.excursions, ("id", "name", "description", "cost"), excursions),
            (self.links, ("excursion", "city"), links),
        )

    def reset_tables(self):
        if not self.confirm("Удалить данные городов и экскурсий и заполнить примерами?"):
            return

        data = self.sample_data()
        with self.connection.conn:
            with self.connection.conn.cursor() as cur:
                cur.execute("SELECT pg_catalog.parse_ident(%s)", (self.cities.table_name(),))
                name_parts = cur.fetchone()[0]
                if len(name_parts) == 2:
                    schema = name_parts[0]
                    cur.execute("SELECT 1 FROM pg_catalog.pg_namespace WHERE nspname = %s", (schema,))
                    if cur.fetchone() is None:
                        cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema)))

                for table, _, _ in reversed(data):
                    cur.execute(table.drop_query())
                for table, columns, rows in data:
                    cur.execute(table.create_query())
                    for row in rows:
                        cur.execute(*table.insert_query(row, columns=columns))

        print("Таблицы созданы заново!")

    def main_cycle(self):
        while True:
            self.show_main_menu()
            step = self.read_next_step()
            if step == "9":
                break
            try:
                if step == "1":
                    destination = self.cities_menu.run()
                    if destination == "9":
                        break
                elif step == "2":
                    self.reset_tables()
                else:
                    print("Выберите команду из меню.")
            except psycopg2.Error as error:
                self.show_db_error(error)
            except ValueError as error:
                print(error)
        print("До свидания!")

    def test(self):
        DbTable.dbconn.test()


if __name__ == "__main__":
    app = None
    try:
        app = Main()
        app.main_cycle()
    except (EOFError, KeyboardInterrupt):
        print("\nРабота программы завершена.")
    except psycopg2.Error:
        print("Не удалось подключиться к БД. Проверьте сервер и config.yaml.")
        sys.exit(1)
    except (OSError, KeyError, TypeError, yaml.YAMLError):
        print("Не удалось прочитать настройки подключения. Проверьте config.yaml.")
        sys.exit(1)
    finally:
        if app is not None:
            app.connection.conn.close()
