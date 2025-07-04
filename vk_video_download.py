import threading
import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox
import yt_dlp
import requests
import logging
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Вывод в консоль
        #logging.FileHandler('vk_video_download.log')  # Вывод в файл
    ]
)
logger = logging.getLogger(__name__)

# https://vk.com/video-87011294_456249654 | example for vk.com
# https://vkvideo.ru/video-50804569_456239864 | example for vkvideo.ru
# https://my.mail.ru/v/hi-tech_mail/video/_groupvideo/437.html | example for my.mail.ru
# https://rutube.ru/video/a16f1e575e114049d0e4d04dc7322667/ | example for rutube.ru
# FromRussiaWithLove | Mons (https://github.com/blyamur/VK-Video-Download/)  | ver. 1.6 | "non-commercial use only, for personal use"

currentVersion = '1.6'

class App(ttk.Frame):
    def __init__(self, parent):
        ttk.Frame.__init__(self)
        for index in [0, 1, 2]:
            self.columnconfigure(index=index, weight=1)
            self.rowconfigure(index=index, weight=1)
        self.setup_widgets()

    def setup_widgets(self):
        self.widgets_frame = ttk.Frame(self, padding=(0, 10, 0, 0))
        self.widgets_frame.grid(
            row=0, column=1, padx=10, pady=(25, 0), sticky="nsew"
        )
        self.widgets_frame.columnconfigure(index=0, weight=1)
        self.label = ttk.Label(
            self.widgets_frame,
            text="Вставьте ссылку(и) на видео через запятую",
            justify="center",
            font=("-size", 15, "-weight", "bold"),
        )
        self.label.grid(row=0, column=0, padx=0, pady=25, sticky="n")

        self.entry_nm = ttk.Entry(self.widgets_frame, font=("Calibri 22"))
        self.entry_nm.insert(tk.END, str(''))
        self.entry_nm.grid(row=1, column=0, columnspan=10, padx=(5, 5), ipadx=150, ipady=5, pady=(0, 0), sticky="ew")
        self.entry_nm.bind('<Return>', self.on_enter_pressed)
        
        # Привязка стандартных горячих клавиш для английской раскладки
        self.entry_nm.bind('<Control-c>', self.copy_text)
        self.entry_nm.bind('<Control-v>', self.paste_text)
        self.entry_nm.bind('<Control-x>', self.cut_text)
        self.entry_nm.bind('<Control-a>', self.select_all)
        
        # Привязка для обработки русской раскладки через keycode
        self.entry_nm.bind('<Control-KeyPress>', self.handle_control_key)

        self.bt_frame = ttk.Frame(self, padding=(0, 0, 0, 0))
        self.bt_frame.grid(row=1, column=0, padx=(10, 10), pady=0, columnspan=10, sticky="n")

        self.accentbutton = ttk.Button(
            self.bt_frame, text="Скачать видео", style="Accent.TButton", command=self.get_directory_string
        )
        self.accentbutton.grid(row=0, column=0, columnspan=3, ipadx=30, padx=2, pady=(5, 0), sticky="n")

        self.bt_frame.columnconfigure(index=0, weight=1)
        self.status_label = ttk.Label(
            self.bt_frame,
            text=" ",
            justify="center",
            font=("-size", 10, "-weight", "normal"),
        )
        self.status_label.grid(row=1, column=0, padx=0, pady=15, sticky="n") 

        self.copy_frame = ttk.Frame(self, padding=(0, 0, 0, 10))
        self.copy_frame.grid(row=8, column=0, padx=(10, 10), pady=5, columnspan=10, sticky="s")
        self.UrlButton = ttk.Button(
            self.copy_frame, text="About", style="Url.TButton", command=self.openweb
        )
        self.UrlButton.grid(row=1, column=0, padx=20, pady=0, columnspan=2, sticky="n")
        self.UrlButton = ttk.Button(
            self.copy_frame, text="Vers.: " + currentVersion + " ", style="Url.TButton", command=self.checkUpdate
        ) 
        self.UrlButton.grid(row=1, column=4, padx=20, pady=0, columnspan=2, sticky="w")
        self.UrlButton = ttk.Button(
            self.copy_frame, text="Donate", style="Url.TButton", command=self.donate
        )
        self.UrlButton.grid(row=1, column=7, padx=20, pady=0, columnspan=2, sticky="w")

    def handle_control_key(self, event):
        """Обработка горячих клавиш для русской раскладки через keycode."""
        try:
            keycode = event.keycode
            char = event.char.lower()  # Для отладки, на случай если char доступен
            #logger.info(f"Control key pressed: char={char}, keycode={keycode}")
            if keycode == 67:  # Ctrl+C or Ctrl+С
                self.copy_text()
                return "break"
            elif keycode == 86:  # Ctrl+V or Ctrl+В
                self.paste_text()
                return "break"
            elif keycode == 88:  # Ctrl+X or Ctrl+Ч
                self.cut_text()
                return "break"
            elif keycode == 65:  # Ctrl+A or Ctrl+Ф
                self.select_all()
                return "break"
        except Exception as e:
            #logger.error(f"Error in handle_control_key: {str(e)}")
            self.status_label.configure(text=f"Ошибка обработки клавиши: {str(e)}")
            return "break"

    def copy_text(self, event=None):
        """Копирование текста из Entry."""
        try:
            self.entry_nm.event_generate("<<Copy>>")
            #logger.info("Text copied from Entry")
            return "break"
        except Exception as e:
            #logger.error(f"Error in copy_text: {str(e)}")
            self.status_label.configure(text=f"Ошибка копирования: {str(e)}")
            return "break"

    def paste_text(self, event=None):
        """Вставка текста в Entry."""
        try:
            self.entry_nm.event_generate("<<Paste>>")
            #logger.info("Text pasted into Entry")
            return "break"
        except Exception as e:
            #logger.error(f"Error in paste_text: {str(e)}")
            self.status_label.configure(text=f"Ошибка вставки: {str(e)}")
            return "break"

    def cut_text(self, event=None):
        """Вырезание текста из Entry."""
        try:
            self.entry_nm.event_generate("<<Cut>>")
            #logger.info("Text cut from Entry")
            return "break"
        except Exception as e:
            #logger.error(f"Error in cut_text: {str(e)}")
            self.status_label.configure(text=f"Ошибка вырезания: {str(e)}")
            return "break"

    def select_all(self, event=None):
        """Выделение всего текста в Entry."""
        try:
            self.entry_nm.event_generate("<<SelectAll>>")
            #logger.info("All text selected in Entry")
            return "break"
        except Exception as e:
            #logger.error(f"Error in select_all: {str(e)}")
            self.status_label.configure(text=f"Ошибка выделения текста: {str(e)}")
            return "break"

    def openweb(self):
        try:
            webbrowser.open_new_tab('https://github.com/blyamur/VK-Video-Download')
            #logger.info("Opened GitHub page")
        except Exception as e:
            #logger.error(f"Error opening web page: {str(e)}")
            self.status_label.configure(text=f"Ошибка открытия страницы: {str(e)}")

    def donate(self):
        try:
            webbrowser.open_new_tab('https://ko-fi.com/monseg')
            #logger.info("Opened donation page")
        except Exception as e:
            #logger.error(f"Error opening donation page: {str(e)}")
            self.status_label.configure(text=f"Ошибка открытия страницы: {str(e)}")

    def checkUpdate(self, method='Button'):
        try:
            #logger.info("Checking for updates")
            github_page = requests.get('https://raw.githubusercontent.com/blyamur/VK-Video-Download/main/README.md')
            github_page_html = str(github_page.content).split()
            for i in range(0, 8):
                try:
                    index = github_page_html.index(('1.' + str(i)))
                    version = github_page_html[index]
                except ValueError:
                    continue

            if float(version) > float(currentVersion):
                self.updateApp(version)
            else:
                if method == 'Button':
                    messagebox.showinfo(title='Обновления не найдены', message=f'Обновления не найдены.\nТекущая версия: {version}')
                    #logger.info(f"No updates found. Current version: {version}")
        except requests.exceptions.ConnectionError as e:
            #logger.error(f"Connection error during update check: {str(e)}")
            if method == 'Button':
                messagebox.showwarning(title='Нет доступа к сети', message='Нет доступа к сети.\nПроверьте подключение к интернету.')
        except Exception as e:
            #logger.error(f"Error in checkUpdate: {str(e)}")
            self.status_label.configure(text=f"Ошибка проверки обновлений: {str(e)}")

    def updateApp(self, version):
        try:
            update = messagebox.askyesno(title='Найдено обновление', message=f'Доступна новая версия {version} . Обновимся?')
            if update:
                webbrowser.open_new_tab('https://github.com/blyamur/VK-Video-Download')
                #logger.info(f"Update prompted for version {version}")
        except Exception as e:
            #logger.error(f"Error in updateApp: {str(e)}")
            self.status_label.configure(text=f"Ошибка обновления: {str(e)}")

    def get_directory_string(self):
        try:
            if self.entry_nm.get() == '':
                self.status_label.configure(text="Вы не ввели ссылку на видео")
                #logger.warning("Empty video URL input")
                return
            video_urls = self.entry_nm.get().split(',')
            for video_url in video_urls:
                video_url = video_url.strip()
                if video_url:
                    #logger.info(f"Starting download for URL: {video_url}")
                    t = threading.Thread(target=self.download_video, args=(video_url,))
                    t.start()
            self.entry_nm.delete(0, tk.END)
        except Exception as e:
            #logger.error(f"Error in get_directory_string: {str(e)}")
            self.status_label.configure(text=f"Ошибка: {str(e)}")

    def download_video(self, video_url):
        try:
            ydl_opts = {'outtmpl': 'downloads/%(title)s.mp4', 'quiet': True, 'progress_hooks': [self.my_hook]}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
                info = ydl.extract_info(video_url, download=True)
                self.status_label.configure(text=f"Видео успешно скачано: «{info['title']}»")
                logger.info(f"Video downloaded successfully: {info['title']}")
        except Exception as e:
            logger.error(f"Error downloading video {video_url}: {str(e)}")
            self.status_label.configure(text=f"Ошибка скачивания: {str(e)}")

    def my_hook(self, d):
        try:
            if d['status'] == 'downloading':
                percent_str_clear = d['_percent_str'].replace('[0;94m', '')
                percent_str = percent_str_clear
                percent_str = ''.join(chr for chr in percent_str if chr.isprintable())
                percent = percent_str.split('%')[0].strip()
                root.after(0, lambda: self.status_label.configure(text=f"Скачиваем... {percent}% ", font=("Arial", 10)))
                logger.debug(f"Download progress: {percent}%")
            elif d['status'] == 'finished':
                root.after(0, lambda: self.status_label.configure(text="Загрузка завершена!", font=("Arial", 10)))
                logger.info("Download completed")
        except Exception as e:
            logger.error(f"Error in my_hook: {str(e)}")
            self.status_label.configure(text=f"Ошибка прогресса: {str(e)}")

    def on_enter_pressed(self, event):
        try:
            #logger.info("Enter key pressed")
            self.get_directory_string()
        except Exception as e:
            #logger.error(f"Error in on_enter_pressed: {str(e)}")
            self.status_label.configure(text=f"Ошибка: {str(e)}")

if __name__ == "__main__":
    try:
        # Проверка наличия файлов темы
        if not os.path.exists('theme/vk_theme.tcl'):
            #logger.error("Theme file 'theme/vk_theme.tcl' not found")
            raise FileNotFoundError("Theme file 'theme/vk_theme.tcl' not found")
        if not os.path.exists('theme/icon.ico'):
            #logger.error("Icon file 'theme/icon.ico' not found")
            raise FileNotFoundError("Icon file 'theme/icon.ico' not found")

        root = tk.Tk()
        w = root.winfo_screenwidth()
        h = root.winfo_screenheight()
        w = w // 2 
        h = h // 2 
        w = w - 200
        h = h - 200
        root.geometry('680x350+{}+{}'.format(w, h))
        root.resizable(False, False)
        root.title("Скачать видео с VK.com")
        root.iconbitmap('theme/icon.ico')
        root.tk.call("source", "theme/vk_theme.tcl")
        root.tk.call("set_theme", "light")
        app = App(root)
        app.pack(fill="both", expand=True)
        root.update()
        logger.info("Application started")
        root.mainloop()
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
