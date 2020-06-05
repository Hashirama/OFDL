import json
import requests
import math
import os
import sqlite3
from sqlite3 import Error

MESSAGES = 0b1000000
PICTURES = 0b0100000
VIDEOS = 0b0010000
HIGHLIGHTS = 0b0001000
STORIES = 0b0000100
ARCHIVED = 0b0000010
AUDIO = 0b0000001

class Onlyfans:
    def __init__(self):
        self.active_subs = []
        self.expired_subs = []
        self.all_subs = []
        self.links = []
        self.current_sub_list = []
        self.all_files_size = 0
        self.current_dl = 0
        self.config = {}
        self.filter_list = []
        self.session = requests.Session()
        self.conn = self.get_database()

    def get_database(self):
        conn = None
        try:
            conn = sqlite3.connect('onlyfans.sqlite3.db', check_same_thread=False)
            c = conn.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS `entries`"
                      "(`id`	TEXT, `url` TEXT, `userid` TEXT, `username` TEXT, `filename` TEXT);")
        except Error as e:
            print (e)
        return conn
    
    def load_config(self):
        try:
            self.f = open("config.json")
            self.config = json.load(self.f)
            self.f.close()
            if len(self.config) > 0:
                self.set_values()
        except FileNotFoundError:
            pass

    def set_values(self):
        self.user_agent = self.config["user-agent"]
        self.sess = self.config["cookie"]
        self.app_token = self.config["app-token"]

    def get_subscriptions(self):
        if len(self.config) == 0:
            return
        self.session.headers = {
            'User-Agent': self.user_agent, 'Referer': 'https://onlyfans.com',
            'accept': 'application/json, text/plain, */*',
            'Cookie' : self.sess}

        r = self.session.get(
                "https://onlyfans.com/api2/v2/users/me?app-token=" + self.app_token)
        if r.status_code != 200:
            print ("Login failed")
            print (r.content)
            return
        
        r = self.session.get(
                "https://onlyfans.com/api2/v2/subscriptions/count/all?app-token="+self.app_token)
        r = json.loads(r.text)
        count = r["subscriptions"]["all"]

        offset_range = math.ceil(count / 99)
        offsets = list(range(offset_range))

        subscription_link = "https://onlyfans.com/api2/v2/subscriptions/subscribes?limit=99&offset=&app-token=" + self.app_token

        for off in offsets:
            offset_str = off * 99
            sub_temp = subscription_link.replace("offset=", "offset=" + str(offset_str))
            json_result = self.session.get(sub_temp)
            json_result = json.loads(json_result.content)
            for sub in json_result:
                if sub["subscribedBy"] == True and sub["username"] not in self.active_subs:
                    self.active_subs.append(sub["username"])
                else:
                    if sub["username"] not in self.expired_subs:
                        self.expired_subs.append(sub["username"])
                if sub["username"] not in self.all_subs:
                    self.all_subs.append(sub["username"])


    def return_active_subs(self):
        return self.active_subs

    def return_expired_subs(self):
        return self.expired_subs

    def return_all_subs(self):
        return self.all_subs

    def get_user_info(self, username):
        link = 'https://onlyfans.com/api2/v2/users/' + username + '&app-token=' + self.app_token
        return_dict = {}
        r = self.session.get(link)
        json_data = json.loads(r.text)
        if json_data is None:
            return
        if "error" in json_data:
            print (json_data)
            return
        return_dict["photosCount"] = json_data["photosCount"]
        return_dict["videosCount"] = json_data["videosCount"]
        return_dict["audiosCount"] = json_data["audiosCount"]
        return_dict["archivedPostsCount"] = json_data["archivedPostsCount"]
        return_dict["id"] = json_data["id"]
        return_dict["username"] = username

        self.current_sub_list.append(return_dict)

        return return_dict

    def reset_download_size(self):
        self.current_dl = 0
        self.all_files_size = 0


    def get_links(self, info, flag, index):
        if info is None:
            return
        user_id = info["id"]
        offsets = []
        images = []
        videos = []
        audio = []
        stories = []
        highlights = []
        archived = []
        total_count = info["photosCount"] + info["videosCount"] + info["audiosCount"]

        offset_range = math.ceil(total_count / 100)

        offsets = list(range(offset_range))

        message_api = "https://onlyfans.com/api2/v2/chats/"+str(user_id) + \
        "/messages?limit=100&offset=&order=desc&app-token="+self.app_token

        post_api = "https://onlyfans.com/api2/v2/users/"+ str(user_id) + \
        "/posts?limit=100&offset=&order=publish_date_desc&app-token="+self.app_token

        stories_api = "https://onlyfans.com/api2/v2/users/"+ str(user_id) + \
        "/stories?limit=100&offset=0&order=desc&app-token="+ self.app_token

        archive_api = "https://onlyfans.com/api2/v2/users/"+ str(user_id) + \
        "/posts/archived?limit=100&offset=0&order=publish_date_desc&app-token=" + self.app_token

        highlight_api = "https://onlyfans.com/api2/v2/users/" + str(user_id) + \
                     "/stories/highlights?app-token=" + self.app_token


        audio_api = "https://onlyfans.com/api2/v2/users/" + str(user_id) + \
                    "/posts/audios?limit=10&offset=&order=publish_date_desc&app-token=" + self.app_token


        if flag & HIGHLIGHTS:
            highlight = "https://onlyfans.com/api2/v2/stories/highlights/?app-token=" + self.app_token
            r = self.session.get(highlight_api)
            if "error" not in r.text:
                json_hi = json.loads(r.text)
                for js in json_hi:
                    highlight_temp = highlight.replace("highlights/", "highlights/" + str(js["id"]))
                    r = self.session.get(highlight_temp)
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
                                                r = self.session.head(src)
                                                if "Content-Length" in r.headers:
                                                    file_size = int(r.headers["Content-Length"])
                                            self.all_files_size += file_size
                                            file_dict = {"source" : src, "size": file_size, "index" : index, "id": story_id,
                                                             "date" : date, "flag" : HIGHLIGHTS}
                                            highlights.append(file_dict)
                                       

        if flag & MESSAGES:
            js_message = []
            offset = 0
            r = self.session.get(message_api)
            json_data = json.loads(r.text)
            js_message.append(json_data)
            while json_data["hasMore"] == True:
                message_temp = message_api.replace("offset=", "offset=" + str(offset * 100))
                r = self.session.get(message_temp)
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
                                        r = self.session.head(src)
                                        if "Content-Length" in r.headers:
                                            file_size = int(r.headers["Content-Length"])
                                    if type_src == "photo":
                                        self.all_files_size += file_size
                                        file_dict = {"source" : src, "size": file_size, "index" : index, "id": id_post,
                                                     "date" : date, "flag" : MESSAGES}
                                        images.append(file_dict)
                                    elif type_src == "video":
                                        self.all_files_size += file_size
                                        file_dict = {"source" : src, "size": file_size, "index" : index, "id": id_post,
                                                     "date" : date, "flag" : MESSAGES}
                                        videos.append(file_dict)
                                    elif type_src == "audio":
                                        self.all_files_size += file_size
                                        file_dict = {"source" : src, "size": file_size, "index" : index, "id": id_post,
                                                     "date" : date, "flag" : MESSAGES}
                                        audio.append(file_dict)

        if flag & PICTURES or flag & VIDEOS:
            json_data = []
            for n in offsets:
                offset = str(n * 100)
                post_tmp = post_api.replace("offset=", "offset=" + offset)
                r = self.session.get(post_tmp)
                json_data.append(json.loads(r.text))
                
            r = self.session.get(stories_api)
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
                                    r = self.session.head(src)
                                    if "Content-Length" in r.headers:
                                        file_size = int(r.headers["Content-Length"])
                                file_dict = {"source" : src, "size" : file_size, "index" : index, "id" : post_id,
                                             "date" : date, "flag" : STORIES}
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
                                    if type_src is None or not type_src.startswith('https://cdn'):
                                        continue
                                    if file_size == 0:
                                        r = self.session.head(type_src)
                                        if "Content-Length" in r.headers:
                                            file_size = int(r.headers["Content-Length"])
                                    if ".jpg" in type_src or ".jpeg" in type_src or ".png" in type_src:
                                        self.all_files_size += file_size
                                        file_dict = {"source" : type_src, "size": file_size, "index" : index, "id": id_post,
                                             "date" : date, "flag" : PICTURES}
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
                                    if type_src is None or not type_src.startswith('https://cdn'):
                                        continue

                                    if file_size == 0:
                                        r = self.session.head(type_src)
                                        if "Content-Length" in r.headers:
                                            file_size = int(r.headers["Content-Length"])      
                                    
                                    if ".mp4" in type_src:
                                        self.all_files_size += file_size
                                        file_dict = {"source" : type_src, "size": file_size, "index" : index, "id": id_post,
                                             "date" : date, "flag" : VIDEOS}
                                        videos.append(file_dict)

        if flag & ARCHIVED:
             cnt = info["archivedPostsCount"]
             off_range = math.ceil(cnt / 100)
             offsets_arch = list(range(off_range))

             for off in offsets_arch:
                 arch_temp = archive_api.replace("offset=", "offset=" + str(off))
                 r = self.session.get(arch_temp)
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
                                 if type_src is None or not type_src.startswith('https://cdn'):
                                        continue

                                 if file_size == 0:
                                     r = self.session.head(type_src)
                                     if "Content-Length" in r.headers:
                                         file_size = int(r.headers["Content-Length"])
                                 if ".mp4" in type_src:
                                        self.all_files_size += file_size
                                        file_dict = {"source" : type_src, "size": file_size, "index" : index, "id": id_post,
                                             "date" : date, "flag" : ARCHIVED}
                                        archived.append(file_dict)
                                 if ".jpg" in type_src or ".jpeg" in type_src or ".png" in type_src:
                                        self.all_files_size += file_size
                                        file_dict = {"source" : type_src, "size": file_size, "index" : index, "id": id_post,
                                             "date" : date, "flag" : ARCHIVED}
                                        archived.append(file_dict)


        if flag & AUDIO:
            cnt = info["audiosCount"]
            off_range = math.ceil(cnt / 10)
            offsets_arch = list(range(off_range))

            for off in offsets_arch:
                 audio_api = audio_api.replace("offset=", "offset=" + str(off))
                 r = self.session.get(audio_api)
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
                                 if type_src is None or not type_src.startswith('https://cdn'):
                                        continue
                                 if ".mp3" in type_src:
                                    self.all_files_size += file_size
                                    file_dict = {"source" : type_src, "size": file_size, "index" : index, "id": id_post,
                                                 "date" : date, "flag" : AUDIO}
                                    audio.append(file_dict)
                                 
                         
                 
                                 
                                     
                
            
                            
        self.links += stories + highlights + images + videos + audio + archived

        list_copy = self.links.copy()

        for link in list_copy:    
            filename = link["source"].split('/')[-1]
            filename = filename.split('?')[0]
            if self.select_database(user_id, filename) == True:
                self.links.remove(link)
                self.all_files_size -= link["size"]

    def select_database(self, userid, filename):
        try:
            c = self.conn.cursor()
            c.execute("SELECT * FROM entries where userid = ? AND filename = ?", (userid, filename,))
            data=c.fetchall()
            if len(data) > 0:
                return True
            return False
        except:
            return False

    def insert_database(self, info, file):
        id_user = info["id"]
        username = info["username"]

        url = file["source"].split('?')[0]
        post_id = file["id"]
        File_Name = url.split('/')[-1]
        try:
            c = self.conn.cursor()
            c.execute('INSERT INTO entries VALUES(?,?,?,?,?)', (str(post_id), str(url), str(id_user), str(username),
                                                                  str(File_Name)))
            self.conn.commit()
        except sqlite3.IntegrityError:
            pass


    def return_links(self):
        return self.links
    
    def clear_links(self):
        if len(self.links) > 0:
            del self.links[:]

    def subscript_array(self, ind):
        if ind < len(self.current_sub_list):
            return self.current_sub_list[ind]["username"]
        return ""

    def return_user_array(self):
        return self.current_sub_list

    def clear_array(self):
        if len(self.current_sub_list) > 0:
            del self.current_sub_list[:]

    def clear_filter(self):
        if len(self.filter_list) > 0:
            del self.filter_list[:]

    def download(self, obj, folder, file):
        file_name = file["source"]
        flag = file["flag"]
        File_Extension = file_name.split('.')[-1]
        File_Extension = File_Extension.split('?')[0]
        File_Name = file_name.split('/')[-1]
        File_Name = File_Name.split('?')[0]
        total_download = self.all_files_size
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
            if os.path.isfile("Files/" + folder + "/" + directory + "/Images/" + File_Name) == False:
                with open("Files/" + folder + "/" + directory + "/Images/" + File_Name, "wb") as file:
                    response = self.session.get(file_name, stream=True)
                    tmp = response.headers.get('content-length')
                    if tmp is None:
                        file.write(response.content)
                    else:
                        total_length = int(tmp)
                        for data in response.iter_content(chunk_size=4096):
                            self.current_dl += len(data)
                            obj.ProgressBar['value'] =  (self.current_dl / total_download) * 100
                            file.write(data)
                            
        elif File_Extension == "mp4":
            self.create_dir(folder + "/" + directory + "/Videos")
            if os.path.isfile("Files/" + folder + "/" + directory + "/Videos/" + File_Name) == False:
                with open("Files/" + folder + "/" + directory + "/Videos/" + File_Name, "wb") as file:
                    response = self.session.get(file_name, stream=True)
                    tmp = response.headers.get('content-length')
                    if tmp is None:
                        file.write(response.content)
                    else:
                        total_length = int(tmp)
                        for data in response.iter_content(chunk_size=4096):
                            self.current_dl += len(data)
                            obj.ProgressBar['value'] =  (self.current_dl / total_download) * 100
                            file.write(data)
                            
        elif File_Extension == "mp3":
            self.create_dir(folder + "/" + directory + "/Audio")
            if os.path.isfile("Files/" + folder + "/" + directory + "/Audio/" + File_Name) == False:
                with open("Files/" + folder + "/" + directory + "/Audio/" + File_Name, "wb") as file:
                    response = self.session.get(file_name, stream=True)
                    tmp = response.headers.get('content-length')
                    if tmp is None:
                        file.write(response.content)
                    else:
                        total_length = int(tmp)
                        for data in response.iter_content(chunk_size=4096):
                            self.current_dl += len(data)
                            obj.ProgressBar['value'] =  (self.current_dl / total_download) * 100
                            file.write(data)
                            
        else:
            self.create_dir(folder + "/" + directory + "/Misc")
            if os.path.isfile("Files/" + folder + "/" + directory + "/Misc/" + File_Name) == False:
                with open("Files/" + folder + "/" + directory + "/Misc/" + File_Name, "wb") as file:
                    response = self.session.get(file_name, stream=True)
                    tmp = response.headers.get('content-length')
                    if tmp is None:
                        file.write(response.content)
                    else:
                        total_length = int(tmp)
                        for data in response.iter_content(chunk_size=4096):
                            self.current_dl += len(data)
                            obj.ProgressBar['value'] =  (self.current_dl / total_download) * 100
                            file.write(data)
            

    def create_dir(self, dirname):
        try:
            os.mkdir("Files/" + dirname)
        except FileExistsError:
            pass
