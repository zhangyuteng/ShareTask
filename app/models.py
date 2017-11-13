# -*- coding: utf-8 -*-
import random
from datetime import datetime

import re
from flask import json
from flask_login import current_user
from flask_security import UserMixin, RoleMixin
from sqlalchemy import and_, not_

from . import db

roles_users = db.Table('roles_users',
                       db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
                       db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))


# superuser, admin, author, editor, user
class Role(db.Model, RoleMixin):
    __tablename__ = 'role'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<Role %s>' % self.name


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    last_login_at = db.Column(db.DateTime())
    current_login_at = db.Column(db.DateTime())
    last_login_ip = db.Column(db.String(63))
    current_login_ip = db.Column(db.String(63))
    login_count = db.Column(db.Integer)
    task_id = db.Column(db.Integer)  # 保存用户当前操作的任务id
    task_log_id = db.Column(db.Integer)  # 保存用户当前审核操作的任务记录id
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('user'))  # , lazy='dynamic'))
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)

    task_logs = db.relationship('TaskLog', backref='user', lazy='dynamic')
    check_logs = db.relationship('CheckLog', backref='user', lazy='dynamic')

    def to_json(self):
        assert False, u'这里还没写好'
        json_user = {
            'username': self.username,
            'member_since': self.member_since,
        }
        return json_user

    @property  # for Flask-Admin column_formatters use
    def task_logs_str(self):
        ulist = []
        for t in self.task_logs.all():
            ulist.append(str(t))
        return ulist

    @property  # for Flask-Admin column_formatters use
    def check_logs_str(self):
        ulist = []
        for t in self.check_logs.all():
            ulist.append(str(t))
        return ulist

    def __repr__(self):
        return '<User-%d %r>' % (self.id, self.email)


class Task(db.Model):
    __tablename__ = 'task'
    id = db.Column(db.Integer, primary_key=True)
    babel_net_id = db.Column(db.String(60), unique=True)
    english_lemmas = db.Column(db.Text)
    english_definition = db.Column(db.Text)
    english_examples = db.Column(db.Text)
    chinese_lemmas = db.Column(db.Text)
    potential_translations = db.Column(db.Text)
    status = db.Column(db.Integer, default=0)
    task_logs = db.relationship('TaskLog', backref='task', lazy='dynamic')

    def __init__(self, babel_net_id, english_lemmas, english_definition, english_examples, chinese_lemmas,
                 potential_translations):
        self.babel_net_id = babel_net_id
        self.english_lemmas = english_lemmas
        self.english_definition = english_definition
        self.english_examples = english_examples
        self.chinese_lemmas = chinese_lemmas
        self.potential_translations = potential_translations

    @staticmethod
    def get_one(task_id=0):
        users = User.query.with_lockmode('read').all()
        all_used_task = []
        if task_id > 0:
            task = Task.query.get(task_id)
        elif current_user.task_id and current_user.task_id > 0:
            task = Task.query.get(current_user.task_id)
        else:
            for u in users:
                if u.task_id > 0:
                    all_used_task.append(u.task_id)
            if len(all_used_task) > 0:
                task = Task.query.filter(and_(Task.task_logs == None, not_(Task.id.in_(all_used_task)))).order_by(Task.id.asc()).with_lockmode('read').first()
            else:
                task = Task.query.filter(Task.task_logs == None).order_by(Task.id.asc()).first()
        user = User.query.get(current_user.id)
        user.task_id = task.id
        db.session.add(user)
        db.session.commit()
        # 获取各个单词的解释
        means = {}
        for word in task.english_lemmas.split(', '):
            word = word.replace('_', ' ')
            means[word] = Dictionary.get_means(word)

        setattr(task, 'means', means)
        return task

    def to_json(self):
        data = {
            'id': self.id,
            'babel_net_id': self.babel_net_id,
            'english_lemmas': [i.replace('_', ' ').strip() for i in self.english_lemmas.split(',')],
            'english_definition': self.english_definition,
            'english_examples': self.english_examples,
            'chinese_lemmas': [],
            'potential_translations': [i.strip() for i in self.potential_translations.split(',')],
            'means': self.means
        }
        if hasattr(self, 'task_log'):
            data['chinese_lemmas'] = json.loads(self.task_log.chinese_lemmas)
        return data

    @property  # for Flask-Admin column_formatters use
    def task_logs_str(self):
        ulist = []
        for t in self.task_logs.all():
            ulist.append(str(t))
        return ulist

    def __repr__(self):
        return '<Task-%d %s>' % (self.id, self.english_lemmas)


