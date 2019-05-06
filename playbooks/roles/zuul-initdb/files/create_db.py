#!/bin/python

import mysql.connector
import os
import sys

def connect_mysql():
    mysql_host = os.environ["MYSQL_HOST"]
    root_passwd = os.environ["MYSQL_ROOT_PASSWD"]
    return mysql.connector.connect(host=mysql_host, user="root", passwd=root_passwd)

def create_user(conn):
    username = os.environ["MYSQL_USER"]
    password = os.environ["MYSQL_PASSWD"]

    c = conn.cursor()
    try:
        c.execute("CREATE OR REPLACE USER '{0}'@'%' IDENTIFIED BY '{1}';".format(username, password))
        c.execute("CREATE OR REPLACE USER '{0}'@'localhost' IDENTIFIED BY '{1}';".format(username, password))
    except mysql.connector.Error as err:
        sys.stderr.write("failed to create user {}".format(username))
        raise err
    c.close()

    return username

def create_dbs(conn, username):
    zuul_db_name = os.environ["ZUUL_DATABASE"]
    buildnumber_db_name = os.environ["BUILD_NUMBER_DATABASE"]

    c = conn.cursor()
    for db_name in (zuul_db_name, buildnumber_db_name):
        try:
            c.execute("CREATE DATABASE IF NOT EXISTS `{}`;".format(db_name))
        except mysql.connector.Error as err:
            sys.stderr.write("failed to create database {}".format(db_name))
            raise err

        try:
            c.execute("GRANT ALL privileges ON `{0}`.* TO '{1}'@'%';".format(db_name, username))
            c.execute("GRANT ALL privileges ON `{0}`.* TO '{1}'@'localhost';".format(db_name, username))
        except mysql.connector.Error as err:
            sys.stderr.write("failed to grand privileges to database {0} to user {1}".format(db_name, username))
            raise err

    try:
        c.execute("FLUSH PRIVILEGES;")
    except mysql.connector.Error as err:
        sys.stderr.write("failed to flush priveleges")
        raise err

    c.close()

if __name__ == "__main__":
    try:
        db = connect_mysql()
    except mysql.connector.Error as err:
        sys.stderr.write("failed to connect to mysql: {}". format(err))
        exit(1)

    try:
        username = create_user(db)
        create_dbs(db, username)
        if db.in_transaction:
            db.commit()
    except mysql.connector.Error as err:
        sys.stderr.write("failed to create zuul databases with error: {}". format(err))
        exit(1)
    finally:
        db.close()
