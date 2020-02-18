import os
import json
import time
import threading
import module.OF
import tkinter as tk
from tkinter.ttk import *
import tkinter.simpledialog
from module.OF import Onlyfans
from tkinter import messagebox
from icons.checked import checked_icon
from icons.tristate import tristate_icon
from icons.unchecked import unchecked_icon
from module.DateEntry import DateEntry as DateEntry

class CheckboxTreeview(Treeview):
    def __init__(self, master=None, **kw):
        Treeview.__init__(self, master, **kw)

        self.im_checked = tk.PhotoImage(data=checked_icon)
        self.im_unchecked = tk.PhotoImage(data = unchecked_icon)
        self.im_tristate = tk.PhotoImage(data = tristate_icon)
        self.tag_configure("unchecked", image=self.im_unchecked)
        self.tag_configure("tristate", image=self.im_tristate)
        self.tag_configure("checked", image=self.im_checked)

        self.bind("<Button-1>", self.box_click, True)

    def insert(self, parent, index, iid=None, **kw):
        """ same method as for standard treeview but add the tag 'unchecked'
            automatically if no tag among ('checked', 'unchecked', 'tristate')
            is given """
        if not "tags" in kw:
            kw["tags"] = ("unchecked",)
        elif not ("unchecked" in kw["tags"] or "checked" in kw["tags"]
                  or "tristate" in kw["tags"]):
            kw["tags"] = ("unchecked",)
        Treeview.insert(self, parent, index, iid, **kw)

    def check_descendant(self, item):
        """ check the boxes of item's descendants """
        children = self.get_children(item)
        for iid in children:
            self.item(iid, tags=("checked",))
            self.check_descendant(iid)

    def check_ancestor(self, item):
        """ check the box of item and change the state of the boxes of item's
            ancestors accordingly """
        self.item(item, tags=("checked",))
        parent = self.parent(item)
        if parent:
            children = self.get_children(parent)
            b = ["checked" in self.item(c, "tags") for c in children]
            if False in b:
                # at least one box is not checked and item's box is checked
                self.tristate_parent(parent)
            else:
                # all boxes of the children are checked
                self.check_ancestor(parent)

    def tristate_parent(self, item):
        """ put the box of item in tristate and change the state of the boxes of
            item's ancestors accordingly """
        self.item(item, tags=("tristate",))
        parent = self.parent(item)
        if parent:
            self.tristate_parent(parent)

    def uncheck_descendant(self, item):
        """ uncheck the boxes of item's descendant """
        children = self.get_children(item)
        for iid in children:
            self.item(iid, tags=("unchecked",))
            self.uncheck_descendant(iid)

    def uncheck_ancestor(self, item):
        """ uncheck the box of item and change the state of the boxes of item's
            ancestors accordingly """
        self.item(item, tags=("unchecked",))
        parent = self.parent(item)
        if parent:
            children = self.get_children(parent)
            b = ["unchecked" in self.item(c, "tags") for c in children]
            if False in b:
                # at least one box is checked and item's box is unchecked
                self.tristate_parent(parent)
            else:
                # no box is checked
                self.uncheck_ancestor(parent)

    def box_click(self, event):
        """ check or uncheck box when clicked """
        x, y, widget = event.x, event.y, event.widget
        elem = widget.identify("element", x, y)
        if "image" in elem:
            # a box was clicked
            item = self.identify_row(y)
            tags = self.item(item, "tags")
            if ("unchecked" in tags) or ("tristate" in tags):
                self.check_ancestor(item)
                self.check_descendant(item)
            else:
                self.uncheck_descendant(item)
                self.uncheck_ancestor(item)
                

class FilterDialog(tkinter.simpledialog.Dialog):
    def body(self, master):
        self.geometry("400x150")
        Label(master, text="DD/MM/YYYY").grid(row=0, column=2)
        Label(master, text="Start date: ").grid(row=1, column=1)
        Label(master, text="End date: ").grid(row=2, column=1)

        self.start = DateEntry(master, font=('Helvetica', 15, tk.NORMAL), border=0)
        self.end = DateEntry(master, font=('Helvetica', 15, tk.NORMAL), border=0)

        self.start.grid(row = 1, column = 2)
        self.end.grid(row = 2, column = 2)

        return self.start

    def apply(self):
        self.start_date = self.start.get()
        self.end_date = self.end.get()

        return self.start_date

    def get_dates(self):
        try:
            return [self.start_date, self.end_date]
        except AttributeError:
            return None


