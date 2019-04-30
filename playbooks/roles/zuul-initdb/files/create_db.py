#!/bin/python

import mysql.connector
import os
import sys

mysql_host = os.environ["MYSQL_HOST"]
root_passwd = os.environ["MYSQL_ROOT_PASSWD"]

db_name = os.environ["ZUUL_DATABASE"]
buildnumber_db_name = os.environ["BUILD_NUMBER_DATABASE"]
username = os.environ["MYSQL_USER"]
password = os.environ["MYSQL_PASSWD"]

try:
    db = mysql.connector.connect(
        host=mysql_host,
        user="root",
        passwd=root_passwd
    )
except mysql.connector.Error as err:
    print(err)
    exit(1)

c = db.cursor()
query = """
        CREATE DATABASE IF NOT EXISTS `{0}`;
        CREATE DATABASE IF NOT EXISTS `{1}`;
        CREATE OR REPLACE USER '{2}'@'%' IDENTIFIED BY '{3}';
        GRANT ALL privileges ON `{0}`.* TO '{2}'@'%';
        GRANT ALL privileges ON `{1}`.* TO '{2}'@'%';
        FLUSH PRIVILEGES;""".format(db_name, buildnumber_db_name, username, password)
print("Query: " + query + "\n")
try:
    c.execute(query, multi=True)
except mysql.connector.Error as err:
        print("Failed creating database, err: {}".format(err))
        exit(1)
finally:
    db.close()
