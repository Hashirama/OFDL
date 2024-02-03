import os
import json
import math
import time
import sqlite3
import requests
import hashlib
import datetime
import threading
from typing import *
from queue import Queue
from PyQt5 import QtCore
from sqlite3 import Error
from threading import Thread
from PyQt5.QtCore import pyqtSignal, QObject

ALL         = 0b1111111
MESSAGES    = 0b1000000
PICTURES    = 0b0100000
VIDEOS      = 0b0010000
HIGHLIGHTS  = 0b0001000
STORIES     = 0b0000100
ARCHIVED    = 0b0000010
AUDIO       = 0b0000001

def dynamic_rules():
    url = "https://raw.githubusercontent.com/hashypooh/dynamic_stuff/main/sign.json"
    r = requests.get(url)
    dynamic_json = json.loads(r.text)
    return dynamic_json

dynamic_r = dynamic_rules()


class Worker(Thread):
    def __init__(self, tasks, stop_event: threading.Event) -> None:
        Thread.__init__(self)
        self.tasks = tasks
        self.daemon = True
        self.stop_event = stop_event
        self.start()
    
    def run(self) -> None:
        while not self.stop_event.isSet():
            func, args, kargs = self.tasks.get()
            try: func(*args, **kargs)
            except Exception as e:
                print (e)
            self.tasks.task_done()

class ThreadPool:
    def __init__(self, num_threads: int, stop_event: threading.Event) -> None:
        self.tasks = Queue(num_threads)
        for _ in range(num_threads):
            Worker(self.tasks, stop_event)

    def add_task(self, func, *args: Tuple, **kargs: Dict) -> None:
        self.tasks.put((func, args, kargs))

    def wait_completion(self) -> None:
        self.tasks.join()

class Date:
    def __init__(self, date_time: str) -> None:
        self.date_time = datetime
        try:
            self.dt = datetime.datetime.fromisoformat(date_time)
        except ValueError:
            self.alt_dt = date_time
        
    def date(self) -> str:
        if hasattr(self, 'alt_dt'):
            return self.alt_dt
        return self.dt.strftime("%a,  %d  %B  %Y")
    

class Config:
    def __init__(self, filename: str) -> None:
        self.data = {}
        self.filename = filename
        try:
            file = open(filename, 'r')
            self.data = json.load(file)
            file.close()
        except FileNotFoundError:
            self.write_to_disk()

    def hash(self) -> str:
        if "hash" in self.data:
            return self.data["hash"]
        else: return ""
            

    def user_agent(self) -> str:
        if "user-agent" in self.data:
            return self.data["user-agent"]
        else: return ""
    
    def cookie(self) -> str:
        if "cookie" in self.data:
            return self.data["cookie"]
        else: return ""
    
    def app_token(self) -> str:
        if "app-token" in self.data:
            return self.data["app-token"]
        else:
            self.data["app-token"] = dynamic_r["app_token"]
            self.write_to_disk()
            return self.data["app-token"]
        return ""

    def x_bc(self) -> str:
        if "x-bc" in self.data:
            return self.data["x-bc"]
        else: return ""

    def add_node(self, title: str, text: str) -> None:
        if len(text) > 0:
            self.data[title] = text
            self.write_to_disk()

    def write_to_disk(self) -> None:
        with open(self.filename, 'w') as file:
            json.dump(self.data, file)
            

    def __len__(self) -> int:
        return len(self.data)

    @classmethod
    def create_dir(cls, dirname) -> str:
        if cls is None or dirname is None:
            return
        try:
            path = "Files/{0}".format(dirname)
            if not os.path.isdir(path):
                os.makedirs(path)
        except FileExistsError:
            pass
        finally:
            return path


