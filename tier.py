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
import uuid
from time import gmtime, strftime

import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from tornado import gen
from tornado.concurrent import Future
from tornado.escape import json_encode
from tornado.escape import json_decode
from tornado.options import define, options

from chats import MessageBuffer

define("port", default=8080, help="run on the given port", type=int)

define("mysql_host", default="127.0.0.1:3306", help="database host")
define("mysql_database", default="TIER", help="database name")
define("mysql_user", default="tier", help="database user")
define("mysql_password", default="jian", help="database password")

# A thread pool to be used for password hashing with bcrypt.
executor = concurrent.futures.ThreadPoolExecutor(2)

# Making this a non-singleton is left as an exercise for the reader.
global_message_buffer = MessageBuffer()


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", IndexHandler),

            (r"/auth/signup", AuthSignUpHandler),
            (r"/auth/signin", AuthSignInHandler),
            (r"/auth/signout", AuthSignOutHandler),

            (r"/team/home", TeamHomeHandler),
            (r"/team/join", TeamJoinHandler),

            (r"/team/create", TeamCreateHandler),
            (r"/team/news", TeamNewsHandler),
            (r"/team/meetings", TeamMeetingHandler),
            (r"/team/members", TeamMemberHandler),
            (r"/team/assignments", TeamAssignmentHandler),

            (r"/team/dashboard", DashboardHandler),
            (r"/team/chat/new", MessageNewHandler),
            (r"/team/chat/updates", MessageUpdatesHandler),

            (r"/user/deadlines", UserDeadlineHandler),
            (r"/user/lobby", UserLobbyHandler),
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

        create_join_applys_sql = "CREATE TABLE IF NOT EXISTS joinApplys( \
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY, \
                user_id INT NOT NULL, \
                team_id INT NOT NULL, \
                post_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP \
            );"

        self.db.execute(create_user_sql)
        self.db.execute(create_team_sql)
        self.db.execute(create_userTeam_sql)
        self.db.execute(create_news_sql)
        self.db.execute(create_meetings_sql)
        self.db.execute(create_assignments_sql)
        self.db.execute(create_join_applys_sql)


class BaseHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return self.application.db

    def get_current_user(self):
        user_id = self.get_secure_cookie("tier_user")
        if not user_id: return None
        return self.get_user_by_id(str(user_id))

    def whether_author_exists(self, name):
        return bool(self.db.get("SELECT * FROM user WHERE name = %s", name))

    def redirect_fault_page(self, error_msg):
        self.render("fault.html", error=error_msg)

    def get_user_by_name(self, name):
        user = self.db.get("SELECT * FROM user WHERE name = %s", name)
        return None if not user else user

    def get_team_by_name(self, name):
        team = self.db.get("SELECT * FROM team WHERE name = %s", name)
        return None if not team else team

    def get_user_by_id(self, id):
        user = self.db.get("SELECT * FROM user WHERE id = %s", id)
        return None if not user else user

    def get_team_by_id(self, id):
        team = self.db.get("SELECT * FROM team WHERE id = %s", id)
        return None if not team else team

    def get_teams(self):
        teams = self.db.query("SELECT * FROM team")
        return None if not teams else teams

    def get_teams_by_userid(self, id):
        teams = self.db.query("SELECT * FROM team WHERE id IN (SELECT team_id FROM user_team WHERE user_id = %s)", id)
        return None if not teams else teams

    def get_teams_by_username(self, name):
        user = self.get_user_by_name(name)
        if not user: return None
        return self.get_teams_by_userid(user.id)

    def get_members_by_teamid(self, id):
        members = self.db.query("SELECT * FROM user WHERE id IN (SELECT user_id FROM user_team WHERE team_id = %s)", id)
        return None if not members else members

    def get_members_by_teamname(self, name):
        team = self.get_team_by_name(name)
        if not team: return None
        return self.get_members_by_teamid(team.id)

    def get_teams_except_by_userid(self, id):
        excepted_teams = self.db.query("SELECT * FROM team WHERE id NOT IN (SELECT team_id FROM user_team WHERE user_id = %s)", id)
        return None if not excepted_teams else excepted_teams

    def get_teams_except_by_username(self, name):
        user = self.get_user_by_name(name)
        if not user: return None
        return self.get_teams_except_by_userid(user.id)

    def bind_user_team(self, uid, tid):
        self.db.insert("INSERT INTO user_team(user_id, team_id) VALUES(%s, %s)", uid, tid)

    def insert_team_with_info(self, name, leaderid, intro):
        self.db.insert("INSERT INTO team(name, leader_id, introduction) VALUES(%s, %s, %s)", name, leaderid, intro)
        team = self.get_team_by_name(name)
        self.bind_user_team(leaderid, team.id)

    def get_userTeam_record_by_ids(self, uid, tid):
        record = self.db.get("SELECT * FROM user_team WHERE user_id = %s and team_id = %s", uid, tid)
        return None if not record else record

    def insert_userTeam_record_with_ids(self, uid, tid):
        self.db.insert("INSERT INTO user_team(user_id, team_id) VALUES(%s, %s)", uid, tid)

    def get_news_by_teamid(self, id):
        news = self.db.query("SELECT * FROM news WHERE team_id = %s", id)
        return None if not news else news

    def get_news_by_teamname(self, name):
        team = self.get_team_by_name(name)
        return self.get_news_by_teamid(team.id)

    def insert_news_with_info(self, uid, tid, content):
        self.db.insert("INSERT INFO news(user_id, team_id, content) VALUES(%s, %s, %s)", uid, tid, content)

    def get_applys_by_teamid(self, tid):
        records = self.db.query("SELECT * FROM joinApplys WHERE team_id = %s", tid)
        return None if not records else records

    def get_applys_by_ids(self, uid, tid):
        records = self.db.query("SELECT * FROM joinApplys WHERE user_id = %s AND team_id = %s", uid, tid)
        return None if not records else records

    def get_applys_by_teamname(self, tname):
        team = self.get_team_by_name(tname)
        return self.get_applys_by_teamid(team.id)

    def get_applys_by_names(self, uname, tname):
        user = self.get_user_by_name(uname)
        team = self.get_team_by_name(tname)
        return self.get_applys_by_ids(user.id, team.id)

    def insert_applys_with_info(self, uid, tid):
        self.db.insert("INSERT INTO joinApplys(user_id, team_id) VALUES(%s, %s)", uid, tid)

    def remove_applys_with_info(self, uid, tid):
        self.db.execute("DELETE FROM joinApplys WHERE user_id = %s AND team_id = %s", uid, tid)

    def is_user_team_leader(self, uid, tid):
        record = self.db.get("SELECT * FROM user_team WHERE user_id = %s AND team_id = %s", uid, tid)
        return False if not record else True


class IndexHandler(BaseHandler):
    def get(self):
        if self.request.headers['User-Agent'].find('iPhone') == -1:
            index_html = "index.html"
        else:
            index_html = "indexIOS.html"

        if not self.current_user:
            self.render(index_html, username=None)
        else:
            self.render(index_html, username=self.current_user.name)


class AuthSignUpHandler(BaseHandler):
    def get(self):
        if self.request.headers['User-Agent'].find('iPhone') == -1:
            user_agent = None
        else:
            user_agent = "iPhone"
        self.render("signup.html", user_agent=user_agent, error=None)

    @gen.coroutine
    def post(self):
        name = self.get_argument("name")
        email = self.get_argument("email")
        pwd = self.get_argument("password")

        if self.request.headers['User-Agent'].find('iPhone') == -1:
            user_agent = None
        else:
            user_agent = "iPhone"

        if self.whether_author_exists(name):
            self.render("signup.html", user_agent=user_agent, error="User Exists")
        
        hashed_password = yield executor.submit(
            bcrypt.hashpw, tornado.escape.utf8(pwd),
            bcrypt.gensalt())

        user_id = self.db.execute(
            "INSERT INTO user (email, name, hashed_password) "
            "VALUES (%s, %s, %s)",
            email, name,
            hashed_password)

        self.redirect("/")

    def reg_user_callback(self, name):
        doc = yield self.db.user.find({'name': name})
        print doc
        self.set_secure_cookie("tier_user", str(user_id))
        self.redirect("/")


