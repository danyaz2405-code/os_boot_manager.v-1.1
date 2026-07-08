import os
import ctypes
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import subprocess
import shutil

COLOR_BG = "white"
COLOR_FG = "black"
COLOR_BORDER = "#0055ff"

def is_hidden(path):
    try:
        FILE_ATTRIBUTE_HIDDEN = 0x02
        attrs = ctypes.windll.kernel32.GetFileAttributesW(path)
        if attrs == -1:
            return False
        return (attrs & FILE_ATTRIBUTE_HIDDEN) != 0
    except Exception:
        return False

def get_drives():
    drives = []
    bitmask = ctypes.cdll.kernel32.GetLogicalDrives()
    for i in range(26):
        if bitmask & (1 << i):
            drive = chr(ord('A') + i) + ":\\"
            drives.append(drive)
    return drives

class OSBootManagerEN:
    def __init__(self, root):
        self.root = root
        self.root.title("OS Boot Manager — English")
        self.root.geometry("900x600")
        self.root.configure(bg=COLOR_BG)
        self.current_path = ""

        # --- Top panel ---
        top = tk.Frame(root, bg=COLOR_BG)
        top.pack(fill="x", padx=10, pady=10)

        self.path_var = tk.StringVar()
        self.entry = tk.Entry(
            top, textvariable=self.path_var, font=("Consolas", 11),
            fg=COLOR_FG, bg=COLOR_BG
        )
        self.entry.config(highlightbackground=COLOR_BORDER, highlightthickness=2)
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry.bind("<Return>", lambda e: self.go())

        btn_go = ttk.Button(top, text="Go", command=self.go)
        btn_go.pack(side="left", ipadx=12)

        btn_home = ttk.Button(top, text="Home", command=self.go_home)
        btn_home.pack(side="left", padx=(8, 0), ipadx=12)

        # Filter dropdown
        filter_lbl = tk.Label(top, text="Filter:", bg=COLOR_BG, fg=COLOR_FG)
        filter_lbl.pack(side="left", padx=(15, 5))

        filter_options = ["All", "Folders Only", ".bat", ".exe", ".py", ".txt", ".sh", ".lua"]
        self.filter_var = tk.StringVar(value="All")
        self.combo_filter = ttk.Combobox(top, textvariable=self.filter_var, values=filter_options, state="readonly", width=12)
        self.combo_filter.pack(side="left", padx=(0, 15))
        self.combo_filter.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        self.show_hidden = tk.BooleanVar(value=False)
        chk = ttk.Checkbutton(
            top, text="Show Hidden Items", variable=self.show_hidden, command=self.refresh
        )
        chk.pack(side="right", padx=(10, 0))

        cols = ("name", "type", "date")
        self.tree = ttk.Treeview(root, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("name", text="Name")
        self.tree.heading("type", text="Type")
        self.tree.heading("date", text="Date Modified")
        self.tree.column("name", width=400)
        self.tree.column("type", width=100)
        self.tree.column("date", width=150)

        style = ttk.Style()
        style.configure("Treeview", background=COLOR_BG, foreground=COLOR_FG, fieldbackground=COLOR_BG)
        style.map("Treeview", background=[("selected", COLOR_BORDER)], foreground=[("selected", "white")])

        scrl = ttk.Scrollbar(root, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrl.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=10, pady=(0, 10))
        scrl.pack(side="right", fill="y", pady=(0, 10))

        self.root.bind("<Delete>", lambda e: self.delete_selected())
        self.tree.bind("<Return>", lambda e: self.open_selected())

        # Context menus
        self.menu_disk = tk.Menu(root, tearoff=0)
        self.menu_disk.add_command(label="Open", command=self.open_selected)

        self.menu_item = tk.Menu(root, tearoff=0)
        self.menu_item.add_command(label="Open", command=self.open_selected)
        self.menu_item.add_command(label="Run as Administrator", command=self.run_as_admin)
        self.menu_item.add_command(label="Rename", command=self.rename_selected)
        self.menu_item.add_command(label="Delete", command=self.delete_selected)

        self.menu_empty = tk.Menu(root, tearoff=0)
        self.menu_empty.add_command(label="Create Folder", command=self.create_folder)
        self.menu_empty.add_command(label="Create File", command=self.create_file)

        self.tree.bind("<Button-3>", self.show_context_menu)

        self.refresh()

    def go(self):
        path = self.path_var.get().strip()
        if not path:
            return
        if len(path) == 2 and path[1] == ":":
            path += "\\"
        if os.path.isdir(path):
            self.current_path = path
            self.path_var.set(path)
            self.refresh()
        else:
            messagebox.showerror("Error", "Directory does not exist.")

    def go_home(self):
        self.current_path = ""
        self.path_var.set("")
        self.refresh()

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        path = self.current_path
        if not path:
            for drive in get_drives():
                self.tree.insert("", "end", values=(drive, "Drive", ""), tags=(drive,))
            return

        try:
            entries = os.listdir(path)
        except PermissionError:
            messagebox.showerror("Error", "Access denied.")
            return

        selected_filter = self.filter_var.get()

        for name in entries:
            full_path = os.path.join(path, name)
            if not self.show_hidden.get() and is_hidden(full_path):
                continue
            try:
                stat = os.stat(full_path)
                mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            except Exception:
                mtime = ""
            is_dir = os.path.isdir(full_path)
            item_type = "Folder" if is_dir else "File"

            show_item = False
            if selected_filter == "All":
                show_item = True
            elif selected_filter == "Folders Only":
                if is_dir:
                    show_item = True
            else:
                # Filter by extension
                if not is_dir and name.lower().endswith(selected_filter.lower()):
                    show_item = True
                # Always show folders so navigation works
                if is_dir:
                    show_item = True

            if show_item:
                self.tree.insert("", "end", values=(name, item_type, mtime), tags=(full_path,))

        self.path_var.set(path)

    def get_selected_path(self):
        selected = self.tree.selection()
        if not selected:
            return None
        item = self.tree.item(selected[0])
        values = item["values"]
        name = values[0]
        item_type = values[1]
        if item_type == "Drive":
            return name
        return os.path.join(self.current_path, name)

    def is_drive(self, path):
        return len(path) == 3 and path[1] == ":" and path.endswith(":\\")

    def open_selected(self):
        path = self.get_selected_path()
        if not path:
            return
        if self.is_drive(path):
            self.current_path = path
            self.refresh()
        elif os.path.isdir(path):
            self.current_path = path
            self.refresh()
        elif os.path.isfile(path):
            os.startfile(path)

    def run_as_admin(self):
        path = self.get_selected_path()
        if not path or not os.path.isfile(path) or self.is_drive(path):
            return
        warn = messagebox.askyesno(
            "Warning",
            "Are you sure you want to run as administrator?\nThe program may be dangerous."
        )
        if not warn:
            return
        try:
            subprocess.Popen([
                "powershell", "-Command",
                f"Start-Process -FilePath '{path}' -Verb RunAs"
            ])
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def show_context_menu(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            self.tree.selection_set(row)
            values = self.tree.item(row)["values"]
            item_type = values[1]
            if item_type == "Drive":
                self.menu_disk.post(event.x_root, event.y_root)
            else:
                self.menu_item.post(event.x_root, event.y_root)
        else:
            self.menu_empty.post(event.x_root, event.y_root)

    def rename_selected(self):
        path = self.get_selected_path()
        if not path or not os.path.exists(path) or self.is_drive(path):
            return
        new_name = simpledialog.askstring("Rename", "New name:", initialvalue=os.path.basename(path))
        if new_name:
            dir_name = os.path.dirname(path)
            new_path = os.path.join(dir_name, new_name)
            try:
                os.rename(path, new_path)
                self.refresh()
            except FileExistsError:
                messagebox.showerror("Error", "A file or folder with this name already exists.")
            except PermissionError:
                messagebox.showerror("Error", "Access denied.")

    def delete_selected(self):
        path = self.get_selected_path()
        if not path or self.is_drive(path):
            return
        if not os.path.exists(path):
            return

        confirm = messagebox.askyesno("Confirmation", f"Delete: {path}?\nThis action cannot be undone.")
        if confirm:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                self.refresh()
            except PermissionError:
                messagebox.showerror("Error", "Access denied.")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def create_folder(self):
        name = simpledialog.askstring("Create Folder", "Folder name:")
        if name:
            path = os.path.join(self.current_path, name)
            try:
                os.makedirs(path, exist_ok=False)
                self.refresh()
            except FileExistsError:
                messagebox.showerror("Error", "A folder with this name already exists.")
            except PermissionError:
                messagebox.showerror("Error", "Access denied.")

    def create_file(self):
        top = tk.Toplevel(self.root)
        top.title("Create File")
        top.geometry("360x180")
        top.transient(self.root)
        top.grab_set()
        top.configure(bg=COLOR_BG)

        extensions = [".bat", ".exe", ".py", ".txt", ".sh", ".lua", ".mt3"]

        lbl_name = tk.Label(top, text="File name:", bg=COLOR_BG, fg=COLOR_FG)
        lbl_name.pack(pady=(15, 5))

        entry_name = tk.Entry(top, width=40, font=("Consolas", 10),
                              fg=COLOR_FG, bg=COLOR_BG)
        entry_name.pack(pady=5)
        entry_name.focus()

        lbl_ext = tk.Label(top, text="Extension:", bg=COLOR_BG, fg=COLOR_FG)
        lbl_ext.pack(pady=(5, 5))

        combo_ext = ttk.Combobox(top, values=extensions, state="readonly", width=37)
        combo_ext.current(0)
        combo_ext.pack(pady=5)

        def on_create():
            name = entry_name.get().strip()
            if not name:
                messagebox.showerror("Error", "Please enter a file name.")
                return

            ext = combo_ext.get()
            if name.lower().endswith(ext.lower()):
                full_name = name
            else:
                full_name = name + ext

            full_path = os.path.join(self.current_path, full_name)

            try:
                with open(full_path, "w", encoding="utf-8") as f:
                    pass
                top.destroy()
                self.refresh()
                messagebox.showinfo("Success", f"File created:\n{full_name}")
            except PermissionError:
                messagebox.showerror("Error", "Access denied.")
            except Exception as e:
                messagebox.showerror("Error", str(e))

        btn_create = ttk.Button(top, text="Create", command=on_create)
        btn_create.pack(pady=15)

        top.protocol("WM_DELETE_WINDOW", lambda: top.destroy())

if __name__ == "__main__":
    root = tk.Tk()
    app = OSBootManagerEN(root)
    root.mainloop()
