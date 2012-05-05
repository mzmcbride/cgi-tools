#! /usr/bin/env python
# -*- coding: utf-8 -*-
# version 0.5
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
import cgi, cgitb; cgitb.enable()

import os, urllib
import re
import xml.sax.saxutils
import glob
import MySQLdb

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

cj_info = '' # In case it doesn't get set later.
i = 0
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
        title_info = page_info(db, ns_name, page_title)
        page_status = title_info['page_status']
        if page_status is None:
             css_class = 'red'
        elif page_status == 1:
             i += 1
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
        if count < 30:
            count = '&mdash;'
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

if i > 0:
    redirect_footer = '<div id="redirect-info">redirects are in <i>italics</i></div>'
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

if form:
    try:
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
<div id="footer">
%s<div id="meta-info">
<a href="http://www.gnu.org/copyleft/gpl.html" title="GNU General Public License, version 3">license</a><!--
-->&nbsp;<b>&middot;</b>&nbsp;<!--
--><a href="http://en.wikipedia.org/w/index.php?title=User_talk:MZMcBride/watcher&action=edit&section=new" title="Report a bug">bugs</a><!--
-->&nbsp;<b>&middot;</b>&nbsp;<!--
-->&mdash; indicates the page has fewer than 30 watchers
</div>
</div>
</body>
</html>""" % (redirect_footer)