class MediaItem:
    def __init__(self, data: dict) -> None:
        self.data = data

    def download(self, path: str, total: int) -> None:
        tmp_path = Config.create_dir(path)
        if tmp_path is None:
            return
        if os.path.isfile(tmp_path + self.filename()) == False:
            with open(tmp_path + self.filename(), "wb") as file:
                response = requests.get(self.url(), stream = True)
                tmp = response.headers.get('content-length')
                if tmp is None:
                    file.write(response.content)
                else:
                    total_length = int(tmp)
                    for data in response.iter_content(chunk_size = 4096):
                        file.write(data)
                        

    def __len__(self) -> int:
        return 1

    def media_count(self) -> int:
        return self.__len__()

    def id(self) -> int:
        return self.data["id"]

    def item_type(self) -> str:
        return self.data["type"]

    def filename(self) -> str:
        url = self.url().split('/')[-1].split('?')[0]
        return url

    def username(self) -> str:
        return self.data["username"]

    def user_id(self) -> int:
        return self.data["user_id"]
        
    def url(self) -> str:
        src = ""
        if "info" in self.data:
            info = self.data["info"]
            if info["source"] is not None:
                source = info["source"]
                if source["source"] is not None:
                    src = source["source"]
        if 'files' in self.data:
            files = self.data["files"]
            if 'source' in files:
                source = files["source"]
                if 'url' in source:
                    src = source["url"]
        return src
            

    def width(self) -> int:
        width = 0
        info = self.data["info"]
        if info["source"] is not None:
            source = info["source"]
            if source["source"] is not None:
                width = source["width"]
        return width

    def height(self) -> int:
        height = 0
        info = self.data["info"]
        if info["source"] is not None:
            source = info["source"]
            if source["source"] is not None:
                height = source["height"]
        return height

    def file_extension(self) -> str:
        file = self.url().split('.')[-1]
        file = file.split('?')[0]
        return file

    @classmethod
    def file_size(self, size: int) -> str:
        unit = ["KB", "MB", "GB", "TB"]
        count = -1
        if size < 1024:
            return str(size) + "B"
        else:
            while size >= 1024:
                size /= 1024
                count += 1
        return str('%.2f ' % size) + unit[count]
    

    @classmethod
    def media_items(cls, data: dict) -> Dict:
        media = {}
        def make(_data: dict):
            return cls(_data)
        
        media[data["id"]] = make(data)
        return media

class Post:
    def __init__(self, data: dict) -> None:
        self.media = {}
        self.data = data
        self.parse_media(data)

    def __len__(self) -> int:
        return len(self.media)

    def username(self) -> str:
        if "author" in self.data:
            if "username" in self.data["author"]:
                return self.data["author"]["username"]
        return ""

    def user_id(self) -> str:
        if "author" in self.data:
            if "id" in self.data["author"]:
                return self.data["author"]["id"]
        return ""

    def download(self, display_data: QtCore.pyqtBoundSignal, lock: threading.Lock,
                 conn: sqlite3.Connection, total: List[int]) -> None:
        data = {}
        for media_id, media in self.media.items():
            path = "{0}/{1}/{2}/".format(self.username(), type(self).__name__, media.item_type())
            if conn.does_exist(self.user_id(), self.id(), media.filename()) is not True:
                media.download(path, total)
                conn.insert_database(self, media)
            with lock:
                total[0] = total[0] - 1

            data["username"] = self.username()
            data["path"] = path
            data["filename"] = media.filename()
            data["total"] = total[0]
            display_data.emit(data)


    def can_view(self) -> bool:
        return self.data["canViewMedia"]

    def get_media(self) -> Dict:
        return self.media

    def parse_media(self, data: dict) -> None:
        if "media" in data:
            media = data["media"]
            for item in media:
                info = item["info"]
                source = info["source"]
                if source["source"] is None:
                    continue
                else:
                    media_items = MediaItem.media_items(item)
                    self.media |= media_items
                

    def id(self) -> int:
        return self.data["id"]

    def posted_at(self) -> str:
        return Date(self.data["postedAt"]).date()

    def media_count(self) -> int:
        return len(self.media)
    
    def caption(self) -> str:
        return self.data["rawText"]
    
    @classmethod
    def post_items(cls, data: dict) -> Dict:
        post = {}
        def make(_data):
            return cls(_data)

        post[data["id"]] = make(data)
        return post

