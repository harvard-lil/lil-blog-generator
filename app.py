from ast import literal_eval
from datetime import datetime, timedelta
from functools import wraps
import io
from os import environ
import re
import requests
from unidecode import unidecode
from urllib.parse import urlparse, urljoin
from werkzeug.utils import secure_filename
from yaml import safe_load

from flask import Flask, request, redirect, session, abort, url_for, render_template, send_file
import error_handling

import logging

app = Flask(__name__)
app.config['GITHUB_CLIENT_ID'] = environ.get('GITHUB_CLIENT_ID')
app.config['GITHUB_CLIENT_SECRET'] = environ.get('GITHUB_CLIENT_SECRET')
app.config['GITHUB_ORG_NAME'] = environ.get('GITHUB_ORG_NAME')
app.config['SECRET_KEY'] = environ.get('FLASK_SECRET_KEY')
app.config['SESSION_COOKIE_SECURE'] = literal_eval(environ.get('SESSION_COOKIE_SECURE', 'True'))
app.config['LOGIN_EXPIRY_MINUTES'] = environ.get('LOGIN_EXPIRY', 30)
app.config['LOG_LEVEL'] = environ.get('LOG_LEVEL', 'WARNING')

# register error handlers
error_handling.init_app(app)

AUTHORIZE_URL = 'https://github.com/login/oauth/authorize'
ACCESS_TOKEN_URL = 'https://github.com/login/oauth/access_token'
ORGS_URL = 'https://api.github.com/user/orgs'
REVOKE_TOKEN_URL = 'https://api.github.com/applications/{}/token'.format(app.config['GITHUB_CLIENT_ID'])

###
### UTILS ###
###

@app.before_first_request
def setup_logging():
    if not app.debug:
        # In production mode, add log handler to sys.stderr.
        app.logger.addHandler(logging.StreamHandler())
        app.logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))


def login_required(func):
    @wraps(func)
    def handle_login(*args, **kwargs):
        logged_in = session.get('logged_in')
        valid_until = session.get('valid_until')
        if valid_until:
            valid = datetime.strptime(valid_until, '%Y-%m-%d %H:%M:%S') > datetime.utcnow()
        else:
            valid = False
        if logged_in and logged_in == "yes" and valid:
            app.logger.debug("User session valid")
            return func(*args, **kwargs)
        else:
            app.logger.debug("Redirecting to GitHub")
            session['next'] = request.url
            return redirect('{}?scope=read:org&client_id={}'.format(AUTHORIZE_URL, app.config['GITHUB_CLIENT_ID']))
    return handle_login


def is_safe_url(target):
    '''
        Ensure a url is safe to redirect to, from WTForms
        http://flask.pocoo.org/snippets/63/from WTForms
    '''
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc


_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')

def slugify(text, delim=u'-'):
    """Generates an ASCII-only slug."""
    result = []
    for word in _punct_re.split(text.lower()):
        result.extend(unidecode(word).split())
    return str(delim.join(result))


###
### ROUTES
###

@login_required
@app.route('/', methods=['GET', 'POST'])
def landing():
    if request.method == 'POST':
        r = requests.get('https://raw.githubusercontent.com/harvard-lil/website-static/develop/app/_data/people.yaml')
        authors = sorted(safe_load(r.text).keys())
        return render_template('generator/download.html', context={'heading': 'Download Post', 'authors': authors})
    return render_template('generator/preview.html', context={'heading': 'Preview Blog Post'})


@login_required
@app.route('/download', methods=['POST'])
def download():
    md = io.BytesIO(bytes(render_template('generator/post.md'), 'utf-8'))
    filename = secure_filename(u'{}-{}.md'.format(request.form['date'], slugify(request.form['title'])))
    if not filename:
        filename = u'yyyy-mm-dd-your-title-here.md'
    return send_file(md,
                     attachment_filename=filename,
                     as_attachment=True)


@login_required
@app.route('/editor')
def editor():
    return render_template('generator/editor.html')


@app.route('/login')
def login():
    return render_template('login.html', context={'heading': 'Log In', 'client_id': app.config['GITHUB_CLIENT_ID']})


@app.route("/logout")
def logout():
    session.clear()
    return render_template('generic.html', context={'heading': "Logged Out",
                                                    'message': "You have successfully been logged out."})

@app.route('/auth/github/callback')
def authorized():
    app.logger.debug("Requesting Access Token")
    r = requests.post(ACCESS_TOKEN_URL, headers={'accept': 'application/json'},
                                        data={'client_id': app.config['GITHUB_CLIENT_ID'],
                                              'client_secret': app.config['GITHUB_CLIENT_SECRET'],
                                              'code': request.args.get('code')})
    data = r.json()
    if r.status_code == 200:
        access_token = data.get('access_token')
        scope = data.get('scope')
        app.logger.debug("Received Access Token")
    else:
        app.logger.error("Failed request for access token. Gitub says {}".format(data['message']))
        abort(500)

    if scope == 'read:org':
        app.logger.debug("Requesting User Organization Info")
        r = requests.get(ORGS_URL, headers={'accept': 'application/json',
                                            'authorization': 'token {}'.format(access_token)})

        app.logger.debug("Revoking Github Access Token")
        d = requests.delete(REVOKE_TOKEN_URL,
                            auth=(app.config['GITHUB_CLIENT_ID'], app.config['GITHUB_CLIENT_SECRET']),
                            data={'access_token': access_token})
        app.logger.debug("(Request returned {})".format(d.status_code))

        data = r.json()
        if r.status_code == 200:
            if data and any(org['login'] == app.config['GITHUB_ORG_NAME'] for org in data):
                next = session.get('next')
                session.clear()
                valid_until = (datetime.utcnow() + timedelta(seconds=60*30)).strftime('%Y-%m-%d %H:%M:%S')
                session['valid_until'] = valid_until
                session['logged_in'] = "yes"
                if next and is_safe_url(next):
                    return redirect(next)
                return redirect(url_for('catch_all'))
            else:
                app.logger.warning("Log in attempt from Github user who is not a member of LIL.")
                abort(401)
        else:
            app.logger.error("Failed request for user orgs. Gitub says {}".format(data['message']))
            abort(500)
    else:
        app.logger.warning("Insufficient scope authorized in Github; verify API hasn't changed.")
        abort(401)
