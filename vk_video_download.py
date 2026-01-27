import threading
import tkinter as tk
from tkinter import ttk, messagebox, Menu
import webbrowser
import yt_dlp
import requests
import logging
import os
import random
import string
from logging.handlers import RotatingFileHandler
import datetime
import re
import sys
import time

# https://vk.com/video-87011294_456249654     | example for vk.com
# https://vkvideo.ru/video-50804569_456239864     | example for vkvideo.ru
# https://my.mail.ru/v/hi-tech_mail/video/_groupvideo/437.html     | example for my.mail.ru
# https://rutube.ru/video/a16f1e575e114049d0e4d04dc7322667/     | example for rutube.ru
# FromRussiaWithLove | Mons (https://github.com/blyamur/VK-Video-Download/)  | ver. 1.8 | "non-commercial use only, for personal use"

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler('vk_video_download.log', maxBytes=10 * 1024 * 1024, backupCount=5)
    ]
)
logger = logging.getLogger(__name__)

currentVersion = '2.0'


class App(ttk.Frame):
    def __init__(self, parent):
        ttk.Frame.__init__(self)
        self.root = parent

        for index in [0, 1, 2]:
            self.columnconfigure(index=index, weight=1)
            self.rowconfigure(index=index, weight=1)

        # Контекстное меню
        self.entry_context_menu = Menu(self, tearoff=0)
        self.entry_context_menu.add_command(label="Вырезать", command=self.cut_text)
        self.entry_context_menu.add_command(label="Копировать", command=self.copy_text)
        self.entry_context_menu.add_command(label="Вставить", command=self.paste_text)
        self.entry_context_menu.add_separator()
        self.entry_context_menu.add_command(label="Выделить всё", command=self.select_all)

        # прогресс/состояние
        self.progress_lock = threading.Lock()
        self.download_progress = {}  # thread_id -> text
        self.stop_flags = {}         # thread_id -> threading.Event()
        self.outtmpl_map = {}        # thread_id -> outtmpl
        self.active_downloads = set()

        self.has_activity = False

        # лимит параллельных загрузок
        self.max_workers = 3
        self.semaphore = threading.Semaphore(self.max_workers)

        # статистика
        self.total_jobs = 0
        self.done_jobs = 0

        # троттлинг UI
        self._last_ui_update = 0.0
        self._ui_update_interval = 0.15
        self._pending_ui_update = False

        self.setup_widgets()

    # ------------------ utils ------------------

    def sanitize_filename(self, name: str, max_len=120) -> str:
        """Windows-safe filename"""
        name = (name or "").strip()
        name = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', '_', name)
        name = re.sub(r"\s+", " ", name).strip()
        name = name.rstrip(". ")
        if not name:
            name = "video"
        return name[:max_len]

    def cleanup_temp_files(self, thread_id: str):
        """
        Удаляет временные файлы yt-dlp после отмены.
        """
        try:
            with self.progress_lock:
                outtmpl = self.outtmpl_map.get(thread_id)

            if not outtmpl:
                return

            # outtmpl может быть:
            # downloads/name.%(ext)s
            # downloads/name/video.%(ext)s
            base = outtmpl.replace("%(ext)s", "*")

            folder = os.path.dirname(base)
            if not os.path.isdir(folder):
                return

            # "video.*" -> "video."
            prefix = os.path.basename(base).replace("*", "")

            for fn in os.listdir(folder):
                full = os.path.join(folder, fn)

                # чистим только "свои" файлы (по префиксу)
                if prefix and not fn.startswith(prefix):
                    continue

                # типовые временные хвосты yt-dlp
                if fn.endswith((".part", ".ytdl", ".tmp")) or ".part" in fn:
                    try:
                        os.remove(full)
                    except Exception:
                        pass

        except Exception as e:
            logger.warning(f"[{thread_id}] cleanup_temp_files error: {e}")

    # ------------------ UI ------------------

    def setup_widgets(self):
        self.widgets_frame = ttk.Frame(self, padding=(0, 5, 0, 0))
        self.widgets_frame.grid(row=0, column=1, padx=10, pady=(5, 0), sticky="nsew")
        self.widgets_frame.columnconfigure(index=0, weight=1)
        self.widgets_frame.rowconfigure(index=4, weight=1)  # под таблицу

        self.label = ttk.Label(
            self.widgets_frame,
            text="Вставьте ссылку(и) на видео через запятую",
            justify="center",
            font=("-size", 15, "-weight", "bold"),
        )
        self.label.grid(row=0, column=0, padx=0, pady=10, sticky="n")

        self.entry_nm = ttk.Entry(self.widgets_frame, font=("Calibri 22"))
        self.entry_nm.insert(tk.END, str(''))
        self.entry_nm.grid(
            row=1, column=0, columnspan=10,
            padx=(5, 5), ipadx=150, ipady=5,
            pady=(0, 0), sticky="ew"
        )
        self.entry_nm.bind('<Return>', self.on_enter_pressed)

        # Горячие клавиши
        self.entry_nm.bind('<Control-c>', self.copy_text)
        self.entry_nm.bind('<Control-v>', self.paste_text)
        self.entry_nm.bind('<Control-x>', self.cut_text)
        self.entry_nm.bind('<Control-a>', self.select_all)
        self.entry_nm.bind('<Control-KeyPress>', self.handle_control_key)
        self.entry_nm.bind("<Button-3>", self.show_context_menu)

        # Кнопка "Скачать видео"
        self.bt_frame = ttk.Frame(self, padding=(0, 0, 0, 0))
        self.bt_frame.grid(row=2, column=0, padx=10, pady=(5, 0), columnspan=10, sticky="n")

        self.accentbutton = ttk.Button(
            self.bt_frame,
            text="Скачать видео",
            style="Accent.TButton",
            command=self.get_directory_string
        )
        self.accentbutton.grid(row=0, column=0, columnspan=3, ipadx=30, padx=2, pady=(5, 0), sticky="n")
        self.bt_frame.columnconfigure(0, weight=1)

        # --- Чекбоксы ---
        self.check_frame = ttk.Frame(self.widgets_frame)
        self.check_frame.grid(row=3, column=0, padx=20, pady=(5, 5), sticky="w")

        self.var_random_name = tk.StringVar(value='')
        self.var_limit_length = tk.StringVar(value='')
        self.var_folder = tk.StringVar(value='')

        self.check_random = ttk.Checkbutton(
            self.check_frame,
            text="Случайное имя",
            variable=self.var_random_name,
            onvalue='random',
            offvalue='',
            style="Switch.TCheckbutton"
        )
        self.check_random.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="w")

        self.check_limit = ttk.Checkbutton(
            self.check_frame,
            text="Ограничить длину до 50 симв.",
            variable=self.var_limit_length,
            onvalue='limit',
            offvalue='',
            style="Switch.TCheckbutton"
        )
        self.check_limit.grid(row=0, column=1, padx=(0, 10), pady=0, sticky="w")

        self.check_folder = ttk.Checkbutton(
            self.check_frame,
            text="Отдельная папка для видео",
            variable=self.var_folder,
            onvalue='folder',
            offvalue='',
            style="Switch.TCheckbutton"
        )
        self.check_folder.grid(row=0, column=2, padx=0, pady=0, sticky="w")

        # --- Таблица загрузок ---
        self.table_frame = ttk.Frame(self.widgets_frame)
        self.table_frame.grid(row=4, column=0, padx=10, pady=(5, 0), sticky="nsew")
        self.table_frame.rowconfigure(0, weight=1)
        self.table_frame.columnconfigure(0, weight=1)

        # стиль фона списка
        style = ttk.Style()
        style.configure(
            "Custom.Treeview",
            background="#EDEEF0",
            fieldbackground="#EDEEF0",
            foreground="#000000",
            rowheight=24
        )
        style.map("Custom.Treeview", background=[("selected", "#D6D8DC")])

        columns = ("id", "name", "status", "action")
        self.tree = ttk.Treeview(
            self.table_frame,
            columns=columns,
            show="headings",
            height=5,
            style="Custom.Treeview"
        )

        self.tree.heading("id", text="#")
        self.tree.heading("name", text="Имя / источник")
        self.tree.heading("status", text="Статус")
        self.tree.heading("action", text="")

        self.tree.column("id", width=60, anchor="center", stretch=False)
        self.tree.column("name", width=380, anchor="w", stretch=True)
        self.tree.column("status", width=150, anchor="w", stretch=False)
        self.tree.column("action", width=50, anchor="center", stretch=False)

        self.tree.grid(row=0, column=0, sticky="nsew")

        self.scrollbar = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        # клики по таблице (Cancel)
        self.tree.bind("<Button-1>", self.on_tree_click)

        # --- нижняя строка статуса ---
        self.status_label = ttk.Label(
            self.widgets_frame,
            text="Готов к загрузке",
            justify="left",
            anchor="w",
            font=("-size", 10, "-weight", "normal"),
            wraplength=650,
            foreground="#aaaaaa"
        )
        self.status_label.grid(row=5, column=0, padx=20, pady=(5, 5), sticky="ew")

        # --- Кнопки: About, Версия, Donate ---
        self.copy_frame = ttk.Frame(self, padding=(0, 0, 0, 10))
        self.copy_frame.grid(row=8, column=0, padx=10, pady=5, columnspan=10, sticky="s")

        self.UrlButton = ttk.Button(self.copy_frame, text="About", style="Url.TButton", command=self.openweb)
        self.UrlButton.grid(row=1, column=0, padx=20, pady=0, columnspan=2, sticky="n")

        self.UrlButton = ttk.Button(
            self.copy_frame, text="Vers.: " + currentVersion + " ", style="Url.TButton", command=self.checkUpdate
        )
        self.UrlButton.grid(row=1, column=4, padx=20, pady=0, columnspan=2, sticky="w")

        self.UrlButton = ttk.Button(self.copy_frame, text="Donate", style="Url.TButton", command=self.donate)
        self.UrlButton.grid(row=1, column=7, padx=20, pady=0, columnspan=2, sticky="w")

    def on_tree_click(self, event):
        """Клик по колонке Action отменяет конкретную загрузку"""
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        col = self.tree.identify_column(event.x)
        row_id = self.tree.identify_row(event.y)

        if not row_id:
            return

        # Action колонка = 4
        if col != "#4":
            return

        values = self.tree.item(row_id, "values")
        if not values:
            return

        thread_id = values[0]  # "#1"
        self.cancel_download(thread_id)

    def cancel_download(self, thread_id: str):
        with self.progress_lock:
            flag = self.stop_flags.get(thread_id)

        if flag:
            flag.set()
            self.set_status_error(f"Остановка {thread_id}...")

    # ------------------ common handlers ------------------

    def show_context_menu(self, event):
        try:
            self.entry_nm.focus_set()
            self.entry_context_menu.tk_popup(event.x_root, event.y_root)
        except Exception as e:
            logger.error(f"Error showing context menu: {str(e)}")
            self.set_status_error(f"Ошибка: {str(e)}")
        finally:
            self.entry_context_menu.grab_release()

    def handle_control_key(self, event):
        try:
            keycode = event.keycode
            if keycode == 67:
                self.copy_text(); return "break"
            elif keycode == 86:
                self.paste_text(); return "break"
            elif keycode == 88:
                self.cut_text(); return "break"
            elif keycode == 65:
                self.select_all(); return "break"
        except Exception as e:
            self.set_status_error(f"Ошибка: {str(e)}")
            return "break"

    def copy_text(self, event=None):
        self.entry_nm.event_generate("<<Copy>>")
        return "break"

    def paste_text(self, event=None):
        self.entry_nm.event_generate("<<Paste>>")
        return "break"

    def cut_text(self, event=None):
        self.entry_nm.event_generate("<<Cut>>")
        return "break"

    def select_all(self, event=None):
        self.entry_nm.event_generate("<<SelectAll>>")
        return "break"

    def openweb(self):
        webbrowser.open_new_tab('https://github.com/blyamur/VK-Video-Download')

    def donate(self):
        webbrowser.open_new_tab('https://ko-fi.com/monseg')

    def checkUpdate(self, method='Button'):
        try:
            logger.info("Проверка обновлений")
            github_page = requests.get('https://raw.githubusercontent.com/blyamur/VK-Video-Download/main/README.md')
            github_page_html = str(github_page.content).split()
            version = None
            for i in range(0, 9):
                try:
                    idx = github_page_html.index(f'1.{i}')
                    version = github_page_html[idx]
                    break
                except ValueError:
                    continue

            if version and float(version) > float(currentVersion):
                update = messagebox.askyesno("Обновление", f"Доступна версия {version}. Обновиться?")
                if update:
                    webbrowser.open_new_tab('https://github.com/blyamur/VK-Video-Download')
            elif method == 'Button':
                messagebox.showinfo("Обновления", "Нет новых версий")
        except Exception as e:
            logger.error(f"Ошибка проверки: {e}")

    # ------------------ downloads ------------------

    def get_directory_string(self):
        try:
            urls_input = self.entry_nm.get().strip()
            if not urls_input:
                self.set_status_error("Введите ссылку")
                return

            video_urls = [url.strip() for url in urls_input.split(',') if url.strip()]
            if not video_urls:
                self.set_status_error("Нет корректных ссылок")
                return

            video_urls = list(dict.fromkeys(video_urls))
            self.total_jobs = len(video_urls)
            self.done_jobs = 0

            self.has_activity = True
            self.entry_nm.delete(0, tk.END)

            # очищаем таблицу
            for item in self.tree.get_children():
                self.tree.delete(item)

            # заполняем строки
            for idx, url in enumerate(video_urls, start=1):
                thread_id = f"#{idx}"

                short_url = url
                if len(short_url) > 60:
                    short_url = short_url[:57] + "..."

                with self.progress_lock:
                    self.stop_flags[thread_id] = threading.Event()
                    self.download_progress[thread_id] = "  0.0%"

                self.tree.insert("", "end", iid=thread_id, values=(thread_id, short_url, "  0.0%", "✖"))


                t = threading.Thread(target=self.download_video, args=(url, idx))
                t.daemon = True
                t.start()

            self.update_status_bar(force=True)

        except Exception as e:
            logger.error(f"Ошибка: {e}")
            self.set_status_error(f"Ошибка: {str(e)}")

    def make_progress_hook(self, thread_id):
        tid = thread_id

        def hook(d):
            self.my_hook(d, tid)

        return hook

    def download_video(self, video_url, serial_number):
        thread_id = f"#{serial_number}"

        with self.semaphore:
            try:
                os.makedirs('downloads', exist_ok=True)

                with self.progress_lock:
                    self.active_downloads.add(thread_id)

                # имя
                timestr = datetime.datetime.now().strftime('%d%m%Y_%H%M%S_%f')[:-4]
                random_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=4))

                use_random_name = (self.var_random_name.get() == 'random')
                limit_length = (self.var_limit_length.get() == 'limit')
                use_folder = (self.var_folder.get() == 'folder')

                title = "video"

                if not use_random_name:
                    try:
                        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                            info = ydl.extract_info(video_url, download=False) or {}
                            title = (info.get('title') or "video")
                    except Exception as e:
                        logger.warning(f"[{serial_number}] Не удалось получить метаданные: {e}")

                title = self.sanitize_filename(title, max_len=50 if limit_length else 120)

                if use_random_name:
                    filename_base = f"{timestr}_{random_suffix}"
                    display_name = filename_base
                else:
                    filename_base = f"{title}_{timestr}_{random_suffix}"
                    display_name = title

                display_name = self.sanitize_filename(display_name, max_len=80)

                # обновляем колонку name
                def _set_name():
                    if self.tree.exists(thread_id):
                        values = list(self.tree.item(thread_id, "values"))
                        values[1] = display_name
                        self.tree.item(thread_id, values=values)

                self.root.after(0, _set_name)

                # расширение не форсим
                if use_folder:
                    outtmpl = f'downloads/{filename_base}/video.%(ext)s'
                else:
                    outtmpl = f'downloads/{filename_base}.%(ext)s'

                with self.progress_lock:
                    self.outtmpl_map[thread_id] = outtmpl

                ydl_opts = {
                    'outtmpl': outtmpl,
                    'quiet': True,
                    'no_warnings': True,
                    'logtostderr': False,
                    'progress_hooks': [self.make_progress_hook(thread_id)],
                }

                # ВАЖНО: ловим отмену тут, чтобы реально остановить ydl.download()
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([video_url])
                except yt_dlp.utils.DownloadError as e:
                    if "Cancelled by user" in str(e):
                        with self.progress_lock:
                            self.download_progress[thread_id] = "Отменено ⛔"
                        self.update_row(thread_id, "Отменено ⛔")
                        self.cleanup_temp_files(thread_id)
                        self.update_status_bar(force=True)
                        return
                    raise

                self.update_status_bar(force=True)

            except Exception as e:
                logger.error(f"[{serial_number}] Ошибка: {e}")
                with self.progress_lock:
                    self.download_progress[thread_id] = "Ошибка ❌"
                self.update_row(thread_id, "Ошибка ❌")
                self.update_status_bar(force=True)

            finally:
                with self.progress_lock:
                    self.active_downloads.discard(thread_id)

    def my_hook(self, d, thread_id):
        stop_event = self.stop_flags.get(thread_id)
        if stop_event and stop_event.is_set():
            # ВАЖНО: не ловим тут, пусть прервёт ydl.download()
            raise yt_dlp.utils.DownloadError("Cancelled by user")

        if d.get('status') == 'downloading':
            raw_percent = d.get('_percent_str', '0%')
            clean_percent = re.sub(r'\x1b\[[0-9;]*m', '', raw_percent)
            clean_percent = clean_percent.replace(',', '.').strip()

            match = re.search(r'(\d+\.?\d*)\s*%', clean_percent)
            val = float(match.group(1)) if match else 0.0
            percent = f"{val:5.1f}%"

            with self.progress_lock:
                self.download_progress[thread_id] = percent

            self.update_row(thread_id, percent)
            self.update_status_bar()

        elif d.get('status') == 'finished':
            with self.progress_lock:
                self.download_progress[thread_id] = "Готово ✅"
            self.update_row(thread_id, "Готово ✅")
            self.update_status_bar(force=True)

    # ------------------ UI updates ------------------

    def update_row(self, thread_id: str, status_text: str):
        def _update():
            if self.tree.exists(thread_id):
                values = list(self.tree.item(thread_id, "values"))
                # values = (#, name, status, X)
                values[2] = status_text

                # если готово/ошибка/отмена - убираем X
                if status_text in ("Готово ✅", "Ошибка ❌", "Отменено ⛔"):
                    values[3] = ""

                self.tree.item(thread_id, values=values)

        self.root.after(0, _update)

    def update_status_bar(self, force=False):
        now = time.time()

        if not force:
            if (now - self._last_ui_update) < self._ui_update_interval:
                if not self._pending_ui_update:
                    self._pending_ui_update = True
                    self.root.after(int(self._ui_update_interval * 1000), self.update_status_bar)
                return

        self._pending_ui_update = False
        self._last_ui_update = now

        with self.progress_lock:
            done = sum(1 for v in self.download_progress.values() if v in ("Готово ✅", "Ошибка ❌", "Отменено ⛔"))
            total = self.total_jobs if self.total_jobs else len(self.download_progress)

        text = f"Готово: {done}/{total}"
        self.root.after(0, lambda: self.status_label.configure(text=text, foreground="#000000"))

    def set_status_error(self, msg):
        self.root.after(0, lambda: self.status_label.configure(text=msg, foreground="#d93025"))

    def on_enter_pressed(self, event):
        self.get_directory_string()


if __name__ == "__main__":
    try:
        if not os.path.exists('theme/vk_theme.tcl'):
            raise FileNotFoundError("Файл темы не найден: theme/vk_theme.tcl")
        if not os.path.exists('theme/icon.ico'):
            raise FileNotFoundError("Файл иконки не найден: theme/icon.ico")

        root = tk.Tk()
        w = root.winfo_screenwidth() // 2 - 200
        h = root.winfo_screenheight() // 2 - 200
        root.geometry(f'720x430+{w}+{h}')
        root.resizable(False, False)
        root.title("Скачать видео с VK.com")
        root.iconbitmap('theme/icon.ico')
        root.tk.call("source", "theme/vk_theme.tcl")
        root.tk.call("set_theme", "light")

        app = App(root)
        app.pack(fill="both", expand=True)
        root.update()
        logger.info("Приложение запущено")

        def on_closing():
            root.destroy()
            sys.exit(0)

        root.protocol("WM_DELETE_WINDOW", on_closing)

        root.mainloop()

    except Exception as e:
        logger.error(f"Ошибка запуска: {e}")
        messagebox.showerror("Ошибка", f"Ошибка запуска: {e}")
        sys.exit(1)
