import json
import logging
from datetime import datetime
from urllib.parse import urljoin, urlparse, urlunsplit, urlencode

import requests
import math
import os
import sqlite3
from sqlite3 import Error
import time as time2
import hashlib

MESSAGES = 0b1000000
PICTURES = 0b0100000
VIDEOS = 0b0010000
HIGHLIGHTS = 0b0001000
STORIES = 0b0000100
ARCHIVED = 0b0000010
AUDIO = 0b0000001

API_PATH = 'https://onlyfans.com/api2/v2/'


class OnlyFans:
    def __init__(self):
        self._add_datetime_to_files = True
        self._active_subs = []
        self._expired_subs = []
        self._all_subs = []
        self._links = []
        self._current_sub_list = []
        self._all_files_size = 0
        self._current_dl = 0
        self._config = {}
        self.filter_list = []
        self._session = requests.Session()
        self._connection, self._cursor = self.get_database()

    @property
    def all_files_size(self):
        return self._all_files_size

    @all_files_size.setter
    def all_files_size(self, file_sizes):
        self._all_files_size = file_sizes

    def _url_generator(self, *path, **query):
        schema_delimiter = '://'
        schema, url = API_PATH.split(schema_delimiter, 1)
        net_lock, *api_path = url.split('/')
        api_path = list(filter(None, api_path))
        path = '/'.join(api_path + list(path))
        if 'app-token' not in query:
            query['app-token'] = self.app_token
        query = urlencode(query)
        return urlunsplit((schema, net_lock, path, query, ''))

    @staticmethod
    def get_database():
        data_base_name = 'onlyfans.sqlite3.db'
        conn = None
        cursor = None
        try:
            conn = sqlite3.connect(data_base_name, check_same_thread=False)
            cursor = conn.cursor()
            raw_sql = ("CREATE TABLE IF NOT EXISTS `entries`"
                       "(`id`	TEXT, `url` TEXT, `userid` TEXT, "
                       "`username` TEXT, `filename` TEXT);")
            cursor.execute(raw_sql)

            # TODO: add another tables by default

            conn.commit()

        except Error as e:
            logging.exception(
                'An exception occurred while connecting to db %s %s',
                data_base_name, e)
        return conn, cursor

    def load_config(self):
        config_name = 'config.json'
        if not os.path.isfile(config_name):
            return
        with open(config_name) as file:
            try:
                self._config = json.load(file)
            except json.JSONDecodeError:
                logging.warning('Config file %s is corrupted', )

        try:
            self.f = open("config.json")

            self.f.close()
            if len(self._config) > 0:
                self.set_values()
        except FileNotFoundError:
            pass

    def set_values(self):
        self.user_agent = self._config["user-agent"]
        self.sess = self._config["cookie"]
        self.app_token = self._config["app-token"]

    def create_sign(self, session, url, sess, user_agent, text="onlyfans"):
        time = str(int(round(time2.time() * 1000 - 301000)))
        path = url.split(".")[1]
        path = path.split("m", 1)[1]
        a = [sess, time, path, user_agent, text]
        msg = "\n".join(a)
        message = msg.encode("utf-8")
        hash_object = hashlib.sha1(message)
        sha_1 = hash_object.hexdigest()
        session.headers["sign"] = sha_1
        session.headers["time"] = time

        return sha_1, time

    def get_sess(self):
        sess = self.sess
        sess = sess[sess.find("sess=") + 5:]
        sess = sess[0:sess.find(";"):]
        return sess

    def get_subscriptions(self):
        if len(self._config) == 0:
            return
        self_url = self._url_generator('users', 'me')
        sub_url = self._url_generator('subscriptions', 'count' 'all')

        self._session.headers = {
            'User-Agent': self.user_agent,
            'Referer': 'https://onlyfans.com',
            'accept': 'application/json, text/plain, */*',
            'Cookie': self.sess,
        }

        self.create_sign(self._session, self_url, self.get_sess(),
                         self.user_agent)

        r = self._session.get(self_url)
        if r.status_code != 200:
            print("Login failed")
            print(r.content)
            return

        self.create_sign(self._session, self_url, self.get_sess(),
                         self.user_agent)
        r = self._session.get(sub_url)

        r = json.loads(r.text)
        count = r["subscriptions"]["all"]

        limit = 99

        subscription_link = self._url_generator('subscriptions',
                                                'subscribes',
                                                limit=limit,
                                                offset='offset_counter')

        for offset in [
                str(offset * limit)
                for offset in range(math.ceil(count / limit))
        ]:
            sub_temp = subscription_link.replace('offset_counter', offset)

            self.create_sign(self._session, sub_temp, self.get_sess(),
                             self.user_agent)
            json_result = self._session.get(sub_temp)
            json_result = json.loads(json_result.content)
            for sub in json_result:
                if sub["subscribedBy"] == True and sub[
                        "username"] not in self._active_subs:
                    self._active_subs.append(sub["username"])
                else:
                    if sub["username"] not in self._expired_subs:
                        self._expired_subs.append(sub["username"])
                if sub["username"] not in self._all_subs:
                    self._all_subs.append(sub["username"])

    def return_active_subs(self):
        return self._active_subs

    def return_expired_subs(self):
        return self._expired_subs

    def return_all_subs(self):
        return self._all_subs

    def get_user_info(self, username):
        link = self._url_generator('users', username)
        return_dict = {}

        self.create_sign(self._session, link, self.get_sess(), self.user_agent)
        r = self._session.get(link)
        json_data = json.loads(r.text)
        if json_data is None:
            return
        if "error" in json_data:
            print(json_data)
            return
        return_dict["photosCount"] = json_data["photosCount"]
        return_dict["videosCount"] = json_data["videosCount"]
        return_dict["audiosCount"] = json_data["audiosCount"]
        return_dict["archivedPostsCount"] = json_data["archivedPostsCount"]
        return_dict["id"] = json_data["id"]
        return_dict["username"] = username

        self._current_sub_list.append(return_dict)

        return return_dict

    def reset_download_size(self):
        self._current_dl = 0
        self._all_files_size = 0

    def get_links(self, info, flag, index):
        if info is None:
            return
        user_id = info["id"]
        images = []
        videos = []
        audio = []
        stories = []
        highlights = []
        archived = []
        total_count = info["photosCount"] + info["videosCount"] + info[
            "audiosCount"]

        limit = 100
        offset_range = math.ceil(total_count / limit)

        offsets = list(range(offset_range))

        str_user_id = str(user_id)

        message_api = self._url_generator('chats',
                                          str_user_id,
                                          'messages',
                                          limit=limit,
                                          offset='',
                                          order='desc')

        users_tuple = ('users', str_user_id)

        post_api = self._url_generator(*users_tuple,
                                       'posts',
                                       limit=limit,
                                       offset='',
                                       order='publish_date_desc')

        stories_api = self._url_generator(*users_tuple,
                                          'stories',
                                          limit=limit,
                                          offset='0',
                                          order='desc')

        archive_api = self._url_generator(*users_tuple,
                                          'posts',
                                          'archived',
                                          limit=limit,
                                          offset='0',
                                          order='publish_date_desc')

        highlight_api = self._url_generator(*users_tuple, 'stories',
                                            'highlights')

        audio_api = self._url_generator(*users_tuple,
                                        'posts',
                                        'audios',
                                        limit=10,
                                        offset='',
                                        order='publish_date_desc')

        if flag & HIGHLIGHTS:
            highlight = self._url_generator('stories', 'highlights')
            r = self._session.get(highlight_api)
            if "error" not in r.text:
                json_hi = json.loads(r.text)
                for js in json_hi:
                    highlight_temp = highlight.replace(
                        "highlights/", "highlights/" + str(js["id"]))

                    self.create_sign(self._session, highlight_temp,
                                     self.get_sess(), self.user_agent)
                    r = self._session.get(highlight_temp)
                    json_data = json.loads(r.text)
                    if "id" in json_data and "createdAt" in json_data and "stories" in json_data:
                        highlight_id = json_data["id"]
                        date = json_data["createdAt"]
                        stories_json = json_data["stories"]
                        for story in stories_json:
                            if "media" in story and "id" in story:
                                media = story["media"]
                                story_id = story["id"]
                                for m in media:
                                    if "source" in m:
                                        src_json = m["source"]
                                        if "source" in src_json:
                                            src = src_json["source"]
                                            file_size = src_json["size"]
                                            if file_size == 0:
                                                r = self._session.head(src)
                                                if "Content-Length" in r.headers:
                                                    file_size = int(r.headers[
                                                        "Content-Length"])
                                            self._all_files_size += file_size
                                            file_dict = {
                                                "source": src,
                                                "size": file_size,
                                                "index": index,
                                                "id": story_id,
                                                "date": date,
                                                "flag": HIGHLIGHTS
                                            }
                                            highlights.append(file_dict)

        if flag & MESSAGES:
            js_message = []
            offset = 0

            self.create_sign(self._session, message_api, self.get_sess(),
                             self.user_agent)
            r = self._session.get(message_api)
            json_data = json.loads(r.text)
            js_message.append(json_data)
            while json_data["hasMore"] == True:
                message_temp = message_api.replace(
                    "offset=", "offset=" + str(offset * 100))
                r = self._session.get(message_temp)
                json_data = json.loads(r.text)
                js_message.append(json_data)
                offset += 1
            for j in js_message:
                if "list" in j:
                    json_list = j["list"]
                    for sec in json_list:
                        if "media" in sec:
                            media = sec["media"]
                            date = sec["createdAt"]
                            for m in media:
                                if "src" in m and "type" in m:
                                    id_post = sec["id"]
                                    type_src = m["type"]
                                    src = m["src"]
                                    if src is None:
                                        continue
                                    m_info = m["info"]
                                    m_info = m_info["source"]
                                    file_size = m_info["size"]

                                    if file_size == 0:
                                        r = self._session.head(src)
                                        if "Content-Length" in r.headers:
                                            file_size = int(
                                                r.headers["Content-Length"])
                                    if type_src == "photo":
                                        self._all_files_size += file_size
                                        file_dict = {
                                            "source": src,
                                            "size": file_size,
                                            "index": index,
                                            "id": id_post,
                                            "date": date,
                                            "flag": MESSAGES
                                        }
                                        images.append(file_dict)
                                    elif type_src == "video":
                                        self._all_files_size += file_size
                                        file_dict = {
                                            "source": src,
                                            "size": file_size,
                                            "index": index,
                                            "id": id_post,
                                            "date": date,
                                            "flag": MESSAGES
                                        }
                                        videos.append(file_dict)
                                    elif type_src == "audio":
                                        self._all_files_size += file_size
                                        file_dict = {
                                            "source": src,
                                            "size": file_size,
                                            "index": index,
                                            "id": id_post,
                                            "date": date,
                                            "flag": MESSAGES
                                        }
                                        audio.append(file_dict)

        if flag & PICTURES or flag & VIDEOS:
            json_data = []
            for n in offsets:
                offset = str(n * 100)
                post_tmp = post_api.replace("offset=", "offset=" + offset)

                self.create_sign(self._session, post_tmp, self.get_sess(),
                                 self.user_agent)
                r = self._session.get(post_tmp)
                json_data.append(json.loads(r.text))

            self.create_sign(self._session, stories_api, self.get_sess(),
                             self.user_agent)
            r = self._session.get(stories_api)
            js = json.loads(r.text)
            for j in js:
                if "media" in j and "createdAt" in j:
                    m = j["media"]
                    date = j["createdAt"]
                    post_id = j["id"]
                    for media in m:
                        if "source" in media:
                            file_details = media["source"]
                            if "source" in file_details and "size" in file_details:
                                src = file_details["source"]
                                file_size = file_details["size"]

                                if file_size == 0:
                                    r = self._session.head(src)
                                    if "Content-Length" in r.headers:
                                        file_size = int(
                                            r.headers["Content-Length"])
                                file_dict = {
                                    "source": src,
                                    "size": file_size,
                                    "index": index,
                                    "id": post_id,
                                    "date": date,
                                    "flag": STORIES
                                }
                                stories.append(file_dict)

        if flag & PICTURES:
            for j in json_data:
                for js in j:
                    if "postedAt" in js and "media" in js and "id" in js:
                        date = js["postedAt"]
                        media = js["media"]
                        id_post = js["id"]
                        for m in media:
                            if "source" in m:
                                file_details = m["source"]
                                if "size" in file_details and "source" in file_details:
                                    file_size = file_details["size"]
                                    type_src = file_details["source"]
                                    if type_src is None or not type_src.startswith(
                                            'https://cdn'):
                                        continue
                                    if file_size == 0:
                                        r = self._session.head(type_src)
                                        if "Content-Length" in r.headers:
                                            file_size = int(
                                                r.headers["Content-Length"])
                                    if ".jpg" in type_src or ".jpeg" in type_src or ".png" in type_src:
                                        self._all_files_size += file_size
                                        file_dict = {
                                            "source": type_src,
                                            "size": file_size,
                                            "index": index,
                                            "id": id_post,
                                            "date": date,
                                            "flag": PICTURES
                                        }
                                        images.append(file_dict)

        if flag & VIDEOS:
            for j in json_data:
                for js in j:
                    if "postedAt" in js and "media" in js and "id" in js:
                        date = js["postedAt"]
                        media = js["media"]
                        id_post = js["id"]
                        for m in media:
                            if "source" in m:
                                file_details = m["source"]
                                if "size" in file_details and "source" in file_details:
                                    file_size = file_details["size"]
                                    type_src = file_details["source"]
                                    if type_src is None or not type_src.startswith(
                                            'https://cdn'):
                                        continue

                                    if file_size == 0:
                                        r = self._session.head(type_src)
                                        if "Content-Length" in r.headers:
                                            file_size = int(
                                                r.headers["Content-Length"])

                                    if ".mp4" in type_src:
                                        self._all_files_size += file_size
                                        file_dict = {
                                            "source": type_src,
                                            "size": file_size,
                                            "index": index,
                                            "id": id_post,
                                            "date": date,
                                            "flag": VIDEOS
                                        }
                                        videos.append(file_dict)

        if flag & ARCHIVED:
            cnt = info["archivedPostsCount"]
            off_range = math.ceil(cnt / 100)
            offsets_arch = list(range(off_range))

            for off in offsets_arch:
                arch_temp = archive_api.replace("offset=",
                                                "offset=" + str(off))

                self.create_sign(self._session, arch_temp, self.get_sess(),
                                 self.user_agent)
                r = self._session.get(arch_temp)
                js = json.loads(r.text)

                for j in js:
                    if "postedAt" in j and "media" in j and "id" in j:
                        date = j["postedAt"]
                        media = j["media"]
                        id_post = j["id"]
                        for m in media:
                            if "source" in m:
                                file_details = m["source"]
                                if "size" in file_details and "source" in file_details:
                                    file_size = file_details["size"]
                                    type_src = file_details["source"]
                                if type_src is None or not type_src.startswith(
                                        'https://cdn'):
                                    continue

                                if file_size == 0:
                                    r = self._session.head(type_src)
                                    if "Content-Length" in r.headers:
                                        file_size = int(
                                            r.headers["Content-Length"])
                                if ".mp4" in type_src:
                                    self._all_files_size += file_size
                                    file_dict = {
                                        "source": type_src,
                                        "size": file_size,
                                        "index": index,
                                        "id": id_post,
                                        "date": date,
                                        "flag": ARCHIVED
                                    }
                                    archived.append(file_dict)
                                if ".jpg" in type_src or ".jpeg" in type_src or ".png" in type_src:
                                    self._all_files_size += file_size
                                    file_dict = {
                                        "source": type_src,
                                        "size": file_size,
                                        "index": index,
                                        "id": id_post,
                                        "date": date,
                                        "flag": ARCHIVED
                                    }
                                    archived.append(file_dict)

        if flag & AUDIO:
            cnt = info["audiosCount"]
            off_range = math.ceil(cnt / 10)
            offsets_arch = list(range(off_range))

            for off in offsets_arch:
                audio_api = audio_api.replace("offset=", "offset=" + str(off))

                self.create_sign(self._session, audio_api, self.get_sess(),
                                 self.user_agent)
                r = self._session.get(audio_api)
                js = json.loads(r.text)

                for j in js:
                    if "postedAt" in j and "media" in j and "id" in j:
                        date = j["postedAt"]
                        media = j["media"]
                        id_post = j["id"]
                        for m in media:
                            if "source" in m:
                                file_details = m["source"]
                                if "size" in file_details and "source" in file_details:
                                    file_size = file_details["size"]
                                    type_src = file_details["source"]
                                if type_src is None or not type_src.startswith(
                                        'https://cdn'):
                                    continue
                                if ".mp3" in type_src:
                                    self._all_files_size += file_size
                                    file_dict = {
                                        "source": type_src,
                                        "size": file_size,
                                        "index": index,
                                        "id": id_post,
                                        "date": date,
                                        "flag": AUDIO
                                    }
                                    audio.append(file_dict)

        self._links += stories + highlights + images + videos + audio + archived

        list_copy = self._links.copy()

        for link in list_copy:
            filename = link["source"].split('/')[-1]
            filename = filename.split('?')[0]
            if self.select_database(user_id, filename):
                self._links.remove(link)
                self._all_files_size -= link["size"]

    def select_database(self, userid, filename):
        try:
            self._cursor.execute(
                "SELECT * FROM entries where userid = ? AND filename = ?", (
                    userid,
                    filename,
                ))
            return len(self._cursor.fetchall())
        except Error:
            return False

    def insert_database(self, info, file):
        id_user = info["id"]
        username = info["username"]

        url = file["source"].split('?')[0]
        post_id = file["id"]
        File_Name = url.split('/')[-1]
        try:
            c = self._connection.cursor()
            c.execute('INSERT INTO entries VALUES(?,?,?,?,?)',
                      (str(post_id), str(url), str(id_user), str(username),
                       str(File_Name)))
            self._connection.commit()
        except sqlite3.IntegrityError:
            pass

    def return_links(self):
        return self._links

    def clear_links(self):
        if len(self._links) > 0:
            del self._links[:]

    def subscript_array(self, ind):
        if ind < len(self._current_sub_list):
            return self._current_sub_list[ind]["username"]
        return ""

    def return_user_array(self):
        return self._current_sub_list

    def clear_array(self):
        if len(self._current_sub_list) > 0:
            del self._current_sub_list[:]

    def clear_filter(self):
        if len(self.filter_list) > 0:
            del self.filter_list[:]

    def download(self, obj, folder, file):

        use_local_tz = False  # TODO: need to add in the GUI

        file_name = file["source"]
        flag = file["flag"]
        File_Extension = file_name.split('.')[-1]
        File_Extension = File_Extension.split('?')[0]
        File_Name = file_name.split('/')[-1]
        File_Name = File_Name.split('?')[0]
        try:
            if self._add_datetime_to_files and 'date' in file:
                file_datetime = datetime.fromisoformat(file['date'])
                if use_local_tz:
                    file_datetime = file_datetime.replace()
                str_datetime = file_datetime.strftime('%Y-%m-%d_%H-%M-%S')
                File_Name = f'{str_datetime}_{File_Name}'

        except ValueError:
            pass  # incorrect datetime format, skipped...
        total_download = self._all_files_size
        directory = ""

        if flag & MESSAGES:
            directory = "Messages"
        elif flag & VIDEOS or flag & PICTURES:
            directory = "Posts"
        elif flag & HIGHLIGHTS:
            directory = "Highlights"
        elif flag & STORIES:
            directory = "Stories"
        elif flag & ARCHIVED:
            directory = "Archived"

        self.create_dir(folder + "/" + directory)

        if File_Extension == "jpg" or File_Extension == "jpeg" or File_Extension == "png":
            self.create_dir(folder + "/" + directory + "/Images")
            if os.path.isfile("Files/" + folder + "/" + directory +
                              "/Images/" + File_Name) == False:
                with open(
                        "Files/" + folder + "/" + directory + "/Images/" +
                        File_Name, "wb") as file:
                    response = self._session.get(file_name, stream=True)
                    tmp = response.headers.get('content-length')
                    if tmp is None:
                        file.write(response.content)
                    else:
                        total_length = int(tmp)
                        for data in response.iter_content(chunk_size=4096):
                            self._current_dl += len(data)
                            obj.ProgressBar['value'] = (self._current_dl /
                                                        total_download) * 100
                            file.write(data)

        elif File_Extension == "mp4":
            self.create_dir(folder + "/" + directory + "/Videos")
            if os.path.isfile("Files/" + folder + "/" + directory +
                              "/Videos/" + File_Name) == False:
                with open(
                        "Files/" + folder + "/" + directory + "/Videos/" +
                        File_Name, "wb") as file:
                    response = self._session.get(file_name, stream=True)
                    tmp = response.headers.get('content-length')
                    if tmp is None:
                        file.write(response.content)
                    else:
                        total_length = int(tmp)
                        for data in response.iter_content(chunk_size=4096):
                            self._current_dl += len(data)
                            obj.ProgressBar['value'] = (self._current_dl /
                                                        total_download) * 100
                            file.write(data)

        elif File_Extension == "mp3":
            self.create_dir(folder + "/" + directory + "/Audio")
            if os.path.isfile("Files/" + folder + "/" + directory + "/Audio/" +
                              File_Name) == False:
                with open(
                        "Files/" + folder + "/" + directory + "/Audio/" +
                        File_Name, "wb") as file:
                    response = self._session.get(file_name, stream=True)
                    tmp = response.headers.get('content-length')
                    if tmp is None:
                        file.write(response.content)
                    else:
                        total_length = int(tmp)
                        for data in response.iter_content(chunk_size=4096):
                            self._current_dl += len(data)
                            obj.ProgressBar['value'] = (self._current_dl /
                                                        total_download) * 100
                            file.write(data)

        else:
            self.create_dir(folder + "/" + directory + "/Misc")
            if os.path.isfile("Files/" + folder + "/" + directory + "/Misc/" +
                              File_Name) == False:
                with open(
                        "Files/" + folder + "/" + directory + "/Misc/" +
                        File_Name, "wb") as file:
                    response = self._session.get(file_name, stream=True)
                    tmp = response.headers.get('content-length')
                    if tmp is None:
                        file.write(response.content)
                    else:
                        total_length = int(tmp)
                        for data in response.iter_content(chunk_size=4096):
                            self._current_dl += len(data)
                            obj.ProgressBar['value'] = (self._current_dl /
                                                        total_download) * 100
                            file.write(data)

    def create_dir(self, dirname):
        try:
            os.mkdir("Files/" + dirname)
        except FileExistsError:
            pass
