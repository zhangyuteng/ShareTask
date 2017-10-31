# -*- coding: utf-8 -*-
import bs4
import re
from app.main.dictionary import POS_N, POS_A, POS_D, POS_V, POS_P, POS_DET, POS_NONE, POS_PRON, POS_QUN, POS_M, \
    POS_SYMBOL, POS_ABBR, POS_E, POS_L, POS_PREP
from pprint import pprint
import difflib

REspace = re.compile(ur'\s{2,}')
REchinese = re.compile(ur'[\u4e00-\u9fa5]+')


def deal_text(text):
    """
    处理从网页中获取的字符串，去掉收尾的空格，去掉中间多余的空格
    :param text:
    :return:
    """
    return REspace.sub(u' ', text.strip())


def oxford8parser(html):
    """
    牛津词典解析器
    :param html:
    :return:
    """
    result = []
    soup = bs4.BeautifulSoup(html, 'html.parser')
    pgs = soup.find_all(class_="p-g")
    if len(pgs) == 0:
        hg = soup.find(class_="h-g")
        if hg is None:
            return result
        pgs = [hg]
        # 检查是否为等价词
        ng = pgs[0].find_all(class_='n-g')
        defg = pgs[0].find(class_='def-g')
        if len(ng) == 0:
            if defg is not None:
                # 根据 thou 添加的规则
                en = ''
                ch = ''
                for i in defg.span.contents:
                    if isinstance(i, bs4.element.NavigableString):
                        en += i.strip() + ' '
                    elif isinstance(i, bs4.element.Tag):
                        if i.has_attr('class') and 'chn' in i.get('class'):
                            ch += i.text.strip() + ' '
                return [{'pos': '', 'mean': {'en': en, 'ch': ch}, 'samples': []}]
            elif pgs[0].find(class_='Ref'):
                a = pgs[0].find_all('a', href=re.compile(ur'entry://.*'))
                if len(a) == 1:
                    # assert len(a) == 1, 'len(a) must be 1'
                    redirect = a[0].text.strip()
                    assert redirect, 'redirect is empty!'
                    return redirect
    for pg in pgs:
        pos = pg.find(class_="pos")
        # la 没有词性
        if pos is None:
            return []
        assert pos is not None, 'can\'t find class=pos'
        pos = pos.get('pos')[0]
        assert pos is not None, 'pos tag don\'t have the attr of pos'

        means = []
        ngs = soup.find_all(class_='n-g')
        for ng in ngs:
            # 获取解释
            defg = ng.find(class_='def-g')
            if defg is None:
                # 发现 grand 这个词的有些意思中，没有定义释义
                continue
            # assert defg is not None, 'can\'t find class=def-g'
            d = defg.find(class_='d')
            if not d:
                d = defg.find(class_='ud')
            assert d is not None, 'can\'t find class=d'
            en = u''
            ch = u''
            for con in d.contents:
                if isinstance(con, bs4.element.NavigableString):
                    en += con.strip() + ' '
                elif isinstance(con, bs4.element.Tag):
                    conclass = con.get('class')
                    if 'chn' in conclass:
                        ch += con.text.strip() + ' '
                    else:
                        en += con.text.strip() + ' '
                        # raise ValueError, 'The pattern don\'t seen: ' + str(con)
                else:
                    raise ValueError, 'The pattern don\'t seen: ' + str(con)
            en = en.strip()
            ch = ch.strip()
            # 获取例句
            samples = []
            xgs = ng.find_all(class_='x-g')
            # 发现有的意思没有例句
            # assert len(xgs) > 0 and isinstance(xgs, list), 'cant find class=x-g'
            if len(xgs) > 0:
                for xg in xgs:
                    x = xg.find(class_='x')
                    if x is None:
                        x = xg.find(class_='unx').contents[0]
                        assert x is not None, 'cant find class=x'
                        x = x.strip()
                    else:
                        x = x.text.strip()
                    tx = xg.find(class_='tx')
                    # 发现 thousand 这个词的例句中，有的没有中文
                    # assert tx is not None, 'cant find class=tx'
                    if tx:
                        tx = tx.text.strip()
                    else:
                        tx = ''
                    assert tx is not None, 'cant find class=tx'
                    samples.append({'en': x, 'ch': tx})
            # TODO: 获取label
            # because it is not important
            # labelg = defg.find(class_='label-g')
            # if labelg:
            #     pass
            #     means[-1]['label'] = label
            result.append({'pos': pos, 'mean': {'en': en, 'ch': ch}, 'samples': samples})

    return result


