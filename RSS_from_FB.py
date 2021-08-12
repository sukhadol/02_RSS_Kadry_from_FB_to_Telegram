#!/usr/bin/python3
# Скрипт для считывания данных из RSS в канал Телеграм
# Разработка Георгия Сухадольского https://sukhadol.ru
# Создано на основе идеи by Yevgeniy Goncharov, https://sys-adm.in
# Описание исходных блоков на основе sqlite: https://sys-adm.in/programming/805-rss-fider-na-python-s-opravkoj-uvedomlenij-v-telegram.html


# Imports
import requests
import feedparser
import os
#import urllib
#import urllib.parse
import random

import psycopg2
from psycopg2 import Error
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT # возможно эта строка только для локальной работы
from requests.models import ProtocolError

from pyquery import PyQuery as pq

# Проверка мы работаем на Heroku или локально, сделано собственной переменной в оболочке Heroku, можно пробовать также значением DYNO 
if 'We_are_on_Heroku' in os.environ:
    Run_On_Heroku = True
else:
    Run_On_Heroku = False

# получаем переменные из окружения или конфиг.файла
if Run_On_Heroku:
    #from os import *
    ChatID_for_RSSfrom_FB = os.environ.get("ChatID_for_RSSfrom_FB")
    Token_bot_for_RSSfrom_FB = os.environ.get("Token_bot_for_RSSfrom_FB")
    #Password_to_local_PostgreSQL =  хммм... наверное для Хероку не требуется?
    #print("ChatID_for_RSSfrom_FB= " + ChatID_for_RSSfrom_FB)
    #print("Token_bot_for_RSSfrom_FB= " + Token_bot_for_RSSfrom_FB)
    DATABASE_URL = os.environ['DATABASE_URL'] # взял по инструкции https://devcenter.heroku.com/articles/heroku-postgresql#connecting-in-python, хотя ключ расположен так же индивидуально у меня в личном кабинете
    port_for_postgres = int(os.environ.get("PORT", 5000))
    host_for_postgres="localhost" # !!!! что-то надо править!!!
    print('...Работаем на Хероку')
else:
    from config_RSS_FB import *
    port_for_postgres="5432"
    host_for_postgres="localhost"
    print('...Работаем локально')

# Указываем ссылку на свой RSS:
RSSfeeds_of_ProZakupki = [
   'https://fetchrss.com/rss/60df3a203862af2f1d5a19e260df2b6a2fe4d94b2622eae3.xml'
]

# User agents - для рандомизации обращения к RSS
uags = [
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Safari/605.1.15',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
]

# Random User Agent (from uags list)
ua = random.choice(uags)

# Header
headers = {
  "Connection" : "close",  # another way to cover tracks
  "User-Agent" : ua
}

# Proxies
proxies = {
}

# Создание базы данных
if Run_On_Heroku:
    #отсюда https://devcenter.heroku.com/articles/heroku-postgresql#connecting-in-python инструкция как подключиться к базе данных
    print('Создавать базу НЕ надо, на Heroku она есть автоматом')

    # начало блока для однократного запуска - хотя возможно и лишнее
    #try:
    #    connection = psycopg2.connect(DATABASE_URL, sslmode='require')
    #    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    #    cursor = connection.cursor()
    #    sql_create_database = 'create database postgres_baze_from_rss'
    #    cursor.execute(sql_create_database)
    #    print('Создали новую базу')
    #except (Exception, Error) as error:
    #    print("Ошибка при работе с PostgreSQL", error)
    #finally:
    #    if connection:
    #        cursor.close()
    #        connection.close()
    #        print("Создание базы данных: Соединение с PostgreSQL закрыто")
    # конец блока для однократного запуска

else:
    try:
        connection = psycopg2.connect(user = "postgres",
                                    password = Password_to_local_PostgreSQL,
                                    host = host_for_postgres,
                                    port = port_for_postgres)
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = connection.cursor()
        sql_create_database = 'create database postgres_baze_from_rss'
        cursor.execute(sql_create_database)
        print('Создали новую базу')
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL", error)
    finally:
        if connection:
            cursor.close()
            connection.close()
            print("Создание базы данных: Соединение с PostgreSQL закрыто") 


