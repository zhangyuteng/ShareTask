# -*- coding: utf-8 -*-
from __future__ import division

from datetime import datetime

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
    logs = TaskLog.query.filter(TaskLog.user_id == current_user.id).order_by(TaskLog.confirmed_at.desc()) \
        .paginate(page, 10, False)
    return render_template('task_logs.html', task_logs=logs, username=current_user.username)


@main.route('/result', methods=['GET'])
@login_required
def task_result():
    logs = CheckLog.query.filter(CheckLog.task_log.has(user_id=current_user.id)).order_by(
        CheckLog.confirmed_at.desc()).all()
    true_num = 0
    total = 0
    fail_num = 0
    error_logs = []
    for log in logs:
        total += 1
        if log.result:
            true_num += 1
        else:
            fail_num += 1
            error_logs.append({'english_lemmas': log.task_log.task.english_lemmas,
                               'english_definition': log.task_log.task.english_definition,
                               'chinese_lemmas': log.task_log.chinese_lemmas_str,
                               'comment': log.comment})
    if total > 0:
        correct_rate = round(true_num / total * 100.0, 2)
    else:
        correct_rate = 0
    return render_template('task_result.html', user=current_user, error_logs=error_logs,
                           correct_rate=correct_rate, total=total, fail_num=fail_num, true_num=true_num)


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

            if tl:
                # 若用户提交过，更新
                tl.chinese_lemmas = form.chinese_lemmas.data
                tl.confirmed_at = datetime.now()
                message = 'Modified successfully'
                db.session.commit()
            else:
                tl = TaskLog(task_id=form.task_id.data,
                             user_id=current_user.id,
                             chinese_lemmas=form.chinese_lemmas.data,
                             confirmed_at=datetime.now())
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


@main.route('/progress')
def progress():
    """
    获取任务完成进度
    :return:
    """
    total = float(Task.query.count())
    rest = float(Task.query.filter(Task.task_logs == None).count())
    done = total - rest
    data = round(done / total * 100., 2)
    return render_json(status=1, data=data)


# 后台管理页面的首页
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
        total = TaskLog.query.count()
        rest = TaskLog.query.filter(TaskLog.check_logs == None).count()
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
    # column_select_related_list = ['mps',]
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
    can_export = True
    column_export_list = ('babel_net_id', 'english_lemmas', 'english_definition', 'english_examples', 'chinese_lemmas', 'potential_translations')
    column_formatters_export = dict(
        babel_net_id=lambda v, c, m, p: m.task_log.task.babel_net_id,
        english_lemmas=lambda v, c, m, p: m.task_log.task.english_lemmas,
        english_definition=lambda v, c, m, p: m.task_log.task.english_definition,
        english_examples=lambda v, c, m, p: m.task_log.task.english_examples,
        chinese_lemmas=lambda v, c, m, p: m.task_log.chinese_lemmas_str,
        potential_translations=lambda v, c, m, p: m.task_log.task.potential_translations,
    )
    column_filters = ('result', 'confirmed_at', 'user.email')
    # Default sort column if no sorting is applied.
    column_default_sort = ('confirmed_at', True)
    # the example of using AJAX for foreign key model loading.
    form_ajax_refs = {
        'task_log': {
            'fields': ('id', ),
            'page_size': 10
        }
    }


class CustomModelViewDictionary(CustomModelViewBase):
    form_columns = (Dictionary.word, Dictionary.chose_dictionary)


class CustomModelViewTaskLog(CustomModelViewBase):
    can_create = False
    # can_edit = False
    column_default_sort = ('confirmed_at', False)
    column_list = ('id', 'chinese_lemmas', 'task', 'user', 'check_logs', 'confirmed_at')
    column_filters = ('task', 'user', 'check_logs')
    form_excluded_columns = ('task', 'check_logs')
    column_formatters = dict(
        check_logs=lambda v, c, m, p: m.check_logs_str,
        chinese_lemmas=lambda v, c, m, p: m.chinese_lemmas_str,
        task=lambda v, c, m, p: m.task.english_lemmas,
        user=lambda v, c, m, p: '{}-{}'.format(m.user.id, m.user.email),
    )
    # Default sort column if no sorting is applied.
    column_default_sort = ('confirmed_at', True)
    column_extra_row_actions = [
        EndpointLinkRowAction('icon-check', 'check.check_task_log', title=u'审查')
    ]

    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False
        if current_user.has_role('admin') or current_user.has_role('checker'):
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

admin.add_view(CustomModelViewTaskLog(TaskLog, db.session, name=u'标注列表'))
admin.add_view(CustomModelViewUser(User, db.session, name=u'用户管理'))
admin.add_view(CustomModelViewCheckLog(CheckLog, db.session, name=u'导出标注记录'))
admin.add_view(CustomModelViewBase(Role, db.session, category='Models'))
admin.add_view(CustomModelViewTask(Task, db.session, category='Models'))
admin.add_view(CustomModelViewDictionary(Dictionary, db.session, category='Models'))
admin.add_view(CustomModelViewParaphrase(Paraphrase, db.session, category='Models'))
admin.add_view(CustomModelViewSample(Sample, db.session, category='Models'))
admin.add_view(CustomModelViewSource(Source, db.session, category='Models'))
admin.add_view(CustomModelViewPos(Pos, db.session, category='Models'))

admin.add_link(MenuLink(name='Logout', endpoint='security.logout'))