class Archived(Post):
    def __init__(self, data: dict) -> None:
        super().__init__(data)

class Story(Post):
    def __init__(self, data: dict) -> None:
        super().__init__(data)

    def parse_media(self, data: dict) -> None:
        if 'media' in data:
            medium = data["media"]
            for media in medium:
                media_items = MediaItem.media_items(media)
                self.media |= media_items

    def username(self):
        if 'username' in self.data:
            return self.data["username"]

    def caption(self) -> str:
        return type(self).__name__

    def posted_at(self) -> str:
        return Date(self.data["createdAt"]).date()

    def can_view(self) -> bool:
        if 'canView' in self.data:
            return self.data['canView']
        return True
    


class Highlight(Post):
    def __init__(self, data: dict) -> None:
        super().__init__(data)

    def parse_media(self, data: dict) -> None:
        if "stories" in data:
            stories = data["stories"]
            for story in stories:
                if "media" in story:
                    medium = story["media"]
                    for media in medium:
                        media_items = MediaItem.media_items(media)
                        self.media |= media_items

    def username(self) -> str:
        if "username" in self.data:
            return self.data["username"]
        return ""

    def can_view(self) -> bool:
        return True

    def caption(self) -> str:
        return self.data["title"]

    def media_count(self) -> int:
        return self.data["storiesCount"]

    def posted_at(self) -> str:
        return Date(self.data["createdAt"]).date()


class MessageItem(MediaItem):
    def __init__(self, data: dict) -> None:
        super().__init__(data)
        self.info = data["info"]
        self.source = self.info["source"]

    def download(self, display_data: QtCore.pyqtBoundSignal, lock: threading.Lock,
                 conn: sqlite3.Connection, total: List[int]) -> None:
        data = {}
        path = "{0}/{1}/{2}/".format(self.username(), type(self).__name__, self.item_type()) #maybe none
        if conn.does_exist(self.user_id(), self.id(), self.filename()) is not True:
            super().download(path, total)
            conn.insert_database(self, self)
        with lock:
            total[0] = total[0] - 1

        data["username"] = self.username()
        data["path"] = path
        data["filename"] = self.filename()
        data["total"] = total[0]
        display_data.emit(data)


    def posted_at(self) -> str:
        return Date(self.data["createdAt"]).date()

    def url(self) -> str:
        return self.data["src"]

    def width(self) -> int:
        return self.source["width"]
    
    def height(self) -> int:
        return self.source["height"]

    def thumbnail(self) -> str:
        return self.data["thumb"]

    def can_view(self) -> bool:
        return self.data["canView"]

    def duration(self) -> int:
        return self.data["duration"]
    
    def caption(self) -> str:
        return self.data["caption"]

    def get_media(self) -> "MessageItem":
        return self