class MyDialog(tkinter.simpledialog.Dialog):

    def body(self, master):

        Label(master, text="Cookie: ").grid(row=0)
        Label(master, text="User Agent: ").grid(row=1)

        self.cookie = Entry(master, width=50)
        self.user_agent = Entry(master, width=50)

        self.cookie.grid(row=0, column=1)
        self.user_agent.grid(row=1, column=1)

        return self.cookie

    def apply(self):
        data = {}
        data["app-token"] = "33d57ade8c02dbc5a333db99ff9ae26a"
        cookie = self.cookie.get()
        user_agent = self.user_agent.get()
        if cookie is not None:
            data["sess"] = cookie
        if user_agent is not None:
            data["user-agent"] = user_agent
        try:
            f = open("config.json", "w")
            json.dump(data, f)
            f.close()
        except IOError:
            pass

class MainWindow:
    def __init__(self, master):
        self.master = master
        self.master.title("OF Downloader")
        self.master.geometry("680x530")
        self.sort = False

        self.TreeView = CheckboxTreeview(master, show="tree")
        self.TreeView.place(x = 20, y = 40, height = 300)

        self.Subscriptions = Label(master, text = "Active Subscriptions")
        self.Subscriptions.place(x = 20, y = 20)

        self.Status = Label(master, text = "Status: Idle")
        self.Status.place(x = 20, y = 440)

        self.FilesLeft = Label(master, text = "Files left to download: 0")
        self.FilesLeft.place(x = 240, y = 440)

        vsb = Scrollbar(master, orient="vertical", command=self.TreeView.yview)
        vsb.place(x=220, y=40, height=200+20)

        self.TreeView.configure(yscrollcommand=vsb.set)

        self.ComboBox = Combobox(master, state= "readonly",
                                 values = ["Active Subscriptions",
                                                   "Expired Subscriptions",
                                                   "All Subscriptions"])

        self.ComboBox.bind("<<ComboboxSelected>>", self.refresh)
        self.ComboBox.current(0)
        self.ComboBox.place(x = 20, y = 350)
        

        self.GetLinks = Button(master, text="Retrieve Links", command=self.Get_Links_T)
        self.GetLinks.place(x = 20, y = 400)

        self.Download = Button(master, text="Download Files", command=self.Download_Files_T)
        self.Download.place(x = 140, y = 400)
        self.Download.configure(state='disabled')

        self.Add = Button(master, text="Add cookies/user agent", command=self.Add_CU)
        self.Add.place(x = 490, y = 10)

        self.Filter = Button(master, text="Filter results by date", command=self.Filter_Date)
        self.Filter.place(x = 485, y = 350)
        self.Filter.configure(state='disabled')

        self.LogText = tk.Text(master, height = 18, width = 48)
        self.LogText.place(x = 240, y = 40)

        self.ProgressBar = Progressbar(master, orient="horizontal",
                                        length=350, mode="determinate")
        self.ProgressBar.place(x = 250, y = 400)
        self.ProgressBar["maximum"] = 100

        self.onlyfans = Onlyfans()
        self.onlyfans.load_config()
        self.onlyfans.get_subscriptions()
        self.Sub_List = self.onlyfans.return_active_subs()
        self.list_subscribers(self.Sub_List)
        


    def list_subscribers(self, lst):
        for x in range(0, len(lst)):
            self.TreeView.insert("", x, lst[x], text=lst[x])
            if lst[x] not in self.Sub_List:
                self.TreeView.insert(lst[x], 0, text="Messages")
            else:
                self.TreeView.insert(lst[x], 0, text="Messages")
                self.TreeView.insert(lst[x], 1, text="Pictures")
                self.TreeView.insert(lst[x], 2, text="Videos")
                self.TreeView.insert(lst[x], 3, text="Highlights")

    def Add_CU(self):
        Diag = MyDialog(self.master)
        self.onlyfans.load_config()
        self.onlyfans.get_subscriptions()
        self.Sub_List = self.onlyfans.return_active_subs()
        self.list_subscribers(self.Sub_List)

    def Filter_Date(self):
        Diag = FilterDialog(self.master)
        dates = Diag.get_dates()
        if dates is None:
            self.display_info(self.onlyfans.return_links())
            self.sort = False
            return
        both = True
        start = []
        end = []
        if len(dates) > 1:
            start += dates[0]
            end += dates[1]

        for c in range(0, len(start)):
            if start[c] == '':
                self.sort = False
                self.display_info(self.onlyfans.return_links())
                return
            if end[c] == '':
                both = False

        if len(self.onlyfans.filter_list) > 0:
            del self.onlyfans.filter_list[:]

        links = self.onlyfans.return_links()
        for link in links:
            date_str = link["date"].split('T')[0]
            year = date_str.split("-")[0]
            month = date_str.split("-")[1]
            day = date_str.split("-")[2]

            if int(start[2]) < int(year):
                if both == True:
                    if int(end[2]) >= int(year):
                        self.onlyfans.filter_list.append(link)
                else:
                    self.onlyfans.filter_list.append(link)
                    
            elif int(start[2]) == int(year):
                if int(start[1]) < int(month):
                    if both == True:
                        if int(end[1]) >= int(month):
                            self.onlyfans.filter_list.append(link)
                    else:
                        self.onlyfans.filter_list.append(link)
                elif int(start[1]) == int(month):
                    if int(start[0]) <= int(day):
                        if both == True:
                            if int(end[0]) >= int(day):
                                self.onlyfans.filter_list.append(link)
                        else:
                            self.onlyfans.filter_list.append(link)

        #for li in self.onlyfans.filter_list:
        #    print (li["date"])
                    

        if len(self.onlyfans.filter_list) > 0:
            self.sort = True
            self.display_info(self.onlyfans.filter_list)
        else:
            self.LogText.delete(1.0, tk.END)
            self.LogText.insert(tk.END, "")

    def link_size(self, links):
        size = 0
        for link in links:
            size += link["size"]
        return size
            
        

    def refresh(self, event):
        choice = self.ComboBox.get()
        self.TreeView.delete(*self.TreeView.get_children())
        if choice == "Expired Subscriptions":
            exp = self.onlyfans.return_expired_subs()
            self.list_subscribers(exp)
            self.Subscriptions.configure(text = "Expired Subscriptions")
        elif choice == "All Subscriptions":
            all_sub = self.onlyfans.return_all_subs()
            self.list_subscribers(all_sub)
            self.Subscriptions.configure(text = "All Subscriptions")
        else:
            active = self.onlyfans.return_active_subs()
            self.list_subscribers(active)
            self.Subscriptions.configure(text = "Active Subscriptions")
        self.ComboBox.selection_clear()

    def File_Size_Str(self, size):
        unit = ["KB", "MB", "GB", "TB"]
        count = -1
        if size < 1024:
            return str(size) + "B"
        else:
            while size >= 1024:
                size /= 1024
                count += 1
        return str('%.2f' % size) + unit[count]

    def Get_Links_T(self):
        threading.Thread(target=self.Get_Links).start()
        self.GetLinks.configure(state='disabled')

    def Download_Files_T(self):
        threading.Thread(target=self.Download_Files).start()
        self.Download.configure(state='disabled')

    def Get_Links(self):
        users = []
        index = 0

        self.Status.configure(text = "Status: Collecting Links ...")
        self.onlyfans.reset_download_size()
        self.onlyfans.clear_links()
        self.onlyfans.clear_array()

        self.Download.configure(state='disabled')
        
        for child in self.TreeView.get_children():
            flag = 0
            state = self.TreeView.item(child)["tags"][0]
            if state == "checked":
                ALL = (module.OF.MESSAGES | module.OF.PICTURES | module.OF.VIDEOS | module.OF.HIGHLIGHTS)
                tmp = { child : ALL}
                users.append(tmp)
            elif state == "unchecked":
                continue
            else:
                for c in self.TreeView.get_children(child):
                    if self.TreeView.item(c)['tags'][0] == 'checked':
                        if self.TreeView.item(c)['text'] == "Messages":
                            flag |= module.OF.MESSAGES
                        elif self.TreeView.item(c)['text'] == "Pictures":
                            flag |= module.OF.PICTURES
                        elif self.TreeView.item(c)['text'] == "Videos":
                            flag |= module.OF.VIDEOS
                        elif self.TreeView.item(c)['text'] == "Highlights":
                            flag |= module.OF.HIGHLIGHTS
                tmp = {child : flag}
                users.append(tmp)
                
        for u in users:
            for key, value in u.items():
                dict_return = self.onlyfans.get_user_info(key)
                if dict_return is None:
                    continue
                self.onlyfans.get_links(dict_return, value, index)
                index += 1
                
        links = self.onlyfans.return_links()
        if len(links) == 0:
            self.GetLinks.configure(state='normal')
            self.Status.configure(text = "Status: Done ...")
            return

        self.display_info(links)
        self.Filter.configure(state='normal')

    def string_flag(self, flag):
        if flag & module.OF.MESSAGES:
            return "Messages"
        elif flag & module.OF.HIGHLIGHTS:
            return "Highlights"
        elif flag & module.OF.PICTURES:
            return "Images"
        elif flag & module.OF.VIDEOS:
            return "Videos"


    def display_info(self, links):
        total_size = 0
        user_size = 0
        file_count = 0
        type_file = {"Messages" : 0, "Highlights" : 0, "Images" : 0, "Videos" : 0}
        
        self.LogText.delete(1.0, tk.END)
        current_user = links[0]["index"]
        flag = 0
        for file in links:
            if file["index"] == current_user:
                total_size += file["size"]
                user_size += file["size"]
                file_count += 1
                flag = file["flag"]
                type_file[self.string_flag(flag)] += 1
            else:
                user_name = self.onlyfans.subscript_array(current_user) + ": \n"
                self.LogText.insert(tk.END, user_name)
                for key, value in type_file.items():
                    self.LogText.insert(tk.END, "   " + key + ": " + str(value) + "\n")
                    type_file[key] = 0
                self.LogText.insert(tk.END, "   Total size: " + self.File_Size_Str(user_size) + "\n")
                
                user_size = 0
                file_count = 1
                current_user = file["index"]
                user_size += file["size"]
                total_size += file["size"]
                flag = file["flag"]

        user_name = self.onlyfans.subscript_array(current_user) + ": \n"
        self.LogText.insert(tk.END, user_name)      
        for key, value in type_file.items():
            self.LogText.insert(tk.END, "   " + key + ": " + str(value) + "\n")
            type_file[key] = 0

        self.LogText.insert(tk.END, "   Total size: " + self.File_Size_Str(user_size) + "\n")      
        self.LogText.insert(tk.END, "\n\n")
                
        temp_str = "Files to be downloaded: " + str(len(links)) + "\n"
        self.LogText.insert(tk.END, temp_str)
        temp_str = "Download Size: " + self.File_Size_Str(total_size) + "\n"
        self.LogText.insert(tk.END, temp_str)

        self.GetLinks.configure(state='normal')
        self.Download.configure(state='normal')
        self.Status.configure(text = "Status: Done ...")

    def write_through_file(self):
        file_name = "onlyfans.continue"
        names = self.onlyfans.return_user_array()
        links = self.onlyfans.return_links()
        try:
            with open(file_name, "w") as write_through:
                for x in range (0, len(names)):
                    write_through.write(names[x]["username"])
                    if x != len(names) - 1:
                        write_through.write(",")
                write_through.write("\n")
                for link in links:
                    json.dump(link, write_through)
                    write_through.write("\n")      
        except IOError:
            pass
    
    def Download_Files(self):
        names = []
        files = []
        if len(self.onlyfans.return_links()) > 0:
            answer = messagebox.askyesno("Question","Start downloading files?")
            if answer != False:
                names = self.onlyfans.return_user_array().copy()
                if self.sort == True:
                    files = self.onlyfans.filter_list.copy()
                    self.onlyfans.all_files_size = self.link_size(files)
                else:
                    files = self.onlyfans.return_links().copy()
                file_len = len(files)
                self.Status.configure(text = "Status: Downloading Files...")
                self.Filter.configure(state='disabled')
                self.ProgressBar['value'] = 0
                
                current_user = files[0]["index"]
                user_folder = self.onlyfans.subscript_array(current_user)
                self.onlyfans.create_dir(user_folder)
                #self.write_through_file()
                
                for file in files:
                    self.FilesLeft.configure(text = "Files left to download: " + str(file_len))
                    if file["index"] == current_user:
                        self.onlyfans.download(self, user_folder, file)
                    else:
                        current_user = file["index"]
                        user_folder = self.onlyfans.subscript_array(current_user)
                        self.onlyfans.create_dir(user_folder)
                        self.onlyfans.download(self, user_folder, file)
                    file_len -= 1
                    self.onlyfans.insert_database(names[current_user], file)
                    #self.write_through_file()
                self.FilesLeft.configure(text = "Files left to download: " + str(file_len))
                self.Status.configure(text = "Status: Done ...")
                        
        else:
            self.Status.configure(text = "Status: Done ...")
            self.Download.configure(state='normal')
            return
        #os.remove("onlyfans.continue")
        self.onlyfans.clear_links()
        self.onlyfans.clear_array()
        self.onlyfans.clear_filter()
        self.Filter.configure(state='disabled')
        self.Download.configure(state='disabled')





if __name__ == "__main__":
    try:
        os.mkdir("Files")
    except FileExistsError:
        pass
    root = tk.Tk()
    
    MainWind = MainWindow(root)
    root.mainloop()
