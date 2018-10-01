# -*- coding: utf-8 -*-
from __future__ import division

from datetime import datetime
from random import random

import os
from flask import render_template, redirect, url_for, request, json, abort
from flask_admin import BaseView, expose
from flask_admin._backwards import ObsoleteAttr
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import rules
from flask_admin.menu import MenuLink
from flask_admin.model.template import LinkRowAction, EndpointLinkRowAction
from flask_babelex import string_types
from flask_security import current_user, login_required, roles_accepted
from flask_security.utils import hash_password
from sqlalchemy import and_
from wtforms import validators, fields

from app.utils import render_json
from . import main
from .forms import TaskLogForm, CKTextAreaField
from .. import db, cache, admin
from ..models import Task, TaskLog, User, Dictionary, Role, CheckLog, Source, Pos, Paraphrase, Sample
from config import Config


# from manage import youdao, iciba, haici, bing, oxford8, ldoce6, YOUDAO, HAICI, ICIBA, BING, LDOCE6, OXFORD8


@main.route('/', methods=['GET', 'POST'])
@main.route('/<int:task_id>', methods=['GET', 'POST'])
@login_required
def index(task_id=0):
    form = TaskLogForm()
    return render_template('index.html',
                           form=form, task_id=task_id, user=current_user)


@main.route('/rule', methods=['GET'])
@login_required
def rule():
    return render_template('rule.html')


@main.route('/logs/', methods=['GET'])
@main.route('/logs/<int:page>', methods=['GET'])
@login_required
def task_logs(page=1):
    task_log_id = request.args.get('task_log_id', type=int, default=0)
    if task_log_id == 0:
        count = TaskLog.query.filter(TaskLog.user_id == current_user.id).order_by(TaskLog.confirmed_at.desc()).count()
        logs = TaskLog.query.filter(TaskLog.user_id == current_user.id).order_by(TaskLog.confirmed_at.desc()) \
            .paginate(page, 10, False)
    else:
        count = 1
        logs = TaskLog.query.filter(and_(TaskLog.id == task_log_id, TaskLog.user_id == current_user.id)).paginate(page,
                                                                                                                  10,
                                                                                                                  False)
        print(logs)
    return render_template('task_logs.html', task_logs=logs, username=current_user.username, count=count)


@main.route('/result', methods=['GET'])
@login_required
def task_result():
    before_count, before_true_rate, after_count, after_true_rate, after_daily_count = TaskLog.get_user_statistics(current_user.id)

    # 获取错误标注的记录
    check_logs = CheckLog.query.filter(CheckLog.task_log.has(user_id=current_user.id)).order_by(
        CheckLog.confirmed_at.desc()).all()
    error_logs = []
    for log in check_logs:
        if not log.result:
            error_logs.append({'english_lemmas': log.task_log.task.english_lemmas,
                               'english_definition': log.task_log.task.english_definition,
                               'chinese_lemmas': log.task_log.chinese_lemmas_str,
                               'comment': log.comment,
                               'task_id': log.task_log.task.id,
                               'id': log.task_log.id})
    return render_template('task_result.html', user=current_user, error_logs=error_logs, before_count=before_count, before_true_rate=before_true_rate,
                           after_count=after_count, after_true_rate=after_true_rate, after_daily_count=after_daily_count)


@main.route('/task', methods=['GET'])
@main.route('/task/<int:task_id>', methods=['GET'])
@login_required
def get_task(task_id=0):
    task = Task.get_one(task_id)
    if task_id > 0:
        # 若当前用户标注过该记录，说明这是修改操作
        task_log = None
        for log in task.task_logs.all():
            if log.user_id == current_user.id:
                task_log = log
        if task_log is not None:
            setattr(task, 'task_log', task_log)
        elif current_user.has_role('admin') or current_user.has_role('checker'):
            # 没有获取到task_log，检查当前用户是否为admin或checker
            pass
        else:
            # 以上条件都不满足，用户没有权限自己选择任务
            redirect(url_for('index'))

    return render_json(task.to_json(), 1)


