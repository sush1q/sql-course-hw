import sys

from project_config import *
from dbconnection import *
from tables.cities_table import *
from tables.excursions_table import *
from tables.excursion_city_table import *


class Main:

    config = ProjectConfig()
    connection = DbConnection(config)
    page_size = 5
    city_page = 0
    excursion_page = 0

    def __init__(self):
        DbTable.dbconn = self.connection
        return

    def db_init(self):
        ct = CitiesTable()
        et = ExcursionsTable()
        ect = ExcursionCityTable()
        ct.create()
        et.create()
        ect.create()
        return

    def db_insert_somethings(self):
        ct = CitiesTable()
        et = ExcursionsTable()
        ect = ExcursionCityTable()
        ct.insert_one(["Токио"])
        ct.insert_one(["Киото"])
        ct.insert_one(["Осака"])
        excursion = et.insert_one(["Обзорная экскурсия по Токио", "Знакомство с городом.", "8500.00"])
        ect.insert_one(["Токио", excursion])
        return

    def db_drop(self):
        ect = ExcursionCityTable()
        et = ExcursionsTable()
        ct = CitiesTable()
        with self.connection.conn:
            ect.drop()
            et.drop()
            ct.drop()
        return

    def show_main_menu(self):
        menu = """Добро пожаловать! 
Основное меню (выберите цифру в соответствии с необходимым действием): 
    1 - просмотр городов;
    2 - сброс и инициализация таблиц;
    9 - выход."""
        print(menu)
        return

    def read_next_step(self):
        return input("=> ").strip()

    def after_main_menu(self, next_step):
        if next_step == "2":
            answer = input("Удалить данные городов и экскурсий и заполнить примерами? (да/нет): ").strip().lower()
            if answer != "да":
                print("Сброс отменён.")
                return "0"
            try:
                self.db_drop()
                self.db_init()
                self.db_insert_somethings()
                print("Таблицы созданы заново!")
            except psycopg2.Error as error:
                self.show_db_error(error)
                print("Сброс и инициализация не завершены.")
            return "0"
        elif next_step != "1" and next_step != "9":
            print("Выбрано неверное число! Повторите ввод!")
            return "0"
        else:
            if next_step == "1":
                self.city_page = 0
            return next_step

    def show_cities(self):
        print("Просмотр списка городов!\n№\tНазвание")
        self.city_name = None
        self.excursion_page = 0
        self.excursion_rows = []
        self.city_rows = None
        self.city_count = 0
        try:
            self.city_count = CitiesTable().count()
            last_page = max(0, (self.city_count - 1) // self.page_size)
            self.city_page = min(self.city_page, last_page)
            self.city_rows = CitiesTable().page(self.city_page, self.page_size)
        except psycopg2.Error as error:
            self.show_db_error(error)
        if self.city_rows is not None:
            for number, city in enumerate(self.city_rows, start=1):
                print(str(number) + "\t" + city[0])
            if not self.city_rows:
                print("Городов пока нет.")
            print(f"Страница {self.city_page + 1} из {last_page + 1}")
        menu = """Дальнейшие операции:
    0 - возврат в главное меню;
    3 - добавление нового города;
    4 - удаление города;
    5 - просмотр экскурсий города;
    8 - переименование города;
    n - следующая страница;
    p - предыдущая страница;
    9 - выход."""
        print(menu)

    def after_show_cities(self, next_step):
        next_step = next_step.lower()
        while True:
            try:
                if next_step == "n":
                    if (self.city_page + 1) * self.page_size < self.city_count:
                        self.city_page += 1
                    else:
                        print("Следующей страницы нет.")
                    return "1"
                elif next_step == "p":
                    if self.city_page > 0:
                        self.city_page -= 1
                    else:
                        print("Предыдущей страницы нет.")
                    return "1"
                elif next_step == "4":
                    self.show_delete_city()
                    return "1"
                elif next_step == "8":
                    self.show_edit_city()
                    return "1"
                elif next_step in ("6", "7", "10", "11"):
                    if self.city_name is None:
                        print("Сначала выберите город!")
                    elif next_step == "6":
                        self.show_add_excursion()
                    elif next_step == "7":
                        self.show_delete_excursion()
                    elif next_step == "10":
                        self.show_attach_excursion()
                    else:
                        self.show_edit_excursion()
                    next_step = "5"
                elif next_step == "5":
                    next_step = self.show_excursions_by_city()
                elif next_step not in ("0", "1", "9", "3"):
                    print("Выбрано неверное число! Повторите ввод!")
                    return "1"
                else:
                    return next_step
            except psycopg2.Error as error:
                self.show_db_error(error)
                return "1"
            except ValueError as error:
                print(error)
                return "1"

    def show_add_city(self):
        name = self.read_city_name("Введите название города")
        if name is not None:
            try:
                CitiesTable().insert_one([name])
                print("Город «" + name + "» добавлен!")
            except psycopg2.errors.UniqueViolation:
                print("Город с таким названием уже существует! Добавление отменено.")
            except psycopg2.Error as error:
                self.show_db_error(error)

    def show_excursions_by_city(self):
        if self.city_name is None:
            self.city_name = self.choose_city()
        if self.city_name is None:
            return '1'
        if CitiesTable().find_by_name(self.city_name) is None:
            print("Выбранный город не существует. Обновите список!")
            self.city_name = None
            return '1'
        print("Выбран город: " + self.city_name)
        print("Экскурсии:\n№\tНазвание\tСтоимость, руб.\tОписание")
        self.excursion_count = ExcursionsTable().count(self.city_name)
        last_page = max(0, (self.excursion_count - 1) // self.page_size)
        self.excursion_page = min(self.excursion_page, last_page)
        self.excursion_rows = ExcursionsTable().page(self.excursion_page, self.page_size, self.city_name)
        for number, excursion in enumerate(self.excursion_rows, start=1):
            excursion_id, title, description, cost = excursion
            print(f"{number}\t{title}\t{cost:.2f}\t{description or '—'}")
        if not self.excursion_rows:
            print("Для этого города экскурсий пока нет.")
        print(f"Страница {self.excursion_page + 1} из {last_page + 1}")
        menu = """Дальнейшие операции:
    0 - возврат в главное меню;
    1 - возврат в просмотр городов;
    6 - создание экскурсии в этом городе;
    7 - удаление экскурсии целиком;
    10 - добавление существующей экскурсии в этот город;
    11 - изменение экскурсии;
    n - следующая страница;
    p - предыдущая страница;
    9 - выход."""
        print(menu)
        while True:
            next_step = self.read_next_step().lower()
            if next_step == 'n':
                if (self.excursion_page + 1) * self.page_size < self.excursion_count:
                    self.excursion_page += 1
                    return '5'
                print("Следующей страницы нет.")
            elif next_step == 'p':
                if self.excursion_page > 0:
                    self.excursion_page -= 1
                    return '5'
                print("Предыдущей страницы нет.")
            elif next_step in ('0', '1', '6', '7', '10', '11', '9'):
                return next_step
            else:
                print("Выбрано неверное число! Повторите ввод!")

    def show_add_excursion(self):
        data = self.read_excursion_data()
        if data is None:
            return
        try:
            ExcursionsTable().insert_one(data, self.city_name)
            print("Экскурсия создана и добавлена в выбранный город!")
        except psycopg2.errors.ForeignKeyViolation:
            print("Выбранный город больше не существует. Создание экскурсии отменено.")

    def read_excursion_data(self, current=None):
        if current is not None:
            print("Пустой ввод сохраняет прежнее значение. /отмена - вернуться.")
        while True:
            title = input("Название экскурсии (/отмена - вернуться): ").strip()
            if title == '/отмена':
                return None
            if not title and current is not None:
                title = current[0]
            if not title or '\x00' in title:
                print("Введите непустое название без нулевых символов!")
            else:
                break
        description_prompt = ("Описание (/очистить - удалить, Enter - сохранить, /отмена - вернуться): "
                              if current is not None else
                              "Описание, можно оставить пустым (/отмена - вернуться): ")
        while True:
            description = input(description_prompt).strip()
            if description == '/отмена':
                return None
            if description == '/очистить':
                description = None
            elif not description and current is not None:
                description = current[1]
            if description is not None and '\x00' in description:
                print("Описание содержит недопустимый нулевой символ!")
            else:
                break
        while True:
            value = input("Стоимость в рублях (/отмена - вернуться): ").strip()
            if value == '/отмена':
                return None
            if not value and current is not None:
                value = current[2]
            try:
                cost = ExcursionsTable.validate_cost(value)
                break
            except ValueError as error:
                print(error)
        if not description and current is None:
            description = None
        return [title, description, cost]

    def show_edit_excursion(self):
        excursion = self.choose_excursion(self.excursion_rows)
        if excursion is None:
            return
        excursion_id, title, description, cost = excursion
        print(f"Выбрана экскурсия «{title}», стоимость {cost:.2f} руб.")
        print("Описание: " + (description or '—'))
        cities = ExcursionsTable().cities_by_excursion(excursion_id)
        print("Связанные города: " + ", ".join(city[0] for city in cities))
        print("Изменения этой экскурсии отразятся во всех связанных городах.")
        data = self.read_excursion_data(excursion[1:])
        if data is None:
            return
        ExcursionsTable().update_one(excursion_id, self.city_name, data)
        print("Данные экскурсии сохранены!")

    def choose_excursion(self, rows):
        if not rows:
            print("Список экскурсий пуст.")
            return None
        while True:
            value = input("Укажите номер строки экскурсии на текущей странице (0 - отмена): ").strip()
            try:
                number = int(value)
            except ValueError:
                print("Введите целый номер строки из показанного списка!")
                continue
            if number == 0:
                return None
            if 1 <= number <= len(rows):
                return rows[number - 1]
            print("Такого номера строки нет! Повторите ввод!")

    def show_attach_excursion(self):
        page = 0
        while True:
            count = ExcursionsTable().count()
            last_page = max(0, (count - 1) // self.page_size)
            page = min(page, last_page)
            rows = ExcursionsTable().page(page, self.page_size)
            print("Все экскурсии:\n№\tНазвание\tСтоимость, руб.\tОписание")
            for number, excursion in enumerate(rows, start=1):
                excursion_id, title, description, cost = excursion
                print(f"{number}\t{title}\t{cost:.2f}\t{description or '—'}")
            print(f"Страница {page + 1} из {last_page + 1}")
            if not rows:
                print("Список экскурсий пуст.")
                return
            value = input("Номер строки (n - далее, p - назад, 0 - отмена): ").strip().lower()
            if value == 'n':
                if page < last_page:
                    page += 1
                else:
                    print("Следующей страницы нет.")
                continue
            if value == 'p':
                if page > 0:
                    page -= 1
                else:
                    print("Предыдущей страницы нет.")
                continue
            try:
                number = int(value)
            except ValueError:
                print("Введите номер строки, n или p!")
                continue
            if number == 0:
                return
            if not 1 <= number <= len(rows):
                print("Такого номера строки нет!")
                continue
            try:
                ExcursionCityTable().insert_one([self.city_name, rows[number - 1][0]])
                print("Экскурсия добавлена в выбранный город!")
            except psycopg2.errors.UniqueViolation:
                print("Эта экскурсия уже добавлена в выбранный город.")
            except psycopg2.errors.ForeignKeyViolation:
                print("Город или экскурсия больше не существуют. Обновите список!")
            return

    def show_delete_excursion(self):
        excursion = self.choose_excursion(self.excursion_rows)
        if excursion is None:
            return
        excursion_id, title, description, cost = excursion
        cities = ExcursionsTable().cities_by_excursion(excursion_id)
        print(f"Будет удалена экскурсия «{title}», стоимость {cost:.2f} руб.")
        print("Описание: " + (description or '—'))
        print("Связанные города: " + (", ".join(city[0] for city in cities) or 'нет'))
        print("Экскурсия будет удалена целиком, включая связи со всеми городами.")
        while True:
            answer = input("Удалить экскурсию? (да/нет): ").strip().lower()
            if answer in ('да', 'д'):
                ExcursionsTable().delete_one(excursion_id, self.city_name)
                print("Экскурсия удалена!")
                return
            if answer in ('нет', 'н', ''):
                print("Удаление отменено.")
                return
            print("Введите «да» или «нет»!")

    def read_city_name(self, prompt):
        while True:
            name = input(prompt + " (/отмена - вернуться): ").strip()
            if name == '/отмена':
                return None
            try:
                return CitiesTable.validate_name(name)
            except ValueError as error:
                print(error)

    def choose_city(self):
        if self.city_rows is None:
            print("Список городов не загружен. Вернитесь к просмотру городов!")
            return None
        if not self.city_rows:
            print("Список городов пуст. Сначала добавьте город!")
            return None
        while True:
            value = input("Укажите номер строки города на текущей странице (0 - отмена): ").strip()
            try:
                number = int(value)
            except ValueError:
                print("Введите целый номер строки из показанного списка!")
                continue
            if number == 0:
                return None
            if 1 <= number <= len(self.city_rows):
                return self.city_rows[number - 1][0]
            print("Такого номера строки нет! Повторите ввод!")

    def show_edit_city(self):
        name = self.choose_city()
        if name is None:
            return
        print("Выбран город: " + name)
        new_name = self.read_city_name("Введите новое название")
        if new_name is None:
            return
        try:
            if CitiesTable().update_one(name, new_name):
                print("Город переименован! Связи с экскурсиями сохранены.")
            else:
                print("Название осталось прежним.")
        except psycopg2.errors.UniqueViolation:
            print("Город с таким названием уже существует! Переименование отменено.")
        except psycopg2.errors.ForeignKeyViolation:
            print("Нельзя переименовать город: он используется другими записями базы. "
                  "Название и связи сохранены.")

    def show_delete_city(self):
        name = self.choose_city()
        if name is None:
            return
        print("Будет удалён город «" + name + "» и его связи с экскурсиями. "
              "Сами экскурсии сохранятся. "
              "Если город используется другими данными базы, удаление будет отменено.")
        while True:
            answer = input("Удалить город? (да/нет): ").strip().lower()
            if answer in ('да', 'д'):
                try:
                    CitiesTable().delete_one(name)
                    print("Город удалён!")
                except psycopg2.errors.ForeignKeyViolation:
                    print("Нельзя удалить город: он используется другими записями базы. "
                          "Город и связи с экскурсиями сохранены.")
                return
            if answer in ('нет', 'н', ''):
                print("Удаление отменено.")
                return
            print("Введите «да» или «нет»!")

    def show_db_error(self, error):
        if isinstance(error, psycopg2.errors.UniqueViolation):
            print("Запись с такими уникальными значениями уже существует. Операция отменена.")
        elif isinstance(error, psycopg2.errors.ForeignKeyViolation):
            print("Операция нарушает связь между записями. Проверьте связанные данные.")
        elif isinstance(error, psycopg2.errors.DependentObjectsStillExist):
            print("Удалить объект нельзя: от него зависят другие объекты базы.")
        elif isinstance(error, psycopg2.errors.InsufficientPrivilege):
            print("У пользователя БД недостаточно прав для этой операции.")
        elif isinstance(error, (psycopg2.OperationalError, psycopg2.InterfaceError)):
            print("Не удалось выполнить операцию: соединение с БД недоступно. "
                  "Проверьте сервер и запустите программу снова.")
        elif isinstance(error, psycopg2.errors.UndefinedTable):
            print("Нужная таблица не найдена. Проверьте выбранную базу и префикс таблиц.")
        elif isinstance(error, psycopg2.IntegrityError):
            print("Операция нарушает ограничения данных. Изменения отменены.")
        else:
            print("Не удалось выполнить запрос к БД. Изменения отменены.")

    def main_cycle(self):
        current_menu = "0"
        next_step = None
        while(current_menu != "9"):
            if current_menu == "0":
                self.show_main_menu()
                next_step = self.read_next_step()
                current_menu = self.after_main_menu(next_step)
            elif current_menu == "1":
                self.show_cities()
                next_step = self.read_next_step()
                current_menu = self.after_show_cities(next_step)
            elif current_menu == "2":
                self.show_main_menu()
            elif current_menu == "3":
                self.show_add_city()
                current_menu = "1"
        print("До свидания!")    
        return

    def test(self):
        DbTable.dbconn.test()

if __name__ == '__main__':
    m = None
    try:
        m = Main()
        m.main_cycle()
    except (EOFError, KeyboardInterrupt):
        print("\nРабота программы завершена.")
    except psycopg2.Error:
        print("Не удалось подключиться к БД. Проверьте сервер и config.yaml.")
        sys.exit(1)
    except (OSError, KeyError, TypeError, yaml.YAMLError):
        print("Не удалось прочитать настройки подключения. Проверьте config.yaml.")
        sys.exit(1)
    finally:
        if m is not None:
            m.connection.conn.close()
