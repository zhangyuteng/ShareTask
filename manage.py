#!.venv/bin/python
# -*- coding: utf-8 -*-
import os
import time

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

from app import create_app, db, user_datastore
from app.models import User, Role, roles_users, Task, TaskLog, CheckLog, Dictionary, Sample, Source, Pos, Paraphrase
from flask_script import Manager, Shell
from flask_migrate import Migrate, MigrateCommand
from flask_security.utils import hash_password
from app.main.fetchdicts import *

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)
migrate = Migrate(app, db)


def make_shell_context():
    return dict(app=app, db=db, User=User, Role=Role, roles_users=roles_users,
                Task=Task, TaskLog=TaskLog, CheckLog=CheckLog, user_datastore=user_datastore,
                Dictionary=Dictionary, Source=Source, Pos=Pos, Paraphrase=Paraphrase, Sample=Sample)


manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)


@manager.command
def test(coverage=False):
    """Run the unit tests."""
    if coverage and not os.environ.get('FLASK_COVERAGE'):
        import sys
        os.environ['FLASK_COVERAGE'] = '1'
        os.execvp(sys.executable, [sys.executable] + sys.argv)
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)
    if COV:
        COV.stop()
        COV.save()
        print('Coverage Summary:')
        COV.report()
        basedir = os.path.abspath(os.path.dirname(__file__))
        covdir = os.path.join(basedir, 'tmp/coverage')
        COV.html_report(directory=covdir)
        print('HTML version: file://%s/index.html' % covdir)
        COV.erase()


@manager.command
def profile(length=25, profile_dir=None):
    """Start the application under the code profiler."""
    from werkzeug.contrib.profiler import ProfilerMiddleware
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[length],
                                      profile_dir=profile_dir)
    app.run()


@manager.command
def deploy():
    """Run deployment tasks."""
    from flask_migrate import init, migrate, upgrade

    # migrate database to latest revision
    try:
        init()
    except:
        pass
    migrate()
    upgrade()


@manager.command
def dropall():
    db.drop_all()
    print "all tables dropped! remember to delete directory: migrations"


@manager.command
def initrole():
    db.session.add(Role(name="superuser"))
    db.session.add(Role(name="admin"))
    db.session.add(Role(name="checker"))
    db.session.add(Role(name="editor"))
    pwd = os.getenv('FLASK_ADMIN_PWD') or raw_input("Pls input Flask admin pwd:")
    admin_user = user_datastore.create_user(email="admin", password=hash_password(pwd))
    superuser_role = user_datastore.find_role('superuser')
    db.session.add(admin_user)
    user_datastore.add_role_to_user(admin_user, superuser_role)
    db.session.commit()
    print "Roles added!"


@manager.command
def adduser():
    username = raw_input("Pls input username:")
    # check user
    exits_user = User.query.filter_by(email=username).first()
    if exits_user:
        return '{} is exits'.format(username)
    pwd = raw_input("Pls input pwd:")
    editor_user = user_datastore.create_user(email=username, password=hash_password(pwd))
    editor_role = user_datastore.find_role('editor')
    db.session.add(editor_user)
    user_datastore.add_role_to_user(editor_user, editor_role)
    db.session.commit()
    print "{} added!".format(username)


@manager.command
def import_task():
    """
    导入需要标注的词典，词典文件需要转为csv格式
    :return:
    """
    import csv
    # 清空表
    db.session.query(Task).delete()
    file_path = os.getenv('DICT_FILE_PATH') or raw_input("Pls input dict file path:")
    if os.path.exists(file_path):
        print 'start import ....'
        with open(file_path, 'rb') as f:
            reader = csv.reader(f)
            next(reader)
            for line in reader:
                line = [item.decode('utf-8', 'ignore') for item in line]
                t = Task(*line)
                db.session.add(t)
            db.session.commit()
        print 'import successfully'

    else:
        print '%s is not exist!' % file_path


