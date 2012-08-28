#! /usr/bin/env python
# Public domain; MZMcBride; 2011
# Version 0.2

import cgi
import operator
import re
import MySQLdb

def database_list():
    databases = []
    conn = MySQLdb.connect(host='sql-s3',
                           db='toolserver',
                           read_default_file='/home/mzmcbride/.my.cnf')
    cursor = conn.cursor()
    cursor.execute('''
    /* yanker.py database_list */
    SELECT
      dbname
    FROM wiki
    WHERE is_closed = 0;
    ''')
    for row in cursor.fetchall():
        database_name = row[0]
        databases.append(database_name)
    cursor.close()
    conn.close()
    return databases

def choose_host_and_domain(db):
    db_props = {}
    conn = MySQLdb.connect(host='sql-s3',
                           db='toolserver',
                           read_default_file='/home/mzmcbride/.my.cnf')
    cursor = conn.cursor()
    cursor.execute('''
    /* yanker.py choose_host_and_domain */
    SELECT
      server,
      domain
    FROM wiki
    WHERE dbname = %s;
    ''' , db)
    for row in cursor.fetchall():
        db_props['host'] = 'sql-s%s' % str(row[0])
        db_props['domain'] = '%s' % row[1]
    cursor.close()
    conn.close()
    return db_props