class AuthSignInHandler(BaseHandler):
    def get(self):
        if self.request.headers['User-Agent'].find('iPhone') == -1:
            user_agent = None
        else:
            user_agent = "iPhone"
        self.render("signin.html", user_agent=user_agent, error=None)

    @gen.coroutine
    def post(self):
        if self.request.headers['User-Agent'].find('iPhone') == -1:
            user_agent = None
        else:
            user_agent = "iPhone"

        user = self.db.get("SELECT * FROM user WHERE email = %s",
                             self.get_argument("email"))
        if not user:
            self.render("signin.html", user_agent=user_agent, error="Email Not Found")
            return

        hashed_password = yield executor.submit(
            bcrypt.hashpw, tornado.escape.utf8(self.get_argument("password")),
            tornado.escape.utf8(user.hashed_password))

        if hashed_password == user.hashed_password:
            self.set_secure_cookie("tier_user", str(user.id))
            self.redirect("/")
        else:
            self.render("signin.html", user_agent=user_agent, error="Incorrect Password")


class AuthSignOutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("tier_user")
        self.redirect("/")


class TeamCreateHandler(BaseHandler):
    def post(self):
        req = json.loads(self.request.arguments['_body'][0])

        resp = {}
        team = self.get_team_by_name(req['name'])

        if not team:
            self.insert_team_with_info(req['name'], self.current_user.id, req['intro'])
            resp['status'] = 'success'
        else:
            resp['status'] = 'exists'

        self.write(json_encode(resp))


class DashboardHandler(BaseHandler):
    def get(self):
        if not self.current_user:
            self.render("fault.html", error="Please Login Firstly")
            return

        team = self.get_team_by_name(self.get_argument('name'))
        members = self.get_members_by_teamid(team.id)
        team_news = self.get_news_by_teamid(team.id)

        applys = None
        if self.is_user_team_leader(self.current_user.id, team.id) == True:
            applys = self.get_applys_by_teamid(team.id)

        if team_news != None:
            for new in team_news:
                user = self.get_user_by_id(new.user_id)
                new['user_name'] = user.name

        if applys != None:
            for apply in applys:
                user = self.get_user_by_id(apply.user_id)
                apply['user_name'] = user.name

        self.render("dashboard.html", username = self.current_user.name, \
            team = team, team_news = team_news, team_members = members, applys = applys, messages = global_message_buffer.cache)


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
        json_msg = self.request.arguments['_body'][0]
        msg_body = json.loads(json_msg)

        action = msg_body['action']
        user = self.get_user_by_name(msg_body['user_name'])
        team = self.get_team_by_name(msg_body['team_name'])
        record = self.get_userTeam_record_by_ids(user.id, team.id)
        pre_apply = self.get_applys_by_ids(user.id, team.id)

        resp = {}
        if not record:
            if action == 'check' and pre_apply == None:
                resp['status'] = 'none'

            elif action == 'check' and pre_apply != None:
                resp['status'] = 'applys'

            elif action == 'apply':
                self.insert_applys_with_info(user.id, team.id)
                resp['status'] = 'applys'

            elif action == 'accept':
                self.insert_userTeam_record_with_ids(user.id, team.id)
                self.remove_applys_with_info(user.id, team.id)
                resp['status'] = 'inserts'
        else:
            resp['status'] = 'exists'

        self.write(json_encode(resp))
 

