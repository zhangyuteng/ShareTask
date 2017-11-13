# -*- coding: utf-8 -*-
from flask import json
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired
import re
from wtforms import (
    widgets,
    StringField,
    TextField,
    TextAreaField,
    PasswordField,
    BooleanField,
    ValidationError,
    Field
)
invaild_RE = re.compile(ur'[\(\)\（\）\〔\〕\]\[]|\.{2,}|;')


class CKTextAreaWidget(widgets.TextArea):
    """CKeditor form for Flask-Admin."""

    def __call__(self, field, **kwargs):
        """Define callable type(class)."""

        # Add a new class property ckeditor: `<input class=ckeditor ...>`
        kwargs.setdefault('class_', 'ckeditor')
        return super(CKTextAreaWidget, self).__call__(field, **kwargs)


class CKTextAreaField(TextAreaField):
    """Create a new Field type."""

    # Add a new widget `CKTextAreaField` inherit from TextAreaField.
    widget = CKTextAreaWidget()


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', default=False)
    remember_me = StringField('remember_me', default=False)


class TaskLogForm(FlaskForm):
    task_id = StringField('ID', validators=[DataRequired()])
    chinese_lemmas = StringField('Chinese Lemmas', validators=[DataRequired()])

    def validate_invaild_symbol(self):
        """
        不能有 括号 省略号 等非标准字符
        :return:
        """
        if not self.chinese_lemmas.data:
            return False
        chineses = json.loads(self.chinese_lemmas.data)
        errors = []
        for item in chineses:
            if invaild_RE.search(item['chinese']):
                errors.append(item['chinese'])
        if errors:
            print errors
            self.errors['chinese_lemmas'] = [u'" {} " have illegal characters'.format(u','.join(errors))]
            return False
        else:
            return True
