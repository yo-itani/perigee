#!/bin/bash
mariadb -u root -p"${MARIADB_ROOT_PASSWORD}" <<-EOSQL
    CREATE DATABASE IF NOT EXISTS perigee_test;
    GRANT ALL PRIVILEGES ON perigee_test.* TO '${MARIADB_USER}'@'%';
    FLUSH PRIVILEGES;
EOSQL