@main.route('/task', methods=['POST'])
@login_required
def post_task():
    form = TaskLogForm()
    if form.validate_on_submit():
        # 检查非法字符
        if form.validate_invaild_symbol():
            tl = TaskLog.query.filter(
                and_(TaskLog.task_id == form.task_id.data, TaskLog.user_id == current_user.id)).first()
            # 清理前后空格
            chineses = json.loads(form.chinese_lemmas.data)
            for i, v in enumerate(chineses):
                chineses[i]['chinese'] = v['chinese'].strip()
                form.chinese_lemmas.data = json.dumps(chineses)

            need_check = False
            if random() <= Config.CHECK_POINT:
                need_check = True
            if os.environ['FLASK_CONFIG'] == 'testing':
                need_check = True
            if tl:
                # 若用户提交过，更新
                tl.chinese_lemmas = form.chinese_lemmas.data
                tl.confirmed_at = datetime.now()
                tl.need_check = need_check
                message = 'Modified successfully'
                db.session.commit()
            else:
                tl = TaskLog(task_id=form.task_id.data,
                             user_id=current_user.id,
                             chinese_lemmas=form.chinese_lemmas.data,
                             need_check=need_check,
                             confirmed_at=datetime.now(),
                             added_at=datetime.now())
                message = 'Saved successfully'
                db.session.add(tl)
                db.session.commit()
            # 将用户正在工作的任务清空
            user = User.query.get(current_user.id)
            user.task_id = None
            db.session.commit()
            return render_json(status=1, message=message)
    errors = []
    for k, v in form.errors.iteritems():
        msg = []
        for m in v:
            msg.append(m)
        errors.append(u'; '.join(msg))
    return render_json(status=0, message='\n'.join(errors))


@main.route('/suggestion')
def suggestion():
    logs = CheckLog.query.filter(CheckLog.task_log.has(user_id=current_user.id)).order_by(
        CheckLog.confirmed_at.desc()).all()
    suggestion_logs = []
    for log in logs:
        if log.result:
            if log.comment and log.result == True:
                suggestion_logs.append({'english_lemmas': log.task_log.task.english_lemmas,
                                        'english_definition': log.task_log.task.english_definition,
                                        'chinese_lemmas': log.task_log.chinese_lemmas_str,
                                        'comment': log.comment,
                                        'task_id': log.task_log.task.id,
                                        'id': log.task_log.id})
    return render_template('task_suggestion.html', user=current_user, suggestion_logs=suggestion_logs)


@main.route('/progress')
def progress():
    """
    获取任务完成进度
    :return:
    """
    total = float(Task.query.count())
    if os.environ['FLASK_CONFIG'] == 'testing':
        done = float(TaskLog.query.filter(TaskLog.user_id == current_user.id).count())
    else:
        rest = float(Task.query.filter(Task.task_logs == None).count())
        done = total - rest
    data = round(done / total * 100., 2)
    return render_json(status=1, data=data)


# 后台管理页面的首页
class StatisticsView(BaseView):
    @expose('/')
    def index(self):
        users = User.query.filter(User.active == True).all()
        users_statistics = []
        for u in users:
            users_statistics.append({
                'username': u.email,
                'realname': u.username,
                'statistics': TaskLog.get_user_statistics(u.id)
            })
        return self.render('admin/statistics.html', users_statistics=users_statistics)


