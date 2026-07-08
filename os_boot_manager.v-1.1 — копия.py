import os
import ctypes
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import subprocess

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

class OSBootManagerRU:
    def __init__(self, root):
        self.root = root
        self.root.title("OS Boot Manager — Русский")
        self.root.geometry("800x500")
        self.root.configure(bg=COLOR_BG)
        self.current_path = ""

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

        btn_go = ttk.Button(top, text="Перейти", command=self.go)
        btn_go.pack(side="left", ipadx=12)

        btn_home = ttk.Button(top, text="Домой", command=self.go_home)
        btn_home.pack(side="left", padx=(8, 0), ipadx=12)

        self.show_hidden = tk.BooleanVar(value=False)
        chk = ttk.Checkbutton(
            top, text="Показывать скрытые элементы", variable=self.show_hidden, command=self.refresh
        )
        chk.pack(side="right", padx=(10, 0))

        cols = ("name", "type", "date")
        self.tree = ttk.Treeview(root, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("name", text="Имя")
        self.tree.heading("type", text="Тип")
        self.tree.heading("date", text="Дата")
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

        # Delete теперь безопасно
        self.root.bind("<Delete>", lambda e: self.delete_selected())
        self.tree.bind("<Return>", lambda e: self.open_selected())

        self.menu_disk = tk.Menu(root, tearoff=0)
        self.menu_disk.add_command(label="Открыть", command=self.open_selected)

        self.menu_item = tk.Menu(root, tearoff=0)
        self.menu_item.add_command(label="Открыть", command=self.open_selected)
        self.menu_item.add_command(label="Запуск от имени администратора", command=self.run_as_admin)
        self.menu_item.add_command(label="Переименовать", command=self.rename_selected)
        self.menu_item.add_command(label="Удалить", command=self.delete_selected)

        self.menu_empty = tk.Menu(root, tearoff=0)
        self.menu_empty.add_command(label="Создать папку", command=self.create_folder)
        self.menu_empty.add_command(label="Создать файл", command=self.create_file)

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
            messagebox.showerror("Ошибка", "Такой папки не существует.")

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
                self.tree.insert("", "end", values=(drive, "Диск", ""), tags=(drive,))
            return

        try:
            entries = os.listdir(path)
        except PermissionError:
            messagebox.showerror("Ошибка", "Нет прав доступа.")
            return

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
            item_type = "Папка" if is_dir else "Файл"
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
        if item_type == "Диск":
            return name
        return os.path.join(self.current_path, name)

    def is_drive(self, path):
        # Простая проверка: диск — это X:\ (ровно 3 символа, заканчивается на :\)
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
            "Внимание",
            "Вы уверены, что хотите запустить от имени администратора?\nПрограмма может быть опасной."
        )
        if not warn:
            return
        try:
            subprocess.Popen([
                "powershell", "-Command",
                f"Start-Process -FilePath '{path}' -Verb RunAs"
            ])
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def show_context_menu(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            self.tree.selection_set(row)
            values = self.tree.item(row)["values"]
            item_type = values[1]
            if item_type == "Диск":
                self.menu_disk.post(event.x_root, event.y_root)
            else:
                self.menu_item.post(event.x_root, event.y_root)
        else:
            self.menu_empty.post(event.x_root, event.y_root)

    def rename_selected(self):
        path = self.get_selected_path()
        if not path or not os.path.exists(path) or self.is_drive(path):
            return
        new_name = simpledialog.askstring("Переименовать", "Новое имя:", initialvalue=os.path.basename(path))
        if new_name:
            dir_name = os.path.dirname(path)
            new_path = os.path.join(dir_name, new_name)
            try:
                os.rename(path, new_path)
                self.refresh()
            except FileExistsError:
                messagebox.showerror("Ошибка", "Файл или папка с таким именем уже существует.")
            except PermissionError:
                messagebox.showerror("Ошибка", "Нет прав доступа.")

    def delete_selected(self):
        path = self.get_selected_path()
        # ГЛАВНАЯ ЗАЩИТА: если это диск — вообще ничего не делаем
        if not path or self.is_drive(path):
            return
        if not os.path.exists(path):
            return

        confirm = messagebox.askyesno("Подтверждение", f"Удалить: {path}?\nЭто действие нельзя отменить.")
        if confirm:
            try:
                if os.path.isdir(path):
                    import shutil
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                self.refresh()
            except PermissionError:
                messagebox.showerror("Ошибка", "Нет прав доступа.")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

    def create_folder(self):
        name = simpledialog.askstring("Создать папку", "Имя папки:")
        if name:
            path = os.path.join(self.current_path, name)
            try:
                os.makedirs(path, exist_ok=False)
                self.refresh()
            except FileExistsError:
                messagebox.showerror("Ошибка", "Папка с таким именем уже существует.")
            except PermissionError:
                messagebox.showerror("Ошибка", "Нет прав доступа.")

    def create_file(self):
        name = simpledialog.askstring("Создать файл", "Имя файла (с расширением):")
        if name:
            path = os.path.join(self.current_path, name)
            try:
                with open(path, "w", encoding="utf-8") as f:
                    pass
                self.refresh()
            except PermissionError:
                messagebox.showerror("Ошибка", "Нет прав доступа.")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = OSBootManagerRU(root)
    root.mainloop()
