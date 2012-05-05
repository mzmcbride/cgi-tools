#! /usr/bin/env python
# Public domain; bjweeks, MZMcBride; 2011

# TODO:
# Add links to wikichecker / contribs links
# Specify which users edited the page in question (need a good layout for this)
# Matches 2 / 3 (1, 2) with "1, 2" being links (and title="" text!) to the top with cite-like highlighting (and maybe colored text?)
# Encode functions / display (format) functions?
# Format dates / numbers in user_stats?
# Combine first edit functions?
# Need to gracefully handle non-existent users
# alert('') for ?dbname (at least for now)
# Fix presentation of similarity data (right / left align text??)

import cgi
import datetime
import operator
import os
import MySQLdb
import re
import urllib

import settings

import cgitb; cgitb.enable()

def error(message):
    print '<html>'
    print '<body>'
    print message
    print '</body>'
    print '</html>'
    quit()

def escape(s):
    s = s.replace('&', '&amp;')
    s = s.replace('>', '&gt;')
    s = s.replace('<', '&lt;')
    s = s.replace('"', '&quot;')
    s = s.replace('\'', '&apos;')
    return s

def database_list():
    conn = MySQLdb.connect(host='sql-s3',
                           db='toolserver',
                           read_default_file='/home/mzmcbride/.my.cnf')
    cursor = conn.cursor()
    cursor.execute('''
    /* stalker.py database_list */
    SELECT
      dbname
    FROM wiki
    WHERE is_closed = 0;
    ''')
    databases = cursor.fetchall()
    cursor.close()
    conn.close()
    return [database[0] for database in databases]

def choose_host_and_domain(db):
    conn = MySQLdb.connect(host='sql-s3',
                           db='toolserver',
                           read_default_file='/home/mzmcbride/.my.cnf')
    cursor = conn.cursor()
    cursor.execute('''
    /* stalker.py choose_host_and_domain */
    SELECT
      server,
      domain
    FROM wiki
    WHERE dbname = %s;
    ''' , db)
    for row in cursor.fetchall():
        host = 'sql-s%s' % str(row[0])
        domain = '%s' % row[1]
    cursor.close()
    conn.close()
    return {'host': host, 'domain': domain}

def get_namespace_names(db):
    namespaces = {}
    conn = MySQLdb.connect(host='sql-s3',
                           db='toolserver',
                           read_default_file='/home/mzmcbride/.my.cnf')
    cursor = conn.cursor()
    cursor.execute('''
    /* stalker.py get_namespace_names */
    SELECT
      ns_id,
      ns_name
    FROM namespace
    WHERE dbname = %s
    AND ns_id >= 0;
    ''' , db)
    for row in cursor.fetchall():
        namespaces[row[0]] = unicode(row[1], 'utf-8')
    cursor.close()
    conn.close()
    return namespaces

def get_user_info(cursor, user):
    cursor.execute('''
    /* stalker.py get_user_info */
    SELECT
      user_name,
      user_registration,
      user_editcount
    FROM user
    WHERE user_name = %s;
    ''' , user)
    for row in cursor.fetchall():
        user_name = row[0]
        if not row[1]:
            user_registration = '<i>none</i>'
        else:
            user_registration = row[1]
        if not row[2]:
            user_editcount = '<i>none</i>'
        else:
            user_editcount = row[2]
    return user_name, user_registration, user_editcount

def get_first_live_edit(cursor, user):
    cursor.execute('''
    /* stalker.py get_first_live_edit */
    SELECT
      MIN(rev_timestamp)
    FROM revision
    WHERE rev_user_text = %s;
    ''' , user)
    for row in cursor.fetchall():
        if not row[0]:
            rev_timestamp = '<i>none</i>'
        else:
            rev_timestamp = row[0]
    return rev_timestamp

def get_first_dead_edit(cursor, user):
    cursor.execute('''
    /* stalker.py get_first_dead_edit */
    SELECT
      MIN(ar_timestamp)
    FROM archive
    WHERE ar_user_text = %s;
    ''' , user)
    for row in cursor.fetchall():
        if not row[0]:
            rev_timestamp = '<i>none</i>'
        else:
            rev_timestamp = row[0]
    return rev_timestamp

def pagesEdited(cursor, namespaces_input, user):
    cursor.execute('''
    /* stalker.py pagesEdited */
    SELECT DISTINCT
      ns_name,
      page_title
    FROM page
    JOIN toolserver.namespace
    ON dbname = '%s'
    AND page_namespace = ns_id
    JOIN revision
    ON rev_page = page_id
    WHERE rev_user_text = '%s'
    %s;
    ''' % (MySQLdb.escape_string(db),
           MySQLdb.escape_string(user),
           namespaces_input))
    return [('%s:%s' % (row[0], row[1])).lstrip(':') for row in cursor.fetchall()]