class Profile:
    def __init__(self, data) -> None:
        self.data = data
        self.info = {}
        self.flags = 0
        self.gathered_flags = 0
        self.posts = {}
        self.error = False
        self.lock = threading.Lock()

    def __len__(self) -> int:
        return len(self.fetch_posts())

    def set_error(self) -> bool:
        self.error = True
        return self.error

    def error_set(self) -> bool:
        return self.error


    def download(self, stop_event, display_data: QtCore.pyqtBoundSignal,
                 post_ids: list[int],
                 total: List[int]) -> None:
        data = {}
        pool = ThreadPool(2, stop_event)
        data["info"] = "Downloading..."
        display_data.emit(data)
        for post_id in post_ids:
            conn = Database("onlyfans.sqlite3.db")
            _post = self.fetch_posts()[int(post_id)]
            pool.add_task(_post.download, display_data, self.lock, conn, total)
        pool.wait_completion()
        if total[0] == 0:
            data["info"] = "Completed..."
            display_data.emit(data)

    def fetch_posts(self) -> Dict:
        entire_list = {key : self.posts[key] for key in self.posts if len(self.posts[key]) > 0}
        result = entire_list.copy()
        for key, value in entire_list.items():
            _type = type(value).__name__
            flags = self.get_flag()
            if not (flags & MESSAGES) and _type == "MessageItem" or \
               not (flags & PICTURES) and _type == "Post" or \
               not (flags & VIDEOS) and _type == "Post" or \
               not (flags & HIGHLIGHTS) and _type == "Highlight" or \
               not (flags & STORIES) and _type == "Story" or \
               not (flags & ARCHIVED) and _type == "Archived" or \
               not (flags & AUDIO) and _type == "Audio":
                del result[key]
                
        return result

    def post_count(self) -> int:
        return len(self.posts)

    def media_count(self) -> int:
        total = 0
        posts = self.fetch_posts()
        for key in posts:
            post = posts[key]
            if post.can_view():
                total += post.media_count()
        return total

    def parse_posts(self, data: dict) -> None:
        posts = {}
        if "Highlight" in data:
            posts |= Highlight.post_items(data)
        elif "list" in data and "Message" in data:
            node_list = data["list"]
            for node in node_list:
                media = node["media"]
                for m in media:
                    if 'canView' in m:
                        canView = m["canView"]
                        if canView is False:
                            continue
                        text = node["text"]
                        created_at = node["createdAt"]
                        m["createdAt"] = Date(created_at).date() 
                        m["caption"] = text
                        m["username"] = node["fromUser"]["username"]
                        m["user_id"] = node["fromUser"]["id"]
                        posts |= MessageItem.media_items(m)
        elif "Story" in data:
            posts |= Story.post_items(data)
        elif "Archived" in data:
            posts |= Archived.post_items(data)
        elif "Post" in data:
            posts |= Post.post_items(data)
                
        self.posts |= posts

    def get_flag(self) -> int:
        return self.flags
    
    def put_flag(self, flag: int) -> None:
        self.flags = flag

    def set_info(self, info: dict) -> None:
        self.info = info

    def is_active(self) -> bool:
        return self.data["subscribedBy"] == True

    def username(self) -> str:
        return self.data["username"]

    def avatar(self) -> str:
        return self.data["avatar"]

    def sm_avatar(self, size: int) -> str: 
        if self.data["avatarThumbs"] is not None:
            if size == 50:
                return self.data["avatarThumbs"]["c50"]
            else:
                return self.data["avatarThumbs"]["c144"]
        else:
            return ""

    def id(self) -> int:
        return self.data["id"]

    def photo_count(self) -> int:
        if len(self.info) > 0: return self.info["photosCount"]

    def videos_count(self) -> int:
        if len(self.info) > 0: return self.info["videosCount"]

    def audio_count(self) -> int:
        if len(self.info) > 0: return self.info["audiosCount"]

    def archive_count(self) -> int:
        if len(self.info) > 0: return self.info["archivedPostsCount"]

    @classmethod
    def profile_items(cls, data: dict) -> Dict:
        profiles = {}
        def make(_data):
            return cls(_data)

        for node in data:
            profiles[node["username"]] = make(node)
        return profiles            
            
        
    