# Создание таблицы в базе данных 
try:
    if Run_On_Heroku:
    #отсюда https://devcenter.heroku.com/articles/heroku-postgresql#connecting-in-python инструкция как подключиться к базе данных
        connection = psycopg2.connect(DATABASE_URL, sslmode='require')


        # Выполнение SQL-запроса для удаления записи из таблицы
        cursor = connection.cursor()
        cursor.execute("DELETE FROM Table_Data_From_FB_RSS_kadry WHERE id < 3 RETURNING id;")
        connection.commit()
        count = cursor.rowcount
        print(count, "Запись успешно удалена")
        # Получить результат
        cursor.execute("SELECT * from mobile")
        print("Результат", cursor.fetchall())




    else:
        connection = psycopg2.connect(user="postgres",
    #                                password="Univer312",
    #                                host="localhost",
    #                                port="5432",
    #                                database="postgres_baze_from_rss")    
                                     password=Password_to_local_PostgreSQL,
                                     host=host_for_postgres,
                                     port=port_for_postgres,
                                     database="postgres_baze_from_rss")
    cursor = connection.cursor()
    # SQL-запрос для создания новой таблицы, добавил опцию ..if not exists..
    create_table_query = '''CREATE TABLE if not exists Table_Data_From_FB_RSS_kadry
                          (ID_time timestamp PRIMARY KEY     NOT NULL,
                          title_of_article       TEXT    NOT NULL,
                          Date_of_article       TEXT    NOT NULL); '''
    # Выполнение команды: создает новую таблицу
    cursor.execute(create_table_query)
    connection.commit()
    print("Таблица успешно создана в PostgreSQL ИЛИ проверено ее уже наличие")
except (Exception, Error) as error:
    print("Ошибка при работе с PostgreSQL-133: ", error)
finally:
    if connection:
        cursor.close()
        connection.close()
        print("Создание таблицы: Соединение с PostgreSQL закрыто\n")


# Пишем процедуры проверки наличия постов в БД Table_Data_From_FB_RSS_kadry:
def article_NOT_in_BazeFromRSS(article_title, article_date):
    try:
        if Run_On_Heroku:
            connection = psycopg2.connect(DATABASE_URL, sslmode='require')
        else:
            connection = psycopg2.connect(user="postgres",
                                          password=Password_to_local_PostgreSQL,
                                          host=host_for_postgres,
                                          port=port_for_postgres,
                                          database="postgres_baze_from_rss")
        cursor = connection.cursor()
        # Получить результат выборки наличия идентичных постов в базе
        postgreSQL_select_Query = "SELECT * from Table_Data_From_FB_RSS_kadry WHERE title_of_article=%s AND Date_of_article=%s"     # %s - означает принятый аргумент, n$ - позиция
        cursor.execute(postgreSQL_select_Query, (article_title, article_date))
        if not cursor.fetchall():
            return True
        else:
            return False
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL-161", error)
    finally:
        if connection:
            cursor.close()
            connection.close()
            print("=>Проверки наличия постов в БД: Соединение с PostgreSQL закрыто")

# Добавление постов в таблицу Table_Data_From_FB_RSS_kadry:
def add_article_to_db(article_title, article_date):
    try:
        if Run_On_Heroku:
            connection = psycopg2.connect(DATABASE_URL, sslmode='require')
        else:
            connection = psycopg2.connect(user="postgres",
                                          password=Password_to_local_PostgreSQL,
                                          host=host_for_postgres,
                                          port=port_for_postgres,
                                          database="postgres_baze_from_rss")
        cursor = connection.cursor()
        postgreSQL_to_ins_Query = "INSERT INTO Table_Data_From_FB_RSS_kadry VALUES (now(),%s,%s)"
        cursor.execute(postgreSQL_to_ins_Query, (article_title, article_date))
        connection.commit()
        print('...=> добавили пост в базу')
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL-185", error)
    finally:
        if connection:
            cursor.close()
            connection.close()
            print("...Добавление постов: Соединение с PostgreSQL закрыто")

# Процедура отправки сообщения Телеграм боту:
def bot_sendtext(bot_message):
    try:
        #bot_message = urllib.parse.quote(bot_message)
        send_text = 'https://api.telegram.org/bot' + Token_bot_for_RSSfrom_FB + '/sendMessage?chat_id=' + ChatID_for_RSSfrom_FB + '&parse_mode=Markdown&text=' + bot_message
        requests.get(send_text, proxies=proxies, headers=headers)
        #print('...send_text= ')
        #print(send_text)
    except (Exception, Error) as error:
        print("Какая-то ошибка - 196: ", error)

