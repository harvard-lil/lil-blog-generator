import re
import StringIO
import requests
from yaml import safe_load
from unidecode import unidecode
from werkzeug.utils import secure_filename


from flask import render_template, send_file

_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')

def slugify(text, delim=u'-'):
    """Generates an ASCII-only slug."""
    result = []
    for word in _punct_re.split(text.lower()):
        result.extend(unidecode(word).split())
    return unicode(delim.join(result))

def proxy_request(request, path):
    '''
        This function will be called on every web request caught by our
        default route handler (that is, on every request except for:
        a) requests for resources in /static and
        b) requests for urls with route especially defined in app.py.

        request = the request object as received by the parent Flask
        view function (http://flask.pocoo.org/docs/0.12/api/#incoming-request-data)

        path = the route requested by the user (e.g. '/path/to/route/i/want')

        proxy_response should return the response to be forwarded to the user.
        Treat it like a normal Flask view function:

        It should return a value that Flask can convert into a response using
        http://flask.pocoo.org/docs/0.12/api/#flask.Flask.make_response,
        just like any function you woulld normally decorate with @app.route('/route'),
        where Flask calls make_response implicitly.

        e.g.
        def proxy_request(request, path):
            return 'Hello World'

        You can use flask.make_response to help construct complex responses:
        http://flask.pocoo.org/docs/0.12/api/#flask.Flask.make_response
    '''
    if path == 'download' and request.method == 'POST':
        md = StringIO.StringIO(render_template('generator/post.md').encode('utf-8'))
        filename = secure_filename(u'{}-{}.md'.format(request.form['date'], slugify(request.form['title'])))
        if not filename:
            filename = u'yyyy-mm-dd-your-title-here.md'
        return send_file(md,
                         attachment_filename=filename,
                         as_attachment=True)
    elif path == 'editor':
        return render_template('generator/editor.html')
    elif request.method == 'POST':
        r = requests.get('https://raw.githubusercontent.com/harvard-lil/website-static/develop/app/_data/people.yaml')
        authors = sorted(safe_load(r.text).keys())
        return render_template('generator/download.html', context={'heading': 'Download Post', 'authors': authors})
    return render_template('generator/preview.html', context={'heading': 'Preview Blog Post'})
