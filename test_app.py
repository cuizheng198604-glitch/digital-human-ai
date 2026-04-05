# -*- coding: utf-8 -*-
from web.app import app
print("Flask app initialized OK")
print("Routes:", [str(rule) for rule in app.url_map.iter_rules()])
