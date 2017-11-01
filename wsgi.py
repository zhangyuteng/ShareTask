# -*- coding: utf-8 -*-
import os


if os.path.exists('.env'):
    print('Importing environment from .env...')
    for line in open('.env'):
        var = line.strip().split('=')
        if len(var) == 2:
            os.environ[var[0]] = var[1]

COV = None
if os.getenv('FLASK_COVERAGE').lower() == 'on':
    print('start coverage')
    import coverage

    COV = coverage.coverage(branch=True, include='app/*')
    COV.start()

from app import create_app

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
