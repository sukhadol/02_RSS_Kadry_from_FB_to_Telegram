#!/usr/bin/python3
# Скрипт для считывания данных из RSS в канал Телеграм и обмена информацией с ВК
# Разработка Георгия Сухадольского https://sukhadol.ru

import requests
import feedparser
import os
#import urllib
#import urllib.parse
import random

import psycopg2
from psycopg2 import Error
from requests.models import ProtocolError
from pyquery import PyQuery as pq

import vk_api
from vk_api import VkApi
import time

#=================================================================
# ВВОДНАЯ ЧАСТЬ
#=================================================================

# Проверка мы работаем на Heroku или локально, сделано собственной переменной в оболочке Heroku 
if 'We_are_on_Heroku' in os.environ:
    Run_On_Heroku = True
else:
    Run_On_Heroku = False

# получаем переменные из окружения или конфиг.файла ChatID_for_RSSfrom_FB, Token_bot_for_RSSfrom_FB
if Run_On_Heroku:
    ChatID_for_RSSfrom_FB = os.environ.get("ChatID_for_RSSfrom_FB")
    Token_bot_for_RSSfrom_FB = os.environ.get("Token_bot_for_RSSfrom_FB")
    DATABASE_URL = os.environ['DATABASE_URL'] # взял по инструкции https://devcenter.heroku.com/articles/heroku-postgresql#connecting-in-python, хотя ключ расположен так же индивидуально у меня в личном кабинете
    #port_for_postgres = int(os.environ.get("PORT", 5000))
    #host_for_postgres="localhost" # !!!! что-то надо править?!!
    print('===================== НАЧАЛИ...Работаем на Хероку')
    # теперь переменные для работы с ВК
    groupId_in_VK = os.environ.get("groupId_in_VK")
    token_VK_servisny=os.environ.get("token_VK_servisny") #Сервисный ключ доступа в приложении ВК
    token_VK_access_token_to_walls = os.environ.get("token_VK_access_token_to_walls")  # Токен ВК с доступом только к wall, для опубликования там сообщений
    # ниже две переменные - пока для тестового канала
    #Token_bot_for_communikate_VK = os.environ.get("Token_bot_for_communikate_VK")
    #ChatID_Telegram_from_VK = os.environ.get("ChatID_Telegram_from_VK")
    Token_bot_for_communikate_VK = Token_bot_for_RSSfrom_FB
    ChatID_Telegram_from_VK =ChatID_for_RSSfrom_FB

else:
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT # эта строка похоже нужна только для локальной работы
    from my_config_kadry import *
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
user_agent = random.choice(uags)

# Header
headers = {
  "Connection" : "close",  # another way to cover tracks
  "User-Agent" : user_agent
}

# Proxies
proxies = {
}

#=================================================================
# СОЗДАНИЕ ТАБЛИЦ БАЗ ДАННЫХ
#=================================================================

# Создание базы данных
if Run_On_Heroku:
    #отсюда https://devcenter.heroku.com/articles/heroku-postgresql#connecting-in-python инструкция как подключиться к базе данных
    print('Создавать базу НЕ надо, на Heroku она есть автоматом')
else:
    try:
        connection = psycopg2.connect(user = "postgres",
                                    password = Password_to_local_PostgreSQL,
                                    host = host_for_postgres,
                                    port = port_for_postgres)
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = connection.cursor()
        sql_create_database = 'create database postgres_baze_from_rss' # база единая и для ФБ и для ВК
        cursor.execute(sql_create_database)
        print('Создали новую базу')
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL - стр.100", error)
    finally:
        if connection:
            cursor.close()
            connection.close()
            print("Создание базы данных: Соединение с PostgreSQL закрыто") 


