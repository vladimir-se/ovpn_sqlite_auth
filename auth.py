#!/usr/bin/env python3
#coding: utf-8

import sqlite3
import argparse
import getpass
import hashlib
import os
import re


class PasswordMismatch(Exception):
    '''
    Exception для ошибки сравнения паролей.
    '''
    def __init__(self):
        self.printerror()

    def printerror(self):
        print('Пароли не совпадают!')


class DBWorker():
    def __init__(self):
        self.DB_NAME = 'ovpn.db'
        self.DB_PATH = os.path.dirname(os.path.realpath(__file__)) + os.sep + self.DB_NAME
        try:
            self.conn = sqlite3.connect(self.DB_PATH)
            self.curs = self.conn.cursor()
        except:
            exit(1)
    
    def finish(self):
        '''
        Коммит и закрытие соединения с БД.
        '''
        self.conn.commit()
        self.conn.close()

    def pass_check(self, not_auth = False, password = '', password2 = ''):
        '''
        Ввод, проверка и шифрование пароля.
        '''
        if not_auth:
            while True:
                # Ввод паролей
                password = getpass.getpass(prompt='Введите пароль пользователя: ', stream=None)
                password2 = getpass.getpass(prompt='Повторите пароль пользователя: ', stream=None)
                # Хэширование
                password = hashlib.sha512(bytes(password, 'utf-8')).digest()
                password2 = hashlib.sha512(bytes(password2, 'utf-8')).digest()
                if password != password2:
                    print('Пароли не совпадают')
                    continue
                break
            return(password)
        # Прорверка пароля при авторизации в OpenVPN.
        else:
            # password2 полученные из БД имеет тип str, чтобы корректно сравнить пароли password в str.
            password = str(hashlib.sha512(bytes(password, 'utf-8')).digest())
            return password == password2

    def db_init(self, args=False):
        '''
        Инициализация БД.
        '''
        try:
            self.curs.execute('''CREATE TABLE "users" (
                "id"	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                "login"	TEXT NOT NULL UNIQUE,
                "password"	TEXT NOT NULL,
                "active"	INTEGER NOT NULL
            )''')
            self.finish()
        except:
            return(1)
        print('Инициализация БД прошла успешно!')
        return(0)

    def db_chk_user(self, login):
        '''
        Проверка имени пользователя на корректность.
        Проверка наличия пользователя в БД.
        '''
        pattern = re.compile("[A-Za-z0-9]+")
        if (pattern.fullmatch(login) is None) or (len(login) < 3):
            print('Не корректное имя пользователя!')
            exit(1)

        if (self.curs.execute(f'SELECT "login" FROM "users" WHERE "users"."login" = "{login}";').fetchone()):
            return(True)
        return(False)

    def db_adduser(self, args):
        '''
        Добавление пользователя в БД.
        '''
        # Если пользователя нет в БД.
        if not self.db_chk_user(args.login):
            try:
                # Шифруем и проверяем пароль.
                password = self.pass_check(not_auth=True)
                # Добавляем новую запись в БД.
                self.curs.execute(f'''INSERT INTO "users" ("login", "password", "active") VALUES 
                    ("{args.login}",
                    "{password}", 
                    "{int(args.activate)}");''')
                self.finish()
                print(f'Пользователь {args.login} успепшно добавлен!')
                exit(0)
            except sqlite3.OperationalError:
                print('Ошибка БД! Пользователь не добавлен.')
                exit(1)
            except KeyboardInterrupt:
                print('Пользователь не добавлен.')
                exit(1)
        else:
            print(f'Пользователь {args.login} уже существует!')
            exit(1)

    def db_activuser(self, args):
        '''
        Активация пользователя.
        '''
        if self.db_chk_user(args.login):
            try:
                self.curs.execute(f'UPDATE "users" SET "active" = "{int( not args.deactivate)}" WHERE "users"."login" = "{args.login}";')
                self.finish()
                if not args.deactivate:
                    print("Учетная запись активирована.")
                else:
                    print("Учетная запись деактивирована.")
            except sqlite3.OperationalError:
                print('Ошибка записи в БД.')
                exit(1)
    
    def db_user_isactive(self, login):
        '''
        Активна ли учетная запись пользователя.
        '''
        if self.curs.execute(f'SELECT "active" FROM "users" WHERE "users"."login" = "{login}";').fetchone()[0]:
            return 1
        else:
            return 0

    def db_change_pwd(self, args):
        '''
        Изменение пользовательского пароля.
        '''
        if self.db_chk_user(args.login):
            password = self.pass_check(not_auth=True)
            try:
                self.curs.execute(f'UPDATE "users" SET "password" = "{password}" WHERE "users"."login" = "{args.login}";')
                self.finish()
                print('Парорль успешно изменен.')
                exit(0)
            except sqlite3.OperationalError:
                print('Ошибка записи в БД.')
                exit(1)
        else:
            print(f'Пользователь {args.login} не существует!')
            exit(1)

    def db_userinfo(self, args):
        '''
        Информация о пользователе из базы.
        '''
        if self.db_chk_user(args.login):
            if self.db_user_isactive(args.login):
                print(f'Пользователь {args.login} активен.')
                exit(0)
            else:
                print(f'Пользователь {args.login} не активен.')
                exit(0)
        print(f'Пользователь {args.login} не существует!')
        exit(1)

    def auth(self, args):
        '''
        Авторизация в OpenVPN.
        '''
        authfile = open(args.file, 'r')
        login, password = [i.strip() for i in authfile.readlines()]
        authfile.close()

        if self.db_chk_user(login) and self.db_user_isactive(login):
            password2 = self.curs.execute(f'SELECT "password" FROM "users" WHERE "users"."login" = "{login}";').fetchone()[0]
            if self.pass_check(not_auth=False, password=password, password2=password2):
                exit(0)
        exit(1)

