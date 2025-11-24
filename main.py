import os
import sys
from shutil import rmtree
from datetime import datetime
import csv
import sqlite3
from random import choice, choices

from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QMainWindow, QWidget, QApplication, QFileDialog, QSlider, QTableWidgetItem, QMessageBox
from PyQt6 import QtCore
from PIL import Image, ImageDraw, ImageFont

from ui import Ui_MainWindow
from newsetui import Ui_Form

SOURCE_PATH = 'source_file_path'
FUNC_NAME = 'function_name'
EDIT_PROJECT = 'editing_old_project'
META = 'meta'
JACKAL_VALUE = 'jackal_value'
TOP_TEXT = 'top_text'
BOTTOM_TEXT = 'bottom_text'

JACKAL_DEGREES = {1: 'Как обычно', 2: 'Что-то в глаз попало', 20: 'Шакал одобряет', 40: 'Шакальность зашкаливает!',
                  60: 'МАКСИМУМ ШАКАЛЬНОСТИ!!!', 80: 'А тут была картинка?', 101: ''}
FUNC_TYPES = {'p_jackal': 1, 'demik': 2, 'v_jackal': 3, 'bomb': 4}
TRANSP_FUNCTIONS_TABLE = {1: 'Шакальное фото', 2: 'Демотиватор', 3: 'Шакальное видео', 4: 'Наложение'}
TRANSP_FUNCTIONS = {1: 'p_jackal', 2: 'demik', 3: 'v_jackal', 4: 'bomb'}
SAVING_FORMATS = {'p_jackal': 'jpg', 'demik': 'jpg', 'v_jackal': 'mp4', 'bomb': 'mp4'}


def is_image(filepath):
    try:
        with Image.open(filepath) as _:
            return True, ''
    except FileNotFoundError:
        return False, 'Не найден исходный файл проекта'
    except:
        return False, 'Этот формат не поддерживается'


def jackal_degree(n):
    m = 1
    for j in JACKAL_DEGREES.keys():
        if int(n) < j:
            return JACKAL_DEGREES[m]
        m = j
    return


def show_elements(*args):
    for el in args:
        el.show()


def hide_elements(*args):
    for el in args:
        el.hide()


def dict_to_str(dic: dict):
    out = []
    for k, v in dic.items():
        out.append(k + '::' + str(v))
    return ';;'.join(out)


def str_to_dict(st: str):
    out = {}
    for el in st.split(';;'):
        k, v = el.split('::')
        out[k] = v
        print(k, v, out)
    return out