# Создание таблицы по получению RSS с ФБ в базе данных 
try:
    if Run_On_Heroku:
    #отсюда https://devcenter.heroku.com/articles/heroku-postgresql#connecting-in-python инструкция как подключиться к базе данных
        connection = psycopg2.connect(DATABASE_URL, sslmode='require')
        # Выполнение SQL-запроса для удаления записи из таблицы - для тестирования базы
        #cursor = connection.cursor()
        #cursor.execute("DELETE FROM Table_Data_From_FB_RSS_kadry WHERE title_of_article = 'Добрый вечер, коллеги! МГТУ Станкин требуются специалисты по осуществлению закупок - начальник  отдела и рядовые специалисты. Пр...';")
        #connection.commit()
        #count = cursor.rowcount
        #print(count, "Запись успешно удалена")
        ## Получить результат
        #cursor.execute("SELECT * from mobile")
        #print("Результат", cursor.fetchall())

    else:
        connection = psycopg2.connect(user="postgres",
                                     password=Password_to_local_PostgreSQL,
                                     host=host_for_postgres,
                                     port=port_for_postgres,
                                     database="postgres_baze_from_rss")
    cursor = connection.cursor()
    # SQL-запрос для создания новой таблицы импорта RSS из ФБ, добавил опцию ..if not exists..
    create_table_query = '''CREATE TABLE if not exists Table_Data_From_FB_RSS_kadry
                          (ID_time timestamp PRIMARY KEY     NOT NULL,
                          title_of_article       TEXT    NOT NULL,
                          Date_of_article       TEXT    NOT NULL); '''
    # Выполнение команды: создает новую таблицу
    cursor.execute(create_table_query)
    connection.commit()
    print("Таблица Table_Data_From_FB_RSS_kadry импорта RSS из ФБ успешно создана в PostgreSQL ИЛИ проверено ее уже наличие")
except (Exception, Error) as error:
    print("Ошибка при работе с PostgreSQL-140: ", error)
finally:
    if connection:
        cursor.close()
        connection.close()
        print("Создание таблицы Table_Data_From_FB_RSS_kadry: Соединение с PostgreSQL закрыто\n")

# Создание таблицы по получению постов из VK --> Телеграм
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
    # SQL-запрос для создания новой таблицы получения постов из VK
    create_table_query = '''CREATE TABLE if not exists Table_Data_From_VK_to_telegram
                          (ID_time timestamp PRIMARY KEY     NOT NULL,
                          id_of_article       TEXT    NOT NULL,
                          title_of_article       TEXT    NOT NULL); '''
    # Выполнение команды: создает новую таблицу Table_Data_From_VK_to_telegram
    cursor.execute(create_table_query)
    connection.commit()
    print("Таблица Table_Data_From_VK_to_telegram получения данных из VK успешно создана в PostgreSQL ИЛИ проверено ее уже наличие")
except (Exception, Error) as error:
    print("Ошибка при работе с PostgreSQL-168: ", error)
finally:
    if connection:
        cursor.close()
        connection.close()
        print("Создание таблицы Table_Data_From_VK_to_telegram: Соединение с PostgreSQL закрыто\n")

# Создание таблицы по получению постов из Телеграм --> VK
# try:
#     if Run_On_Heroku:
#         connection = psycopg2.connect(DATABASE_URL, sslmode='require')
#     else:
#         connection = psycopg2.connect(user="postgres",
#                                      password=Password_to_local_PostgreSQL,
#                                      host=host_for_postgres,
#                                      port=port_for_postgres,
#                                      database="postgres_baze_from_rss")
#     cursor = connection.cursor()
#     # SQL-запрос для создания новой таблицы получения постов из VK
#     create_table_query = '''CREATE TABLE if not exists Table_Data_From_telegram_to_VK
#                           (ID_time timestamp PRIMARY KEY     NOT NULL,
#                           id_of_article       TEXT    NOT NULL,
#                           title_of_article       TEXT    NOT NULL); '''
#     # Выполнение команды: создает новую таблицу Table_Data_From_VK_to_telegram
#     cursor.execute(create_table_query)
#     connection.commit()
#     print("Таблица Table_Data_From_telegram_to_VK получения данных из VK успешно создана в PostgreSQL ИЛИ проверено ее уже наличие")
# except (Exception, Error) as error:
#     print("Ошибка при работе с PostgreSQL-168-1: ", error)
# finally:
#     if connection:
#         cursor.close()
#         connection.close()
#         print("Создание таблицы Table_Data_From_telegram_to_VK: Соединение с PostgreSQL закрыто\n")

#=================================================================
# АНАЛИЗ ДАННЫХ В БАЗАХ
#=================================================================

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
        postgreSQL_select_Query_RSS = "SELECT * from Table_Data_From_FB_RSS_kadry WHERE title_of_article=%s AND Date_of_article=%s"     # %s - означает принятый аргумент, n$ - позиция
        cursor.execute(postgreSQL_select_Query_RSS, (article_title, article_date))
        if not cursor.fetchall():
            return True
        else:
            return False
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL-199", error)
    finally:
        if connection:
            cursor.close()
            connection.close()
            print("=>Проверки наличия постов в БД: Соединение с PostgreSQL закрыто")