# 柯林斯英汉双解大词典 词性映射为规范格式
collinsPOS = {
    'N-UNCOUNT': POS_N,
    'N-COUNT-COLL': POS_N,
    'N-COUNT': POS_N,
    'N-SING': POS_N,
    'N-VAR': POS_N,
    'N': POS_N,
    'N-PLURAL': POS_N,
    'NUM': POS_M,
    'PHRASE': POS_N,
    'V-T': POS_V,
    'V': POS_V,
    'ADJ': POS_A,
    'DET': POS_DET,
    'QUANT': POS_QUN,
    'QUANT-PLURAL': POS_QUN,
    'PRON': POS_PRON,
    'SYMBOL for': POS_SYMBOL,
    'ABBREVIATION for': POS_ABBR,
    'PRON-SING': POS_PRON,
    'ADV': POS_D,
    'INTERJ': POS_E,
    'the INTERNET DOMAIN NAME for': POS_N,
    'PREP': POS_PREP,
}


def collinsyhparser(html):
    result = []
    soup = bs4.BeautifulSoup(html, 'html.parser')
    ols = soup.find_all(class_="ol")
    # assert len(ols) > 0, "can't find class=ol"
    if not ols:
        ul = soup.find('ul', class_='ul')
        if ul is not None:
            ols = [ul]
        else:
            a = soup.find_all('a', href=re.compile(ur'entry://.*'))
            # Mv 没有任何释义
            # assert len(a) >= 1, 'number of a must be greater than 1'
            if len(a) == 1:
                redirect = a[0].text.strip()
                assert redirect, 'cant find redirect'
            elif len(a) > 1:
                # 参考单词aging  see age, ageing
                # 选择相似度最高的那个词
                title = soup.find(class_='title').text.strip()
                redirect = ''
                max_ratio = 0
                for i in a:
                    w = i.text.strip()
                    seq = difflib.SequenceMatcher(None, title, w)
                    if seq.ratio() >  max_ratio:
                        max_ratio = seq.ratio()
                        redirect = w
            else:
                # Mv 没有任何释义
                return []
            return redirect

    for ol in ols:
        lis = ol.find_all('li')
        assert len(lis) > 0, "length of lis is 0!"
        for li in lis:
            # 检查是否有释义，如果没有就舍弃
            collinsMajorTrans = li.find(class_='collinsMajorTrans')
            if collinsMajorTrans is None:
                continue
            additional = collinsMajorTrans.find(class_="additional")
            if additional is None:
                continue
            pos = ""
            mean = ""
            samples = []
            # 获取释义和词性
            p = collinsMajorTrans.p
            assert p is not None, "cant find p tag"
            for item in p.contents:
                if isinstance(item, bs4.element.Tag):
                    if item.has_attr('class') and 'additional' in item.get('class'):
                        # get POS
                        text = item.text.strip()
                        if text.startswith('[') and text.endswith(']'):
                            continue
                        assert pos == '', '发现多个词性 {}'.format(text)
                        pos = collinsPOS.get(text)
                        if pos is None:
                            pos = text
                        # assert pos is not None, "'{}' is not in collisPOS.".format(text)
                    else:
                        mean += item.text.strip() + " "
                elif isinstance(item, bs4.element.NavigableString):
                    item = REspace.sub(u' ', item.strip())
                    if item:
                        mean += item.strip() + " "
                else:
                    raise TypeError, "the type of item is {}".format(type(item))
            # 发现，有的释义没有词性，比如 C 单词的释义
            # assert pos.strip() != '', "cant find pos"
            # 发现 pill 中有的释义，只有词性，没有解释
            if mean.strip() == '':
                continue
            # assert mean.strip() != '', "cant find meam"
            # 将mean的中文和英文拆分
            if mean.count(u'.') == 1:
                en, ch = mean.split('.')
                en = en.strip() + '.'
                ch = ch.strip()
            elif mean.count(u'.') > 1:
                index = mean.rfind(u'.') + 1
                en = mean[:index]
                ch = mean[index:]
            elif mean.count(u'etc ') == 1:
                en, ch = mean.split('etc ')
                en = en.strip() + ' etc.'
                ch = ch.strip()
            else:
                print u'柯林斯词典中未发现英文释义, {}'.format(mean)
                en = ''
                ch = mean
            mean = {'en': en, 'ch': ch}
            # 获取例句
            examples = li.find_all(class_="examples")
            if len(examples) != 0:
                for example in examples:
                    ps = example.find_all('p')
                    assert len(ps) == 2, 'example is not format'
                    en = ps[0].text.strip()
                    assert en != '', 'cant find example en'
                    ch = ps[1].text.strip()
                    # 存在没有中文的英文例句
                    # assert ch != '', 'cant find example ch'
                    samples.append({'ch': ch, 'en': en})
            result.append({'pos': pos, 'mean': mean, 'samples': samples})
    return result


