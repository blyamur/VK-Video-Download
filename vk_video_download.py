import yt_dlp
import os
from os import path
import tkinter as tk
from tkinter import StringVar
from tkinter import ttk
from tkinter import messagebox
import requests
import webbrowser
#https://vk.com/video-87011294_456249654 example 
#FromRussiaWithLove | Mons (https://github.com/blyamur/VK-Video-Download/)  | ver. 1.1 | "non-commercial use only, for personal use

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
			text="Вставьте ссылку на видео",
			justify="center",
			font=("-size", 15, "-weight", "bold"),
		)
		self.label.grid(row=0, column=0,padx=0, pady=25, sticky="n")

		self.entry_nm = ttk.Entry(self.widgets_frame, font=("Calibri 22"))
		self.entry_nm.insert(tk.END, str(''))
		self.entry_nm.grid(row=1, column=0, columnspan=10, padx=(5, 5), ipadx=190, ipady=5, pady=(0, 0), sticky="ew")

		self.bt_frame = ttk.Frame(self, padding=(0, 0, 0, 0))
		self.bt_frame.grid(row=2, column=0, padx=(10, 10), pady=0, columnspan=10, sticky="n")

		self.accentbutton = ttk.Button(
			self.bt_frame, text="Скачать видео", style="Accent.TButton",command=lambda:get_directory_string('url')
		)
		self.accentbutton.grid(row=0, column=0,columnspan=3, ipadx=30, padx=2, pady=(5, 0), sticky="n")

        
		self.bt_frame.columnconfigure(index=0, weight=1)
		self.label = ttk.Label(
			self.bt_frame,
			text=" ", 
			justify="center",
			font=("-size", 10, "-weight", "normal"),
		)
		self.label.grid(row=1, column=0,padx=0, pady=15, sticky="n") 


		self.copy_frame = ttk.Frame(self, padding=(0, 0, 0, 10))
		self.copy_frame.grid(row=8, column=0, padx=(10, 10), pady=5, columnspan=10 , sticky="s")
		self.UrlButton = ttk.Button(
			self.copy_frame, text="About", style="Url.TButton",command=openweb
		)
		self.UrlButton.grid(row=1, column=0, padx=20, pady=0, columnspan=2, sticky="n")
		self.UrlButton = ttk.Button(
			self.copy_frame, text="Vers.: " +currentVersion+" ", style="Url.TButton",command=checkUpdate
		) 
		self.UrlButton.grid(row=1, column=4, padx=20, pady=0, columnspan=2, sticky="w")
		self.UrlButton = ttk.Button(
			self.copy_frame, text="Donate", style="Url.TButton",command=donate
		)
		self.UrlButton.grid(row=1, column=7, padx=20, pady=0, columnspan=2, sticky="w")

#
		def get_directory_string(string):
			if string == 'url':
				if self.entry_nm.get() == '':
					self.label.configure(text="Вы не ввели ссылку на видео")
					pass
				else:
					video_url = self.entry_nm.get()
					self.label.configure(text="Скачиваем.")
					try:
						ydl_opts = {'outtmpl': 'downloads/%(title)s.%(ext)s',}
						with yt_dlp.YoutubeDL(ydl_opts) as ydl:
							ydl.download([video_url])
							self.label.configure(text="Скачиваем...")
							info = ydl.extract_info(video_url, download=True)
							self.entry_nm.delete(0, tk.END)
							self.label.configure(text="Видео успешно скачано\n «"+info['title']+"» ")
							
					except:
						self.entry_nm.delete(0, tk.END)
						self.entry_nm.insert(tk.END, str(''))
						self.label.configure(text="Произошла ошибка")
						

def openweb():
	webbrowser.open_new_tab('https://github.com/blyamur/VK-Video-Download')
def donate():
	webbrowser.open_new_tab('https://yoomoney.ru/to/41001158104834')
def checkUpdate(method='Button'):
	try:
		github_page = requests.get('https://raw.githubusercontent.com/blyamur/VK-Video-Download/main/README.md')
		github_page_html = str(github_page.content).split()
		print()
		for i in range(0,3):
			try:
				index = github_page_html.index(('1.' + str(i)))
				version = github_page_html[index]
			except ValueError:
				pass
			# отображать всплывающее окно, если найдено обновление
		if float(version) > float(currentVersion):
			updateApp(version)
		else:
			if method == 'Button':
				messagebox.showinfo(title='Обновления не найдены', message=f'Обновления не найдены.\nТекущая версия: {version}')
	# не проверять наличие обновлений в офлайн-режиме
	except requests.exceptions.ConnectionError:
		if method == 'Button':
			messagebox.showwarning(title='Нет доступа к сети', message='Нет доступа к сети.\nПроверьте подключение к интернету.')
		elif method == 'Button':
			pass

def updateApp(version):
	update = messagebox.askyesno(title='Найдено обновление', message=f'Доступна новая версия {version} . Обновимся?')
	if update:
		webbrowser.open_new_tab('https://github.com/blyamur/VK-Video-Download')
os.system('cls||clear')

if __name__ == "__main__":
	root = tk.Tk()
	w = root.winfo_screenwidth()
	h = root.winfo_screenheight()
	w = w//2 
	h = h//2 
	w = w - 200
	h = h - 200
	root.geometry('640x320+{}+{}'.format(w, h))
	root.resizable(False, False)
	root.title("Скачать видео с VK.com")
	root.iconbitmap('theme/icon.ico')
	root.tk.call("source", "theme/vk_theme.tcl")
	root.tk.call("set_theme", "light")
	currentVersion = '1.1'
	app = App(root)
	app.pack(fill="both", expand=True)
	root.update()
	root.mainloop()
