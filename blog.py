import webapp2
import random
import os
import jinja2

from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), autoescape=True)

import re
USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
PASS_RE = re.compile(r"^.{3,20}$")
EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")
def valid_username(username):
	return USER_RE.match(username)

def valid_password(password):
	return PASS_RE.match(password)

def valid_email(email):
	return EMAIL_RE.match(email)


class User(db.Model):
	username = db.StringProperty(required=True)
	password = db.StringProperty(required=True)
	email = db.StringProperty()

import string
import random
import hashlib

def make_salt():
	return ''.join(random.choice(string.letters) for i in xrange(5)) 

def make_cookie(name):
	return str(name+'|'+hashlib.sha256(name).hexdigest())

def make_password(name, pw, salt = None):
	if not salt:
		salt = make_salt()
	return hashlib.sha256(name + pw + salt).hexdigest()+'|'+salt

def valid_pass(name, pw, h):
	salt = h.split('|')[1]
	return h == make_password(name, pw, salt)

def valid_cookie(h):
	name = h.split('|')[0]
	return h == make_cookie(name)


class Handler(webapp2.RequestHandler):
	def write(self, *a, **kw):
		self.response.write(*a, **kw)

	def render_str(self, template, **kw):
		t = jinja_env.get_template(template)
		return t.render(kw)

	def render(self, template, **kw):
		self.write(self.render_str(template, **kw))

class Post(db.Model):
	title = db.StringProperty(required = True)
	body = db.TextProperty(required = True)
	created_on = db.DateTimeProperty(auto_now_add = True)
	created_by = db.StringProperty(default="anonymous")

class FrontPage(Handler):
	def get(self):
		# posts = db.GqlQuery("SELECT * FROM Post")
		# users = db.GqlQuery("SELECT * from User")
		# for post in posts:
		# 	post.delete()
		# for user in users:
		# 	user.delete()
		username = "Login"
		page = "login"
		cookie = self.request.cookies.get("username")
		if cookie:
			if valid_cookie(cookie):
				username = cookie.split('|')[0]
				page = "welcome"
		posts = db.GqlQuery("SELECT * FROM Post ORDER BY created_on desc limit 10")
		self.render("front.html", posts = posts, login=username, page=page, ttl="buZZpost")

class PostHandler(Handler):
	def get(self):
		self.render("post.html")

	def post(self):
		title = self.request.get("title")
		body = self.request.get("body")

		if title != '' and body != '':
			username = ''
			f = 0
			cookie = self.request.cookies.get("username")
			if cookie:
				if valid_cookie(cookie):
					username = cookie.split('|')[0]
				else:
					f = 1
					error = "You must be logged in!"
					self.render("post.html", error=error, title=title, body=body)
			else:
				f = 1
				error = "You must be logged in!"
				self.render("post.html", error=error, title=title, body=body)

			if f == 0:
				post = Post(title=title, body=body, created_by=username)
				post.title = post.title.replace("\n", "<br>")
				post.body = post.body.replace("\n", "<br>")
				post.put()
				self.redirect("/newpost/%s" % str(post.key().id()))
		else:
			error = "You must enter both values!"
			self.render("post.html", error=error, title=title, body=body)

class NewPostHandler(Handler):
	def get(self, post_id):
		key = db.Key.from_path('Post', int(post_id))
		post = db.get(key)

		if not post:
			self.error(404)
			return

		self.render("newpost.html", post=post, idf=post_id, ttl=post.title)

class SignUpHandler(Handler):
	def get(self):
		self.render("signup.html")

	def post(self):
		username = self.request.get('username')
		password = self.request.get('password')
		verify = self.request.get('verify')
		email = self.request.get('email')

		flag = 0

		uerr = ''
		perr = ''
		verr = ''
		eerr = ''

		if valid_username(username) == None:
			uerr = "Please enter a valid username"
			flag = 1
		if valid_password(password) == None:
			perr = "Please enter a valid password"
			flag = 1
		if email != '':
			if valid_email(email) == None:
				eerr = "Please enter a valid email"
				flag = 1
		if password != verify:
			verr = "Passwords don't match"
			flag = 1

		

		if flag == 1:
			self.render("signup.html", username=username, email= email, uerr= uerr, perr=perr, verr=verr, eerr=eerr)
		else:
			f = 0
			password = make_password(username, password)
			user = User(username = username, password = password, email = email)
			users = db.GqlQuery("SELECT *  FROM User where username = '%s'" % username)
			for usr in users:
				if usr.username == username:
					self.render("signup.html", uerr="User already exists!")
					f = 1
			if f != 1:
				user.put()
				self.response.headers.add_header('Set-Cookie', 'username=%s; Path=/' % make_cookie(username))
				self.redirect('/welcome')

class WelcomeHandler(Handler):
	def get(self):
		cookie = self.request.cookies.get('username')
		if cookie:
			if valid_cookie(cookie):
				username = cookie.split('|')[0]
				posts = db.GqlQuery("SELECT * from Post where created_by = '%s'" % username)
				self.render('welcome.html', username=username, posts = posts)
			else:
				self.redirect('/login')
		else:
			self.redirect('/login')

class LoginHandler(Handler):
	def get(self):
		self.render("login.html");

	def post(self):
		username = self.request.get("username");
		password = self.request.get("password");
		users = db.GqlQuery("SELECT * from User");
		f = 1
		for usr in users:
			if usr.username == username:
				if valid_pass(username, password, usr.password):
					f = 0
					self.response.headers.add_header("Set-Cookie", 'username=%s; Path=/' % str(make_cookie(username)))
					self.redirect('/welcome')
			else:
				f = 0
				self.render('login.html', error="Invalid Login!") 
		if f == 1:
			self.render('login.html', error="Invalid login!")

class LogoutHandler(Handler):
	def get(self):
		self.response.headers.add_header('Set-Cookie', 'username=; Path=/')
		self.redirect('/')

class ArchivesHandler(Handler):
	def get(self):
		posts = db.GqlQuery("SELECT * FROM Post ORDER BY created_on desc")
		self.render("front.html", posts = posts)


app = webapp2.WSGIApplication([('/', FrontPage),
							   ('/newpost', PostHandler),
							   ('/signup', SignUpHandler),
							   ('/newpost/([0-9]+)', NewPostHandler),
							   ('/welcome', WelcomeHandler),
							   ('/login', LoginHandler),
							   ('/logout', LogoutHandler),
							   ('/archives', ArchivesHandler)], debug=True)
