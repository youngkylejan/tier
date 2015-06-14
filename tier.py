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

import json
import datetime
import unicodedata
import bcrypt
import concurrent.futures
import MySQLdb
import os.path
import re
import subprocess
import torndb

import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from tornado import gen
from tornado.escape import json_encode
from tornado.escape import json_decode
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

            (r"/team/lobby", TeamLobbyHandler),
            (r"/team/home", TeamHomeHandler),
            (r"/team/join", TeamJoinHandler),
            (r"/team/create", TeamCreateHandler),
            (r"/team/news", TeamNewsHandler),
            (r"/team/meetings", TeamMeetingHandler),
            (r"/team/members", TeamMemberHandler),
            (r"/team/assignment", TeamAssignmentHandler),

            (r"/dashboard", DashboardHandler),
        ]
        settings = dict(
            app_title=u"Tier",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
            cookie_secret="62oETzKXQAGaYdkL5gEmGeJJFuYq7EQnp2XdTP1o/Vo=",
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
                email VARCHAR(30) NOT NULL UNIQUE, \
                name VARCHAR(30) NOT NULL, \
                hashed_password VARCHAR(100) NOT NULL \
            )"

        create_team_sql = "CREATE TABLE IF NOT EXISTS team ( \
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY, \
                name VARCHAR(30) NOT NULL UNIQUE, \
                leader_id INT NOT NULL REFERENCES user(id), \
                introduction TEXT NOT NULL \
            )"

        create_userTeam_sql = "CREATE TABLE IF NOT EXISTS user_team( \
                user_id INT NOT NULL, \
                team_id INT NOT NULL, \
                PRIMARY KEY(user_id, team_id) \
            );"

        create_news_sql = "CREATE TABLE IF NOT EXISTS news( \
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY, \
                user_id INT NOT NULL, \
                team_id INT NOT NULL, \
                content TEXT NOT NULL, \
                post_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP \
            );"

        create_meetings_sql = "CREATE TABLE IF NOT EXISTS meetings( \
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY, \
                team_id INT NOT NULL, \
                content TEXT NOT NULL, \
                meeting_time DATETIME NOT NULL, \
                post_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP \
            );"

        create_assignments_sql = "CREATE TABLE IF NOT EXISTS assignments( \
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY, \
                team_id INT NOT NULL, \
                target_uid INT NOT NULL, \
                content TEXT NOT NULL, \
                deadline DATETIME NOT NULL, \
                post_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP \
            );"

        self.db.execute(create_user_sql)
        self.db.execute(create_team_sql)
        self.db.execute(create_userTeam_sql)
        self.db.execute(create_news_sql)
        self.db.execute(create_meetings_sql)
        self.db.execute(create_assignments_sql)


class BaseHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return self.application.db

    def get_current_user(self):
        user_id = self.get_secure_cookie("tier_user")
        if not user_id: return None
        return self.db.get("SELECT * FROM user WHERE id = %s", str(user_id))

    def whether_author_exists(self, name):
        sql = "SELECT * FROM user WHERE name = '{}'".format(name)
        return bool(self.db.get(sql))

    def redirect_fault_page(self, error_msg):
        self.render("fault.html", error=error_msg)


class IndexHandler(BaseHandler):
    def get(self):
        if not self.current_user:
            self.render("index.html", username=None)
        else:
            self.render("index.html", username=self.current_user.name)


class AuthRegisterHandler(BaseHandler):
    def get(self):
        self.render("register.html", error=None)

    @gen.coroutine
    def post(self):

        name = self.get_argument("name")
        email = self.get_argument("email")
        pwd = self.get_argument("password")

        if self.whether_author_exists(name):
            self.render("register.html", error="User Exists")
        
        hashed_password = yield executor.submit(
            bcrypt.hashpw, tornado.escape.utf8(pwd),
            bcrypt.gensalt())

        user_id = self.db.execute(
            "INSERT INTO user (email, name, hashed_password) "
            "VALUES (%s, %s, %s)",
            email, name,
            hashed_password)


    def reg_user_callback(self, name):
        doc = yield self.db.user.find({'name': name})
        print doc
        self.set_secure_cookie("tier_user", str(user_id))
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
        self.redirect("/")
        return


class TeamLobbyHandler(BaseHandler):
    def get(self):
        if not self.current_user:
            self.render("fault.html", error="Please Login Firstly!")
            return

        teams = self.db.query("SELECT * FROM team")

        self.render("team_lobby.html", username=self.current_user.name, teams=teams)


class DashboardHandler(BaseHandler):
    def get(self):
        if not self.current_user:
            self.render("fault.html", error="Please Login Firstly")
            return

        qry_sql_user_team = "SELECT team_id FROM user_team WHERE user_id = {}".format(self.current_user.id)
        team_names = self.db.query("SELECT name FROM team WHERE id in (" + qry_sql_user_team + ")")

        self.render("dashboard.html", username = self.current_user.name, user_teams = team_names)