class Onlyfans(QtCore.QObject):
    data_display = QtCore.pyqtSignal(object)
    stop_event = threading.Event()
    def __init__(self) -> None:
        QtCore.QObject.__init__(self)
        self.profiles = {}
        self.session = requests.Session()
        self.set_session_headers()
        self.logged_in = self.user_logged_in()
        
        self.base_url = "https://onlyfans.com/"
        self.login = "https://onlyfans.com/api2/v2/users/login"
        self.customer = "https://onlyfans.com/api2/v2/users/me"
        self.users = "https://onlyfans.com/api2/v2/users/{0}"
        self.message_api = "https://onlyfans.com/api2/v2/chats/{0}/messages?limit={1}&offset={2}&order=desc"
        self.stories_api = "https://onlyfans.com/api2/v2/users/{0}/stories?limit=100&offset={1}&order=desc"
        self.list_highlights = "https://onlyfans.com/api2/v2/users/{0}/stories/highlights?limit=100&offset={1}&order=desc"
        self.highlight = "https://onlyfans.com/api2/v2/stories/highlights/{0}"
        self.post_api = "https://onlyfans.com/api2/v2/users/{0}/posts?limit={1}&offset={2}&order=publish_date_desc&skip_users_dups=0"
        self.archived_posts = "https://onlyfans.com/api2/v2/users/{0}/posts/archived?limit=100&offset={1}&order=publish_date_desc"
        self.subscribe = "https://onlyfans.com/api2/v2/users/{identifier}/subscribe"
        self.audio = "https://onlyfans.com/api2/v2/users/{0}/posts/audios?limit=10&offset={1}&order=publish_date_desc&skip_users=all&counters=0&format=infinite"
        self.subscription_count = "https://onlyfans.com/api2/v2/subscriptions/count/all"
        self.subscriptions = "https://onlyfans.com/api2/v2/subscriptions/subscribes?offset={0}&type=all&sort=desc&field=expire_date&limit=10"


    def signal_stop_event(self) -> None:
        self.stop_event.set()
        
                
    def user_logged_in(self) -> bool:
        data = {}
        settings = {}
        additional = {}
        data["info"] = "Attempting to log in"
        self.data_display.emit(data)
        self.set_session_headers()
        self.init_url = "https://onlyfans.com/api2/v2/init"
        self.create_sign(self.session, self.init_url)
        r = self.session.get(self.init_url)
        if r.status_code != 200:
            return False
        json_response = json.loads(r.text)
        if "settings" in json_response:
            settings = json_response["settings"]
        if "upload" in json_response and "geoUploadArgs" in json_response["upload"] and \
           "additional" in json_response["upload"]["geoUploadArgs"]:
            additional = json_response["upload"]["geoUploadArgs"]["additional"]

        if "isAuth" in json_response:
            return json_response["isAuth"]
        elif "userLoginPrefix" in settings and "user" in additional:
            if len(settings["userLoginPrefix"]) > 0 and len(additional["user"]) > 0:
                return True
        return False


    def set_session_headers(self) -> None:
        self.load_config()
        self.session.headers = {
            'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36",
            'Referer': 'https://onlyfans.com/',
            'accept': 'application/json, text/plain, */*',
            'app-token': dynamic_r["app_token"],
            'accept-encoding': 'gzip, deflate, br'
        }
        if hasattr(self, 'user_agent') and hasattr(self, 'cookie') and hasattr(self, 'x_bc'):
            if len(self.user_agent) > 0 and len(self.cookie) > 0 and len(self.app_token) > 0 and \
               len(self.x_bc) > 0:
                self.session.headers = {
                    'User-Agent': self.user_agent,
                    'Referer': 'https://onlyfans.com/',
                    'accept': 'application/json, text/plain, */*',
                    'Cookie' : self.cookie,
                    'app-token': self.app_token,
                    'x-bc': self.x_bc,
                    'accept-encoding': 'gzip, deflate, br'
                }

    def download_profiles(self, user_post_ids: dict, total: List[int]) -> None:
        pool = ThreadPool(2, self.stop_event)
        profiles = self.return_all_subs()
        for username_key in user_post_ids:
            profile = profiles[username_key]
            data = {}
            data["info"] = "Starting download..."
            self.data_display.emit(data)
            pool.add_task(profile.download, self.stop_event, self.data_display,
                          user_post_ids[username_key], total)
        
            
        
    
    def load_config(self) -> None:
        config = Config("config.json")
        if len(config) > 0:
            self.user_agent = config.user_agent()
            self.cookie = config.cookie()
            self.app_token = config.app_token()
            self.x_bc = config.x_bc()
        self.config = config

    def is_config_empty(self) -> int:
        return len(self.config) == 0

    @classmethod
    def create_sign(self, session: requests.sessions.Session, link: str) -> None:
        _time = str(int(round(time.time() * 1000)))
        index = link.find('//') + 2
        index = link.find('/', index)
        path = link[index:]
        msg = "\n".join([dynamic_r["static_param"], _time, path, str(0)])
        message = msg.encode("utf-8")
        _hash = hashlib.sha1(message)
        sha1 = _hash.hexdigest()
        sha1_enc = sha1.encode("ascii")
        checksum = (
            sum([sha1_enc[number] for number in dynamic_r["checksum_indexes"]])
            + sum(number for number in dynamic_r["checksum_constants"])
        )
        session.headers["sign"] = dynamic_r["sign_format"].format(sha1, format(abs(checksum), 'x'))
        session.headers["time"] = _time


    def get_subscriptions(self) -> int:
        if len(self.profiles) > 0:
            return len(self.profiles)
        global_limit = 10
        global_offset = 0

        if self.user_logged_in() is not True:
            print ("Login failed")
            return

        users = []
        
        while True:
            temp_sub = self.subscriptions.format(global_offset)
            self.create_sign(self.session, temp_sub)
            r = self.session.get(temp_sub)
            if len(r.text) > 0:
                r = json.loads(r.text)
                users.append(r)
                global_offset += 10
                if len(r) == 0:
                    break

        for user in users:
            profile = Profile.profile_items(user)
            self.profiles |= profile

        count = len(self.profiles)
        return count


    def return_active_subs(self) -> Dict:
        active_subscriptions = {}
        for key in self.profiles:
            profile = self.profiles[key]
            if profile.is_active():
                active_subscriptions[key] = profile
        return active_subscriptions
        

    def return_expired_subs(self) -> Dict:
        expired_subscriptions = {}
        for key in self.profiles:
            profile = self.profiles[key]
            if not profile.is_active():
                expired_subscriptions[key] = profile
        return expired_subscriptions

    def return_all_subs(self) -> Dict:
        return self.profiles

    def get_user_info(self, profile) -> bool:
        if len(profile.info) > 0:
            return True
        link = self.users.format(profile.username())

        self.create_sign(self.session, link)
        r = self.session.get(link)
        json_data = json.loads(r.text)

        if json_data is None:
            return False
        if "error" in json_data:
            if profile.error_set() is False:
                profile.set_error()
            print (json_data)
            return False

        profile.set_info(json_data)
        return True


    def get_links(self, profile):
        total_post = profile.photo_count() + profile.videos_count()
        audio_count = profile.audio_count()
        limit = 100
        flag = profile.get_flag()

        if ((flag & PICTURES) or (flag & VIDEOS)) and \
        not (profile.gathered_flags & (PICTURES | VIDEOS)):
            offset_range = math.ceil(total_post / 100)
            offsets = list(range(offset_range))
            for offset in offsets:
                new_offset = offset * 100
                link = self.post_api.format(profile.id(), limit, new_offset)
                self.create_sign(self.session, link)
                r = self.session.get(link)
                if(len(r.text)) > 0:
                    json_data = json.loads(r.text)
                    for node in json_data:
                        node["Post"] = True
                        profile.parse_posts(node)
                        profile.gathered_flags |= (PICTURES | VIDEOS)

        if (flag & AUDIO) and not (profile.gathered_flags & AUDIO):
            offset_range = math.ceil(audio_count / 10)
            offsets = list(range(offset_range))
            for offset in offsets:
                new_offset = offset * 10
                link = self.audio.format(profile.id(), new_offset)
                self.create_sign(self.session, link)
                r = self.session.get(link)
                json_data = json.loads(r.text)
                if "list" in json_data:
                    profile.parse_posts(json_data["list"])
                    profile.gathered_flags |= AUDIO

        if (flag & STORIES) and not (profile.gathered_flags & STORIES):
            link = self.stories_api.format(profile.id(), 0)
            self.create_sign(self.session, link)
            r = self.session.get(link)
            json_data = json.loads(r.text)
            for node in json_data:
                node["Story"] = True
                node["username"] = profile.username()
                profile.parse_posts(node)
                profile.gathered_flags |= STORIES

        if (flag & HIGHLIGHTS) and not (profile.gathered_flags & HIGHLIGHTS):
            link = self.list_highlights.format(profile.id(), 0)
            self.create_sign(self.session, link)
            r = self.session.get(link)
            json_data = json.loads(r.text)
            if 'list' in json_data:
                for node in json_data["list"]:
                    highlight_id = node["id"]
                    link = self.highlight.format(highlight_id)
                    self.create_sign(self.session, link)
                    r = self.session.get(link)
                    _json_data = json.loads(r.text)
                    _json_data["Highlight"] = True
                    _json_data["username"] = profile.username()
                    profile.parse_posts(_json_data)
                    profile.gathered_flags |= HIGHLIGHTS

        if (flag & MESSAGES) and not (profile.gathered_flags & MESSAGES):
            offset = 0
            link = self.message_api.format(profile.id(), limit, offset)
            self.create_sign(self.session, link)
            r = self.session.get(link)
            json_data = json.loads(r.text)
            json_data["Message"] = True
            profile.parse_posts(json_data)
            if "hasMore" in json_data:
                hasMore = json_data["hasMore"]
                while hasMore:
                    offset += limit
                    link = self.message_api.format(profile.id(), limit, offset)
                    self.create_sign(self.session, link)
                    r = self.session.get(link)
                    _json_data = json.loads(r.text)
                    _json_data["Message"] = True
                    if "list" in _json_data:
                        if len(_json_data["list"]) > 0:
                            profile.parse_posts(_json_data)
                    hasMore = _json_data["hasMore"]
                    profile.gathered_flags |= MESSAGES

        if (flag & ARCHIVED) and not (profile.gathered_flags & ARCHIVED):
            count = profile.archive_count()
            offset_range = math.ceil(count / 100)
            offsets = list(range(offset_range))
            for offset in offsets:
                new_offset = offset * 100
                link = self.archived_posts.format(profile.id(), new_offset)
                self.create_sign(self.session, link)
                r = self.session.get(link)
                json_data = json.loads(r.text)
                for node in json_data:
                    node["Archived"] = True
                    profile.parse_posts(node)
                    profile.gathered_flags |= ARCHIVED


class Database:
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.conn = self.get_database()


    def does_exist(self, user_id: str, post_id: str, filename: str) -> bool:
        try:
            c = self.conn.cursor()
            c.execute("SELECT * FROM entries where userid = ? AND id = ? AND filename = ?",
                      (user_id, post_id, filename,))
            data = c.fetchall()
            if len(data) > 0:
                return True
            return False
        except:
            return False

    def insert_database(self, post: Post, file: MediaItem) -> None:
        id_user = post.user_id()
        username = post.username()

        url = file.url()
        post_id = post.id()
        file_name = file.filename()
        try:
            c = self.conn.cursor()
            c.execute('INSERT INTO entries VALUES(?,?,?,?,?)', (str(post_id), str(url), str(id_user),
                                                                str(username),
                                                                  str(file_name)))
            self.conn.commit()
        except sqlite3.IntegrityError:
            pass

    def get_database(self) -> sqlite3.Connection:
        conn = None
        try:
            conn = sqlite3.connect(self.filename, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS `entries`"
                      "(`id`	TEXT, `url` TEXT, `userid` TEXT, `username` TEXT, `filename` TEXT);")
        except Error as e:
            print (e)
        finally:
            return conn

        