# 英汉大词典（第二版）陆谷孙 词性映射为规范格式
yhdcdPOS = {
    'n.': POS_N,
    'vi.': POS_V,
    'vl.': POS_V,
    'vt.': POS_V,
    'a.': POS_A,
    'ad.': POS_A,
    'pron.': POS_PRON,
    'abbr.': POS_ABBR,
    'int.': POS_L,
    'n. & a.': POS_N,
}


def yhdcdparser(html):
    soup = bs4.BeautifulSoup(html, 'html.parser')
    result = []
    pos = ''
    mean = ''
    samples = []
    for tag in soup.contents:
        if not isinstance(tag, bs4.element.Tag):
            continue
        if not tag.has_attr('class'):
            continue
        classs = tag.get('class')
        if classs[0] not in ['tag3', 'table', 'ex', 'ex_c']:
            continue

        if 'tag3' in classs:
            text = tag.text.strip()
            # 发现 shit 有的tag3中没有词性
            if text == '':
                continue
            # assert text != '', 'cant find pos'
            if mean != '':
                result.append({'pos': pos, 'mean': {'ch': mean, 'en': ''}, 'samples': samples})
                mean = ''
                samples = []
            pos = yhdcdPOS.get(text)
            if pos is None:
                pos = text
            # assert pos is not None, '\'{}\' is not in yhdcdPOS'.format(text)
            continue
        if 'table' in classs:
            if mean != '':
                result.append({'pos': pos, 'mean': {'ch': mean, 'en': ''}, 'samples': samples})
                mean = ''
                samples = []
            for i in tag.contents:
                if isinstance(i, bs4.element.NavigableString):
                    text = i.strip()
                    if text != '':
                        mean += text + ' '
            mean = mean.strip()
            continue
        if 'ex' in classs:
            samples.append({'en': tag.text.strip()})
            continue
        if 'ex_c' in classs:
            samples[-1]['ch'] = tag.text.strip()
            continue
    # 保存最后一个的结果
    if not mean:
        start = False
        for tag in soup.contents:
            if isinstance(tag, bs4.element.Tag):
                if tag.has_attr('class'):
                    if 'tag4' in tag.get('class'):
                        start = True
                        pos = POS_N
                        mean += deal_text(tag.text)
            if isinstance(tag, bs4.element.NavigableString) and start:
                mean += deal_text(tag)
    if not mean:
        # lauryl alcohol
        start = False
        for tag in soup.contents:
            if isinstance(tag, bs4.element.Tag):
                if tag.has_attr('class'):
                    if 'tag2' in tag.get('class'):
                        start = True
                        pos = POS_N
                        mean += deal_text(tag.text)
            if isinstance(tag, bs4.element.NavigableString) and start:
                mean += deal_text(tag)
    if len(result) == 0:
        # 此时如果还没有得到释义，可能是有需要调整的释义
        a = soup.find_all(text=re.compile(ur'='))
        if len(a) == 1:
            redirect = a[0].replace(u'=', '').strip()
            # apartment house 没有跳转
            # assert redirect, 'redirect is empyt!'
            if redirect:
                return redirect
    if mean:
        result.append({'pos': pos, 'mean': {'ch': mean, 'en': ''}, 'samples': samples})
    return result