class TeamHomeHandler(BaseHandler):
    def get(self):
        if not self.current_user:
            self.redirect_fault_page("Please Login Firstly!")
            return

        team_name = self.get_argument("name")
        team = self.db.get("SELECT * FROM team WHERE name = %s", team_name)

        if not team:
            self.redirect_fault_page("Team Not Exists")
            return

        leader = self.db.get("SELECT * FROM user WHERE id = %s", team.leader_id)

        self.render("team_home.html", username=self.current_user.name, \
            team_name=team.name, leader_name=leader.name, intro=team.introduction)


class TeamJoinHandler(BaseHandler):
    def post(self):
        user = self.current_user
        team = self.db.get("SELECT * FROM team WHERE name = %s", self.request.arguments['_name'])
        action = self.request.arguments['_action']

        record = self.db.get("SELECT * FROM user_team WHERE user_id = {} and team_id = {}".format(user.id, team.id))
        
        resp = {}
        if not record:
            if action == 'check':
                resp['status'] = 'none'
            else:
                self.db.insert("INSERT INTO user_team(user_id, team_id) VALUES({}, {})".format(user.id, team.id))
                resp['status'] = 'inserts'
        else:
            resp['status'] = 'exists'

        self.write(json_encode(resp))
 

class TeamCreateHandler(BaseHandler):
    def post(self):
        json_msg = self.request.arguments['_create_info'][0]
        msg_body = json.loads(json_msg)
        
        user = self.current_user
        name = msg_body['name']
        intro = msg_body['intro']

        team_record = self.db.get("SELECT * FROM team WHERE name = %s", name)

        resp = {}
        if not team_record:
            self.db.insert("INSERT INTO team(name, leader_id, introduction) VALUES(%s, %s, %s)", name, user.id, intro)
            resp['status'] = 'success'
        else:
            resp['status'] = 'exists'

        self.write(json_encode(resp))


class TeamNewsHandler(BaseHandler):
    def post(self):
        json_msg = self.request.arguments['_body'][0]
        msg_body = json.loads(json_msg)

        resp = {}

        if msg_body['type'] == "post_msg":
            user = self.current_user
            team = self.db.get("SELECT * FROM team WHERE name = %s", msg_body['team'])
            new_content = msg_body['content']

            row = self.db.insert("INSERT INTO news(user_id, team_id, content) VALUES(%s, %s, %s)", user.id, team.id, new_content)

            if row is not None:
                resp = { 'status' : 'success'}
            else:
                resp = { 'status' : 'failed'}

            self.write(json_encode(resp))

        else:
            team = self.db.get("SELECT * FROM team WHERE name = %s", msg_body['team'])
            msgs = self.db.query("SELECT * FROM news WHERE team_id = %s", team.id)

            resp['msgs'] = []
            for msg in msgs:
                user_id = msg['user_id']
                user = self.db.get("SELECT * FROM user WHERE id = %s", user_id)
                resp['msgs'].append({
                    'user' : user.name,
                    'time' : msg['post_time'].strftime('%Y-%m-%d %H:%M:%S'),
                    'content' : msg['content']
                })

            self.write(json_encode(resp))


class TeamMeetingHandler(BaseHandler):
    def post(self):
        json_msg = self.request.arguments['_body'][0]
        msg_body = json.loads(json_msg)

        resp = {}

        if msg_body['type'] == "create":
            team = self.db.get("SELECT * FROM team WHERE name = %s", msg_body['team'])
            content = msg_body['content']
            meeting_time = msg_body['time']

            print meeting_time

            row = self.db.insert("INSERT INTO meetings(team_id, content, meeting_time) VALUES(%s, %s, %s)", \
                team.id, content, meeting_time)

            resp = { 'status' : 'success' } if row is not None else { 'status' : 'failed' }

            self.write(json_encode(resp))

        else:
            return


class TeamMemberHandler(BaseHandler):
    def post(self):
        json_msg = self.request.arguments['_body'][0]
        msg_body = json.loads(json_msg)

        team = self.db.get("SELECT * FROM team WHERE name = %s", msg_body['team'])
        users = self.db.query("SELECT user_id FROM user_team WHERE team_id = %s", team.id)

        user_names = []
        for user in users:
            user_names.append(self.db.get("SELECT name FROM user WHERE id = %s", user['user_id'])['name'])

        resp = { 'members' : user_names }
        self.write(json_encode(resp))


class TeamAssignmentHandler(BaseHandler):
    def post(self):
        json_msg = self.request.arguments['_body'][0]
        msg_body = json.loads(json_msg)

        team_id = self.db.get("SELECT id FROM team WHERE name = %s", msg_body['team'])['id']
        target_uid = self.db.get("SELECT id FROM user WHERE name = %s", msg_body['assignee'])['id']
        self.db.insert("INSERT INTO assignments(team_id, target_uid, content, deadline) VALUES(%s, %s, %s, %s)", \
            team_id, target_uid, msg_body['content'], msg_body['deadline'])

        resp = { 'status' : 'success' }
        self.write(json_encode(resp))
        

def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