def pagesEditedAll(cursor, user):
    cursor.execute('''
    /* stalker.py pagesEditedAll */
    SELECT DISTINCT
      ns_name,
      page_title
    FROM page
    JOIN toolserver.namespace
    ON dbname = %s
    AND page_namespace = ns_id
    JOIN revision
    ON rev_page = page_id
    WHERE rev_user_text = %s;
    ''' , (db, user))
    return [('%s:%s' % (row[0], row[1])).lstrip(':') for row in cursor.fetchall()]

form = cgi.FieldStorage()
# Pick a db; make enwiki_p the default
if form.getvalue('db') is not None:
    db = form.getvalue('db')
else:
    db = 'enwiki_p'

# All right, now let's pick a host and domain
try:
    connection_props = choose_host_and_domain(db)
    host = connection_props['host']
    domain = connection_props['domain']
except:
    host = None
    domain = None

namespace_names = get_namespace_names(db)

print """\
Content-Type: text/html;charset=utf-8\n
<!doctype html>
<html>
<head>
<meta http-equiv="content-type" content="text/html; charset=utf-8"> 
<link rel="stylesheet" href="../cgi-tools-common.css" type="text/css" />
<script type="text/javascript" src="/~mzmcbride/jquery-1.3.2.min.js"></script>
<script type="text/javascript" src="/~mzmcbride/jquery.tablesorter.js"></script>
<script type="text/javascript">
$(document).ready(function()
{
    $('input.focus').focus();
    $('.results').tablesorter(
        {widgets: ['zebra']}
    );
}
);
</script>
<title>stalker</title>
</head>
<body>
<h1 id="header"><a href="/~mzmcbride/stalker/">stalker</a></h1>"""

if not form:
    print """\
<form id="input-form" method="get">
<table class="inner-table">
<tr>
<th colspan="2">Input users below.</th>
</tr>
<tr>
<td class="bold">Database</td>
<td>
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
</td>
</tr>\
"""
    for i in range(1,11):
        if i == 1:
            focus = 'focus '
        else:
            focus = ''
        print """\
<tr>
<td class="bold">User %i</td>
<td><input class="%susername" type="text" id="user%i" name="user%i" /></td>
</tr>""" % (i, focus, i, i)
    print """\
<tr>
<td class="bold">Namespaces</td>
<td>
<table style="border:none; font-size:inherit;">"""
    count = 0
    for k,v in sorted(namespace_names.iteritems(), key=operator.itemgetter(0)):
        if count % 2 == 0:
            print '<tr style="border:none;">'
        if v == '':
            v = '(Main)'
        print """\
<td style="border:none;"><input id="ns%s" type="checkbox" name="namespace" value="%s" /></td>
<td style="border:none;"><label for="ns%s">%s</label></td>""" % (k, k, k, v.encode('utf-8'))
        if count % 2 != 0:
            print '</tr>'
        count += 1
    print """\
</table>
</td>
<tr>
<td colspan="2" class="submit"><input type="submit" value="Submit" id="submit" /></td>
</tr>
</table>
</form>
"""

