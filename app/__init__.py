# -*- coding: utf-8 -*-

from flask import Flask
from flask_admin import Admin
from flask_security import Security, SQLAlchemyUserDatastore
from flask_sqlalchemy import SQLAlchemy
from flask_cache import Cache

from config import config

db = SQLAlchemy()

# models引用必须在 db/login_manager之后，不然会循环引用
from .models import User, Role

user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(datastore=user_datastore, register_blueprint=False)
cache = Cache(config={'CACHE_TYPE': 'simple'})

admin = Admin(name=u'知识众包平台管理')


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    db.init_app(app)
    # 这里如果不传入user_datastore，会将前面传入的user_datastore设置为None
    security.init_app(app, datastore=user_datastore, register_blueprint=True)
    cache.init_app(app, config={'CACHE_TYPE': 'simple'})
    admin.init_app(app)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app
