# coding=utf8
import json
from functools import wraps

import os

from app.models import Dictionary, Pos, Source, Paraphrase, Sample
from . import OXFORD8, COLLINYH, YHDCD, LODCE, SJDNYHHYSJCD, JQGJYHSJCD, OXFORD8_MDX_FILE, \
    COLLINYH_MDX_FILE, YHDCD_MDX_FILE, LODCE_MDX_FILE, SJDNYHHYSJCD_MDX_FILE, JQGJYHSJCD_MDX_FILE
from .mdict.readmdict import MDX
from .parser import oxford8parser, collinsyhparser, yhdcdparser, lodcepaser, sjdnyhhysjcdpaser, jqgjyhsjcdpaser
from app import db
import pickle

__author__ = "zhangyuteng"


def void_return(fun):
    @wraps(fun)
    def check(self):
        if not self.result or not self.valid:
            return ''
        else:
            return fun(self)

    return check


class Dicts:
    def __init__(self, phrase='', source=OXFORD8, only_use_db=True, html_cache=False):
        self.phrase = phrase.lower()
        self.source = source
        self._source_id = 0
        self.result = {}
        self.valid = True
        self.raw = ''
        self.is_new = False
        self.dicts = {}
        self.only_use_db = only_use_db
        self.mdx_file = None
        self.parser = None
        self.html_cache = html_cache
        self.used_phrases = []
        if self.source == OXFORD8:
            self.mdx_file = OXFORD8_MDX_FILE
            self.parser = oxford8parser
        elif self.source == COLLINYH:
            self.mdx_file = COLLINYH_MDX_FILE
            self.parser = collinsyhparser
        elif self.source == YHDCD:
            self.mdx_file = YHDCD_MDX_FILE
            self.parser = yhdcdparser
        elif self.source == LODCE:
            self.mdx_file = LODCE_MDX_FILE
            self.parser = lodcepaser
        elif self.source == SJDNYHHYSJCD:
            self.mdx_file = SJDNYHHYSJCD_MDX_FILE
            self.parser = sjdnyhhysjcdpaser
        elif self.source == JQGJYHSJCD:
            self.mdx_file = JQGJYHSJCD_MDX_FILE
            self.parser = jqgjyhsjcdpaser

    def load_mdx(self):
        if len(self.dicts) == 0:
            pickle_file = u'./tmp/{}.pkl'.format(os.path.basename(self.mdx_file))
            if os.path.exists(pickle_file):
                print u'load {}'.format(pickle_file)
                with open(pickle_file, 'rb') as f:
                    self.dicts = pickle.load(f)
            else:
                print u'load {}'.format(self.mdx_file)
                mdx = MDX(self.mdx_file)
                self.dicts = {}
                for k, v in mdx.items():
                    k = k.lower()
                    if k in self.dicts:
                        self.dicts[k] += v
                    else:
                        self.dicts[k] = v
                print u'cache {}'.format(pickle_file)
                with open(pickle_file, 'wb') as f:
                    pickle.dump(self.dicts, f)

    def get_source_id(self):
        if self._source_id == 0:
            source = Source.query.filter(Source.name==self.source).first()
            self._source_id = source.id
        return self._source_id

    def get_html(self):
        if self.html_cache:
            cache_file = 'tmp/{}_{}.pkl'.format(self.source, self.phrase)
            if os.path.exists(cache_file):
                with open(cache_file, 'rb') as f:
                    result = pickle.load(f)
            else:
                self.load_mdx()
                result = self.dicts.get(self.phrase)
                with open(cache_file, 'wb') as f:
                    pickle.dump(result, f)
        else:
            self.load_mdx()
            result = self.dicts.get(self.phrase)
        return result

    def set_phrase(self, phrase):
        self.phrase = phrase.lower()
        self.used_phrases.append(self.phrase)

    def valid_check(self):
        if not self.result:
            self.is_new = True
            self.valid = False
            return False

        if 'errorCode' not in self.result:
            self.is_new = True

        if not self.is_new:
            if 'translation' not in self.result or \
                    (len(self.result['translation']) == 1 and self.result['translation'][0] == self.result['query']):
                self.valid = False

    def executor(self):
        """
        查询一个单词的解释，先从数据库，如果数据库中没有再从本地词典文件中查询，从本地词典中查询的结果将保存到数据库中
        :param phrase:
        :param only_use_db: 若为True，只从数据库中查询，提高系统运行速度
        :return:
        """
        # print self.spider()
        # return ''
        dictionary = Dictionary.query.filter(Dictionary.word == self.phrase).first()
        paraphrase = None
        if dictionary:
            paraphrase = dictionary.paraphrases.filter(Paraphrase.source_id==self.get_source_id()).all()
        if not paraphrase and not self.only_use_db:
            paraphrase = self.spider()
            if len(paraphrase) > 0:
                self.save_paraphrase(paraphrase)
        self.result = paraphrase
        return self.result

    def spider(self):
        """
        通过解析词典文件获取单词解释
        :return:
        """
        while True:
            html = self.get_html()
            if html:
                result = self.parser(html)
                if isinstance(result, unicode):
                    if result.lower() not in self.used_phrases:
                        self.set_phrase(result)
                    else:
                        return []
                else:
                    return result
            else:
                return []

    def save_paraphrase(self, paraphrase):
        dictinoary = Dictionary.query.filter(Dictionary.word==self.phrase).first()
        if dictinoary is None:
            dictinoary = Dictionary(word=self.phrase)
            db.session.add(dictinoary)
            db.session.commit()
        source = Source.query.filter(Source.name==self.source).first()
        assert source is not None, "can't find '{}' source".format(self.source)
        for item in paraphrase:
            pos = Pos.query.filter(Pos.name == item['pos']).first()
            if pos is None:
                # 添加该词性到数据库中，并标记来源
                pos = Pos(name=item['pos'], comment=self.source)
                db.session.add(pos)
                db.session.commit()
            assert pos is not None, "{}\ncon't find '{}' pos".format(str(item), item['pos'])
            paraphrase = Paraphrase(dictionary_id=dictinoary.id, source_id=source.id, pos_id=pos.id, ch=item['mean']['ch'], en=item['mean']['en'])
            db.session.add(paraphrase)
            db.session.commit()
            for sample in item['samples']:
                sample = Sample(ch=sample['ch'], en=sample['en'], paraphrase_id=paraphrase.id)
                db.session.add(sample)
            db.session.commit()


if __name__ == '__main__':
    dicts = Dicts()
    print (dicts.executor('mean'))
