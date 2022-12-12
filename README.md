
# lil-blog-generator

This app makes it easier to write [blog posts for the LIL website](https://github.com/harvard-lil/website-static#writing-blog-posts-docker-not-required).

Write your post using the WYSIWYG editor, then click the download button. You'll get a markdown file that you can upload straight to Github, following the on-screen instructions.


## Running locally

1. [Install Poetry](https://python-poetry.org/docs/#installation) and install requirements:

```
poetry install
```

2. Configure local settings:

```
echo "FLASK_SECRET_KEY=adjkahflashfjdlsahfjahlsdfa" >> .flaskenv
echo "FLASK_DEBUG=1" >> .flaskenv
```

### (Recommended)

To bypass login locally:
```
echo "BYPASS_LOGIN=True" >> .flaskenv
```

3. Run the Flask development server

```
poetry run flask run
```

For deployment, if you make changes to `poetry.lock`, e.g. with `poetry add <package>`, export the conventional requirements file:

```
poetry export -o requirements.txt
```

## Authentication via Github

In production, this app authenticates via Github. Configuration can be found in the "Developer Settings > OAuth Apps" section of the LIL Github organization; the application looks for corresponding [`GITHUB_*` env vars](https://github.com/harvard-lil/lil-blog-generator/blob/develop/app.py#L19-L21).

You can partially test the integration locally: does the redirect occur? Does the auth flow work as expected on the Github side?

But, after successfully authenticating, Github cannot, of course, hand things back to localhost.

So unless specifically working on authentication, you will likely want to [disable login locally](#recommended).