# Процедура получения фида, проверки его наличия в БД:
def read_article_feed(feed):
    try:
        feedparser.USER_AGENT = ua #потенциально строку можно и отключить
        feed = feedparser.parse(feed)
        #feed_for_print = feed[: 80] + '...(есть продолжение)'
        #print('...feed= ')
        #print(feed)
        #print(feed_for_print)
        for article in feed['entries']:
            #print('\n...пробуем очистку основного текста от кодов =')
            document = pq(article['summary'])
            text_of_article = document.text() # это получили чистый текст
            text_of_article = text_of_article.replace("(Feed generated with FetchRSS)", "") # убрали фразу (Feed generated with FetchRSS)
            text_of_article = text_of_article.replace("\n\n\n", "\n")      
            # если в ФБ был репост, то видим на странице пустое сообщение, поэтому его корректируем
            if text_of_article == '':
                text_of_article = text_of_article + article['title']
                text_of_article = text_of_article.replace("A post from", "Репост от") + ", поэтому полный текст сообщения смотрите на Facebook по ссылке"


            # далее блок для ситуации, когда пост пустой, только с картинкой. Надо выявить что это картинка и отправить ее в телеграм вместо текстового сообщения.     
            # проверяем есть ли в тексте картинка. Точнее, ссылка на картинку 
            #text_contain_link_img = document('img')
            #text_img_url = text_contain_link_img.attr.src 
            #print('text_img_url = ')
            #print(text_img_url)"""
            # ссылки на картинки имеют примерно такой вид:  'https://scontent.fuio21-1.fna.fbcdn.net/v/t39.30808-6/p526x296/224814408_642300336746164_111193416309050958_n.jpg?_nc_cat=104&amp;ccb=1-4&amp;_nc_sid=8bfeb9&amp;_nc_ohc=UAecGpHkqOwAX8jbrXr&amp;_nc_oc=AQkVEDVvCWflBpBL5TXZ6-0gZ8HZ3d3cXClRnSOLvmjJYi42BABYQ65vNvm33zC_MGI&amp;_nc_ht=scontent.fuio21-1.fna&amp;oh=a46c7f7d2ffdf54f812dca4546812434&amp;oe=6119E316'
            #если реальной картинки нет, то fetchrss.com подставляет свою, ее надо НЕ учитывать. Т.е. алгоритм работы с картинкой должен запускаться только когда картинка НЕ от fetchrss.com  
            #if 'fetchrss.com' not in text_img_url:
            #    # !!! здесь как раз и надо как-то прописать код отправки картинки. Сначала надо локально сохранить картинку, потом ее выдать и удалить. Заготовка на будущее
            #    # но!! визуально сильно выбивается из общего стиля, поэтому не стал запускать
            #    file_to_send_as_img = open("D:\\09.jpg", "rb")  # - вариант что уже картинка у нас есть, далее работает. Сохранение из Инета не делал
            #    IfWithoutText_url = "https://api.telegram.org/bot" + Token_bot_for_RSSfrom_FB + "/sendPhoto"
            #    IfWithoutText_files = {'photo': file_to_send_as_img} 
            #    IfWithoutText_data = {'chat_id' : ChatID_for_RSSfrom_FB, "caption": '(Форвард нового сообщения из Фейсбука)\n' +  text_of_article + article['link']}
            #    requests.post(IfWithoutText_url, files=IfWithoutText_files, data=IfWithoutText_data)
            #    #IfWithoutText_result= requests.post(IfWithoutText_url, files=IfWithoutText_files, data=IfWithoutText_data)
            #    #print(IfWithoutText_result.json())
            #    #print('IfWithoutText_result.text = ')
            #    #print(IfWithoutText_result.text)
            #else:
            #    print('ничего не делаем') """

            #print('text_of_article = ')
            #print(text_of_article)
            if article_NOT_in_BazeFromRSS(article['title'], article['published']):
                add_article_to_db(article['title'], article['published'])
                bot_sendtext('*Форвард нового сообщения из Фейсбука:*\n\n' + text_of_article + article['link'])
                print('...добавляем в базу пост с заголовком= ')
                print(article['title'])
            else:
                print('...добавлять и публиковать данный пост не надо, уже есть, речь о посте=')
                print(article['title'])
#               print(text_of_article)
    except (Exception, Error) as error:
        print("Какая-то ошибка - 231: ", error)

# Проверяем каждый фид из списка:
def spin_feds():
    try:
        for x in RSSfeeds_of_ProZakupki:
            #print('..RSSfeeds_of_ProZakupki=')
            #print(x)
            read_article_feed(x)
    except (Exception, Error) as error:
        print("Какая-то ошибка - 241: ", error)

# Получение данных, просто для себя чтобы узнать что хранится в таблице Table_Data_From_FB_RSS_kadry.
def get_posts():
    try:
        if Run_On_Heroku:
            connection = psycopg2.connect(DATABASE_URL, sslmode='require')
        else:
            connection = psycopg2.connect(user="postgres",
                                          password=Password_to_local_PostgreSQL,
                                          host=host_for_postgres,
                                          port=port_for_postgres,
                                          database="postgres_baze_from_rss")
        cursor = connection.cursor()
        # Получить результат
        cursor.execute("SELECT * from Table_Data_From_FB_RSS_kadry")
        print("\nРезультат суммарно базы данных", cursor.fetchall()) #fetchall() – возвращает записи в виде упорядоченного списка
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL", error)
    finally:
        if connection:
            cursor.close()
            connection.close()
            print("Получение данных: Соединение с PostgreSQL закрыто\n")

# Запускаем все это дело:
if Run_On_Heroku: #вариант для Heroku
    if __name__ == '__main__':
        spin_feds()
        get_posts()
        if connection:
            cursor.close()
            connection.close()
else: #вариант для локального
    if __name__ == '__main__':
        spin_feds()
        get_posts()
        if connection:
            cursor.close()
            connection.close()