# Добавление постов в таблицу Table_Data_From_FB_RSS_kadry:
def add_article_to_db_from_FB(article_title, article_date):
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
        print("Ошибка при работе с PostgreSQL-223", error)
    finally:
        if connection:
            cursor.close()
            connection.close()
            print("...Добавление постов: Соединение с PostgreSQL закрыто")

# Пишем процедуры проверки наличия постов в БД Table_Data_From_VK_to_telegram:
def article_NOT_in_BazeFromVK(article_id):
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
        postgreSQL_select_Query_to_VK = "SELECT * from Table_Data_From_VK_to_telegram WHERE id_of_article=%s"     # %s - означает принятый аргумент, n$ - позиция
        cursor.execute(postgreSQL_select_Query_to_VK, (str(article_id), ))
        #cursor.execute("SELECT * from Table_Data_From_VK_to_telegram WHERE id_of_article=%s", (str(article_id), ))
        if not cursor.fetchall():
            return True
        else:
            return False
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL-250", error)
    finally:
        if connection:
            cursor.close()
            connection.close()
            print("=>Проверки наличия постов в БД: Соединение с PostgreSQL закрыто")

# Добавление постов в таблицу Table_Data_From_VK_to_telegram:
def add_article_to_db_from_VK(article_id, article_title):
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
        postgreSQL_to_ins_Query = "INSERT INTO Table_Data_From_VK_to_telegram VALUES (now(),%s,%s)"
        cursor.execute(postgreSQL_to_ins_Query, (article_id, article_title))
        connection.commit()
        print('...=> добавили пост в базу')
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL-274", error)
    finally:
        if connection:
            cursor.close()
            connection.close()
            print("...Добавление постов: Соединение с PostgreSQL закрыто")



#=================================================================
# РАБОТА С RSS из FACEBOOK
#=================================================================

def bot_sendtext_to_VK_from_FB(message_to_VK):
    try:
        print('...отправка в ВК')
        #message_to_VK = message_to_VK.replace("#", " %23")  # шестнадцатеричный код символа # = 0023, т.е. для отображения в теории '\x23' но оно не сработало, рекомендовали замену на %23.
        params = {'owner_id':int(groupId_in_VK), 'from_group': 1, 'message': message_to_VK, 'access_token': token_VK_access_token_to_walls, 'v':5.103} # это отправка дубля на ВК
        response = requests.get('https://api.vk.com/method/wall.post', params=params)
        print(response.text[0:100]) # если все верно - то публикуем только первые 100 символов
    except (Exception, Error) as error:
        print("Какая-то ошибка - 293-1: ", error)

def bot_sendtext_to_telega_kadry(bot_message):
    try:
        send_text = 'https://api.telegram.org/bot' + Token_bot_for_RSSfrom_FB + '/sendMessage?chat_id=' + ChatID_for_RSSfrom_FB + '&parse_mode=Markdown&text=' + bot_message
        requests.get(send_text, proxies=proxies, headers=headers)
        #message_to_VK = bot_message
        #params = {'owner_id':int(groupId_in_VK), 'from_group': 1, 'message': message_to_VK, 'access_token': token_VK_access_token_to_walls, 'v':5.103} # это отправка дубля на ВК
        #response = requests.get('https://api.vk.com/method/wall.post', params=params)
        #print(response.text)
    except (Exception, Error) as error:
        print("Какая-то ошибка - 293-2: ", error)


