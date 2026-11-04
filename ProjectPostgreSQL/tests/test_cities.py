"""Проверки обязательных операций. Для SQL-тестов нужна отдельная база sql_course_test_…"""

from decimal import Decimal
from contextlib import redirect_stdout
from io import StringIO
import os
import runpy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

import psycopg2
from psycopg2 import sql

from dbtable import DbTable
# Эталонный main запускает меню при загрузке. Загружаем его с подменённым
# подключением и командой выхода, не меняя запуск программы ради тестов.
with patch('dbconnection.DbConnection', return_value=SimpleNamespace(conn=None, prefix='public.')):
    with patch('builtins.input', return_value='9'), redirect_stdout(StringIO()):
        Main = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'main.py'))['Main']
from tables.cities_table import CitiesTable
from tables.excursions_table import ExcursionsTable
from tables.excursion_city_table import ExcursionCityTable


class InputTests(unittest.TestCase):
    def setUp(self):
        self.previous = DbTable.dbconn
        self.previous_connection = Main.connection
        Main.connection = SimpleNamespace(conn=None)
        self.app = Main()
        self.app.city_rows = [('Киото',), ('Токио',)]

    def tearDown(self):
        DbTable.dbconn = self.previous
        Main.connection = self.previous_connection

    def test_selection_retries_invalid_input(self):
        with patch('builtins.input', side_effect=['', 'abc', '-1', '3', '1.5', '2']):
            with redirect_stdout(StringIO()):
                self.assertEqual(self.app.choose_city(), 'Токио')

    def test_selection_cancel_and_empty_list(self):
        with redirect_stdout(StringIO()):
            with patch('builtins.input', return_value='0'):
                self.assertIsNone(self.app.choose_city())
            self.app.city_rows = []
            self.assertIsNone(self.app.choose_city())

    def test_city_name_validation(self):
        for name in ('', '  ', 'Город\x00', None):
            with self.assertRaises(ValueError):
                CitiesTable.validate_name(name)
        self.assertEqual(CitiesTable.validate_name(" Л'Аквила "), "Л'Аквила")
        with patch('builtins.input', side_effect=[' ', 'Киото']):
            with redirect_stdout(StringIO()):
                self.assertEqual(self.app.read_city_name('Название'), 'Киото')
        with patch('builtins.input', return_value='/отмена'):
            self.assertIsNone(self.app.read_city_name('Название'))

    def test_common_errors_do_not_assume_city_operation(self):
        for error in (psycopg2.errors.UniqueViolation(), psycopg2.errors.ForeignKeyViolation(),
                      psycopg2.errors.DependentObjectsStillExist(), psycopg2.Error()):
            output = StringIO()
            with redirect_stdout(output):
                self.app.show_db_error(error)
            self.assertNotIn('город', output.getvalue().lower())
            self.assertNotIn('сброс', output.getvalue().lower())

    def test_duplicate_city_is_explained_in_add_form(self):
        output = StringIO()
        with patch('builtins.input', return_value='Киото'):
            with patch.object(CitiesTable, 'insert_one', side_effect=psycopg2.errors.UniqueViolation()):
                with redirect_stdout(output):
                    self.app.show_add_city()
        self.assertIn('Город с таким названием уже существует', output.getvalue())
        self.assertIn('Добавление отменено', output.getvalue())

    def test_delete_requires_confirmation(self):
        with patch('builtins.input', side_effect=['1', 'ошибка', 'нет']):
            with patch.object(CitiesTable, 'delete_one') as delete:
                with redirect_stdout(StringIO()):
                    self.app.show_delete_city()
                delete.assert_not_called()

    def test_excursion_selection_uses_row_number(self):
        rows = [(900, 'Экскурсия', None, Decimal('1.00'))]
        with patch('builtins.input', side_effect=['', '1; DROP TABLE excursions', '900', '-1', '1']):
            with redirect_stdout(StringIO()):
                self.assertEqual(self.app.choose_excursion(rows)[0], 900)

    def test_excursion_form_retries_invalid_price(self):
        self.app.city_name = 'Киото'
        output = StringIO()
        with patch('builtins.input', side_effect=['', 'Храмы', '', 'NaN', '-1', '1.001', '12,34']):
            with patch.object(ExcursionsTable, 'insert_one') as insert:
                with redirect_stdout(output):
                    self.app.show_add_excursion()
        insert.assert_called_once_with(['Храмы', None, Decimal('12.34')], 'Киото')

    def test_excursion_form_can_be_cancelled_at_each_step(self):
        self.app.city_name = 'Киото'
        for values in (['/отмена'], ['Храмы', '/отмена'], ['Храмы', '', '/отмена']):
            with self.subTest(values=values), patch('builtins.input', side_effect=values):
                with patch.object(ExcursionsTable, 'insert_one') as insert:
                    self.app.show_add_excursion()
                    insert.assert_not_called()

    def test_duplicate_excursion_link_is_explained(self):
        self.app.city_name = 'Киото'
        rows = [(900, 'Экскурсия', None, Decimal('1.00'))]
        output = StringIO()
        with patch.object(ExcursionsTable, 'count', return_value=1), patch.object(ExcursionsTable, 'page', return_value=rows):
            with patch('builtins.input', return_value='1'):
                with patch.object(ExcursionCityTable, 'insert_one', side_effect=psycopg2.errors.UniqueViolation()):
                    with redirect_stdout(output):
                        self.app.show_attach_excursion()
        self.assertIn('уже добавлена в выбранный город', output.getvalue())

    def test_edit_form_keeps_values_and_clears_description(self):
        current = ('Прежнее название', 'Прежнее описание', Decimal('100.00'))
        with patch('builtins.input', side_effect=['', '', '']), redirect_stdout(StringIO()):
            self.assertEqual(self.app.read_excursion_data(current), list(current))
        with patch('builtins.input', side_effect=['', '/очистить', '0', '12,34']), redirect_stdout(StringIO()):
            self.assertEqual(self.app.read_excursion_data(current), [current[0], None, Decimal('12.34')])

    def test_edit_can_be_cancelled_without_update(self):
        self.app.city_name = 'Киото'
        self.app.excursion_rows = [(900, 'Экскурсия', None, Decimal('1.00'))]
        with patch.object(ExcursionsTable, 'cities_by_excursion', return_value=[('Киото',)]):
            with patch.object(ExcursionsTable, 'update_one') as update:
                with patch('builtins.input', side_effect=['1', '/отмена']), redirect_stdout(StringIO()):
                    self.app.show_edit_excursion()
                update.assert_not_called()

    def test_city_page_navigation_stops_at_boundaries(self):
        self.app.city_page = 0
        self.app.city_count = self.app.page_size
        with redirect_stdout(StringIO()):
            self.assertEqual(self.app.after_show_cities('p'), '1')
            self.assertEqual(self.app.city_page, 0)
            self.assertEqual(self.app.after_show_cities('n'), '1')
            self.assertEqual(self.app.city_page, 0)
            self.app.city_count += 1
            self.app.after_show_cities('n')
            self.assertEqual(self.app.city_page, 1)
            self.app.after_show_cities('p')
            self.assertEqual(self.app.city_page, 0)

    def test_attach_selects_row_on_current_page(self):
        self.app.city_name = 'Киото'
        self.app.page_size = 1
        first = [(10, 'Первая', None, Decimal('1.00'))]
        second = [(900, 'Вторая', None, Decimal('2.00'))]
        with patch.object(ExcursionsTable, 'count', return_value=2):
            with patch.object(ExcursionsTable, 'page', side_effect=[first, second]):
                with patch.object(ExcursionCityTable, 'insert_one') as insert:
                    with patch('builtins.input', side_effect=['n', '1']), redirect_stdout(StringIO()):
                        self.app.show_attach_excursion()
                insert.assert_called_once_with(['Киото', 900])