class TeamNewsHandler(BaseHandler):
    def post(self):
        json_msg = self.request.arguments['_body'][0]
        msg_body = json.loads(json_msg)

        resp = {}

        user = self.current_user
        team = self.get_team_by_name(msg_body['team'])
        new_content = msg_body['content']

        row = self.db.insert("INSERT INTO news(user_id, team_id, content) VALUES(%s, %s, %s)", user.id, team.id, new_content)

        if row is not None:
            resp = { 'status' : 'success'}
        else:
            resp = { 'status' : 'failed'}

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

            row = self.db.insert("INSERT INTO meetings(team_id, content, meeting_time) VALUES(%s, %s, %s)", \
                team.id, content, meeting_time)

            resp = { 'status' : 'success' } if row is not None else { 'status' : 'failed' }

            self.write(json_encode(resp))

        else:
            uid = self.db.get("SELECT id FROM user WHERE name = %s", msg_body['user'])['id']
            teams = self.db.query("SELECT team_id FROM user_team WHERE user_id = %s", uid)

            meetings = []
            for team in teams:
                team_name = self.db.get("SELECT name FROM team WHERE id = %s", team['team_id'])['name']
                queryed_meetings = self.db.query("SELECT * FROM meetings WHERE team_id = %s", team['team_id'])
                
                for meeting in queryed_meetings:
                    if meeting:
                        meetings.append(
                            {
                                'team': team_name,
                                'meeting_time': meeting['meeting_time'].strftime('%Y-%m-%d %H:%M:%S'),
                                'content': meeting['content']
                            }
                        )

            resp = { 'meetings' : meetings }
            self.write(json_encode(resp))


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


class UserDeadlineHandler(BaseHandler):
    def post(self):
        json_msg = self.request.arguments['_body'][0]
        msg_body = json.loads(json_msg)

        resp = {}

        uid = self.db.get("SELECT id FROM user WHERE name = %s", msg_body['user'])['id']
        teams = self.db.query("SELECT team_id FROM user_team WHERE user_id = %s", uid)

        deadlines = []
        for team in teams:
            team_name = self.db.get("SELECT name FROM team WHERE id = %s", team['team_id'])['name']
            queryed_assignments = self.db.query("SELECT * FROM assignments WHERE team_id = %s and target_uid = %s", team['team_id'], uid)
            for assignment in queryed_assignments:
                if assignment:
                    deadlines.append(
                        {
                            'team': team_name,
                            'deadline': assignment['deadline'].strftime('%Y-%m-%d %H:%M:%S'),
                            'content': assignment['content']
                        }
                    )

        resp = { 'deadlines' : deadlines }
        self.write(json_encode(resp))


class UserLobbyHandler(BaseHandler):
    def get(self):
        if not self.current_user:
            self.redirect_fault_page("login firstly!")
            return

        if self.request.headers['User-Agent'].find('iPhone') == -1:
            user_agent = None
        else:
            user_agent = "iPhone"

        args = {}
        args['user_agent'] = user_agent
        args['username'] = self.current_user.name
        args['excepted_teams'] = self.get_teams_except_by_userid(self.current_user.id)
        args['joined_teams'] = self.get_teams_by_userid(self.current_user.id)

        self.render("user_lobby.html", **args)


class MessageNewHandler(BaseHandler):
    def post(self):
        message = {
            "id": str(uuid.uuid4()),
            "user_name": self.current_user.name,
            "body": self.get_argument("body"),
            "post_time": strftime("%Y-%m-%d %H:%M:%S", gmtime())
        }
        # to_basestring is necessary for Python 3's json encoder,
        # which doesn't accept byte strings.
        message["html"] = tornado.escape.to_basestring(
            self.render_string("modules/message.html", message=message))
        if self.get_argument("next", None):
            self.redirect("/team/chat/new", self.get_argument("next"))
        else:
            self.write(message)
        global_message_buffer.new_messages([message])


class MessageUpdatesHandler(BaseHandler):
    @gen.coroutine
    def post(self):
        cursor = self.get_argument("cursor", None)
        # Save the future returned by wait_for_messages so we can cancel
        # it in wait_for_messages
        self.future = global_message_buffer.wait_for_messages(cursor=cursor)
        messages = yield self.future
        if self.request.connection.stream.closed():
            return
        self.write(dict(messages=messages))

    def on_connection_close(self):
        global_message_buffer.cancel_wait(self.future)


def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port, "0.0.0.0")
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
