import os
import sys
import time
import json
import sqlite3
import requests
import module.snafylno as snafylno
from typing import *
from queue import Queue
from PyQt5 import QtGui
from PyQt5 import QtCore
from threading import Thread
from PyQt5.QtGui import QPixmap, QCloseEvent
from module.snafylno import Config
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QWidget
from module.snafylno import Onlyfans
from PyQt5.QtWidgets import QTabWidget
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QGridLayout
from PyQt5.QtWidgets import QTreeWidget
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QTreeWidgetItem
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal


class Settings:
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.config = self.load_settings(filename)

    def load_settings(self, filename: str) -> Dict:
        data = {}
        if os.path.isfile(filename):
            file = open(filename, 'r')
            data = json.load(file)
            file.close()
        else:
            data["show_avatar"] = False
            with open(filename, 'w') as file:
                json.dump(data, file)

        return data

    def save_settings(self) -> None:
        with open(self.filename, 'w') as file:
            json.dump(self.config, file)

    def show_avatar(self) -> bool:
        return self.config['show_avatar']

    def set_option(self, key: str, value) -> str:
        self.config[key] = value
        self.save_settings()
        return self.config[key]


class ConfigDlg(QWidget):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setWindowTitle(title)
        self.setGeometry(100, 100, 300, 100)
        self.move(350, 45)
        self.title = title

        self.edit = QLineEdit(parent = self)
        self.edit.move(10, 10)
        self.edit.resize(250, 30)

        self.add_node = QPushButton("Ok", parent = self)
        self.add_node.move(10, 50)
        self.add_node.clicked.connect(self._add_node)

    def _add_node(self) -> None:
        if len(self.edit.text()) > 0:
            config = Config('config.json')
            config.add_node(self.title, self.edit.text())
        self.close()

        

class OptionWindow(QWidget):
    def __init__(self, Onlyfans: snafylno.Onlyfans,
                 grab_subscriptions: Callable, data_display: QtCore.pyqtBoundSignal) -> None:
        super().__init__()
        self.setWindowTitle('Options')
        self.setGeometry(100, 100, 250, 180)
        self.move(300, 45)
        self.Onlyfans = Onlyfans
        self.grab_subs = grab_subscriptions
        self.data_display = data_display

        self.settings = Settings('settings.json')

        self.display_avatar = QPushButton("Show Avatars: {0}".format(self.settings.show_avatar()), parent = self)
        self.display_avatar.move(10, 10)
        self.display_avatar.clicked.connect(self.change_option_avatar)

        self.add_user_agent = QPushButton("Add a user agent", parent = self)
        self.add_user_agent.move(10, 50)
        self.add_user_agent.clicked.connect(self.add_useragent)

        self.add_cookie_str = QPushButton("Add cookie", parent = self)
        self.add_cookie_str.move(10, 90)
        self.add_cookie_str.clicked.connect(self.add_cookie)

        self.add_cookie_str = QPushButton("Add X-BC", parent = self)
        self.add_cookie_str.move(10, 130)
        self.add_cookie_str.clicked.connect(self.add_x_bc)
        

    def check_login(self) -> None:
        if self.Onlyfans.user_logged_in() is True:
            count = self.grab_subs(self.data_display)

    def closeEvent(self, event) -> None:
        if self.Onlyfans.user_logged_in() is not True:
            return

        self.Onlyfans.load_config()
        thread = Thread(target = self.check_login)
        thread.start()

    def add_useragent(self) -> None:
        self.user_agent_dialog = ConfigDlg('user-agent')
        self.user_agent_dialog.show()

    def add_cookie(self) -> None:
        self.cookie_dialog = ConfigDlg('cookie')
        self.cookie_dialog.show()

    def add_x_bc(self) -> None:
        self.x_bc_dialog = ConfigDlg('x-bc')
        self.x_bc_dialog.show()


    def change_option_avatar(self) -> bool:
        current_option = self.settings.show_avatar()
        new_option = self.settings.set_option('show_avatar', (not current_option))
        self.display_avatar.setText("Show Avatars: {0}".format(new_option))

        return new_option

    def show_avatar(self) -> bool:
        return self.settings.show_avatar()


        