if __name__ == '__main__':
    db = DBWorker()

    parser = argparse.ArgumentParser()   
    subparser = parser.add_subparsers()

    ''' Инициализация БД '''
    init_parser = subparser.add_parser('init', help='Инициализация БД')
    # init_parser.add_argument('database', metavar='users', help='БД пользователей')
    init_parser.set_defaults(func=db.db_init)

    ''' Добавдение пользователя '''
    adduser_parser = subparser.add_parser('uadd', help='Добавление пользователя')
    adduser_parser.add_argument('login', metavar='login', help='Имя пользователя (не менее 3х символов латинского алфавита и цифры)')
    adduser_parser.add_argument('-a', dest='activate', action='store_true', help='Активировать пользователя')
    adduser_parser.set_defaults(func=db.db_adduser)

    ''' Активация пользователя '''
    active_parser = subparser.add_parser('act', help='Активация пользователя')
    ''' Деактивация пользователя '''
    active_parser.add_argument('-d', dest='deactivate', action='store_true', default=False, help='Деактивировать пользователя')
    active_parser.add_argument('login', metavar='login', help='Имя пользователя')
    active_parser.set_defaults(func=db.db_activuser)

    ''' Смена пароля пользователю '''
    chpwd_parser = subparser.add_parser('pch', help='Смена пароля пользователя')
    chpwd_parser.add_argument('login', metavar='login', help='Имя пользователя')
    chpwd_parser.set_defaults(func=db.db_change_pwd)

    ''' Информация о пользователе '''
    user_info_parser = subparser.add_parser('inf', help='Информация о пользователе')
    user_info_parser.add_argument('login', metavar='login', help='Имя пользователя')
    user_info_parser.set_defaults(func=db.db_userinfo)

    ''' Авторизация OpenVPN via-file '''
    ovpnauth_parser = subparser.add_parser('auth-via-file', help='Авторизация OpenVPN через файл')
    ovpnauth_parser.add_argument('file', metavar='auth-file', help='Файл для авторизации')
    ovpnauth_parser.set_defaults(func=db.auth)

    args = parser.parse_args()

    # Выводить подсказку если скрипт запущен без параметров.
    if not vars(args):
        parser.print_usage()
    else:
        args.func(args)