else:
    user_numbers = {}
    users_unsorted = []
    users = []
    namespaces = []
    for field in form:
        if re.match('user\d\d?', field):
            user = re.sub('_', ' ', form[field].value) # Convert underscores to spaces.
            user = user[0].upper() + user[1:]
            user_number = field.lstrip('user')
            user_numbers[user] = user_number
            users_unsorted.append([int(user_number), user])
        for namespace in form.getlist('namespace'):
            if re.match('namespace', field):
                namespaces.append(namespace)
    users_sorted = sorted(users_unsorted, key=operator.itemgetter(0))
    for user in users_sorted:
        user_name = user[1]
        users.append(user_name)
    f = open('/home/mzmcbride/scripts/wikistalk/wikistalk.log', 'a')
    f.write('%s - %s - %s\n' % (datetime.datetime.utcnow(), os.environ['HTTP_X_FORWARDED_FOR'], ','.join(users)))
    f.close()
    user_stats = []
    try:
        conn = MySQLdb.connect(host=host,
                               db=db,
                               read_default_file='/home/mzmcbride/.my.cnf')
        cursor = conn.cursor()
    except MySQLdb.OperationalError, message:
        error(message)
    for user in users:
        user_no = user_numbers[user]
        try:
            user_name, user_registration, user_editcount = get_user_info(cursor, user)
            linked_user_name = '<a href="//%s/wiki/User:%s">%s</a>' % (domain,
                                                                       urllib.quote(user_name),
                                                                       escape(user_name))
            first_live_edit = get_first_live_edit(cursor, user)
            first_dead_edit = get_first_dead_edit(cursor, user)
            table_row = '''\
<tr class="user%s">
<td>%s</td>
<td>%s</td>
<td>%s</td>
<td>%s</td>
<td>%s</td>
<td>%s</td>
</tr>''' % (user_no,
            user_no,
            linked_user_name,
            user_registration,
            user_editcount,
            first_live_edit,
            first_dead_edit)
        except UnboundLocalError:
            table_row = '''\
<tr>
<td>%s</td>
<td>%s</td>
<td colspan="4">
<i>Sorry, this user is not registered.</i>
</td>
</tr>''' % (user_no, escape(user))
        user_stats.append(table_row)
    print """\
<div class="not-header">
<table class="outer-table">
<tr>
<td>
<div class="user-info">
<table class="inner-table results">
<thead>
<tr>
<th>No.</th>
<th>Username</th>
<th>Registration date</th>
<th>Edit count</th>
<th>First live edit</th>
<th>First deleted edit</th>
</tr>
</thead>
<tbody>
%s
</tbody>
</table>
</div>
</td>
</tr>
<tr>""" % '\n'.join(user_stats)

    contribs = {}
    print """\
<td>
<div class="main-content">
<table class="inner-table results">
<thead>
<tr>
<th>No.</th>
<th>Page</th>
<th>Similarity</th>
</tr>
</thead>
<tbody>\
"""

    try:
        conn = MySQLdb.connect(host=host,
                               db=db,
                               read_default_file='/home/mzmcbride/.my.cnf')
        cursor = conn.cursor()
    except MySQLdb.OperationalError, message:
        error(message)
    for user in users:
        if not namespaces:
            try:
                contribs[user] = pagesEditedAll(cursor, user)
            except MySQLdb.OperationalError, message:
                error(message)
        else:
            namespaces_clean = []
            for namespace in namespaces:
                if re.match(r'\d+', namespace):
                    namespaces_clean.append(namespace)
            if form.getvalue('all') == 'on':
                namespaces_input = ''
            elif len(namespaces_clean) > 0:
                namespaces_input = 'AND page_namespace IN (%s)' % (','.join(namespaces_clean))
            else:
                namespaces_input = ''
            try:
                contribs[user] = pagesEdited(cursor, namespaces_input, user)
            except MySQLdb.OperationalError, message:
                error(message)
    cursor.close()
    conn.close()
    edited = {}
    for user, articles in contribs.items():
        for page in articles:
            if edited.has_key(page):
                edited[page].append(user)
            else:
                edited[page] = [user]
    count = 1
    sorted_dict = sorted(edited.iteritems(), key=lambda (k,v): (v,k)) #might want to fix this
    if 'SlimVirgin' in users and 'Jayjg' in users and 'Jpgordon' in users:
        print 'Cabal score: <b>OVER 9000!</b><br />'
    if sorted_dict:
        for page, users_matched in sorted_dict:
            users_matched_unsorted = []
            users_matched_final = []
            if len(users_matched) > 1:
                for user in users_matched:
                    users_matched_unsorted.append([int(user_numbers[user]), user])
                users_matched_sorted = sorted(users_matched_unsorted, key=operator.itemgetter(0))
                for user in users_matched_sorted:
                    user_name = user[1]
                    users_matched_final.append(user_name)
                print """\
<tr>
<td>%(count)s</td>
<td><a href="//%(domain)s/wiki/%(epage)s">%(fpage)s</a></td>
<td>%(editedby)d/%(users)d [%(specifics)s]</td>
</tr> """ % { 'domain': domain,
              'epage': re.sub(r'(%20| )', '_', urllib.quote(page)),
              'fpage': re.sub(r'_', ' ', page),
              'count': count,
              'editedby': len(users_matched),
              'users': len(users),
              'specifics': ', '.join(['<span title="%s">%s</span>' % (escape(user),
                                                                      user_numbers[user]) for user in users_matched_final]) }
                count += 1
        if count == 1:
            print """\
<tr>
<td colspan="3"><i>Sorry, no results were found.</i></td>
</tr> """

    print """\
</tbody>
</table>
</div>
</td>
</tr>
</table>
</div>"""

print """\
<div id="footer">
<div id="meta-info">
public domain&nbsp;<b>&middot;</b>&nbsp;\
<a href="//en.wikipedia.org/w/index.php?title=User_talk:MZMcBride&amp;action=edit&amp;section=new" title="Report a bug">bugs</a>
</div>
</div>
<script type="text/javascript">
    $(document).ready(function() {
        $("#input-form").submit(function() {
            var i = 3;
            for (i=3;i<11;i++) {
                if($("#user"+i).val()=="") {
                    $("#user"+i).remove();
                }
            }
        });
     });
</script>
</body>
</html>\
"""
