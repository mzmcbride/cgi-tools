#! /usr/bin/env python
# -*- coding: utf-8 -*-
# version 0.8
# test cases:
# http://toolserver.org/~mzmcbride/cgi-bin/watcher-test.py?titles=user%20talk:Philippe|main%20Page|User_talk:MZMcBride
# http://toolserver.org/~mzmcbride/cgi-bin/watcher-test.py?db=enwiki_p&titles=Wikipedia_caultk:Sandbox|Wikipedia_caulk:Sandbox
# http://toolserver.org/~mzmcbride/cgi-bin/watcher-test.py?db=enwiki_p&titles=Fooooooo|Barbbbbbb|
# http://toolserver.org/~mzmcbride/cgi-bin/watcher-test.py?db=enwiki_p&titles=Main+Page%7CFooooooooo|||
# http://toolserver.org/~mzmcbride/cgi-bin/watcher-test.py?db=bgwiki_p&titles=<b>test</b>
# Wikipédia:Annonces with frwiki_p
# Интранет on bgwiki_p
# HAGGER????????????????????????????????????????????? on enwiki_p
# Main page on enwiki_p
# http://toolserver.org/~mzmcbride/cgi-bin/watcher-test.py?db=enwiktionary_p&titles=fap
# http://toolserver.org/~mzmcbride/cgi-bin/watcher-test.py?db=dewiki_p
# http://toolserver.org/~mzmcbride/cgi-bin/watcher-test.py?db=
# http://toolserver.org/~mzmcbride/cgi-bin/watcher-test.py
# http://toolserver.org/~mzmcbride/cgi-bin/watcher-test.py?db=dewiki_ppppp
import cgi, cgitb; cgitb.enable()

import os
import urllib
import urllib2
import re
import xml.sax.saxutils
import glob
import MySQLdb
import Cookie
import hashlib

import settings

if os.environ.has_key('HTTP_COOKIE'):
    dough = os.environ['HTTP_COOKIE']
    cookies = dough.split(';')
    for i in cookies:
        cookie_session = i.split('=')[1]
else:
    cookie_session = 'invalid'

