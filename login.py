#! /usr/bin/env python
# -*- coding: utf-8 -*-
# version 0.1

import cgi
import Cookie
import hashlib
import MySQLdb
import os
import re
import urllib
import urllib2

import settings

def trusted_users():
    trusted_users = []
    conn = MySQLdb.connect(host='sql-s7',
                           db='metawiki_p',
                           read_default_file='/home/mzmcbride/.my.cnf')
    cursor = conn.cursor()
    cursor.execute('''
    /* login.py SLOW_OK */
    SELECT DISTINCT
      pl_title
    FROM pagelinks
    JOIN page
    ON pl_from = page_id
    WHERE page_namespace = 0
    AND page_title = 'Toolserver/watcher'
    AND pl_namespace IN (2,3);
    ''')
    for row in cursor.fetchall():
        trusted_users.append(re.sub('_', ' ', row[0]))
    cursor.close()
    conn.close()
    return trusted_users

secret_key = settings.secret_key
login_status = 'You\'re not logged in.'
form = cgi.FieldStorage()
# Some debugging code
try:
    logout_input = form["logout"].value
except:
    logout_input = '0'
try:
    language_input = form["language"].value
except:
    language_input = None
try:
    project_input = form["project"].value
except:
    project_input = None
try:
    user_input = form["user"].value
except:
    user_input = None
try:
    password_input = form["password"].value
except:
    password_input = None
try:
    tool_input = form["tool"].value
except:
    tool_input = 'watcher'

if user_input is None and logout_input == '0':
    if os.environ.has_key('QUERY_STRING') and tool_input == 'watcher':
        if form.getvalue('titles') is not None:
            return_string = '?' + os.environ['QUERY_STRING']
        else:
            return_string = ''
    else:
        return_string = ''
    print """\
Content-Type: text/html;charset=utf-8\n
<!doctype html>
<html>
<head>
<link rel="stylesheet" href="../style.css?2" type="text/css" />
<title>login</title>
</head>
<body>
<div class="header" id="main-title"><a href="/~mzmcbride/cgi-bin/login.py" title="login">login</a></div>
<form action="http://toolserver.org/~mzmcbride/cgi-bin/login.py%s" method="post">
<table id="input" class="inner-table">
<tr>
<th colspan="2" class="header">Input your <a href="http://toolserver.org/~magnus/tusc.php" title="Toolserver User Screening Control">TUSC</a> info.</th>
</tr>
<tr>
<th>Language</th>
<th style="padding:.3em;">
<input id="language" name="language" style="width:100%%;" />
</th>
</tr>
<tr>
<th>Project</th>
<th style="padding:.3em;">
<input id="project" name="project" style="width:100%%;" />
</th>
</tr>
<tr>
<th>Username</th>
<th style="padding:.3em;">
<input id="username" name="user" style="width:100%%;" />
</th>
</tr>
<tr>
<th>Password</th>
<th style="padding:.3em;">
<input id="password" type="password" name="password" style="width:100%%;" />
</th>
</tr>
<tr>
<th>Tool</th>
<th style="padding:.3em;">
<select id="tool" name="tool" style="width:100%%;">
<option value="watcher" selected="selected">watcher</option>
</select>
</th>
</tr>
<tr>
<td colspan="2" id="input-cell">
<input id="go-button" type="submit" value="Login!" style="width:100%%; margin:0" />
</td>
</tr>
</table>
</form>""" % return_string

elif (language_input
      and project_input
      and user_input
      and password_input
      and tool_input):
    url = 'http://toolserver.org/~magnus/tusc.php'
    values = {'language' : language_input,
              'project' : project_input,
              'user' : user_input,
              'password' : password_input,
              'botmode': '1',
              'check': '1'}
    data = urllib.urlencode(values)
    req = urllib2.Request(url, data)
    response = urllib2.urlopen(req)
    valid_user_check = response.read()
    if valid_user_check == '1':
        if user_input in trusted_users(): # FIXME Need to check for global account
             m = hashlib.md5()
             m.update(user_input)
             m.update(tool_input)
             m.update(secret_key)
             session = m.hexdigest()
             cookie = Cookie.SimpleCookie()
             cookie['mz_chocolate_chip'] = session
             cookie['mz_chocolate_chip']['max-age'] = 60**5
             cookie['mz_chocolate_chip']['path'] = '/~mzmcbride/watcher/'
             if tool_input == 'watcher' and form.getvalue('titles') is not None:
                  return_message = ' Proceed to <a href="http://toolserver.org/~mzmcbride/watcher/?db=%s&titles=%s" title="watcher">watcher</a>?' % (form.getvalue('db'), form.getvalue('titles'))
             else:
                  return_message = ' Proceed to <a href="http://toolserver.org/~mzmcbride/watcher/" title="watcher">watcher</a>?'
             login_status = 'You\'re now logged in!%s' % return_message
             print cookie
        else:
             login_status = 'Sorry, you\'re not on the <a href="http://meta.wikimedia.org/wiki/Toolserver/watcher" title="access list">access list</a>.'
    elif valid_user_check == '0':
        login_status = 'Sorry, there\'s something wrong with your <a href="http://toolserver.org/~magnus/tusc.php" title="Toolserver User Screening Control">TUSC</a> info.'
    else:
        login_status = 'Sorry, there was an error. It was likely due to setting the wrong language or project. Please remember that sites like Wikimedia Commons use language: commons and project: wikimedia.'
    print """\
Content-Type: text/html;charset=utf-8\n
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
<head>
<link rel="stylesheet" href="../style.css?2" type="text/css" />
<title>login</title>
</head>
<body>
<div class="header" id="main-title"><a href="/~mzmcbride/cgi-bin/login.py" title="login">login</a></div>
<div style="margin:0 auto; width:50%%; text-align:center;">%s</div>""" % (login_status)

else:
    if logout_input == '1':
         if tool_input == 'watcher':
             if form.getvalue('titles') is not None:
                 return_message = ' Return to <a href="http://toolserver.org/~mzmcbride/cgi-bin/watcher.py?db=%s&titles=%s" title="watcher">watcher</a>?' % (form.getvalue('db'), form.getvalue('titles'))
             else:
                 return_message = ' Return to <a href="http://toolserver.org/~mzmcbride/cgi-bin/watcher.py" title="watcher">watcher</a>?'
         else:
             return_message = ''
         login_status = 'You\'re now logged out. Congratulations.%s' % return_message
         cookie = Cookie.SimpleCookie()
         cookie['mz_chocolate_chip'] = 'invalid'
         cookie['mz_chocolate_chip']['max-age'] = 0
         cookie['mz_chocolate_chip']['path'] = '/~mzmcbride/watcher/'
         print cookie
    else:
         login_status = 'Sorry, some piece of your login credentials is missing.'
    print """\
Content-Type: text/html;charset=utf-8\n
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
<head>
<link rel="stylesheet" href="../style.css?2" type="text/css" />
<title>login</title>
</head>
<body>
<div class="header" id="main-title"><a href="/~mzmcbride/cgi-bin/login.py" title="login">login</a></div>
<div style="margin:0 auto; width:50%%; text-align:center;">%s</div>""" % (login_status)

print """\
<div id="footer">
<div id="meta-info">
<a href="http://www.gnu.org/copyleft/gpl.html" title="GNU General Public License, version 3">license</a><!--
-->&nbsp;<b>&middot;</b>&nbsp;<!--
--><a href="http://en.wikipedia.org/w/index.php?title=User_talk:MZMcBride&action=edit&section=new" title="Report a bug">bugs</a>
</div>
</div>
</body>
</html>"""