# Процедура получения фида, проверки его наличия в БД:
def read_article_feed(feed):
    try:
        feedparser.USER_AGENT = user_agent #потенциально строку можно и отключить
        feed = feedparser.parse(feed)
        #feed_for_print = feed[: 80] + '...(есть продолжение)'
        #print('...feed= ')
        #print(feed)
        #print(feed_for_print)
        for article in feed['entries']:
            document = pq(article['summary'])
            text_of_article = document.text() # это получили чистый текст, без кодов
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

            if article_NOT_in_BazeFromRSS(article['title'], article['published']):
                add_article_to_db_from_FB(article['title'], article['published'])
                if(len(text_of_article)) > 2500: # без этого ограничения выдавало ошибку 414 Request-URI Too Large
                    bot_sendtext_to_VK_from_FB('Форвард нового сообщения из Фейсбука:\n\n' + text_of_article[: 2500] + '...\n\nПродолжение в источнике:\n' + article['link']) #эта строка была сокращенной версией, без учета излишне длинных сообщений
                else:
                    bot_sendtext_to_VK_from_FB('Форвард нового сообщения из Фейсбука:\n\n' + text_of_article + article['link']) #эта строка была сокращенной версией, без учета излишне длинных сообщений
                full_text = '*Форвард нового сообщения из Фейсбука:*\n\n' + text_of_article + article['link']
                full_text = full_text.replace("#", " %23")  # шестнадцатеричный код символа # = 0023, т.е. для отображения в теории '\x23' но оно не сработало, рекомендовали замену на %23.
                if len(full_text) > 4096:
                    full_text_fix= len(full_text)
                    while full_text_fix > 4096:
                        first_part_text = full_text[0:4096-35]
                        point_end_of_text = first_part_text.rfind("\n")  
                        first_part_to_send = first_part_text[0:point_end_of_text]               
                        bot_sendtext_to_telega_kadry(first_part_to_send + '\n_(продолжение следует...)_')
                        full_text = '\n_(...продолжение)_\n' + full_text[point_end_of_text:len(full_text)]
                        full_text_fix= len(full_text)
                    else:
                        bot_sendtext_to_telega_kadry(full_text)
                else:
                    bot_sendtext_to_telega_kadry(full_text)

                print('...публикуем и добавляем в базу пост с заголовком= ')
                print(article['title'])
            else:
                print('...добавлять и публиковать данный пост не надо, уже есть, речь о посте=')
                print((article['title'])[:100]) #публикуем только первые 100 символов
#               print(text_of_article)
    except (Exception, Error) as error:
        print("Какая-то ошибка - 364: ", error)

# Проверяем каждый фид из списка:
def spin_feds():
    try:
        for x in RSSfeeds_of_ProZakupki:
            #print('..RSSfeeds_of_ProZakupki=')
            #print(x)
            read_article_feed(x)
    except (Exception, Error) as error:
        print("Какая-то ошибка - 374: ", error)

#=================================================================
# Получение данных, просто для себя чтобы узнать что хранится в таблице Table_Data_From_FB_RSS_kadry.
#=================================================================
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
        # cursor.execute("SELECT * from Table_Data_From_FB_RSS_kadry") # это полная выборка из базы, она только перегрузит нас данными
        # print("\nРезультат суммарно базы данных", cursor.fetchall()) #fetchall() – возвращает записи в виде упорядоченного списка

        numb_days = 14 # глубина выборки базы для публикации. Увы, в следующей строчке автоматом не подхватилось, в причинах разбираться не стал, указал вручную
        cursor.execute("SELECT title_of_article, Date_of_article from Table_Data_From_FB_RSS_kadry WHERE (EXTRACT('DAY' FROM (now() - to_timestamp(Date_of_article, 'Dy DD Mon YYYY'))))<14")
        print("======================Результат базы данных RSS из Facebook за " + str(numb_days) + " последних дней =") # вернем записи поштучно
        for result in cursor:
            print(str(result))

    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL-401", error)
    finally:
        if connection:
            cursor.close()
            connection.close()
            print("Получение данных: Соединение с PostgreSQL закрыто\n")

#=================================================================
# РАБОТА С ТЕЛЕГРАМ
#=================================================================

# Процедура отправки сообщения в канал Телеграм из ВК (после тестирования можно поставить токен ):
def bot_sendtext_to_telega_from_VK(bot_message):
    try:
        send_text = 'https://api.telegram.org/bot' + Token_bot_for_communikate_VK + '/sendMessage?chat_id=' + ChatID_Telegram_from_VK + '&parse_mode=Markdown&text=' + bot_message
        requests.get(send_text, proxies=proxies, headers=headers)
    except (Exception, Error) as error:
        print("Какая-то ошибка - 418: ", error)