@manager.command
def initdictdata():
    """
    添加词典的初始数据，主要有词典来源数据，单词词性数据
    :return:
    """
    sourcedata = [
        {'name': OXFORD8, 'comment': u'牛津高阶英汉双解词典(简体) 第 8 版'},
        {'name': COLLINYH, 'comment': u'柯林斯英汉双解大词典'},
        {'name': YHDCD, 'comment': u'英汉大词典（第二版）陆谷孙'},
        {'name': LODCE, 'comment': u'朗文当代英语大词典(英汉汉英)第4版'},
        {'name': SJDNYHHYSJCD, 'comment': u'21世紀電腦英漢漢英雙向辭典'},
        {'name': JQGJYHSJCD, 'comment': u'剑桥高阶英汉双解词典（第3版）'}
    ]
    posdata = [
        {'name': POS_N, 'comment': u'名词'},
        {'name': POS_V, 'comment': u'动词'},
        {'name': POS_A, 'comment': u'形容词'},
        {'name': POS_D, 'comment': u'副词'},
        {'name': POS_P, 'comment': u'介词'},
        {'name': POS_DET, 'comment': u'限定词'},
        {'name': POS_PRON, 'comment': u'代词'},
        {'name': POS_QUN, 'comment': u'数量关系词'},
        {'name': POS_M, 'comment': u'数量词'},
        {'name': POS_ABBR, 'comment': u'缩写'},
        {'name': POS_SYMBOL, 'comment': u'象征词'},
        {'name': POS_NONE, 'comment': u'没有词性'},
        {'name': POS_PREP, 'comment': u'柯林斯词典中出现的，不知道什么意思'},
    ]
    for s in sourcedata:
        if Source.query.filter_by(name=s['name']).first() is None:
            s = Source(**s)
            db.session.add(s)
    for p in posdata:
        if Pos.query.filter_by(name=p['name']).first() is None:
            p = Pos(**p)
            db.session.add(p)
    db.session.commit()


@manager.command
def testdict():
    oxford.only_use_db = False
    oxford.html_cache = True
    collinyh.only_use_db = False
    collinyh.html_cache = True
    yhdcd.only_use_db = False
    yhdcd.html_cache = True
    lodce.only_use_db = False
    lodce.html_cache = True
    # oxford.set_phrase("bone")
    # print oxford.executor()
    # collinyh.set_phrase("bone")
    # print collinyh.executor()
    # yhdcd.set_phrase("bone")
    # print yhdcd.executor()
    lodce.set_phrase("family")
    print lodce.executor()

@manager.command
def initdict():
    oxford.only_use_db = False
    oxford.load_mdx()
    collinyh.only_use_db = False
    collinyh.load_mdx()
    yhdcd.only_use_db = False
    yhdcd.load_mdx()
    lodce.only_use_db = False
    lodce.load_mdx()

    tasks = Task.query.filter(Task.status==0).all()
    for task in tasks:
        words = task.english_lemmas.split(', ')
        for w in words:
            word = w.replace('_', ' ')
            print 'fetch {}'.format(word)
            oxford.set_phrase(word)
            ores = 'No'
            if oxford.executor():
                ores = 'Yes'
            collinyh.set_phrase(word)
            cres = 'No'
            if collinyh.executor():
                cres = "Yes"
            yhdcd.set_phrase(word)
            yres = 'No'
            if yhdcd.executor():
                yres = 'Yes'
            lodce.set_phrase(word)
            lres = 'No'
            if lodce.executor():
                lres = 'Yes'
            print u'牛津-{} 柯林斯-{} 英汉-{} 朗文-{}'.format(ores, cres, yres, lres)
        task.status = 1
        db.session.add(task)
        db.session.commit()

@manager.command
def delte():
    d = Dictionary.query.filter_by(word='cipher').first()
    ps = d.paraphrases.all()
    for p in ps:
        if p.source_id==5 and p.id not in [1057,1058,1059,1060,1061,1062,1063,1064,1065,1065,1067,1068,1069,1070]:
            db.session.delete(p)
    db.session.commit()


if __name__ == '__main__':
    manager.run()