class MainWindow(QWidget):
    data_display = QtCore.pyqtSignal(object)
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('OFDL')
        self.setGeometry(100, 100, 900, 500)
        self.move(60, 15)

        self.Onlyfans = Onlyfans()
        self.options_dialog = OptionWindow(self.Onlyfans, self.fetch_and_display_subs, self.data_display)

        layout = QGridLayout()
        self.setLayout(layout)

        self.tabs = QTabWidget()
        self.tabs.resize(600, 400)
        self.general_tab = QWidget()
        self.database_tab = QWidget()
        self.links_tab = QWidget()
        self.download_tab = QWidget()

        self.download_tree = QTreeWidget(parent = self.download_tab)
        self.download_tree.setHeaderLabels(["Model", "Path", "Filename"])
        self.download_tree.resize(720, 300)
        self.download_tree.move(30, 20)
        self.download_tree.columnWidth(300)

        self.information_label_general = QLabel(self.general_tab)
        self.information_label_general.move(0, 405)
        self.information_label_general.resize(500, 50)
        self.information_label_general.setStyleSheet("color: red")

        self.information_label_links = QLabel(self.links_tab)
        self.information_label_links.move(0, 405)
        self.information_label_links.resize(150, 50)
        self.information_label_links.setStyleSheet("color: red")

        self.information_label_download = QLabel(self.download_tab)
        self.information_label_download.move(0, 405)
        self.information_label_download.resize(550, 50)
        self.information_label_download.setStyleSheet("color: red")

        self.information_photo_count = QLabel(self.general_tab)
        self.information_photo_count.move(450, 20)
        self.information_photo_count.resize(150, 80)

        self.information_video_count = QLabel(self.general_tab)
        self.information_video_count.move(600, 20)
        self.information_video_count.resize(150, 80)

        self.information_audio_count = QLabel(self.general_tab)
        self.information_audio_count.move(450, 80)
        self.information_audio_count.resize(150, 80)

        self.information_archive_count = QLabel(self.general_tab)
        self.information_archive_count.move(600, 80)
        self.information_archive_count.resize(150, 80)
        
        self.listing_type = "<h4>Active subscriptions</h4>"

        self.model_label = QLabel(self.listing_type, parent=self.general_tab)
        self.model_label.move(10, 0)

        self.current_user = QLabel("", parent=self.general_tab)
        self.current_user.move(200, 50)
        self.current_user.resize(150, 20)

        self.tree = QTreeWidget(parent = self.general_tab)
        self.tree.setHeaderLabels(["Models"])
        self.tree.resize(150, 200)
        self.tree.move(10, 20)

        self.cb = QComboBox(parent = self.general_tab)
        self.cb.move(5, 220)
        self.cb.addItems(["Active subscriptions", "Expired subscriptions", "All"])
        self.cb.currentIndexChanged.connect(self.combo_change)

        self.tree.itemClicked.connect(self.onItemClicked)

        self.tabs.addTab(self.general_tab, "General")
        self.tabs.addTab(self.links_tab, "Links")
        self.tabs.addTab(self.download_tab, "Downloads")

        self.icon_label = QLabel(parent = self.general_tab)
        self.icon_label.move(200, 10)
        self.icon_label.resize(300, 300)

        self.all_checkbox = QCheckBox("All", parent = self.general_tab)
        self.all_checkbox.move(200, 250)
        self.all_checkbox.stateChanged.connect(self.check_change)

        self.message_checkbox = QCheckBox("Messages", parent = self.general_tab)
        self.message_checkbox.move(300, 250)
        self.message_checkbox.stateChanged.connect(self.check_change)

        self.audio_checkbox = QCheckBox("Audio", parent = self.general_tab)
        self.audio_checkbox.move(400, 250)
        self.audio_checkbox.stateChanged.connect(self.check_change)

        self.highlight_checkbox = QCheckBox("Highlights", parent = self.general_tab)
        self.highlight_checkbox.move(200, 300)
        self.highlight_checkbox.stateChanged.connect(self.check_change)

        self.story_checkbox = QCheckBox("Stories", parent = self.general_tab)
        self.story_checkbox.move(300, 300)
        self.story_checkbox.stateChanged.connect(self.check_change)

        self.post_checkbox = QCheckBox("Posts", parent = self.general_tab)
        self.post_checkbox.move(400, 300)
        self.post_checkbox.stateChanged.connect(self.check_change)

        self.archived_checkbox = QCheckBox("Archived", parent = self.general_tab)
        self.archived_checkbox.move(500, 300)
        self.archived_checkbox.stateChanged.connect(self.check_change)

        self.checkboxes = [self.all_checkbox, self.message_checkbox, self.audio_checkbox,
                           self.highlight_checkbox, self.story_checkbox,
                           self.post_checkbox, self.archived_checkbox]

        self.grab_links = QPushButton("Grab Links", parent = self.general_tab)
        self.grab_links.move(500, 400)
        self.grab_links.clicked.connect(self.get_links)
        self.grab_links.setEnabled(False)

        self.download_links = QPushButton("Download Files", parent = self.links_tab)
        self.download_links.move(100, 400)
        self.download_links.clicked.connect(self.download_files)
        self.download_links.setEnabled(False)

        self.options = QPushButton("Options", parent = self.general_tab)
        self.options.move(700, 10)
        self.options.clicked.connect(self.show_options)
        

        self.tree_links = QTreeWidget(parent = self.links_tab)
        self.tree_links.setHeaderLabels(["Model", "Type", "Caption / Text",
                                         "Date of post", "Post ID"])
        self.tree_links.resize(720, 300)
        self.tree_links.move(30, 20)
        self.tree_links.columnWidth(300)
        
        self.tree_links.setColumnWidth(0, 150)
        self.tree_links.setColumnWidth(2, 300)
        self.tree_links.hideColumn(4)

        self.download_tree.setColumnWidth(1, 300)

        layout.addWidget(self.tabs, 0, 0)

        self.display_checkboxes(False)
        self.show()

        self.Onlyfans.load_config()
        self.data_display.connect(self.update_main)

        if self.Onlyfans.user_logged_in() is True:
            thread = Thread(target = self.fetch_and_display_subs,
                            args=(self.data_display,))
            thread.start()
        else:
            self.information_label_general.setText("Not logged in...")

    def closeEvent(self, event: QCloseEvent) -> None:
        self.Onlyfans.signal_stop_event()


    def show_options(self) -> None:
        self.options_dialog.show()


    def fetch_and_display_subs(self, data_display: QtCore.pyqtBoundSignal) -> int:
        data = {}
        data["info"] = "Fetching subscriptions ..."
        data_display.emit(data)
        self.display_checkboxes(False)
        count = self.Onlyfans.get_subscriptions()
        self.subscription_list = self.Onlyfans.return_active_subs()
        self.display_subscriptions(self.subscription_list, data_display)
        data["info"] = "Done ..."
        data_display.emit(data)
        if count > 0:
            self.grab_links.setEnabled(True)
        self.all_subscriptions = self.Onlyfans.return_all_subs()
        self.expired_subscriptions = self.Onlyfans.return_expired_subs()
        return count
                

    @QtCore.pyqtSlot(QTreeWidgetItem, int)
    def onItemClicked(self, it: QTreeWidgetItem, col: int) -> None:
        self.current_username = it.text(col)

        profile = self.all_subscriptions[self.current_username]
        if self.current_username == profile.username():
            if profile.is_active():
                self.display_checkboxes(True)
            else:
                self.display_checkboxes(False)
                self.message_checkbox.setEnabled(True)
                self.grab_links.setEnabled(True)
                
        if self.Onlyfans.get_user_info(profile) is False:
            self.display_checkboxes(False)
        self.switch_selections(profile.get_flag())

        self.current_user.setText("<h4>" + self.current_username + "</h4>")
        self.information_photo_count.setText("<h4>Photos: {0}".format(profile.photo_count()) + "</h4>")
        self.information_video_count.setText("<h4>Videos: {0}".format(profile.videos_count()) + "</h4>")
        self.information_audio_count.setText("<h4>Audio: {0}".format(profile.audio_count()) + "</h4>")
        self.information_archive_count.setText("<h4>Archived: {0}".format(profile.archive_count()) + "</h4>")
        
        avatar_url = profile.sm_avatar(50)
        pixmap = QPixmap()
        if avatar_url is not None and self.options_dialog.show_avatar() is not False and avatar_url != '':
            r = requests.get(avatar_url)
            if r.status_code == 200:
                pixmap.loadFromData(r.content)
                pixmap = pixmap.scaled(96, 96, QtCore.Qt.KeepAspectRatio)
                self.icon_label.setPixmap(pixmap)
        else:
            self.icon_label.setPixmap(QPixmap())
    
    def _get_links(self, data_display: QtCore.pyqtBoundSignal) -> None:
        data = {}
        profiles = self.Onlyfans.return_all_subs()
        
        for key in profiles:
            profile = profiles[key]
            if profile.get_flag() > 0:
                self.Onlyfans.get_links(profile)
            if profile.error_set() is False and profile.get_flag() > 0:
                data["info"] = "Collected -> {0},  still collecting...".format(profile.username())
                data_display.emit(data)

        data["info"] = "Done ..."
        data_display.emit(data)

        self.display_collected_links(profiles, data_display)
        
        

    def get_links(self) -> None:
        if hasattr(self, 'current_username') is False:
            return
        self.information_label_general.setText("Fetching data ...")
        self.download_links.setEnabled(False)
        thread = Thread(target = self._get_links, args=(self.data_display,))
        thread.start()
        self.grab_links.setEnabled(False)


    def download(self) -> None:
        username = ''
        usernames = {}
        total_posts = [0]
        root = self.tree_links.invisibleRootItem()
        user_count = root.childCount()
        profiles = self.Onlyfans.return_all_subs()
        self.tabs.setCurrentWidget(self.download_tab)
        if user_count < 1:
            return
        for i in range(user_count):
            post_ids = []
            user = root.child(i)
            user_post_count = user.childCount()
            user_all_selected = (user.checkState(2) == QtCore.Qt.Unchecked)
            if user_all_selected:
                continue
            username = user.text(0)
            for x in range(user_post_count):
                user_child = user.child(x)
                state = (user_child.checkState(2) == QtCore.Qt.Checked)
                if state:
                    item_id = user_child.text(4)
                    post_ids.append(item_id)
            total_posts[0] += profiles[username].media_count()
            usernames[username] = post_ids

        profile = profiles[username]   

        self.download_links.setEnabled(False)
        self.Onlyfans.data_display.connect(self.update)
        self.Onlyfans.download_profiles(usernames, total_posts)
        
    def update(self, data: Dict) -> None:
        if 'username' in data and 'path' in data and 'filename' in data:
            item = QTreeWidgetItem(self.download_tree)
            item.setText(0, data["username"])
            item.setText(1, data["path"])
            item.setText(2, data["filename"])
        if 'info' in data:
            self.information_label_download.setText(data['info'])
        elif 'total' in data:
            self.information_label_download.setText("Posts left to download: {0}".format(data["total"]))

    def update_main(self, data: Dict) -> None:
        if 'info' in data:
            self.information_label_general.setText(data['info'])
        if 'display_subscriptions' in data:
            if 'username' in data:
                item = QTreeWidgetItem(self.tree)
                item.setText(0, data["username"])
        if 'display_links' in data:
            profile = data["profile"]
            username = QTreeWidgetItem(self.tree_links)
            username.setText(0, profile.username())
            username.setFlags(QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            username.setCheckState(0, QtCore.Qt.Unchecked)

            fmt = "{0} has {1} media that can be downloaded".format(profile.username(),
                                                                    profile.media_count())
            username.setToolTip(0, fmt)

            user_posts = data["posts"]
            for key in user_posts:
                item = QTreeWidgetItem(username)
                item.setText(1, type(user_posts[key]).__name__)
                item.setText(2, user_posts[key].caption())
                item.setText(3, user_posts[key].posted_at())
                item.setText(4, str(user_posts[key].id()))
                item.setFlags(QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable |
                                   QtCore.Qt.ItemIsEnabled)
                item.setCheckState(2, QtCore.Qt.Checked)
                item.setTextAlignment(3, QtCore.Qt.AlignLeft)

            self.tabs.setCurrentWidget(self.links_tab)
            self.grab_links.setEnabled(True)
            root = self.tree_links.invisibleRootItem()
            count = root.childCount()
            if count > 0:
                self.download_links.setEnabled(True)


    def download_files(self) -> None:
        ret = QMessageBox.question(self, 'MessageBox',
                                   "Would you like to start downloading posts?",
                                   QMessageBox.No | QMessageBox.Yes)
        if ret == QMessageBox.No:
            return

        thread = Thread(target = self.download)
        thread.start()
        
       


    def combo_change(self, i: int) -> None:
        self.tree.clear()
        if i == 0:
            self.display_subscriptions(self.subscription_list,
                                       self.data_display)
        elif i == 1:
            self.display_subscriptions(self.expired_subscriptions,
                                       self.data_display)
        elif i == 2:
            self.display_subscriptions(self.all_subscriptions,
                                       self.data_display)

    def check_change(self, state: int) -> None:
        if isinstance(self.sender(), QCheckBox):
            check_name = self.sender().text()
            user = self.current_username
            if user in self.all_subscriptions:
                profile = self.all_subscriptions[user]
                flag = profile.get_flag()
            if state == QtCore.Qt.Checked:
                self.change_flags(user, check_name, profile, flag, True)
                if self.sender() == self.all_checkbox:
                    for x in range(1, len(self.checkboxes)):
                        self.checkboxes[x].setCheckState(QtCore.Qt.Checked)
                if profile.get_flag() == snafylno.ALL:
                    self.all_checkbox.setCheckState(QtCore.Qt.Checked)
            elif state == QtCore.Qt.Unchecked:
                self.change_flags(user, check_name, profile, flag, False)
                if self.sender() == self.all_checkbox:
                    for x in range(1, len(self.checkboxes)):
                        self.checkboxes[x].setCheckState(QtCore.Qt.Unchecked)
                else:
                    if self.all_checkbox.isChecked():
                        self.all_checkbox.setCheckState(QtCore.Qt.PartiallyChecked)
                    if self.all_checkbox.isTristate() and profile.get_flag() == 0:
                        self.all_checkbox.setCheckState(QtCore.Qt.Unchecked)
            elif state == QtCore.Qt.PartiallyChecked:
                if profile.get_flag() == 0:
                    self.all_checkbox.nextCheckState()
                        

    def change_flags(self, user: str, name: str, _profile: snafylno.Profile, flag: int,
                     state: bool) -> None:
        if name == "All":
            flag = (snafylno.ALL | flag) if state is True else \
                   (~snafylno.ALL & flag)
        elif name == "Messages":
            flag = (snafylno.MESSAGES | flag) if state is True else \
                    (~snafylno.MESSAGES & flag)
        elif name == "Audio":
            flag = (snafylno.AUDIO | flag) if state is True else \
                    (~snafylno.AUDIO & flag)
        elif name == "Highlights":
            flag = (snafylno.HIGHLIGHTS | flag) if state is True else \
                    (~snafylno.HIGHLIGHTS & flag)
        elif name == "Stories":
            flag = (snafylno.STORIES | flag) if state is True else \
                    (~snafylno.STORIES & flag)
        elif name == "Posts":
            flag = (snafylno.PICTURES | snafylno.VIDEOS | flag) if state is True else \
                    ~(snafylno.PICTURES | snafylno.VIDEOS) & flag
        elif name == "Archived":
            flag = (snafylno.ARCHIVED | flag) if state is True else \
                    (~snafylno.ARCHIVED & flag)
        _profile.put_flag(flag)
                
    def switch_selections(self, flag) -> None:
        self.message_checkbox.setChecked(QtCore.Qt.Checked) if (flag & snafylno.MESSAGES) else \
                                                            self.message_checkbox.setChecked(QtCore.Qt.Unchecked)
        self.audio_checkbox.setChecked(QtCore.Qt.Checked) if (flag & snafylno.AUDIO) else \
                                                            self.audio_checkbox.setChecked(QtCore.Qt.Unchecked)
        self.highlight_checkbox.setChecked(QtCore.Qt.Checked) if (flag & snafylno.HIGHLIGHTS) else \
                                                              self.highlight_checkbox.setChecked(QtCore.Qt.Unchecked)
        self.story_checkbox.setChecked(QtCore.Qt.Checked) if (flag & snafylno.STORIES) else \
                                                          self.story_checkbox.setChecked(QtCore.Qt.Unchecked)
        self.post_checkbox.setChecked(QtCore.Qt.Checked) if (flag & snafylno.PICTURES or flag & snafylno.VIDEOS) else \
                                                         self.post_checkbox.setChecked(QtCore.Qt.Unchecked)
        self.archived_checkbox.setChecked(QtCore.Qt.Checked) if (flag & snafylno.ARCHIVED) else \
                                                             self.archived_checkbox.setChecked(QtCore.Qt.Unchecked)
        self.all_checkbox.setCheckState(QtCore.Qt.Checked) if ((flag & snafylno.ALL) == snafylno.ALL) else \
                                                           self.all_checkbox.setCheckState(QtCore.Qt.Unchecked)
        
        


    def display_collected_links(self, profiles: Dict,
                                data_display: QtCore.pyqtBoundSignal) -> None:
        self.tree_links.clear()
        for key in profiles:
            profile = profiles[key]
            if profile.get_flag() == 0 or len(profile) < 1:
                continue
            user_posts = profile.fetch_posts()

            data = {}
            data["display_links"] = True
            data["profile"] = profile
            data["posts"] = user_posts
            data_display.emit(data)

    def display_subscriptions(self, subscriptions: Dict,
                              data_display: QtCore.pyqtBoundSignal) -> None:
        for key in subscriptions:
            profile = subscriptions[key]
            username = profile.username()
            data = {}
            data["display_subscriptions"] = True
            data["username"] = username
            data_display.emit(data)


    def display_checkboxes(self, _bool) -> None:
        for checkbox in self.checkboxes:
            checkbox.setEnabled(_bool)




def except_hook(cls, exception, traceback) -> None:
    sys.__excepthook__(cls, exception, traceback)

    
if __name__ == "__main__":
    import sys
    sys.excepthook = except_hook
    
    app = QApplication(sys.argv)

    Main = MainWindow()
    

    sys.exit(app.exec_())
