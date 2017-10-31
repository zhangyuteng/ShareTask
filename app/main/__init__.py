# -*- coding: utf-8 -*-
from flask import Blueprint

main = Blueprint('main', __name__)

from . import views
# TODO:自定义错误输出
# from . import errors
