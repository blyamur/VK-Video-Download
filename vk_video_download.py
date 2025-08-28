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
        RotatingFileHandler('vk_video_download.log', maxBytes=10*1024*1024, backupCount=5)
    ]
)
logger = logging.getLogger(__name__)

currentVersion = '1.8'

class App(ttk.Frame):
    def __init__(self, parent):
        ttk.Frame.__init__(self)
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
        
        # Хранилище прогресса
        self.download_progress = {}
        self.has_activity = False
        self.active_threads = []  # Список активных потоков

        self.setup_widgets()

    def setup_widgets(self):
        self.widgets_frame = ttk.Frame(self, padding=(0, 5, 0, 0))
        self.widgets_frame.grid(row=0, column=1, padx=10, pady=(5, 0), sticky="nsew")
        self.widgets_frame.columnconfigure(index=0, weight=1)

        self.label = ttk.Label(
            self.widgets_frame,
            text="Вставьте ссылку(и) на видео через запятую",
            justify="center",
            font=("-size", 15, "-weight", "bold"),
        )
        self.label.grid(row=0, column=0, padx=0, pady=15, sticky="n")

        self.entry_nm = ttk.Entry(self.widgets_frame, font=("Calibri 22"))
        self.entry_nm.insert(tk.END, str(''))
        self.entry_nm.grid(row=1, column=0, columnspan=10, padx=(5, 5), ipadx=150, ipady=5, pady=(0, 0), sticky="ew")
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
        self.bt_frame.grid(row=1, column=0, padx=10, pady=0, columnspan=10, sticky="n")

        self.accentbutton = ttk.Button(
            self.bt_frame, text="Скачать видео", style="Accent.TButton", command=self.get_directory_string
        )
        self.accentbutton.grid(row=0, column=0, columnspan=3, ipadx=30, padx=2, pady=(5, 0), sticky="n")

        self.bt_frame.columnconfigure(0, weight=1)

        # --- Статусная строка ---
        self.status_label = ttk.Label(
            self.widgets_frame,
            text="Готов к загрузке",
            justify="center",
            font=("-size", 10, "-weight", "normal"),
            wraplength=600,
            anchor="center",
            foreground="#aaaaaa"
        )
        self.status_label.grid(row=3, column=0, padx=20, pady=(10, 5), sticky="ew")

        # Убрать подсказку через 3 сек
        root.after(3000, self.clear_hint_if_no_activity)

        # --- Чекбоксы ---
        self.check_frame = ttk.Frame(self.widgets_frame)
        self.check_frame.grid(row=2, column=0, padx=20, pady=(5, 5), sticky="w")

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

        # --- Кнопки ---
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

    def clear_hint_if_no_activity(self):
        if not self.has_activity:
            self.status_label.configure(text="")

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
            if keycode == 67:  # Ctrl+C / С
                self.copy_text(); return "break"
            elif keycode == 86:  # Ctrl+V / В
                self.paste_text(); return "break"
            elif keycode == 88:  # Ctrl+X / Ч
                self.cut_text(); return "break"
            elif keycode == 65:  # Ctrl+A / Ф
                self.select_all(); return "break"
        except Exception as e:
            self.set_status_error(f"Ошибка: {str(e)}")
            return "break"

    def copy_text(self, event=None):
        try:
            self.entry_nm.event_generate("<<Copy>>")
            return "break"
        except Exception as e:
            self.set_status_error(f"Ошибка: {str(e)}")
            return "break"

    def paste_text(self, event=None):
        try:
            self.entry_nm.event_generate("<<Paste>>")
            return "break"
        except Exception as e:
            self.set_status_error(f"Ошибка: {str(e)}")
            return "break"

    def cut_text(self, event=None):
        try:
            self.entry_nm.event_generate("<<Cut>>")
            return "break"
        except Exception as e:
            self.set_status_error(f"Ошибка: {str(e)}")
            return "break"

    def select_all(self, event=None):
        try:
            self.entry_nm.event_generate("<<SelectAll>>")
            return "break"
        except Exception as e:
            self.set_status_error(f"Ошибка: {str(e)}")
            return "break"

    def openweb(self):
        try:
            webbrowser.open_new_tab('https://github.com/blyamur/VK-Video-Download')
        except Exception as e:
            self.set_status_error(f"Ошибка: {str(e)}")

    def donate(self):
        try:
            webbrowser.open_new_tab('https://ko-fi.com/monseg')
        except Exception as e:
            self.set_status_error(f"Ошибка: {str(e)}")

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

            video_urls = list(dict.fromkeys(video_urls))  # Убрать дубли

            self.has_activity = True
            self.entry_nm.delete(0, tk.END)

            for idx, url in enumerate(video_urls, start=1):
                t = threading.Thread(target=self.download_video, args=(url, idx))
                t.daemon = True  # Важно: поток завершится при закрытии основного
                t.start()
                self.active_threads.append(t)  # Сохраняем ссылку

        except Exception as e:
            logger.error(f"Ошибка: {e}")
            self.set_status_error(f"Ошибка: {str(e)}")

    def make_progress_hook(self, thread_id):
        def hook(d):
            self.my_hook(d, thread_id)
        return hook

    def download_video(self, video_url, serial_number):
        try:
            os.makedirs('downloads', exist_ok=True)

            timestr = datetime.datetime.now().strftime('%d%m%Y_%H%M%S_%f')[:-4]
            random_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=4))

            use_random_name = (self.var_random_name.get() == 'random')
            limit_length = (self.var_limit_length.get() == 'limit')
            use_folder = (self.var_folder.get() == 'folder')

            if use_random_name:
                filename_base = f"{timestr}_{random_suffix}"
            else:
                with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                    info = ydl.extract_info(video_url, download=False)
                    title = info.get('title', 'video').strip().replace('/', '_').replace('\\', '_')
                if limit_length:
                    title = title[:50]
                filename_base = f"{title}_{timestr}_{random_suffix}"

            if use_folder:
                outtmpl = f'downloads/{filename_base}/video.mp4'
            else:
                outtmpl = f'downloads/{filename_base}.mp4'

            thread_id = f"#{serial_number}"
            self.has_activity = True

            ydl_opts = {
                'outtmpl': outtmpl,
                'quiet': True,
                'progress_hooks': [self.make_progress_hook(thread_id)]
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            self.download_progress[thread_id] = "Готово ✅"
            self.update_progress_display()

        except Exception as e:
            logger.error(f"[{serial_number}] Ошибка: {e}")
            self.download_progress[f"#{serial_number}"] = "Ошибка ❌"
            self.has_activity = True
            self.update_progress_display()

    def my_hook(self, d, thread_id):
        try:
            self.has_activity = True
            if d['status'] == 'downloading':
                raw_percent = d.get('_percent_str', '0%')
                clean_percent = re.sub(r'\x1b\[[0-9;]*m', '', raw_percent)
                clean_percent = clean_percent.replace(',', '.').strip()
                match = re.search(r'(\d+\.?\d*)\s*%', clean_percent)
                percent = match.group(1) + "%" if match else "0%"

                self.download_progress[thread_id] = percent
                self.update_progress_display()

            elif d['status'] == 'finished':
                self.download_progress[thread_id] = "Готово ✅"
                self.update_progress_display()

        except Exception as e:
            logger.error(f"Ошибка в my_hook: {e}")

    def update_progress_display(self):
        line = " ".join([f"{tid} {pct}" for tid, pct in self.download_progress.items()])
        color = "#000000" if self.has_activity else "#aaaaaa"
        root.after(0, lambda: self.status_label.configure(text=line, foreground=color))

    def set_status_error(self, msg):
        self.has_activity = True
        root.after(0, lambda: self.status_label.configure(text=msg, foreground="#d93025"))

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
        root.geometry(f'680x350+{w}+{h}')
        root.resizable(False, False)
        root.title("Скачать видео с VK.com")
        root.iconbitmap('theme/icon.ico')
        root.tk.call("source", "theme/vk_theme.tcl")
        root.tk.call("set_theme", "light")

        app = App(root)
        app.pack(fill="both", expand=True)
        root.update()
        logger.info("Приложение запущено")

        # --- Перехват закрытия окна ---
        def on_closing():
            root.destroy()
            sys.exit(0)  # Завершить программу полностью

        root.protocol("WM_DELETE_WINDOW", on_closing)

        root.mainloop()

    except Exception as e:
        logger.error(f"Ошибка запуска: {e}")
        messagebox.showerror("Ошибка", f"Ошибка запуска: {e}")
        sys.exit(1)