class DataBase:
    def __init__(self):
        self.table = sqlite3.connect('database.db')

    def add_project(self, name, date, time, func_type, res_path, project_dir, params):
        with self.table as table:
            cur = table.cursor()
            cur.execute(
                'INSERT INTO projects (name, date, time, type, res_path, project_dir, params) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (name, date, time, func_type, res_path, project_dir, params))
            table.commit()
            return

    def all_projects(self, params):
        with self.table as table:
            cur = table.cursor()
            return cur.execute(f'SELECT {params} FROM projects').fetchall()

    def one_project(self, param: str, conditions: str, values: tuple):
        with self.table as table:
            cur = table.cursor()
            return cur.execute(f'SELECT {param} FROM projects WHERE {conditions}', values).fetchone()

    def select_setting(self, param):
        with self.table as table:
            cur = table.cursor()
            return cur.execute(f'SELECT {param} FROM settings').fetchone()[0]

    def delete_project(self, conditions: str = None, values: tuple = None):
        with self.table as table:
            cur = table.cursor()
            if conditions is not None:
                cur.execute(f'DELETE FROM projects WHERE {conditions}', values)
            else:
                cur.execute('DELETE FROM projects')


class Settings(QWidget, Ui_Form):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.updated = False

        self.table = sqlite3.connect('database.db')
        with self.table as table:
            cur = table.cursor()
            cur.execute('CREATE TABLE IF NOT EXISTS settings (jackal INT, frame INT, frame_width INT)')
            self.update_sliders()
            table.commit()

        self.edit_jackal.valueChanged.connect(self.change_value_by_slider)
        self.edit_frame.valueChanged.connect(self.change_value_by_slider)
        self.edit_frame_width.valueChanged.connect(self.change_value_by_slider)

        self.val_jackal.valueChanged.connect(self.change_value_by_spinbox)
        self.val_frame.valueChanged.connect(self.change_value_by_spinbox)
        self.val_frame_width.valueChanged.connect(self.change_value_by_spinbox)

        self._reset.clicked.connect(self.reset_settings)
        self._update.clicked.connect(self.update_settings)

    def change_value_by_slider(self):
        spin_boxes = {'jackal': self.val_jackal, 'frame': self.val_frame, 'frame_width': self.val_frame_width}

        param = self.sender().objectName().split('_', maxsplit=1)[-1]
        value = self.sender().value()
        spin_boxes[param].setValue(value)

    def change_value_by_spinbox(self):
        sliders = {'jackal': self.edit_jackal, 'frame': self.edit_frame, 'frame_width': self.edit_frame_width}

        param = self.sender().objectName().split('_', maxsplit=1)[-1]
        value = self.sender().value()
        sliders[param].setValue(value)

    def reset_settings(self):
        with self.table as table:
            cur = table.cursor()
            cur.execute('UPDATE settings SET jackal = 20, frame = 80, frame_width = 3')
            table.commit()
            self.update_sliders()
            self.updated = True
            self.hide()

    def update_settings(self):
        try:
            with self.table as table:
                cur = table.cursor()
                cur.execute('UPDATE settings SET jackal = ?, frame = ?, frame_width = ?',
                            (self.val_jackal.value(), self.val_frame.value(), self.val_frame_width.value()))
                table.commit()
                self.updated = True
                self.hide()
        except sqlite3.OperationalError as e:
            print(e)

    def update_sliders(self):
        with self.table as table:
            cur = table.cursor()
            jackal, frame, frame_width = cur.execute('SELECT * FROM settings').fetchone()
            self.edit_jackal.setValue(jackal)
            self.val_jackal.setValue(jackal)
            self.edit_frame.setValue(frame)
            self.val_frame.setValue(frame)
            self.edit_frame_width.setValue(frame_width)
            self.val_frame_width.setValue(frame_width)


class MemeMaker(QMainWindow, Ui_MainWindow):
    def __init__(self):
        self.function_names = {'p_jackal': self.p_jackal_open, 'demik': self.demik_open}

        super().__init__()
        self.setupUi(self)

        self.function_data = {'source_file_path': '', 'function_name': '', 'meta': {}}
        self.editing = False

        self.db = DataBase()
        self.update_table()

        self.p_jackal_slider = QSlider(QtCore.Qt.Orientation.Horizontal, parent=self.centralwidget)
        self.p_jackal_slider.setGeometry(QtCore.QRect(50, 600, 500, 10))
        self.p_jackal_slider.setMinimum(1)
        self.p_jackal_slider.setMaximum(100)
        self.p_jackal_slider.setObjectName("p_jackal_slider")

        self.basic_buttons = [self.save_button, self.menu_button]
        self.menu_elements = [self.p_jackal_button, self.demik_button, self.projects_button, self.settings_button,
                              self.menu_picture]
        self.p_jackal_elements = [self.p_jackal_slider, self.p_jackal_label]
        self.demik_elements = [self.demik_top_2, self.demik_bottom_2, self.hint_top_2,
                               self.hint_bottom_2]
        self.v_jackal_elements = [self.v_jackal_slider, self.v_jackal_label]
        self.bomb_elements = [self.bomb_overlay]
        self.project_elements = [self.projects_table, self.open_button, self.delete_button, self.menu_button_2]
        self.func_elements = [*self.basic_buttons, *self.menu_elements, *self.p_jackal_elements, *self.demik_elements,
                              *self.v_jackal_elements, *self.bomb_elements, *self.project_elements]

        self.back_to_menu()

        self.p_jackal_button.clicked.connect(self.p_jackal_open)
        self.demik_button.clicked.connect(self.demik_open)
        self.projects_button.clicked.connect(self.projects_list)
        self.settings_button.clicked.connect(self.open_settings_form)

        self.p_jackal.triggered.connect(self.p_jackal_open)
        self.p_jackal_slider.valueChanged.connect(self.p_jackal_transparent)

        self.demik.triggered.connect(self.demik_open)
        # self.demik_button.clicked.connect(self.demik_photo)
        self.demik_top_2.textChanged.connect(self.demik_photo)
        self.demik_bottom_2.textChanged.connect(self.demik_photo)

        self.projects_table.cellClicked.connect(self.item_selected)
        self.projects.triggered.connect(self.projects_list)
        self.drop.triggered.connect(self.drop_table)
        self.open_button.clicked.connect(self.open_project)
        self.delete_button.clicked.connect(self.delete_project)
        self.menu_button_2.clicked.connect(self.back_to_menu)

        self.open_settings.triggered.connect(self.open_settings_form)

        self.save_button.clicked.connect(self.save_media)
        self.menu_button.clicked.connect(self.back_to_menu)

    def p_jackal_transparent(self, value):
        self.function_data[META][JACKAL_VALUE] = int(value)
        self.jackal_photo()

    def p_jackal_open(self):
        try:
            if not self.editing:
                fname = QFileDialog.getOpenFileName(self, 'Выбрать чёткое изображение', '',
                                                    'Фото (*.jpg;*.jpeg;*.png);;Все файлы(*)')[0]
                self.reset_func_data()
            else:
                fname = self.function_data[SOURCE_PATH]
            if fname:
                if is_image(fname)[0]:
                    f = self.function_data
                    f[SOURCE_PATH] = fname
                    f[FUNC_NAME] = 'p_jackal'
                    if not f[META]:
                        f[META][JACKAL_VALUE] = self.db.select_setting('jackal')
                    self.p_jackal_slider.setValue(int(f[META][JACKAL_VALUE]))
                    self.jackal_photo()
                    self.change_elements([*self.p_jackal_elements, *self.basic_buttons])
                else:
                    self.back_to_menu()
                self.statusbar.showMessage(is_image(fname)[1])
        except Exception as e:
            self.statusbar.showMessage(f'Неожиданная ошибка: {e}')

    def jackal_photo(self):
        try:
            f = self.function_data
            self.media.clear()
            fname = f[SOURCE_PATH]
            img = Image.open(fname)
            wid, hei = img.size
            img = img.reduce(int(f[META][JACKAL_VALUE]))
            new = img.copy().resize((wid, hei)).convert('RGB')
            new.save('res.jpg')
            pix = QPixmap('res.jpg').scaled(*new.size, QtCore.Qt.AspectRatioMode.KeepAspectRatio)
            self.media.setPixmap(pix)
            self.p_jackal_label.setText(f'{jackal_degree(f[META][JACKAL_VALUE])} ({f[META][JACKAL_VALUE]})')
            print(f)
        except Exception as e:
            self.statusbar.showMessage(f'Неожиданная ошибка: {e}')

    def demik_open(self):
        try:
            if not self.editing:
                fname = QFileDialog.getOpenFileName(self, 'Выбрать скучное изображение', '',
                                                    'Фото (*.jpg;*.jpeg;*.png);;Все файлы(*)')[0]
                self.reset_func_data()
            else:
                fname = self.function_data[SOURCE_PATH]
            if fname:
                if is_image(fname)[0]:
                    f = self.function_data
                    f[SOURCE_PATH] = fname
                    f[FUNC_NAME] = 'demik'
                    self.demik_top_2.setText(f[META][TOP_TEXT] if f[META] else None)
                    self.demik_bottom_2.setText(f[META][BOTTOM_TEXT] if f[META] else None)
                    self.demik_photo()
                    self.change_elements([*self.demik_elements, *self.basic_buttons])
                else:
                    self.back_to_menu()
                self.statusbar.showMessage(is_image(fname)[1])
        except Exception as e:
            self.statusbar.showMessage(f'Неожиданная ошибка: {e}')

    def demik_photo(self):
        try:
            f = self.function_data
            self.media.clear()
            fname = f[SOURCE_PATH]
            img = Image.open(fname)
            wid, hei = img.size
            frame = self.db.select_setting('frame')
            frame_width = self.db.select_setting('frame_width')
            dem = Image.new('RGB', (wid + frame * 2 + 40, hei + frame * 2 + 190), (0, 0, 0))
            draw = ImageDraw.Draw(dem)
            draw.rectangle((frame, frame, wid + frame + 40, hei + frame + 40), width=frame_width)
            dem.paste(img, (frame + 20, frame + 20))
            if f[META]:
                f[META][TOP_TEXT] = self.demik_top_2.text()
                f[META][BOTTOM_TEXT] = self.demik_bottom_2.text()
            else:
                f[META][TOP_TEXT] = ''
                f[META][BOTTOM_TEXT] = ''
            top_len = draw.textlength(f[META][TOP_TEXT], font=ImageFont.truetype(font='consolab.ttf'),
                                      font_size=100) * 4.6
            bottom_len = draw.textlength(f[META][BOTTOM_TEXT], font=ImageFont.truetype(font='consolab.ttf'),
                                         font_size=70) * 3.17
            self.hint_top_2.setText('Текст сверху (!)' if top_len > wid / 2 else 'Текст сверху')
            self.hint_bottom_2.setText('Текст снизу (!)' if bottom_len > wid / 2 else 'Текст снизу')

            draw.text((round((wid + frame * 2 + 40) / 2 - top_len), hei + frame + frame // 3 + 30),
                      f[META][TOP_TEXT], font=ImageFont.truetype(font='consolab.ttf', size=100), align='center')
            draw.text((round((wid + frame * 2 + 40) / 2 - bottom_len), hei + frame + frame // 3 + 130),
                      f[META][BOTTOM_TEXT], font=ImageFont.truetype(font='consolab.ttf', size=70), align='center')

            dem = dem.convert('RGB')
            dem.convert('RGB').save(f'res.jpg')
            pix = QPixmap(f'res.jpg').scaled(*dem.size, QtCore.Qt.AspectRatioMode.KeepAspectRatio)
            self.media.setPixmap(pix)
            print(f)
        except Exception as e:
            self.statusbar.showMessage(f'Неожиданная ошибка: {e}')

    def projects_list(self):
        self.change_elements(self.project_elements)
        self.media.clear()

    def item_selected(self):
        self.open_button.setEnabled(True)
        self.delete_button.setEnabled(True)
        self.menu_button_2.setEnabled(True)

    def open_project(self):
        try:
            if not self.projects_table.selectedItems():
                self.open_button.setEnabled(False)
                self.delete_button.setEnabled(False)
                self.menu_button_2.setEnabled(False)
            else:
                t = self.projects_table
                i = t.selectedItems()[0]
                print(self.db.all_projects('*'))
                project = self.db.all_projects('type, res_path, params')[i.row()]
                f = self.function_data
                f[FUNC_NAME] = project[0]
                f[SOURCE_PATH] = project[1]
                f[META] = str_to_dict(project[2])
                self.editing = True
                self.change_elements()
                self.function_names[TRANSP_FUNCTIONS[project[0]]]()
        except Exception as e:
            self.statusbar.showMessage(f'Неожиданная ошибка: {e}')

    def delete_project(self):
        try:
            if not self.projects_table.selectedItems():
                self.open_button.setEnabled(False)
                self.delete_button.setEnabled(False)
                self.menu_button_2.setEnabled(False)
            else:
                i = self.projects_table.selectedItems()[0]
                confirm = QMessageBox.warning(self, 'Удалить проект?',
                                              'Файл останется на компьютере, но у приложения не будет к нему доступа',
                                              buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if confirm == QMessageBox.StandardButton.Yes:
                    d, t, n = self.db.all_projects('date, time, name')[i.row()]
                    self.db.delete_project('date = ? AND time = ?', (d, t))
                    rmtree(f'projects/{d}__{t}__{n}')
                    self.update_table()
        except Exception as e:
            self.statusbar.showMessage(f'Неожиданная ошибка: {e}')

    def drop_table(self):
        confirm = QMessageBox.warning(self, 'Вы уверены?',
                                      'Вы удалите все проекты из внутренней базы данных. Изображения останутся у вас на компьютере',
                                      buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            self.db.delete_project()
            self.statusbar.showMessage(
                choices(['Все проекты удалены :(', 'Ты больше не армянин...'], weights=[0.7, 0.3], k=1)[0])
            for tree in os.listdir('projects'):
                rmtree(f'projects/{tree}')
            self.update_table()

    def open_settings_form(self):
        self.settings = Settings()
        self.settings.show()

    def save_media(self):
        try:
            f = self.function_data
            if not self.editing:
                fname = f[SOURCE_PATH]
                fname = fname[fname.rfind('/') + 1:fname.rfind('.')]
            else:
                fname = self.db.one_project('name', 'res_path = ?', (f[SOURCE_PATH],))[0]
            path, ok_pressed = QFileDialog.getSaveFileName(QFileDialog(), 'Выберите, как назвать свой шЕдЕвР',
                                                           f'{fname}.{SAVING_FORMATS[f[FUNC_NAME]]}',
                                                           f'{TRANSP_FUNCTIONS_TABLE[FUNC_TYPES[f[FUNC_NAME]]]} (*.{SAVING_FORMATS[f[FUNC_NAME]]});;Все файлы (*)')

            if ok_pressed:
                name = path[path.rfind('/') + 1:path.rfind('.')]  # .replace(' ', '+')
                if (name,) in self.db.all_projects('name'):
                    r = name.rfind('(')
                    if r == -1:
                        name += ' (1)'
                    else:
                        i = int(name[r + 1:-1]) + 1
                        name += f' ({i})'
                if self.editing:
                    button = self.db.one_project('project_dir', 'res_path = ?', (f[SOURCE_PATH],))[0]
                else:
                    button = True
                if f[FUNC_NAME] in ('p_jackal', 'demik'):
                    img = Image.open(f'res.jpg')
                    img.save(path)
                    now = datetime.now().strftime('%d-%m-%Y__%H-%M-%S-%f')
                    if button:
                        if self.editing:
                            print(self.db.one_project('date, time, name', 'res_path = ?', (f[SOURCE_PATH],)))
                            date1, time1, name1 = self.db.one_project('date, time, name', 'res_path = ?',
                                                                      (f[SOURCE_PATH],))
                            pname = f'projects/{date1}__{time1}__{name1}'
                        else:
                            pname = f'projects/{now}__{name}'
                            os.mkdir(pname)

                        img.save(f'{pname}/project.jpg')
                        source = Image.open(f[SOURCE_PATH])
                        source = source.convert('RGB')
                        source.save(f'{pname}/source.jpg')
                        os.remove('res.jpg')
                        # <-
                        with open(f'{pname}/res.csv', 'w', encoding='utf8', newline='') as file:
                            data = [{'source_file_path': f[SOURCE_PATH], 'function_name': f[FUNC_NAME]}]
                            for m in self.function_data[META].keys():
                                data[0][m] = self.function_data[META][m]
                            # print(data)
                            writer = csv.DictWriter(file, fieldnames=data[0].keys())
                            writer.writeheader()
                            writer.writerows(data)
                    else:
                        pname = f'projects/{now}__{name}'
                    d, t = now.split('__')
                    params = dict_to_str(f[META])
                    print(name, d, t, FUNC_TYPES[f[FUNC_NAME]], f'{pname}/source.jpg', button, params)
                    self.db.add_project(name, d, t, FUNC_TYPES[f[FUNC_NAME]], f'{pname}/source.jpg', button, params)
                    print(self.db.all_projects('*'))
                    self.update_table()
                    self.editing = False

                    self.projects_table.resizeColumnsToContents()
                    # print(self.cur.execute('SELECT * FROM projects').fetchall())
        except Exception as e:
            self.statusbar.showMessage(f'Неожиданная ошибка: {e}')

    def back_to_menu(self):
        self.change_elements(self.menu_elements)
        self.media.clear()
        self.reset_func_data()
        self.statusbar.clearMessage()
        try:
            os.remove('res.jpg')
        except:
            pass
        pix = QPixmap('res/cats/' + choice(os.listdir('res/cats'))).scaled(500, 500,
                                                                           QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        self.menu_picture.setPixmap(pix)
        print('menuha')

    def reset_func_data(self):
        self.function_data = {'source_file_path': '', 'function_name': '', 'meta': {}}

    def change_elements(self, to_show: list = None):
        hide_elements(*self.func_elements)
        if to_show is not None:
            show_elements(*to_show)

    def update_table(self):
        try:
            result = self.db.all_projects('type, date, name')
            self.projects_table.setRowCount(len(result))
            self.projects_table.setColumnCount(len(result[0]) if result else 1)
            for i, elem in enumerate(result):
                for j, val in enumerate(elem):
                    if isinstance(val, int):
                        val = TRANSP_FUNCTIONS_TABLE[val]
                    self.projects_table.setItem(i, j, QTableWidgetItem(str(val)))
        except Exception as e:
            self.statusbar.showMessage(f'Неожиданная ошибка: {e}')


def exception_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


if __name__ == "__main__":
    app = QApplication([])
    w = MemeMaker()
    w.show()
    sys.excepthook = exception_hook
    sys.exit(app.exec())
