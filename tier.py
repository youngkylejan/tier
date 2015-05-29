#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import bcrypt
import concurrent.futures
import MySQLdb
import markdown
import os.path
import re
import subprocess
import torndb
import tornado.escape
from tornado import gen
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import unicodedata

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)
define("mysql_host", default="127.0.0.1:3306", help="database host")
define("mysql_database", default="TIER", help="database name")
define("mysql_user", default="tier", help="database user")
define("mysql_password", default="jian", help="database password")


# A thread pool to be used for password hashing with bcrypt.
executor = concurrent.futures.ThreadPoolExecutor(2)


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", IndexHandler),
            (r"/auth/register", AuthRegisterHandler),
            (r"/auth/login", AuthLoginHandler),
            (r"/auth/logout", AuthLogoutHandler),
        ]
        settings = dict(
            app_title=u"Tier",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
            cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            login_url="/auth/login",
            debug=True,
        )
        super(Application, self).__init__(handlers, **settings)
        
        # Have one global connection to the DB across all handlers
        self.db = torndb.Connection(
            host=options.mysql_host, database=options.mysql_database,
            user=options.mysql_user, password=options.mysql_password)

        self.maybe_create_tables()

    def maybe_create_tables(self):
        
        self.db.execute("SET SESSION default_storage_engine = 'InnoDB'")
        self.db.execute("SET SESSION time_zone = '+0:00'")
        self.db.execute("ALTER DATABASE CHARACTER SET 'utf8'")

        create_user_sql = "CREATE TABLE IF NOT EXISTS user ( \
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY, \
            email VARCHAR(100) NOT NULL UNIQUE, \
            name VARCHAR(100) NOT NULL, \
            hashed_password VARCHAR(100) NOT NULL \
            )"

        create_group_sql = "CREATE TABLE IF NOT EXISTS team ( \
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY, \
            name VARCHAR(100) NOT NULL UNIQUE, \
            leader_id INT NOT NULL REFERENCES user(id) \
            )"

        self.db.execute(create_user_sql)
        self.db.execute(create_group_sql)


class BaseHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return self.application.db

    def get_current_user(self):
        user_id = self.get_secure_cookie("tier_user")
        if not user_id: return None
        return self.db.get("SELECT * FROM user WHERE id = %s", int(user_id))

    def whether_author_exists(self, name):
        sql = "SELECT * FROM user WHERE name = '{}'".format(name)
        return bool(self.db.get(sql))


class IndexHandler(BaseHandler):
    def get(self):
        self.render("index.html", email="kylejan.jan@gmail.com")


class AuthRegisterHandler(BaseHandler):
    def get(self):
        self.render("register.html")

    @gen.coroutine
    def post(self):

        name = self.get_argument("name")
        email = self.get_argument("email")
        pwd = self.get_argument("password")

        if self.whether_author_exists(name):
            raise tornado.web.HTTPError(400, "user already created")
        
        hashed_password = yield executor.submit(
            bcrypt.hashpw, tornado.escape.utf8(pwd),
            bcrypt.gensalt())

        user_id = self.db.execute(
            "INSERT INTO user (email, name, hashed_password) "
            "VALUES (%s, %s, %s)",
            email, name,
            hashed_password)
        
        self.set_secure_cookie("blogdemo_user", str(user_id))
        self.redirect("/")


class AuthLoginHandler(BaseHandler):
    def get(self):
        self.render("login.html", error=None)

    @gen.coroutine
    def post(self):
        user = self.db.get("SELECT * FROM user WHERE email = %s",
                             self.get_argument("email"))
        if not user:
            self.render("login.html", error="Email Not Found")
            return

        hashed_password = yield executor.submit(
            bcrypt.hashpw, tornado.escape.utf8(self.get_argument("password")),
            tornado.escape.utf8(user.hashed_password))

        if hashed_password == user.hashed_password:
            self.set_secure_cookie("tier_user", str(user.id))
            self.redirect("/")
        else:
            self.render("login.html", error="Incorrect Password")


class AuthLogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("tier_user")
        return


def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