class TaskLog(db.Model):
    __tablename__ = 'task_log'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    chinese_lemmas = db.Column(db.Text)
    confirmed_at = db.Column(db.DateTime())

    check_logs = db.relationship('CheckLog', backref='task_log', lazy='dynamic')

    @staticmethod
    def get_one(task_log_id=0):
        if task_log_id > 0:
            task_log = TaskLog.query.get(task_log_id)
        elif current_user.task_log_id > 0:
            task_log = TaskLog.query.get(current_user.task_log_id)
        else:
            users = User.query.with_lockmode('read').all()
            all_used_task = []
            for u in users:
                if u.task_log_id > 0:
                    all_used_task.append(u.task_log_id)
            if len(all_used_task) > 0:
                task_log = TaskLog.query.filter(and_(TaskLog.check_logs == None, not_(TaskLog.id.in_(all_used_task)))).order_by(
                    TaskLog.id.asc()).with_lockmode('read').first()
            else:
                task_log = TaskLog.query.filter(TaskLog.check_logs == None).order_by(TaskLog.id.asc()).first()
        if not task_log:
            return []
        user = User.query.get(current_user.id)
        user.task_log_id = task_log.id
        db.session.add(user)
        db.session.commit()
        # 获取各个单词的解释
        means = {}
        for word in task_log.task.english_lemmas.split(', '):
            word = word.replace('_', ' ')
            means[word] = Dictionary.get_means(word)

        check_log = task_log.check_logs.first()
        if check_log:
            setattr(task_log, 'check_result', int(check_log.result))
            setattr(task_log, 'check_comment', check_log.comment)
        else:
            setattr(task_log, 'check_result', 1)
            setattr(task_log, 'check_comment', '')
        setattr(task_log, 'means', means)
        return task_log

    def to_json(self):
        result = {
            'task_id': self.task.id,
            'username': self.user.email,
            'userid': self.user.id,
            'task_log_id': self.id,
            'english_lemmas': [i.replace('_', ' ').strip() for i in self.task.english_lemmas.split(',')],
            'english_definition': self.task.english_definition,
            'english_examples': self.task.english_examples,
            'chinese_lemmas': json.loads(self.chinese_lemmas),
            'potential_translations': [i.strip() for i in self.task.potential_translations.split(',')],
            'means': self.means,
            'check_result': self.check_result,
            'check_comment': self.check_comment,
        }
        return result

    @property  # for Flask-Admin column_formatters use
    def check_logs_str(self):
        ulist = []
        for t in self.check_logs.all():
            ulist.append(u'{}: {}'.format(t.result, t.comment))
        return ulist

    @property
    def chinese_lemmas_str(self):
        ulist = []
        for t in json.loads(self.chinese_lemmas):
            ulist.append(t['chinese'])
        return '; '.join(ulist)

    def __repr__(self):
        return '<TaskLog-%d Task-%d>' % (self.id, self.task_id)


class CheckLog(db.Model):
    __tablename__ = 'check_log'
    id = db.Column(db.Integer, primary_key=True)
    task_log_id = db.Column(db.Integer, db.ForeignKey('task_log.id'), index=True)
    checker_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    result = db.Column(db.Boolean)  # 是否合格
    comment = db.Column(db.Text)  # 不合格的原因
    confirmed_at = db.Column(db.DateTime())

    def __repr__(self):
        return '<CheckLog-%d %d:%s>' % (self.id, self.task_log_id, self.result)