@unittest.skipUnless(os.environ.get('TEST_DATABASE_DSN'), 'Не задан TEST_DATABASE_DSN')
class DatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = psycopg2.connect(os.environ['TEST_DATABASE_DSN'])
        if not cls.conn.get_dsn_parameters()['dbname'].startswith('sql_course_test_'):
            cls.conn.close()
            raise RuntimeError('Запуск разрешён только в отдельной базе sql_course_test_…')
        cls.schema = 'test_' + uuid.uuid4().hex
        with cls.conn:
            with cls.conn.cursor() as cur:
                cur.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(cls.schema)))
                cur.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(cls.schema)))
        cls.previous = DbTable.dbconn
        cls.previous_connection = Main.connection
        cls.connection = SimpleNamespace(conn=cls.conn, prefix=cls.schema + '.')
        DbTable.dbconn = cls.connection
        Main.connection = cls.connection

    @classmethod
    def tearDownClass(cls):
        try:
            cls.conn.rollback()
            with cls.conn:
                with cls.conn.cursor() as cur:
                    cur.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(cls.schema)))
        finally:
            DbTable.dbconn = cls.previous
            Main.connection = cls.previous_connection
            cls.conn.close()

    def setUp(self):
        source = (Path(__file__).resolve().parents[2] / 'hw-1.sql').read_text()
        source = source.split('-- ================================= hw 2 =======================================')[0]
        with self.conn:
            with self.conn.cursor() as cur:
                cur.execute('SELECT current_schema()')
                self.assertEqual(cur.fetchone()[0], self.schema)
                cur.execute(source)
        self.cities = CitiesTable()
        self.excursions = ExcursionsTable()

    def fetch(self, query, params=()):
        with self.conn:
            with self.conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchall()

    def test_add_duplicate_and_recovery(self):
        self.assertEqual(len(self.cities.all()), 5)
        values = ['Новый город']
        self.cities.insert_one(values)
        self.assertEqual(values, ['Новый город'])
        with self.assertRaises(psycopg2.errors.UniqueViolation):
            self.cities.insert_one(values)
        self.cities.insert_one(['После ошибки'])
        self.assertEqual(len(self.cities.all()), 7)

    def test_excursion_insert_generates_key_and_stores_text(self):
        title = "Экскурсия '); DROP TABLE excursions; --"
        first = self.excursions.insert_one(["  " + title + "  ", None, "12,34"])
        second = self.excursions.insert_one(['Другая экскурсия', 'Описание', '99999999.99'])
        self.assertNotEqual(first, second)
        self.assertEqual(self.fetch('SELECT name, description, cost FROM excursions WHERE id = %s',
                                    (first,)), [(title, None, Decimal('12.34'))])
        self.assertEqual(self.fetch('SELECT count(*) FROM excursions'), [(7,)])

    def test_excursion_insert_rejects_invalid_values_without_changes(self):
        values = [('', None, '1'), ('Город', 123, '1'), ('Город\x00', None, '1')]
        values += [('Экскурсия', None, cost) for cost in
                   ('abc', 'NaN', 'Infinity', '0', '-1', '100000000', '1.001')]
        for data in values:
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.excursions.insert_one(data)
        self.assertEqual(self.fetch('SELECT count(*) FROM excursions'), [(5,)])
        self.excursions.insert_one(['После ошибки', None, '1.00'])
        self.assertEqual(self.fetch('SELECT count(*) FROM excursions'), [(6,)])

    def test_rename_preserves_excursions(self):
        self.cities.insert_one(['Новый город'])
        with self.conn:
            with self.conn.cursor() as cur:
                cur.execute('INSERT INTO excursion_city (excursion, city) VALUES (5, %s)',
                            ('Новый город',))
        before = self.excursions.all_by_city('Новый город')
        self.assertTrue(self.cities.update_one('Новый город', 'Новое имя'))
        self.assertEqual(self.excursions.all_by_city('Новое имя'), before)
        self.assertNotIn(('Новый город',), self.cities.all())
        self.assertEqual(self.fetch('SELECT count(*) FROM excursion_city WHERE excursion = 5'), [(4,)])

    def test_rename_never_changes_out_of_scope_tables(self):
        routes = self.fetch('SELECT * FROM routes ORDER BY id')
        route_cities = self.fetch('SELECT * FROM route_city ORDER BY id')
        excursions = self.excursions.all_by_city('Токио')
        with self.assertRaises(psycopg2.errors.ForeignKeyViolation):
            self.cities.update_one('Токио', 'Эдо')
        self.assertEqual(self.fetch('SELECT * FROM routes ORDER BY id'), routes)
        self.assertEqual(self.fetch('SELECT * FROM route_city ORDER BY id'), route_cities)
        self.assertEqual(self.excursions.all_by_city('Токио'), excursions)
        self.assertNotIn(('Эдо',), self.cities.all())

    def test_variant_works_with_only_assigned_tables(self):
        # Только в отдельной тестовой базе: вариант без связей с другими таблицами.
        with self.conn:
            with self.conn.cursor() as cur:
                cur.execute('DROP TABLE fees, tours, route_city, routes')
        excursions = self.excursions.all_by_city('Токио')
        self.cities.update_one('Токио', 'Эдо')
        self.assertEqual(self.excursions.all_by_city('Эдо'), excursions)
        self.cities.delete_one('Эдо')
        self.assertEqual(self.fetch('SELECT count(*) FROM excursions'), [(5,)])

    def test_reference_reset_initializes_assigned_tables(self):
        with self.conn:
            with self.conn.cursor() as cur:
                cur.execute('DROP TABLE fees, tours, route_city, routes')
        app = Main()
        app.db_drop()
        app.db_init()
        app.db_insert_somethings()
        self.assertEqual(len(self.cities.all()), 3)
        self.assertEqual(len(self.excursions.all_by_city('Токио')), 1)

    def test_reference_reset_cannot_partially_drop_linked_tables(self):
        with self.assertRaises(psycopg2.errors.DependentObjectsStillExist):
            Main().db_drop()
        self.assertEqual(len(self.cities.all()), 5)
        self.assertEqual(self.fetch('SELECT count(*) FROM excursions'), [(5,)])
        self.assertEqual(self.fetch('SELECT count(*) FROM excursion_city'), [(7,)])

    def test_duplicate_rename_rolls_back(self):
        before = self.excursions.all_by_city('Киото')
        with self.assertRaises(psycopg2.errors.UniqueViolation):
            self.cities.update_one('Киото', 'Нара')
        self.assertEqual(self.excursions.all_by_city('Киото'), before)
        self.assertEqual(len(self.cities.all()), 5)
        self.assertFalse(self.cities.update_one('Киото', 'Киото'))

    def test_delete_keeps_excursions_and_other_city_links(self):
        self.cities.insert_one(['Новый город'])
        with self.conn:
            with self.conn.cursor() as cur:
                cur.execute('INSERT INTO excursion_city (excursion, city) VALUES (1, %s), (5, %s)',
                            ('Новый город', 'Новый город'))
        self.cities.delete_one('Новый город')
        self.assertNotIn(('Новый город',), self.cities.all())
        self.assertEqual(self.fetch('SELECT count(*) FROM excursions'), [(5,)])
        self.assertEqual(self.fetch('SELECT count(*) FROM excursion_city'), [(7,)])

    def test_route_prevents_delete_and_links_are_restored(self):
        before = self.excursions.all_by_city('Токио')
        with self.assertRaises(psycopg2.errors.ForeignKeyViolation):
            self.cities.delete_one('Токио')
        self.assertIn(('Токио',), self.cities.all())
        self.assertEqual(self.excursions.all_by_city('Токио'), before)
        self.cities.insert_one(['После ошибки'])

    def test_quotes_and_sql_text_remain_data(self):
        name = "Л'Аквила'); DROP TABLE cities CASCADE; --"
        self.cities.insert_one([name])
        self.assertIn((name,), self.cities.all())
        self.cities.update_one(name, "Город ' с кавычкой")
        self.cities.delete_one("Город ' с кавычкой")
        self.assertEqual(len(self.cities.all()), 5)

    def test_missing_city_is_explained(self):
        with self.assertRaisesRegex(ValueError, 'Город не найден'):
            self.cities.update_one('Нет города', 'Новое имя')
        with self.assertRaisesRegex(ValueError, 'Город не найден'):
            self.cities.delete_one('Нет города')

    def test_new_excursion_is_created_with_selected_city(self):
        title = "Экскурсия '); DROP TABLE excursions; --"
        excursion = self.excursions.insert_one([title, None, '12.34'], 'Токио')
        self.assertIn((excursion, title, None, Decimal('12.34')), self.excursions.all_by_city('Токио'))
        self.assertEqual(self.fetch('SELECT count(*) FROM excursions'), [(6,)])

    def test_missing_city_rolls_back_new_excursion(self):
        with self.assertRaises(psycopg2.errors.ForeignKeyViolation):
            self.excursions.insert_one(['Новая экскурсия', None, '100'], 'Нет города')
        self.assertEqual(self.fetch('SELECT count(*) FROM excursions'), [(5,)])
        self.assertEqual(self.fetch('SELECT count(*) FROM excursion_city'), [(7,)])
        self.excursions.insert_one(['После ошибки', None, '100'], 'Токио')
        self.assertEqual(self.fetch('SELECT count(*) FROM excursions'), [(6,)])

    def test_existing_excursion_can_be_shared_without_duplicate_link(self):
        links = ExcursionCityTable()
        links.insert_one(['Токио', 5])
        with self.assertRaises(psycopg2.errors.UniqueViolation):
            links.insert_one(['Токио', 5])
        self.assertEqual(self.fetch('SELECT count(*) FROM excursions'), [(5,)])
        self.assertEqual(self.fetch('SELECT count(*) FROM excursion_city WHERE excursion = 5'), [(4,)])

    def test_delete_shared_excursion_removes_entity_and_all_links(self):
        self.excursions.delete_one(5, 'Киото')
        self.assertEqual(self.fetch('SELECT count(*) FROM excursions'), [(4,)])
        self.assertEqual(self.fetch('SELECT count(*) FROM excursion_city WHERE excursion = 5'), [(0,)])
        self.assertEqual(self.fetch('SELECT count(*) FROM excursion_city'), [(4,)])
        self.assertEqual(self.excursions.all_by_city('Ито'), [])

    def test_delete_requires_current_city_association(self):
        with self.assertRaisesRegex(ValueError, 'не связана'):
            self.excursions.delete_one(5, 'Токио')
        self.assertEqual(self.fetch('SELECT count(*) FROM excursions'), [(5,)])
        self.assertEqual(self.fetch('SELECT count(*) FROM excursion_city'), [(7,)])

    def test_duplicate_names_are_deleted_by_displayed_row(self):
        title = "Одинаковая экскурсия '); DROP TABLE excursions; --"
        description = "Описание '); DROP TABLE excursion_city; --"
        first = self.excursions.insert_one([title, description, '100'], 'Токио')
        second = self.excursions.insert_one([title, description, '100'], 'Токио')
        app = Main()
        app.city_name = 'Токио'
        app.excursion_rows = self.excursions.all_by_city('Токио')
        number = next(index for index, row in enumerate(app.excursion_rows, 1) if row[0] == second)
        with patch('builtins.input', side_effect=[str(number), 'да']):
            with redirect_stdout(StringIO()):
                app.show_delete_excursion()
        self.assertEqual(self.fetch('SELECT name, description FROM excursions WHERE id = %s',
                                    (first,)), [(title, description)])
        self.assertEqual(self.fetch('SELECT id FROM excursions WHERE id = %s', (second,)), [])

    def test_menu_creates_excursion_and_keeps_city_selected(self):
        app = Main()
        rows = self.cities.all()
        number = next(index for index, row in enumerate(rows, 1) if row[0] == 'Токио')
        output = StringIO()
        answers = ['1', '5', str(number), '6', 'Новая экскурсия', '', '0', '100,50', '1', '9']
        with patch('builtins.input', side_effect=answers):
            with redirect_stdout(output):
                app.main_cycle()
        self.assertIn('Экскурсия создана', output.getvalue())
        self.assertIn(('Новая экскурсия', None, Decimal('100.50')),
                      [row[1:] for row in self.excursions.all_by_city('Токио')])

    def test_excursion_delete_confirmation_shows_all_cities(self):
        app = Main()
        app.city_name = 'Киото'
        app.excursion_rows = self.excursions.all_by_city('Киото')
        number = next(index for index, row in enumerate(app.excursion_rows, 1) if row[0] == 5)
        output = StringIO()
        with patch('builtins.input', side_effect=[str(number), 'нет']):
            with redirect_stdout(output):
                app.show_delete_excursion()
        for city in ('Киото', 'Нара', 'Ито'):
            self.assertIn(city, output.getvalue())
        self.assertEqual(self.fetch('SELECT count(*) FROM excursions'), [(5,)])
        with patch('builtins.input', side_effect=[str(number), 'да']):
            with redirect_stdout(StringIO()):
                app.show_delete_excursion()
        self.assertEqual(self.fetch('SELECT count(*) FROM excursions'), [(4,)])

    def test_missing_city_is_not_shown_as_empty_excursion_list(self):
        app = Main()
        app.city_name = 'Нет города'
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(app.show_excursions_by_city(), '1')
        self.assertIn('город не существует', output.getvalue())

    def test_menu_recovers_from_database_error(self):
        app = Main()
        output = StringIO()
        with patch('builtins.input', side_effect=['1', '3', 'Токио', '1', '3', 'После ошибки', '9']):
            with redirect_stdout(output):
                app.main_cycle()
        self.assertIn('уже существует', output.getvalue())
        self.assertIn(('После ошибки',), self.cities.all())

    def test_city_pages_cover_list_without_overlap(self):
        expected = self.cities.all()
        self.assertEqual(self.cities.count(), len(expected))
        pages = [self.cities.page(number, 2) for number in range(3)]
        self.assertEqual([row for page in pages for row in page], expected)
        self.assertEqual(len(pages[-1]), 1)
        self.assertEqual(self.cities.page(3, 2), [])
        with self.assertRaises(ValueError):
            self.cities.page(-1, 2)

    def test_excursion_pages_filter_city_and_keep_duplicate_names(self):
        self.excursions.insert_one(['Одинаковая', None, '10'], 'Токио')
        self.excursions.insert_one(['Одинаковая', None, '10'], 'Токио')
        expected = self.excursions.all()
        pages = [self.excursions.page(number, 2) for number in range(4)]
        self.assertEqual([row for page in pages for row in page], expected)
        self.assertEqual(self.excursions.count(), len(expected))
        city_rows = self.excursions.all_by_city('Токио')
        self.assertEqual(self.excursions.count('Токио'), len(city_rows))
        self.assertEqual([self.excursions.page(number, 1, 'Токио')[0]
                          for number in range(len(city_rows))], city_rows)
        self.assertEqual(self.excursions.count("Токио' OR 1=1 --"), 0)
        self.assertEqual(self.excursions.page(0, 2, "Токио' OR 1=1 --"), [])

    def test_update_shared_excursion_preserves_keys_and_links(self):
        links = self.fetch('SELECT * FROM excursion_city ORDER BY excursion, city')
        title = "Обновлено '); DROP TABLE excursions; --"
        description = "Описание '); DROP TABLE excursion_city; --"
        self.excursions.update_one(5, 'Киото', [title, description, '12,34'])
        for city in ('Киото', 'Нара', 'Ито'):
            self.assertIn((5, title, description, Decimal('12.34')), self.excursions.all_by_city(city))
        self.assertEqual(self.fetch('SELECT * FROM excursion_city ORDER BY excursion, city'), links)
        self.assertEqual(self.fetch('SELECT count(*) FROM excursions'), [(5,)])

    def test_invalid_update_changes_nothing_and_can_be_retried(self):
        before = self.excursions.all()
        invalid = [('', None, '1'), ('Название', 123, '1'), ('Текст\x00', None, '1')]
        invalid += [('Название', None, value) for value in ('NaN', 'Infinity', '0', '-1', '1.001', '100000000')]
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.excursions.update_one(5, 'Киото', values)
        self.assertEqual(self.excursions.all(), before)
        self.excursions.update_one(5, 'Киото', ['После ошибки', None, '10.00'])
        self.assertEqual(self.fetch('SELECT name FROM excursions WHERE id = 5'), [('После ошибки',)])

    def test_update_requires_current_city_association(self):
        before = self.excursions.all()
        for excursion, city in ((5, 'Токио'), (99999, 'Киото')):
            with self.assertRaisesRegex(ValueError, 'не связана'):
                self.excursions.update_one(excursion, city, ['Название', None, '10'])
        self.assertEqual(self.excursions.all(), before)

    def test_city_selection_uses_current_page(self):
        app = Main()
        app.page_size = 2
        expected = self.cities.all()[2][0]
        with redirect_stdout(StringIO()):
            app.show_cities()
            self.assertEqual(app.after_show_cities('n'), '1')
            app.show_cities()
            with patch('builtins.input', return_value='1'):
                self.assertEqual(app.choose_city(), expected)

    def test_update_uses_row_on_current_excursion_page(self):
        app = Main()
        app.page_size = 1
        app.excursion_page = 1
        app.city_name = 'Киото'
        target = self.excursions.page(1, 1, 'Киото')[0]
        other = [row for row in self.excursions.all() if row[0] != target[0]]
        with patch('builtins.input', return_value='11'), redirect_stdout(StringIO()):
            self.assertEqual(app.show_excursions_by_city(), '11')
        answers = ['1', "Изменённая ' экскурсия", '/очистить', '1.001', '12,34']
        with patch('builtins.input', side_effect=answers), redirect_stdout(StringIO()):
            app.show_edit_excursion()
        self.assertEqual(self.fetch('SELECT name, description, cost FROM excursions WHERE id = %s',
                                    (target[0],)), [("Изменённая ' экскурсия", None, Decimal('12.34'))])
        self.assertEqual([row for row in self.excursions.all() if row[0] != target[0]], other)

    def test_excursion_page_navigation_keeps_selected_city(self):
        app = Main()
        app.page_size = 1
        app.city_name = 'Киото'
        output = StringIO()
        with patch('builtins.input', return_value='n'), redirect_stdout(output):
            self.assertEqual(app.show_excursions_by_city(), '5')
        self.assertEqual(app.excursion_page, 1)
        self.assertEqual(app.city_name, 'Киото')
        with patch('builtins.input', side_effect=['n', 'p']), redirect_stdout(output):
            self.assertEqual(app.show_excursions_by_city(), '5')
        self.assertEqual(app.excursion_page, 0)
        self.assertIn('Следующей страницы нет', output.getvalue())

    def test_last_excursion_page_is_clamped_after_delete(self):
        app = Main()
        app.city_name = 'Токио'
        for number in range(5):
            self.excursions.insert_one([f'Экскурсия {number}', None, '10'], 'Токио')
        app.excursion_page = 1
        with patch('builtins.input', return_value='1'), redirect_stdout(StringIO()):
            app.show_excursions_by_city()
        self.assertEqual(len(app.excursion_rows), 1)
        self.excursions.delete_one(app.excursion_rows[0][0], 'Токио')
        with patch('builtins.input', return_value='1'), redirect_stdout(StringIO()):
            app.show_excursions_by_city()
        self.assertEqual(app.excursion_page, 0)
        self.assertEqual(len(app.excursion_rows), app.page_size)

    def test_attach_can_select_from_another_page(self):
        app = Main()
        app.page_size = 2
        app.city_name = 'Токио'
        rows = self.excursions.all()
        linked = {row[0] for row in self.excursions.all_by_city('Токио')}
        index = next(index for index, row in enumerate(rows) if row[0] not in linked and index >= 2)
        answers = ['n'] * (index // app.page_size) + [str(index % app.page_size + 1)]
        with patch('builtins.input', side_effect=answers), redirect_stdout(StringIO()):
            app.show_attach_excursion()
        self.assertIn(rows[index], self.excursions.all_by_city('Токио'))
        self.assertEqual(self.excursions.count(), len(rows))


if __name__ == '__main__':
    unittest.main()