class CheckView(BaseView):
    @expose('/')
    @expose('/<int:task_log_id>')
    def check_task_log(self, task_log_id=0):
        if task_log_id == 0:
            task_log_id = request.args.get('id')
            if task_log_id:
                task_log_id = int(task_log_id)
            else:
                task_log_id = 0
        return self.render('admin/check.html', task_log_id=task_log_id)

    @expose('/progress')
    @cache.cached(timeout=60)
    def progress(self):
        """
        获取进度
        :return:
        """
        total = TaskLog.query.filter(TaskLog.need_check == True).count()
        rest = TaskLog.query.filter(and_(TaskLog.check_logs == None, TaskLog.need_check == True)).count()
        done = total - rest
        data = {
            'total': total,
            'rest': rest,
            'done': done
        }
        return render_json(status=1, data=data)

    @expose('/task_log', methods=['GET'])
    @expose('/task_log/<int:task_log_id>', methods=['GET'])
    @login_required
    def get_task_log(self, task_log_id=0):
        task_log = TaskLog.get_one(task_log_id)
        if task_log:
            return render_json(data=task_log.to_json())
        else:
            return render_json(status=1, message='暂无需要审核的标注')

    @expose('/task_log', methods=['POST'])
    @login_required
    def post_task_log(self):
        data = request.get_json()
        task_log_id = int(data.get('task_log_id'))
        result = int(data.get('result'))
        comment = data.get('comment')
        if comment:
            comment = comment
        # 检查参数是否合法
        if result not in [0, 1]:
            return render_json(status=0, message='参数错误')
        # 检查TaskLog是否存在
        task_log = TaskLog.query.get(task_log_id)
        if not task_log:
            return render_json(status=0, message='标注记录不存在')
        # 检查当前用户是否对该标注结果审核过，如果审核过，则更新，否则，添加
        check_log = CheckLog.query.filter_by(checker_id=current_user.id).filter_by(task_log_id=task_log.id).first()
        if check_log:
            check_log.result = result
            check_log.comment = comment
        else:
            # 保存记录
            check_log = CheckLog(task_log=task_log, user=current_user, result=result, comment=comment)
        check_log.confirmed_at = datetime.now()
        # 将用户编辑记录清空
        user = User.query.get(current_user.id)
        user.task_log_id = None
        db.session.add(user)
        db.session.add(check_log)
        db.session.commit()
        return render_json(status=1)

    @expose('/users')
    def check_users(self):

        return self.render('admin/check_users.html')

    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False
        if current_user.has_role('checker') or current_user.has_role('admin'):
            return True
        return False

    def _handle_view(self, name, **kwargs):
        """
        Override builtin _handle_view in order to redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('security.login', next=request.url))


# Create customized model view class
class CustomModelViewBase(ModelView):
    # 字段（列）格式化
    # `view` is current administrative view
    # `context` is instance of jinja2.runtime.Context
    # `model` is model instance
    # `name` is property name
    column_display_pk = True  # optional, but I like to see the IDs in the list
    #    column_list = ('id', 'name', 'parent')
    column_auto_select_related = ObsoleteAttr('column_auto_select_related',
                                              'auto_select_related',
                                              True)
    column_display_all_relations = False

    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False
        if current_user.has_role('admin'):
            return True
        return False

    def _handle_view(self, name, **kwargs):
        """
        Override builtin _handle_view in order to redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('security.login', next=request.url))


class CustomModelViewUser(CustomModelViewBase):
    column_list = ('id', 'email', 'username', 'roles', 'active', 'last_login_at', 'current_login_at', 'last_login_ip',
                   'current_login_ip', 'login_count', 'task_id', 'task_log_id')
    column_formatters = dict(
        task_logs=lambda v, c, m, p: m.task_logs_str,
        check_logs=lambda v, c, m, p: m.check_logs_str,
        password=lambda v, c, m, p: '**' + m.password[-6:],
    )
    column_searchable_list = (User.email,)

    form_create_rules = (
        rules.FieldSet(('email', 'username', 'password'), 'Personal'),
        rules.FieldSet(('roles', 'active'), 'Permission'),
    )

    form_edit_rules = (
        rules.FieldSet(('email', 'username'), 'Personal'),
        rules.FieldSet(('roles', 'active', 'task_id', 'task_log_id'), 'Permission'),
        rules.Header('Reset password'),
        rules.Field('new_password')
    )

    column_extra_row_actions = [
        EndpointLinkRowAction('icon-check', 'check.check_task_log', title=u'审查')
    ]

    def get_create_form(self):
        form = self.scaffold_form()
        form.email = fields.StringField('Username', [validators.DataRequired()])
        form.username = fields.StringField(u'姓名', [validators.DataRequired()])
        form.password = fields.PasswordField('Password', [validators.DataRequired()])
        return form

    def get_edit_form(self):
        form = self.scaffold_form()
        delattr(form, 'password')
        form.new_password = fields.PasswordField('New Password')
        return form

    def on_model_change(self, form, model, is_created):
        if is_created is False:
            if form.new_password.data:
                model.password = hash_password(form.new_password.data)
        else:
            if form.password.data:
                model.password = hash_password(form.password.data)


class CustomModelViewTask(CustomModelViewBase):
    # column_select_related_list = ['mps',]
    column_formatters = dict(
        task_logs=lambda v, c, m, p: m.task_logs_str,
    )
    inline_models = (TaskLog,)


class CustomModelViewCheckLog(CustomModelViewBase):
    can_edit = False
    can_create = False
    column_default_sort = ('confirmed_at', True)
    # the example of using AJAX for foreign key model loading.
    form_ajax_refs = {
        'task_log': {
            'fields': ('id',),
            'page_size': 10
        }
    }