get_en = False
# 英汉大词典（第二版）陆谷孙 词性映射为规范格式
lodcePOS = {
    'verb': POS_V,
    'number': POS_M,
    'adjective': POS_A,
    'noun': POS_N,
    'pronoun': POS_PRON,
    'determiner': POS_DET,
    'number & noun': POS_N,
    'adverb': POS_D,
}


def lodcepaser(html):
    result = []
    soup = bs4.BeautifulSoup(html, 'html.parser')

    def is_useful(tag):
        global get_en
        if tag.name not in ['span', 'font']:
            return False
        tag_hase_color = tag.attrs.has_key('color')
        tag_hase_style = tag.attrs.has_key('style')
        if tag_hase_color and tag_hase_style:
            return False
        elif tag_hase_color:
            color = tag.get('color')
            if color == u'#008080':
                get_en = True
                return True
            elif color == u'navy':
                return True
            else:
                return False
        elif tag_hase_style:
            style = tag.get('style')
            if get_en == True and style == u'color:grey;':
                get_en = False
                return True
            elif style == u'display:block;background-color:#FAF187;':
                get_en = False
                return True
            else:
                return False

        if tag.attrs == {}:
            return True
        return False

    tags = soup.find_all(is_useful, recursive=False)
    pos = ''
    mean = {'en': '', 'ch': ''}
    samples = []
    get_en = False
    for i in tags:
        if i.name == 'span':
            text = i.text.strip()
            # alderman 没有词性
            # assert text != '', "cant find text of pos"
            # 将当前释义的结果保存
            if mean['ch']:
                result.append({'pos': pos, 'mean': mean, 'samples': samples})
                mean = {'en': '', 'ch': ''}
                samples = []
            pos = lodcePOS.get(text)
            if pos is None:
                pos = text
            # assert pos is not None, '\'{}\' is not in lodcePOS'.format(text)
        if i.attrs == {}:
            # 将当前释义的结果保存
            if mean['ch']:
                result.append({'pos': pos, 'mean': mean, 'samples': samples})
                mean = {'en': '', 'ch': ''}
                samples = []
            mean['en'] = i.text.strip()
            # 柯林斯词典中，有的释义没有英文解释
            # assert mean['en'] != '', 'mean.en is empyt'
        if i.has_attr('color'):
            color = i.get('color')
            if color == u'navy':
                # assert mean['en'] != '', 'mean.en must have value'
                mean['ch'] = i.text.strip().replace(u'&nbsp;', '')
                assert mean['ch'] != '', 'mean.ch is empyt'
            elif color == u'#008080':
                samples.append({'en': i.text.strip().replace(u'&nbsp;', ''), 'ch': ''})
        if i.has_attr('style'):
            style = i.get('style')
            if style == u'color:grey;':
                assert samples[-1]['en'] != '' and samples[-1]['ch'] == '', u'出现意外错误'
                samples[-1]['ch'] = i.text.strip().replace(u'&nbsp;', '')
    result.append({'pos': pos, 'mean': mean, 'samples': samples})
    return result


def sjdnyhhysjcdpaser(html):
    result = []
    # print html
    return result


def jqgjyhsjcdpaser(html):
    result = []

    return result

