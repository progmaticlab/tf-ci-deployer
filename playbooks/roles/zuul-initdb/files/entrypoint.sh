#!/bin/sh
set -e

pip install mysql-connector
python /root/create_db.py