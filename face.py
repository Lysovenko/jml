# Copyright 2015 Serhiy Lysovenko
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Making a face of the application
"""

from tkinter import Tk, Menu, PhotoImage, ttk, Text, StringVar, messagebox, \
    BooleanVar
from tkinter.filedialog import askdirectory
from os.path import isdir, join, dirname
from os import makedirs
from threading import Lock
from sithub import get_sites, web_search, get_datapage
from load import Loader
from settings import Config
from dialogs import DlgDelay


def autoscroll(sbar, first, last):
    """Hide and show scrollbar as needed."""
    first, last = float(first), float(last)
    if first <= 0 and last >= 1:
        sbar.grid_remove()
    else:
        sbar.grid()
    sbar.set(first, last)


class Face:
    def __init__(self, root):
        root.title(_("JML media loader"))
        root.protocol("WM_DELETE_WINDOW", self.on_delete)
        self.root = root
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=1)
        self.ufid = []
        self.cfg = Config()
        root.geometry(self.cfg.get("geometry"))
        self.add_control(root)
        pw = ttk.Panedwindow(root, orient="vertical")
        self.pw = pw
        pw.add(self.make_tree())
        pw.add(self.make_text_field())
        pw.grid(column=0, row=1, columnspan=2, sticky="senw")
        self.pw.sashpos(0, self.cfg.get("sashpos"))
        self.sz = ttk.Sizegrip(root)
        self.sz.grid(column=1, row=2, sticky="se")
        self.status = StringVar()
        st_lab = ttk.Label(root, textvariable=self.status)
        st_lab.grid(column=0, row=2, sticky="we")
        self.add_menu()
        self.locked = False
        self.loader = Loader(self.sstatus)
        self.slock = Lock()
        self.pages = {}
        self.do_remember()
        root.tk.call("wm", "iconphoto", root._w,
                     PhotoImage(file=join(dirname(__file__), "icon.gif")))

    def do_remember(self):
        self.remember = self.cfg.get("remembered", {})
        for i, d in self.remember.items():
            self.pages[i] = {"entered": False}
            tags = ("page", "bmk")
            self.pages[i].update(d)
            if "folder" in d and d["folder"] is not None:
                tags += ("folder",)
            self.tree.insert("", "end", i, text=d["title"], tags=tags)

    def add_control(self, frame):
        self.control = ttk.Frame(frame)
        self.control.grid_columnconfigure(1, weight=1)
        self.control.grid(column=0, row=0, columnspan=2, sticky="ew")
        self.btn = ttk.Button(self.control, command=self.search,
                              text=_("Search"), width=8)
        self.btn.grid(column=0, row=0, sticky="w")
        self.entry = ttk.Entry(self.control, width=60)
        self.entry.grid(column=1, row=0, sticky="ew", padx=3)
        self.entry.bind("<KeyPress-Return>", self.search)
        self.dirname = StringVar()
        self.dirname.set(self.cfg.get("last-dir", ""))
        self.dirbut = ttk.Button(self.control, command=self.ask_dir,
                                 text=_("Browse..."))
        self.dirbut.grid(column=0, row=1, sticky="ew")
        self.dirlab = ttk.Label(self.control, textvariable=self.dirname)
        self.dirlab.grid(row=1, column=1, sticky="ew")

    def make_tree(self):
        frame = ttk.Frame(self.pw)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        self.tree = tree = ttk.Treeview(frame, selectmode="extended")
        self.treef = frame
        tree.grid(column=0, row=0, sticky="nwes")
        vsb = ttk.Scrollbar(frame, command=tree.yview, orient="vertical")
        vsb.grid(column=1, row=0, sticky="ns")
        tree["yscrollcommand"] = lambda f, l: autoscroll(vsb, f, l)
        hsb = ttk.Scrollbar(
            frame, command=tree.xview, orient="horizontal")
        hsb.grid(column=0, row=1, sticky="ew")
        tree["xscrollcommand"] = lambda f, l: autoscroll(hsb, f, l)
        tree.tag_bind("page", "<Return>", self.enter_page)
        tree.tag_bind("page", "<Double-Button-1>", self.enter_page)
        tree.tag_bind("page", "<Delete>", self.del_page)
        tree.tag_bind("page", "<Insert>", self.remember_pg)
        tree.tag_bind("file", "<Return>", self.enter_file)
        tree.tag_bind("file", "<Double-Button-1>", self.enter_file)
        tree.tag_configure("page", background="gray")
        tree.tag_configure("file", foreground="blue", font="Monospace 12")
        tree.tag_configure("bmk", foreground="red")
        tree.tag_configure("folder", font="Times 14 bold")
        return frame

    def make_text_field(self):
        frame = ttk.Frame(self.pw)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        text = Text(frame, state="disabled", wrap="word",
                    font="Times 14")
        self.text = text
        text.grid(column=0, row=0, sticky="nwes")
        vsb = ttk.Scrollbar(frame, command=self.text.yview, orient="vertical")
        vsb.grid(column=1, row=0, sticky="ns")
        text["yscrollcommand"] = lambda f, l: autoscroll(vsb, f, l)
        self.text_curinfo = None
        text.tag_configure("h1", font="Times 16 bold", relief="raised")
        return frame

    def add_menu(self):
        top = self.tree.winfo_toplevel()
        top["menu"] = self.menubar = Menu(top)
        self.mfile = Menu(self.menubar)
        self.medit = Menu(self.menubar)
        self.msites = Menu(self.menubar)
        self.menubar.add_cascade(menu=self.mfile, label=_("File"))
        self.menubar.add_cascade(menu=self.medit, label=_("Edit"))
        self.menubar.add_cascade(menu=self.msites, label=_("Sites"))
        self.mfile.add_command(label=_("Search"), command=self.search)
        self.mfile.add_command(label=_("Select dir..."), command=self.ask_dir)
        self.mfile.add_command(label=_("Select default folder..."),
                               command=self.ask_dir)
        self.mfile.add_command(label=_("Quit"), command=self.on_delete,
                               accelerator="Ctrl+Q", underline=1)
        self.root.bind_all("<Control-q>", lambda x: self.on_delete())
        self.medit.add_command(label=_("Clear"), command=self.clear_list)
        self.medit.add_command(label=_("Delay..."), command=self.ask_delay)
        sel_sites = self.cfg.get("sites", set())
        self.sites = [i + (BooleanVar(),) for i in get_sites()]
        for site, name, bvar in self.sites:
            bvar.set(site in sel_sites)
            self.msites.add_checkbutton(
                label=name, onvalue=True, offvalue=False, variable=bvar)

    def search(self, evt=None):
        self.sstatus(_("Wait..."))
        sr = web_search(
            self.entry.get(), {i[0] for i in self.sites if i[2].get()})
        if sr is None:
            return
        self.insert_pages(sr)

    def insert_pages(self, pages, where=""):
        spages = self.pages
        for i in pages:
            h = i["hash"]
            if h not in spages:
                self.tree.insert(where, "end", h, text=i["title"],
                                 tags=("page",))
                spages[h] = {"entered": False}
                spages[h]["site"] = i["site"]
                spages[h]["page"] = i["page"]
        self.sstatus(_("OK"))

    def remember_pg(self, evt=None):
        """Switch page remember"""
        iid = self.tree.focus()
        if iid in self.remember:
            self.tree.item(iid, tags=("page",))
            self.remember.pop(iid)
        else:
            self.tree.item(iid, tags=("page", "bmk"))
            pg = self.pages[iid]
            remember = dict()
            for name in ("site", "page", "folder"):
                if name in pg:
                    remember[name] = pg[name]
            remember["title"] = self.tree.item(iid)["text"]
            self.remember[iid] = remember

    def clear_list(self, evt=None):
        for i in self.pages:
            self.tree.delete(i)
        self.pages.clear()
        del self.ufid[:]
        self.do_remember()

    def ask_dir(self, evt=None):
        if self.locked:
            return
        inidir = self.dirname.get()
        text = None
        curinfo = self.text_curinfo
        if curinfo in self.remember:
            curem = self.remember[curinfo]
            text = curem["title"]
            inidir = curem.get("folder", inidir)
        dname = askdirectory(initialdir=inidir, parent=self.root)
        if type(dname) == str and dname:
            if not isdir(dname):
                if messagebox.askyesno(
                        message=_("Are you sure you want to create "
                                  "a new directory?"),
                        icon="question", title=_("New directory")) is False:
                    return
                makedirs(dname)
            if text is not None:
                self.remember[curinfo]["folder"] = dname
            else:
                self.dirname.set(dname)

    def ask_delay(self, evt=None):
        cfg = {"delay": "0"}
        DlgDelay(self.root, _("Delay time"), cfg=cfg)
        if cfg["OK button"]:
            self.loader.set_delay(cfg["delay"])

    def del_page(self, evt=None):
        if type(evt) == str:
            iid = evt
        else:
            iid = self.tree.focus()
            if iid in self.remember:
                if messagebox.askyesno(
                        message=_("Are you sure you want to "
                                  "delete preserved page?"),
                        icon="question", title=_("Deletion")) is False:
                    return
        next_focus = self.tree.next(iid)
        if not next_focus:
            next_focus = self.tree.prev(iid)
        self.tree.delete(iid)
        if next_focus:
            self.tree.focus(item=next_focus)
            self.tree.selection_add(next_focus)
        self.remember.pop(iid, None)
        page = self.pages.pop(iid)
        if "contains" in page:
            i = 0
            ufids = self.ufid
            while i < len(ufids):
                if ufids[i][3] == iid:
                    ufids.pop(i)
                else:
                    i += 1

    def enter_page(self, evt=None):
        self.sstatus(_("Wait..."))
        iid = self.tree.focus()
        if not self.pages[iid]["entered"]:
            self.pages[iid]["entered"] = True
            try:
                items, info, ptype = get_datapage(
                    self.pages[iid]["site"], self.pages[iid]["page"])
            except Exception as err:
                self.sstatus(_("Error: {0}").format(err))
                return
            if ptype == "Files":
                self.deflate_datapage(items, info, iid)
            if ptype == "Catalog":
                self.insert_pages(items, iid)
                if info:
                    self.pages[iid]["info"] = info
                    self.text_info(iid)
        else:
            self.text_info(iid)

    def deflate_datapage(self, items, info, iid):
        if items:
            if info:
                self.pages[iid]["info"] = info
                self.text_info(iid)
            tids = []
            for u, f in items:
                tid = self.tree.insert(iid, "end", text=f, tags=("file",))
                self.ufid.append((u, f, tid, iid))
                tids.append(tid)
            self.pages[iid]["contains"] = tids
            self.sstatus(_("OK"))
        else:
            self.del_page(iid)
            self.sstatus(_("Bad item detected and destroyed"))

    def text_info(self, iid):
        if self.text_curinfo != iid:
            self.text_curinfo = iid
            info = self.pages[iid].get("info")
            if not info:
                return
            text = self.text
            text["state"] = "normal"
            text.delete("1.0", "end")
            for i in info:
                text.insert("end", *i)
            text["state"] = "disabled"

    def enter_file(self, evt=None):
        sel = self.tree.selection()
        ufids = []
        for i in self.ufid:
            if i[2] in sel:
                ufids.append(i)
        ddir = self.dirname.get()
        for t in ufids:
            iid = t[3]
            odir = ddir
            if iid in self.remember:
                odir = self.remember[iid].get("folder", odir)
            self.loader.add_file(t[0], join(odir, t[1]))

    def on_delete(self):
        cfg = self.cfg
        cfg["remembered"] = self.remember
        cfg["last-dir"] = self.dirname.get()
        cfg["geometry"] = self.root.geometry()
        cfg["sashpos"] = self.pw.sashpos(0)
        cfg["sites"] = set({i[0] for i in self.sites if i[2].get()})
        cfg.save()
        self.root.destroy()

    def sstatus(self, msg):
        self.slock.acquire()
        self.status.set(msg)
        self.slock.release()


def start_face():
    try:
        import gettext
    except ImportError:
        __builtins__.__dict__["_"] = str
    else:
        localedir = join(dirname(__file__), "i18n", "locale")
        if isdir(localedir):
            gettext.install("jml", localedir=localedir)
        else:
            gettext.install("jml")
    root = Tk()
    f = Face(root)
    root.mainloop()


if __name__ == "__main__":
    start_face()
