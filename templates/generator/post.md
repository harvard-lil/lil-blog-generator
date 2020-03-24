---
title: {{ request.form['title'] }}
author: {{ request.form['author'] }}
{% if request.form['tags'] %}{% set tag_list = request.form['tags'].split(' ') %}tags:{% for tag in tag_list %}
- {{ tag }}{% endfor %}{% endif %}
---
{{request.form['content']}}