class CustomModelViewDictionary(CustomModelViewBase):
    form_columns = (Dictionary.word, Dictionary.chose_dictionary)


class CustomModelViewTaskLog(CustomModelViewBase):
    can_create = False
    can_edit = False
    column_list = ('id', 'task', 'chinese_lemmas', 'check_logs', 'annotator', 'annotate_time', 'checker', 'check_time')
    column_labels = dict(task='en_lemmas', chinese_lemmas='cn_lemmas')
    column_filters = (
        'id', 'confirmed_at', 'task.english_lemmas', 'chinese_lemmas', 'user.id', 'user.email', 'user.username',
        'check_logs', 'check_logs.user.email')
    form_excluded_columns = ('task', 'check_logs')
    column_formatters = dict(
        check_logs=lambda v, c, m, p: m.check_logs_str,
        chinese_lemmas=lambda v, c, m, p: m.chinese_lemmas_str,
        task=lambda v, c, m, p: m.task.english_lemmas,
        user=lambda v, c, m, p: '{}-{}'.format(m.user.id, m.user.email),
        babel_net_id=lambda v, c, m, p: m.task.babel_net_id,
        english_lemmas=lambda v, c, m, p: m.task.english_lemmas,
        english_definition=lambda v, c, m, p: m.task.english_definition,
        english_examples=lambda v, c, m, p: m.task.english_examples,
        potential_translations=lambda v, c, m, p: m.task.potential_translations,
        check_result=lambda v, c, m, p: m.check_logs_str,
        annotator=lambda v, c, m, p: '{}-{}'.format(m.user.id, m.user.email),
        checker=lambda v, c, m, p: m.checker_str,
        annotate_time=lambda v, c, m, p: m.confirmed_at,
        check_time=lambda v, c, m, p: m.check_time_str
    )
    can_export = True
    # column_export_list = ('babel_net_id', 'english_lemmas', 'english_definition', 'english_examples', 'chinese_lemmas',
    #                       'potential_translations', 'check_result')
    column_export_list = (
        'id', 'task', 'english_definition', 'chinese_lemmas', 'check_logs', 'annotator', 'annotate_time', 'checker',
        'check_time')
    # Default sort column if no sorting is applied.
    column_default_sort = ('confirmed_at', True)
    column_extra_row_actions = [
        EndpointLinkRowAction('icon-check', 'check.check_task_log', title=u'审查')
    ]

    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False
        if current_user.has_role('admin') or current_user.has_role('superchecker'):
            return True
        return False


class CustomModelViewParaphrase(CustomModelViewBase):
    can_create = False
    column_formatters = dict(
        samples=lambda v, c, m, p: m.samples_str,
    )
    column_searchable_list = (Paraphrase.ch, Paraphrase.dictionary_id)
    column_filters = (Paraphrase.ch, Paraphrase.en)
    form_excluded_columns = ('task', 'samples', 'dictionary')

    column_select_related_list = ()


class CustomModelViewSample(CustomModelViewBase):
    can_create = False
    form_columns = (Sample.ch, Sample.en)


class CustomModelViewSource(CustomModelViewBase):
    form_columns = (Source.name, Source.china_name, Source.comment)


class CustomModelViewPos(CustomModelViewBase):
    form_columns = (Pos.name, Pos.tag, Pos.comment)


admin.add_view(CheckView(name=u'审查', endpoint='check'))
admin.add_view(StatisticsView(name=u'统计', endpoint='statistics'))

admin.add_view(CustomModelViewTaskLog(TaskLog, db.session, name=u'标注列表'))
admin.add_view(CustomModelViewUser(User, db.session, name=u'用户管理'))
admin.add_view(CustomModelViewCheckLog(CheckLog, db.session, name=u'审核记录'))
admin.add_view(CustomModelViewBase(Role, db.session, category='Models'))
admin.add_view(CustomModelViewTask(Task, db.session, category='Models'))
admin.add_view(CustomModelViewDictionary(Dictionary, db.session, category='Models'))
admin.add_view(CustomModelViewParaphrase(Paraphrase, db.session, category='Models'))
admin.add_view(CustomModelViewSample(Sample, db.session, category='Models'))
admin.add_view(CustomModelViewSource(Source, db.session, category='Models'))
admin.add_view(CustomModelViewPos(Pos, db.session, category='Models'))

admin.add_link(MenuLink(name='Logout', endpoint='security.logout'))