def get_namespace_names(db):
    namespaces = {}
    conn = MySQLdb.connect(host='sql-s3',
                           db='toolserver',
                           read_default_file='/home/mzmcbride/.my.cnf')
    cursor = conn.cursor()
    cursor.execute('''
    /* yanker.py get_namespace_names */
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

def underscore(text):
    text = re.sub(r'(%20| )', '_', text)
    return text

def prettify(text):
    text = re.sub('_', ' ', text)
    return text

form = cgi.FieldStorage()
# Pick a db; make enwiki_p the default
if form.getvalue('db') is not None:
    db = form.getvalue('db')
else:
    db = 'enwiki_p'

# Use the limit if it's set in the initial URL
if form.getvalue('limit') is not None:
    try:
        if int(form.getvalue('limit')) > 5000:
            limit_input = '5000'
        else:
            limit_input = form.getvalue('limit')
    except:
        limit_input = '5000'
else:
    limit_input = '5000'

# All right, now let's pick a host and domain
try:
    db_props = choose_host_and_domain(db)
    host = db_props['host']
    domain = db_props['domain']
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
<title>yanker</title>
<link rel="stylesheet" href="../style-yanker.css?3" type="text/css" />
</head>
<body>
<div class="header" id="main-title"><a href="/~mzmcbride/yanker/" title="yanker">yanker</a></div>"""

if form.getvalue('list') is None:
    print """\
<form action="/~mzmcbride/yanker/" method="get">
<table id="input" class="inner-table">
<tr>
<th colspan="3" class="header">Make your choices.</th>
</tr>
<tr>
<td class="bold">Database</td>
<td>
<select id="database" name="db" style="width:100%;">"""
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
<td>
<input id="go-button" type="submit" value="Go" style="margin:0;" />
</td>
</tr>
<tr>
<td class="bold">
List
</td>
<td colspan="2">
<select id="list" name="list" style="width:100%%;">
<option value="">Select one</option>
<option value="pages">Pages in a category</option>
<option value="pages">Page titles matching a particular pattern</option>
<option value="loldongs">loldongs</option>
</select>
</td>
</tr>
<tr>
<td class="bold">
%s
</td>
<td colspan="2">
<input class="text-input" id="category" type="text" name="category" />
</td>
</tr>
<tr>
<td class="bold">
Page
</td>
<td colspan="2">
<input class="text-input" id="page" type="text" name="page" value="" />
</td>
</tr>
<tr>
<td class="bold">
Pattern
</td>
<td colspan="2">
<input class="text-input" id="pattern" type="text" name="pattern" value="" />
</td>
</tr>
<tr>
<td class="bold">
Namespaces
</td>
<td colspan="2">
<table style="border:none; font-size:inherit;">""" % (namespace_names[14].encode('utf-8'))
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
</tr>
<tr>
<td class="bold">
Limit
</td>
<td colspan="2">
<input class="text-input" id="limit" type="text" name="limit" value="%s" />
</td>
</tr>
<tr>
<td class="bold">
Sort
</td>
<td colspan="2">
<select id="sort" name="sort" style="width:100%%;">
<option value="">None</option>
<option value="asc">Ascending (A&rarr;Z)</option>
<option value="desc">Descending (Z&rarr;A)</option>
</select>
</td>
</tr>
<tr>
<td class="bold">
Line wrapper
</td>
<td colspan="2">
<input class="text-input" id="wrapper" type="text" name="wrapper" value="$1" />
</td>
</tr>
</table>
</form>""" % limit_input

elif form.getvalue('list') in ('pages', 'files', 'categories', 'links', 'templates', 'externallinks'):
    target_column = 'page_title'
    # Sort order
    if form.getvalue('sort') == 'asc':
        sort_query_input = 'ORDER BY %s ASC' % target_column
    elif form.getvalue('sort') == 'desc':
        sort_query_input = 'ORDER BY %s DESC' % target_column
    else:
        sort_query_input = ''

    # Limits
    try:
        if int(form.getvalue('limit')) > 5000:
            limit_query_input = 'LIMIT 5000'
        elif int(form.getvalue('limit')) > 0:
            limit_query_input = 'LIMIT %s' % int(form.getvalue('limit'))
        else:
            limit_query_input = 'LIMIT 5000'
    except:
        limit_query_input = 'LIMIT 5000'

    # Line wrapper
    try:
        wrapper_input = form.getvalue('wrapper').decode('utf-8')
    except:
        wrapper_input = '$1'

    # Underscores or spaces in results?
    if form.getvalue('prettify') == '1':
        prettify_status = True
    else:
        prettify_status = False

    # Namespaces!
    try:
        if form['namespace'] is not None:
            namespace_input = 'AND page_namespace IN (%s)' % (','.join(str(int(x)) for x in form.getlist('namespace')))
        else:
            namespace_input = ''
    except:
        namespace_input = ''

    if form.getvalue('list') == 'pages' and form.getvalue('category'):
        category_input = underscore(form['category'].value)
        target_column = 'page_title'
        results = []
        conn = MySQLdb.connect(host=host,
                               db=db,
                               read_default_file='/home/mzmcbride/.my.cnf')
        cursor = conn.cursor()
        query = '''
        /* yanker.py &list=pages&category= */
        SELECT
          page_namespace,
          page_title
        FROM page
        JOIN categorylinks
        ON cl_from = page_id
        WHERE cl_to = '%s'
        %s
        %s
        %s;
        ''' % (MySQLdb.escape_string(category_input),
               MySQLdb.escape_string(namespace_input),
               sort_query_input,
               limit_query_input)
        cursor.execute(query)
        for row in cursor.fetchall():
            page_namespace = namespace_names[row[0]].encode('utf-8')
            page_title = unicode(row[1], 'utf-8')
            if row[0] in (6,14):
                full_page_title = ':%s:%s' % (page_namespace, page_title)
            elif row[0] == 0:
                full_page_title = '%s' % (page_title)
            else:
                full_page_title = '%s:%s' % (page_namespace, page_title)
            if prettify_status:
                full_page_title = prettify(full_page_title)
            re_row = re.sub('\$1', full_page_title, wrapper_input)
            results.append(re_row)
        cursor.close()
        conn.close()

    elif form.getvalue('list') == 'pages' and form.getvalue('pattern'):
        pattern_input = underscore(form['pattern'].value)
        target_column = 'page_title'
        results = []
        conn = MySQLdb.connect(host=host,
                               db=db,
                               read_default_file='/home/mzmcbride/.my.cnf')
        cursor = conn.cursor()
        query = '''
        /* yanker.py &list=pages&pattern= */
        SELECT
          page_namespace,
          page_title
        FROM page
        WHERE page_title RLIKE '%s'
        %s
        %s
        %s;
        ''' % (MySQLdb.escape_string(pattern_input),
               MySQLdb.escape_string(namespace_input),
               sort_query_input,
               limit_query_input)
        cursor.execute(query)
        for row in cursor.fetchall():
            page_namespace = namespace_names[row[0]].encode('utf-8')
            page_title = unicode(row[1], 'utf-8')
            if row[0] in (6,14):
                full_page_title = ':%s:%s' % (page_namespace, page_title)
            elif row[0] == 0:
                full_page_title = '%s' % (page_title)
            else:
                full_page_title = '%s:%s' % (page_namespace, page_title)
            if prettify_status:
                full_page_title = prettify(full_page_title)
            re_row = re.sub('\$1', full_page_title, wrapper_input)
            results.append(re_row)
        cursor.close()
        conn.close()

    final_results = '\n'.join(results).encode('utf-8')

    print """\
<textarea id="results" style="font-size:1em; width:100%%; overflow:auto; height:500px;">
%s
</textarea>""" % (cgi.escape(final_results, quote=True))

elif form.getvalue('list') == 'loldongs':
    print """\
<div style="text-align:center; padding:5px; font-size:4em;">loldongs</div>"""

elif host is None:
    print """\
<pre>
You didn't specify an appropriate database name.
</pre>"""

print """\
<div id="footer">
<div id="meta-info">public domain&nbsp;<b>&middot;</b>&nbsp;\
<a href="//en.wikipedia.org/w/index.php?title=User_talk:MZMcBride/yanker&amp;action=edit&amp;section=new" title="Report a bug">bugs</a>
</div>
</div>
</body>
</html>"""
