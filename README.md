### Скрипт на python для скачивания видео с vk.com (GIU)
#### Version: 1.1 (текущая)

![Light screenshot](https://raw.githubusercontent.com/blyamur/VK-Video-Download/main/app_screen.jpg)




### Что это?

Скрипт на python 3, с графическим интерфейсом, для скачивания видео с сервиса vk.com 




### Как начать использовать?

1. Скачайте архив с последней версией и распакуйте в любое удобное для вас место; 

2. Установите необходимые компоненты и зависимости если такая необходимость имеется;

3. Запустите файл (скрипт) *vk_video_download.py* ;

4. В появившемся окне вставьте ссылку на видео в поле ввода и нажмите кнопку *Скачать видео*;

5. В случае удачного скачивания, появится уведомление, а видео будет сохранено в той же папке, что и скрипт.

> Ссылка должна быть вида: *https://vk.com/video-100000000_100000000* 



### Возможные проблемы

- Не вставляется ссылка в поле ввода
> У вас скорее всего включена русская раскладка клавиатуры, переключите на английскую.

- Приложение (скрипт) во время скачивание зависает
> Это особенность работы, в это время в фоне идет скачивание, по окончанию скачивания скрипт сам отвиснет.

- Видео не скачивается
> Видео или закрыто для доступа посторонним или имеет формат\источник не поддерживаемый youtube-dl




---
#### Для работы вам понадобится только содержимое папки *theme* и файл *vk_video_download.py*

*  **vk_video_download.py** - скрипт для скачивания видео с vk.com 

*  **theme** - Папка с темой оформления (стили, иконка и пр.)

*  **requirements.txt** - Зависимости


Команда для установка необходимых компонентов

    pip install -r requirements.txt
    
Или отдельная установка youtube-dl

    pip install youtube-dl
    
Команда на сборку exe файла в pyinstaller: 

    pyinstaller vk_video_download.py --noconsole --onefile --icon=icon.ico

Или можно воспользоваться [GUI for Pyinstaller based on Tkinker](https://github.com/blyamur/GUI-Pyinstaller-Pichuga)
    
---
***Скрипт был протестирован только в Windows с использованием версии Python 3.10.2***


### Полезные ссылки:

[GUI for Pyinstaller based on Tkinker](https://github.com/blyamur/GUI-Pyinstaller-Pichuga)

[youtube-dl  manual](https://github.com/ytdl-org/youtube-dl)

[Requests manual](https://github.com/psf/requests)

### Copyrights and Licenses
Not for commercial use.


*Thanks for reading :heart_eyes_cat:*
> Спасибо за чтение!

  
© 2022 From Russia with ❤ 