class Dictionary(db.Model):
    __tablename__ = 'dictionary'
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(60))
    chose_dictionary = db.Column(db.String(60))  # 查询时使用的词典
    paraphrases = db.relationship('Paraphrase', backref='dictionary', lazy='dynamic')

    @staticmethod
    def get_means(word):
        dictionary = Dictionary.query.filter_by(word=word.lower()).first()
        if dictionary:
            result = {}
            paraphrases = dictionary.paraphrases.all()
            for p in paraphrases:
                if p.pos.tag == 'n':
                    if p.ch:
                        p.ch = p.ch.replace(u'; ', u';')
                        p.ch = p.ch.replace(u'； ', u';')
                        p.ch = p.ch.replace(u'；', u';')
                        p.ch = p.ch.replace(u',', u';')
                        p.ch = p.ch.replace(u'，', u';')
                        p.ch = re.sub(ur':$|：$', u'', p.ch)
                        ch = p.ch.split(';')
                    if p.source.comment in result:
                        result[p.source.comment].append({'id': p.id, 'ch': ch, 'en': p.en, 'samples': [i.to_json() for i in p.samples.all()]})
                    else:
                        result[p.source.comment] = [{'id': p.id, 'ch': ch, 'en': p.en, 'samples': [i.to_json() for i in p.samples.all()]}]
            # 挑选两个词典
            if len(result) > 0:
                if len(result) > 2:
                    # 对大于两个的随机选择两个
                    if dictionary.chose_dictionary:
                        # 已经选取过
                        chose = dictionary.chose_dictionary.split(u',')
                    else:
                        chose = random.sample(result.keys(), 2)
                        # 小于两个词典的直接返回
                        dictionary.chose_dictionary = ','.join(chose)
                        db.session.add(dictionary)
                        db.session.commit()
                    # 删除未选择的词典
                    for k in result.keys():
                        if k not in chose:
                            del result[k]
            return result
        else:
            # print '{} is not found'.format(word)
            return None

    def __repr__(self):
        return '<Dictionary-%d %s>' % (self.id, self.word)


class Source(db.Model):
    __tablename__ = 'source'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60))
    china_name = db.Column(db.String(60))
    comment = db.Column(db.String(255))
    paraphrases = db.relationship('Paraphrase', backref='source', lazy='dynamic')

    def __repr__(self):
        return '<Source-%d %s>' % (self.id, self.name)


class Pos(db.Model):
    __tablename__ = 'pos'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60))  # 词典中的词性标记，不规范
    tag = db.Column(db.String(60))  # 词性标记
    comment = db.Column(db.String(255))
    paraphrases = db.relationship('Paraphrase', backref='pos', lazy='dynamic')

    def __repr__(self):
        return '<Pos-%d %s>' % (self.id, self.name)


class Paraphrase(db.Model):
    __tablename__ = 'paraphrase'
    id = db.Column(db.Integer, primary_key=True)
    dictionary_id = db.Column(db.Integer, db.ForeignKey('dictionary.id'), index=True)
    pos_id = db.Column(db.Integer, db.ForeignKey('pos.id'), index=True)
    source_id = db.Column(db.Integer, db.ForeignKey('source.id'), index=True)
    ch = db.Column(db.Text)
    en = db.Column(db.Text)
    samples = db.relationship('Sample', backref='paraphrase', lazy='dynamic')

    @property  # for Flask-Admin column_formatters use
    def samples_str(self):
        ulist = []
        for t in self.samples.all():
            ulist.append(str(t))
        return ulist

    def __repr__(self):
        return '<Paraphrase-%d %s>' % (self.id, self.dictionary.word)


class Sample(db.Model):
    __tablename__ = 'sample'
    id = db.Column(db.Integer, primary_key=True)
    ch = db.Column(db.Text)
    en = db.Column(db.Text)
    paraphrase_id = db.Column(db.Integer, db.ForeignKey('paraphrase.id'), index=True)

    def to_json(self):
        return {
            'id': self.id,
            'ch': self.ch,
            'en': self.en
        }

    def __repr__(self):
        return '<Sample-%d>' % (self.id,)

