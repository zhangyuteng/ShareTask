# -*- coding: utf-8 -*-
from flask import jsonify


def render_json(data='', status=1, message='', redirect=''):
    if status not in [1, 0]:
        raise ValueError, 'status must be 1 or 0'
    status = 'success' if status == 1 else 'fail'
    return jsonify({
        'status': status,
        'data': data,
        'message': message,
        'redirect': redirect
    })
