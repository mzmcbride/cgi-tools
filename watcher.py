#! /usr/bin/env python
# -*- coding: utf-8 -*-
# version 0.2
# test cases:
# http://toolserver.org/~mzmcbride/cgi-bin/watcher-test.py?db=enwiki_p&titles=user%20talk:Philippe|main%20Page|User_talk:MZMcBride
# http://toolserver.org/~mzmcbride/cgi-bin/watcher-test.py?db=enwiki_p&titles=Wikipedia_caultk:Sandbox|Wikipedia_caulk:Sandbox
# http://toolserver.org/~mzmcbride/cgi-bin/watcher-test.py?db=enwiki_p&titles=Fooooooo|Barbbbbbb|
# http://toolserver.org/~mzmcbride/cgi-bin/watcher-test.py?db=enwiki_p&titles=Main+Page%7CFooooooooo|||
# http://toolserver.org/~mzmcbride/cgi-bin/watcher-test.py?db=frwiki_p&titles=Wikip%E9dia%3AAnnonces
import cgi, cgitb; cgitb.enable()

import os, urllib
import re
import xml.sax.saxutils
import glob
import MySQLdb
import settings

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
    conn = MySQLdb.connect(host='sql-s1', db='toolserver', read_default_file='/home/mzmcbride/.my.cnf')
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

def count_watchers(db, namespace, page_title):
    conn = MySQLdb.connect(host=host, db=db, read_default_file='/home/mzmcbride/.my.cnf')
    cursor = conn.cursor()
    cursor.execute('''
    /* watcher.py count_watchers */
    SELECT
      COUNT(*)
    FROM watchlist
    JOIN toolserver.namespace
    ON dbname = %s
    AND wl_namespace = ns_id
    WHERE ns_name = %s
    AND wl_title = %s;
    ''' , (db, ns_name, page_title))
    for row in cursor.fetchall():
        return row[0]
    cursor.close()
    conn.close()

form = cgi.FieldStorage()
# Pick a db; make enwiki_p the default
try:
    db = form['db'].value
except:
    db = 'enwiki_p'

# All right, now let's pick a host and domain
host_and_domain = choose_host_and_domain(db)
host = host_and_domain[0]
domain = host_and_domain[1]

if 'titles' in form:
    input = form["titles"].value
else:
    input = ''

output = []
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
        try:
            page_title = re.sub(r'(%20| )', '_', pre_title[0].upper() + pre_title[1:])
        except:
            page_title = ''
        combined_title = re.sub(r'(%20| )', '_', '%s:%s' % (ns_name, page_title))
        count = count_watchers(db, ns_name, page_title)
        if count == 0 and re.search(':', title):
            ns_name = ''
            if count_watchers(db, ns_name, combined_title) > 0:
                count = count_watchers(db, ns_name, combined_title)
                pretty_title = '%s:%s' % (re.sub('_', ' ', ns_name), re.sub('_', ' ', combined_title))
            else:
                ns_name = re.sub('_', ' ', title.split(':')[0][0].upper() + title.split(':')[0][1:])
                count = count_watchers(db, ns_name, page_title)
                pretty_title = '%s:%s' % (re.sub('_', ' ', ns_name), re.sub('_', ' ', page_title))
        elif not re.search(':', title):
            ns_name = ''
            pre_title = re.sub(r'(%20| )', '_', pre_title[0].upper() + pre_title[1:])
            count = count_watchers(db, ns_name, pre_title) # Bad hack like what.
            pretty_title = '%s' % (re.sub('_', ' ', pre_title))
        else:
            pretty_title = '%s:%s' % (re.sub('_', ' ', ns_name), re.sub('_', ' ', page_title))
        pretty_title = xml.sax.saxutils.escape(pretty_title.lstrip(':'))
        table_row = '<tr><td><a href="http://%s/wiki/%s" title="%s">%s</a></td><td>%s</td></tr>' % (domain,
                                                                                                    urllib.quote(pretty_title),
                                                                                                    pretty_title,
                                                                                                    pretty_title,
                                                                                                    count)
    output.append(table_row)

print """\
Content-Type: text/html\n
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
<head>
<link rel="stylesheet" href="../style.css" type="text/css" />
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
<div class="header" id="main-title"><a href="/~mzmcbride/cgi-bin/watcher.py" title="watcher">watcher</a></div>"""

if form:
    try:
        print """\
<table id="results" class="inner-table">
<thead>
<tr>
<th class="header">Page</th>
<th class="header">Watchers</th>
</tr>
</thead>
<tbody>
%s
</tbody>
</table>""" % ('\n'.join(output))

    except:
        print """\
<pre>
There was some sort of error. Sorry. :-(
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
        if i == 'enwiki_p':
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
<div class="footer">
<a href="http://www.gnu.org/copyleft/gpl.html" title="GNU General Public License, version 3">license</a><!--
-->&nbsp;<b>&middot;</b>&nbsp;<!--
--><a href="http://en.wikipedia.org/w/index.php?title=User_talk:MZMcBride&action=edit&section=new" title="Report a bug">bugs</a>
</div>
</body>
</html>
"""