# Получение постов из сообщества ВК.  
def grabber_from_VK():
    my_offset = 0    # начальный индекс поиска публикаций
    my_count = 90   #шаг продвижения индекса поиска публикаций
    try:
        for i_tmp in range(0,4): # т.е. фактически опросим страницу (сообщество) 4 раза по count публикаций, боле чем достаточно
            params = {'owner_id':str(groupId_in_VK),'offset':my_offset,'count':my_count,'filter':'all','extended':0,'access_token':token_VK_servisny,'v':5.103}         #формирование списка параметров запроса к api
            posts = requests.get('https://api.vk.com/method/wall.get',params)         #отправка запроса с заданными параметрами
            posts_number = len(posts.json()['response']['items']) # число новых постов, полученных в текущем проходе
            for j in range(posts_number-1,-1,-1): #теперь будем обрабатывать и выгружать все полученные из ВК посты, начиная с более старых (ранних)
                #print('... элемент по порядку J=' + str(j) + '   count=' + str(my_count))
                #print('id=' + str(posts.json()['response']['items'][j]['id']) + '  text=' + str(posts.json()['response']['items'][j]['text']))
                #elem_id = 'id_' + str(posts.json()['response']['items'][j]['id'])
#                elem_id = str(posts.json()['response']['items'][j]['id']) 
#                print('...проверяем элемент id = ' + elem_id)

                if article_NOT_in_BazeFromVK(str(posts.json()['response']['items'][j]['id'])):
                    #еще проверяем на зацикливание форвардов из разных источников. 
                    elem_txt=(posts.json()['response']['items'][j]['text']) 
                    if(elem_txt.startswith(('Форвард нового сообщения из Фейсбука', 'Форвард нового сообщения из Телеграм'))):
                        print('...публиковать данный пост не надо, это было в ВК и так уже форвард. Но чтобы не сбиваться - надо добавить его в базу. Речь о посте=')
                        print(posts.json()['response']['items'][j]['text'])
                        add_article_to_db_from_VK(str(posts.json()['response']['items'][j]['id']), posts.json()['response']['items'][j]['text'])
                    else:
                        add_article_to_db_from_VK(str(posts.json()['response']['items'][j]['id']), posts.json()['response']['items'][j]['text'])
                        full_text = '*Форвард нового сообщения из ВКонтакте:*\n\n' + str(posts.json()['response']['items'][j]['text']) + '\n\n'+'https://vk.com/wall'+str(groupId_in_VK)+'\_'+str(posts.json()['response']['items'][j]['id'])
                        #print('...full_text = ' + full_text)
                        full_text = full_text.replace("#", " %23")  # шестнадцатеричный код символа # = 0023, т.е. для отображения '\x23'.
                        if len(full_text) > 4096:
                            full_text_fix= len(full_text)
                            while full_text_fix > 4096:
                                first_part_text = full_text[0:4096-35]
                                point_end_of_text = first_part_text.rfind("\n")  
                                first_part_to_send = first_part_text[0:point_end_of_text]               
                                bot_sendtext_to_telega_from_VK(first_part_to_send + '\n_(продолжение следует...)_')
                                full_text = '\n_(...продолжение)_\n' + full_text[point_end_of_text:len(full_text)]
                                full_text_fix= len(full_text)
                            else:
                                bot_sendtext_to_telega_from_VK(full_text)
                        else:
                            bot_sendtext_to_telega_from_VK(full_text)
                        print('...публикуем и добавляем в базу пост с содержанием= ')
                        print(posts.json()['response']['items'][j]['text'])
                else:
                    print('...добавлять и публиковать данный пост не надо, уже есть, речь о посте=')
                    print(posts.json()['response']['items'][j]['text'])
            my_offset += my_count   # наращивание шага продвижения по публикациям, чтобы на всякий случай пройти несколько циклов, если надо
            time.sleep(2)        # принудительная «приостановка» работы программы, для соблюдения требований api по количеству запрсов
    except (Exception, Error) as error:
        print("Какая-то ошибка - 459: ", error)
#=================================================================
# ЗАПУСК
#=================================================================

# Запускаем все это дело:
if Run_On_Heroku: #вариант для Heroku
    if __name__ == '__main__':
        spin_feds()
        get_posts()
        print("===================== теперь обработка ВК")
        grabber_from_VK()
        if connection:
            cursor.close()
            connection.close()
else: #вариант для локального
    if __name__ == '__main__':
        spin_feds()
        get_posts()
        grabber_from_VK()
        if connection:
            cursor.close()
            connection.close()