def trusted_users():
    trusted_users = []
    conn = MySQLdb.connect(host='sql-s3', db='metawiki_p', read_default_file='/home/mzmcbride/.my.cnf')
    cursor = conn.cursor()
    cursor.execute('''
    /* deliverybot-2.py SLOW_OK */
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
        page_title = u'%s' % unicode(row[0], 'utf-8')
        trusted_users.append(re.sub('_', ' ', page_title))
    cursor.close()
    conn.close()
    return trusted_users

def database_list():
    conn = MySQLdb.connect(host='sql-s3', db='toolserver', read_default_file='/home/mzmcbride/.my.cnf')
    cursor = conn.cursor()
    cursor.execute('''
    /* wikistalk.py database_list */
    SELECT
      dbname
    FROM wiki
    WHERE is_closed = 0;
    ''')
    return [row[0] for row in cursor.fetchall()]

def choose_host_and_domain(db):
    conn = MySQLdb.connect(host='sql-s3', db='toolserver', read_default_file='/home/mzmcbride/.my.cnf')
    cursor = conn.cursor()
    cursor.execute('''
    /* watcher.py choose_host_and_domain */
    SELECT
      server,
      domain
    FROM wiki
    WHERE dbname = '%s';
    ''' % db)
    for row in cursor.fetchall():
      host = 'sql-s%s' % str(row[0])
      domain = '%s' % row[1]
    return host, domain
    cursor.close()
    conn.close()

def page_info(db, namespace, page_title):
    conn = MySQLdb.connect(host=host, db=db, read_default_file='/home/mzmcbride/.my.cnf')
    cursor = conn.cursor()
    cursor.execute('''
    /* watcher.py page_info */
    SELECT
      page_is_redirect,
      COUNT(*)
    FROM watchlist
    JOIN toolserver.namespace
    ON dbname = %s
    AND wl_namespace = ns_id
    LEFT JOIN page
    ON page_namespace = wl_namespace
    AND page_title = wl_title
    WHERE ns_name = %s
    AND wl_title = %s;
    ''' , (db, ns_name, page_title))
    for row in cursor.fetchall():
        return { 'page_status': row[0], 'count': row[1]}
    cursor.close()
    conn.close()

secret_key = settings.secret_key
trusted_keys = []
for name in trusted_users():
    n = hashlib.md5()
    n.update(name)
    n.update('watcher')
    n.update(secret_key)
    trusted_keys.append(n.hexdigest())

if cookie_session in trusted_keys:
    logged_in = True
else:
    logged_in = False

form = cgi.FieldStorage()
# Pick a db; make enwiki_p the default
if form.getvalue('db') is not None:
    db = form.getvalue('db')
else:
    db = 'enwiki_p'

# All right, now let's pick a host and domain
try:
    host_and_domain = choose_host_and_domain(db)
    host = host_and_domain[0]
    domain = host_and_domain[1]
except:
    host = None
    domain = None

if 'titles' in form:
    input = form["titles"].value
else:
    input = ''

cj_info = '' # In case it doesn't get set later.
redirect_count = 0
exclude_count = 0
output = []
if host is not None:
    for title in input.split('|'):
        if title == '':
            continue
        else:
            try:
                ns_name = re.sub('_', ' ', title.split(':')[0][0].upper() + title.split(':')[0][1:])
            except:
                ns_name = ''
            if title.split(':')[0] == title:
                ns_name = ''
            try:
                pre_title = title.split(':')[1]
            except:
                pre_title = title.split(':')[0]
            if re.search('wikt', db, re.I):
                page_title = re.sub(r'(%20| )', '_', pre_title[0] + pre_title[1:])
            else:
                try:
                    page_title = re.sub(r'(%20| )', '_', pre_title[0].upper() + pre_title[1:])
                except:
                    page_title = ''
            combined_title = re.sub(r'(%20| )', '_', '%s:%s' % (ns_name, page_title))
            title_info = page_info(db, ns_name, page_title)
            page_status = title_info['page_status']
            if page_status is None:
                 css_class = 'red'
            elif page_status == 1:
                 redirect_count += 1
                 css_class = 'redirect'
            else:
                 css_class = 'normal'
            count = title_info['count']
            if count == 0 and re.search(':', title):
                ns_name = ''
                if page_info(db, ns_name, combined_title) > 0:
                    title_info = page_info(db, ns_name, combined_title)
                    count = title_info['count']
                    pretty_title = '%s:%s' % (re.sub('_', ' ', ns_name), re.sub('_', ' ', combined_title))
                else:
                    ns_name = re.sub('_', ' ', title.split(':')[0][0].upper() + title.split(':')[0][1:])
                    title_info = page_info(db, ns_name, page_title)
                    count = title_info['count']
                    pretty_title = '%s:%s' % (re.sub('_', ' ', ns_name), re.sub('_', ' ', page_title))
            elif not re.search(':', title):
                ns_name = ''
                if re.search('wikt', db, re.I):
                     pre_title = re.sub(r'(%20| )', '_', pre_title[0] + pre_title[1:])
                else:
                     pre_title = re.sub(r'(%20| )', '_', pre_title[0].upper() + pre_title[1:])
                title_info = page_info(db, ns_name, pre_title) # Bad hack like what.
                count = title_info['count']
                pretty_title = '%s' % (re.sub('_', ' ', pre_title))
            else:
                pretty_title = '%s:%s' % (re.sub('_', ' ', ns_name), re.sub('_', ' ', page_title))
            pretty_title = pretty_title.lstrip(':').decode('utf8')
            # Just for fun :-)
            try:
                if re.match('centi(jimboe?s?|jimbeaux?)$', form["measure"].value.lower(), re.I):
                    cj_count = page_info(db, 'User', 'Jimbo_Wales')['count']
                    cj_info = '<div id="subheadline">1 centijimbo is %.2f watchers</div>' % (float(cj_count)/100)
                    cj_header = '<th class="header">Centijimbos</th>'
                    if count < 30:
                        cj_data = '<td>&mdash;</td>'
                    else:
                        cj_data = '<td>%.1f</td>' % ((float(count)/cj_count) * 100)
                else:
                    cj_info = ''
                    cj_header = ''
                    cj_data = ''
            except:
                cj_info = ''
                cj_header = ''
                cj_data = ''
            if logged_in:
                count = count
            elif count < 30:
                count = '&mdash;'
                exclude_count += 1
            else:
                count = count
            table_row = '<tr><td><a href="http://%s/wiki/%s" title="%s" class="%s">%s</a></td><td>%s</td>%s</tr>' % (domain,
                                                                                                                     urllib.quote(pretty_title.encode('utf8')),
                                                                                                                     xml.sax.saxutils.escape(pretty_title.encode('utf8')),
                                                                                                                     css_class,
                                                                                                                     xml.sax.saxutils.escape(pretty_title.encode('utf8')),
                                                                                                                     count,
                                                                                                                     cj_data)
        output.append(table_row)

if logged_in:
    login_footer = '<a href="http://toolserver.org/~mzmcbride/cgi-bin/login.py?logout=1" title="log out">log out</a>'
else:
    login_footer = '<a href="http://toolserver.org/~mzmcbride/cgi-bin/login.py" title="log in">log in</a>'

if exclude_count > 0:
    exclude_footer = '&mdash; indicates the page has fewer than 30 watchers<br />'
else:
    exclude_footer = ''

if redirect_count > 0:
    redirect_footer = 'redirects are in <i>italics</i>'
else:
    redirect_footer = ''

print """\
Content-Type: text/html;charset=utf-8\n
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
<head>
<link rel="stylesheet" href="../style.css?2" type="text/css" />
<script type="text/javascript" src="../jquery-1.3.2.min.js"></script> 
<script type="text/javascript" src="../jquery.tablesorter.js"></script>
<script type="text/javascript">
    $(document).ready(function() 
    {
        $('input.focus:first').focus();
        $('#results').tablesorter({widgets: ['zebra']});
    } 
); 
</script>
<title>watcher</title>
</head>
<body>
<div class="header" id="main-title"><a href="/~mzmcbride/cgi-bin/watcher.py" title="watcher">watcher</a></div>
%s""" % (cj_info)

if input:
    if db and host is not None and input:
         print """\
<table id="results" class="inner-table">
<thead>
<tr>
<th class="header">Page</th>
<th class="header">Watchers</th>
%s</tr>
</thead>
<tbody>
%s
</tbody>
</table>""" % (cj_header, '\n'.join(output))
    else:
        print """\
<pre>
There was some sort of error. Sorry. :-(
</pre>"""

elif host is None:
    print """\
<pre>
You didn't specify an appropriate database name.
</pre>"""

else:
    print """\
<form action="http://toolserver.org/~mzmcbride/cgi-bin/watcher.py" method="get">
<table id="input" class="inner-table">
<tr>
<th colspan="2" class="header">Input page titles. Separate multiple titles with |.</th>
</tr>
<tr>
<th>Database</th>
<th>
<select id="database" name="db">"""
    for i in database_list():
        if i == '%s' % db:
            print """\
<option value="%s" selected="selected">%s</option>""" % (i, i)
        else:
            print """\
<option value="%s">%s</option>""" % (i, i)
    print """\
</select>
</th>
</tr>
<tr>
<td colspan="2" id="input-cell">
<input class="focus" id="input" name="titles" size="50" /><input id="go-button" type="submit" value="Go" />
</td>
</tr>
</table>
</form>"""

print """\
<div id="footer">
<div id="redirect-info">
%s%s
</div>
<div id="meta-info">
%s<!--
-->&nbsp;<b>&middot;</b>&nbsp;<!--
--><a href="http://www.gnu.org/copyleft/gpl.html" title="GNU General Public License, version 3">license</a><!--
-->&nbsp;<b>&middot;</b>&nbsp;<!--
--><a href="http://en.wikipedia.org/w/index.php?title=User_talk:MZMcBride/watcher&action=edit&section=new" title="Report a bug">bugs</a>
</div>
</div>
</body>
</html>""" % (exclude_footer, redirect_footer, login_footer)
