# coding=utf8
import json
import random

import bs4
import urllib
import requests

from contextlib import contextmanager
from . import YOUDAO, ICIBA, HAICI, BING, OXFORD8, LDOCE6

import time

__author__ = "hellflame"


def get_proxy():
    return requests.get("http://127.0.0.1:5010/get/").content


def delete_proxy(proxy):
    requests.get("http://127.0.0.1:5010/delete/?proxy={}".format(proxy))


def user_agent():
    """
    return an User-Agent at random
    :return:
    """
    ua_list = [
        'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101',
        'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.122',
        'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71',
        'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95',
        'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.71',
        'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; QQDownload 732; .NET4.0C; .NET4.0E)',
        'Mozilla/5.0 (Windows NT 5.1; U; en; rv:1.8.1) Gecko/20061208 Firefox/2.0.0 Opera 9.50',
        'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:34.0) Gecko/20100101 Firefox/34.0',
        ]
    return random.choice(ua_list)


def header():
    """
    basic header
    :return:
    """
    return {'User-Agent': user_agent(),
            'Accept': '*/*',
            'Connection': 'keep-alive',
            'Referer': 'http://www.youdao.com/',
            'Accept-Language': 'zh-CN,zh;q=0.8'}


class Spider(object):
    def __init__(self, lang='eng', timeout=3, source='youdao'):
        self.__timeout = timeout
        if source == YOUDAO:
            self.__html_url = "https://m.youdao.com/dict?le={}&q=".format(lang)
            self.deploy = self.YoudaoDeploy
        elif source == ICIBA:
            self.__html_url = "http://www.iciba.com/"
            self.deploy = self.IcibaDeploy
            # self.__html_url = "http://www.iciba.com/index.php?a=getWordMean&c=search&list=1,3,4,8,9,12,13,15&callback=json&word="
            # self.deploy = self.IcibaAPIDeploy
        elif source == HAICI:
            self.__html_url = "http://dict.cn/"
            self.deploy = self.HaiciDeploy
        elif source == BING:
            self.__html_url = "http://xtk.azurewebsites.net/BingDictService.aspx?Word="
            self.deploy = self.BingDeploy


    @contextmanager
    def soup(self, target_word, use_proxy=True):
        url = self.__html_url + urllib.quote(target_word.replace('/', ''))
        retry_count = 5
        retry_interval = 3
        while retry_count > 0:
            try:
                if use_proxy:
                    proxy = get_proxy()
                    req = requests.get(url, timeout=self.__timeout, headers=header(), proxies={"http": "http://{}".format(proxy)})
                else:
                    req = requests.get(url, timeout=self.__timeout, headers=header())
                if req.status_code == 200:
                    break
                elif req.status_code == 429:
                    # 被封的IP，暂时不删除，只做更换处理
                    continue
                else:
                    continue
            except Exception as e:
                print e
                retry_count -= 1
                if proxy:
                    delete_proxy(proxy)
                time.sleep(retry_interval)
        if retry_count <= 0:
            exit(1)
            # delete_proxy(proxy)
            yield bs4.BeautifulSoup('', 'html.parser')
        else:
            yield bs4.BeautifulSoup(req.content, 'html.parser')

    def YoudaoDeploy(self, word):
        with self.soup(word) as soup:
            match = soup.find(id='ec')
            if match:
                # pronunciation
                pronounces = []
                translate = []
                web_translate = []

                # translation
                if match.find('ul'):
                    _normal_trans = match.find_all('li')
                    for _nt in _normal_trans:
                        translate.append(_nt.text.strip())

                return 0, {
                    'pronounces': pronounces,
                    'translate': translate,
                    'web_translate': web_translate
                }
            else:
                # sentence translate may go here, but I won't use youdao. Better use google translate
                similar = soup.find(class_='error-typo')
                if similar:
                    possibles = []
                    similar = similar.find_all(class_='typo-rel')
                    for s in similar:
                        title = s.find(class_='title')
                        content = s.get_text()
                        if title:
                            title = title.get_text().replace(' ', '').replace('\n', '')
                            content = content.replace(title, '').replace(' ', '').replace('\n', '')
                        else:
                            continue
                        possibles.append({
                            'possible': title,
                            'explain': content
                        })
                    return 1, {
                        'possibles': possibles
                    }
                return None, None

    def IcibaDeploy(self, word):
        with self.soup(word, use_proxy=False) as soup:
            match = soup.find(class_='keyword')
            if match:
                pronounces = []
                translate = []
                web_translate = []

                # pronunciation
                wordbook = soup.find(class_='base-speak')
                if wordbook:
                    [i.strip() for i in wordbook.strings if i.strip()]

                # translation
                _normal_trans = soup.find(class_='in-base').find('ul').find_all('li')
                for _nt in _normal_trans:
                    # type_ = _nt.span.string.strip()
                    # title = ''.join([i.strip() for i in _nt.p.strings if i.strip()])
                    translate.append(''.join(_nt.strings).replace(u'\n', u''))

                # web translation
                # TODO: it is hard

                return 0, {
                    'pronounces': pronounces,
                    'translate': translate,
                    'web_translate': web_translate
                }
            else:
                return None, None

    def IcibaAPIDeploy(self, word):
        with self.soup(word, use_proxy=False) as soup:
            text = soup.text[5:-1]
            match = json.loads(text)
            # errno 没有查到
            if match['errno'] == 0:
                pronounces = []
                try:
                    translate = [i['part'] + ';'.join(i['means']) for i in match['baesInfo']['symbols'][0]['parts']]
                except Exception as e:
                    print e
                    print match
                    exit(1)
                web_translate = []
                if 'netmean' in match:
                    web_translate = [i['exp'] for i in match['netmean']['PerfectNetExp']]
                if 'ph_en' in match['baesInfo']['symbols'][0] and match['baesInfo']['symbols'][0]['ph_en']:
                    pronounces.append(match['baesInfo']['symbols'][0]['ph_en'])
                if 'ph_am' in match['baesInfo']['symbols'][0] and match['baesInfo']['symbols'][0]['ph_am']:
                    pronounces.append(match['baesInfo']['symbols'][0]['ph_am'])

                return 0, {
                    'pronounces': pronounces,
                    'translate': translate,
                    'web_translate': web_translate
                }
            else:
                return None, None

    def HaiciDeploy(self, word):
        with self.soup(word, use_proxy=False) as soup:
            match = soup.find(class_='dict-basic-ul')
            if match:
                # pronunciation
                pronounces = []
                translate = []
                web_translate = []

                # pronunciation
                # TODO: it is not use

                # translation
                _normal_trans = match.find_all('li')
                for _nt in _normal_trans:
                    # type_ = _nt.span.string.strip()
                    # title = ''.join([i.strip() for i in _nt.p.strings if i.strip()])
                    if _nt.script == None:
                        translate.append(''.join(_nt.strings).replace(u'\n', u''))

                # web translation
                # TODO: it is hard

                return 0, {
                    'pronounces': pronounces,
                    'translate': translate,
                    'web_translate': web_translate
                }
            else:
                # 查找翻译
                basic = soup.find(class_="basic")
                if basic:
                    # pronunciation
                    pronounces = []
                    translate = []
                    web_translate = []
                    translate.append(soup.find(class_='basic').find('strong').text.strip())
                    return 0, {
                        'pronounces': pronounces,
                        'translate': translate,
                        'web_translate': web_translate
                    }
                return None, None

    def BingDeploy(self, word):
        with self.soup(word, use_proxy=False) as soup:
            text = str(soup)
            if text.find('xJonathan@outlook.com') != -1:
                return None, None
            soup = json.loads(text)
            if soup['defs']:
                pronounces = []
                translate = [i['pos'] + i['def'] for i in soup['defs']]
                web_translate = []

                return 0, {
                    'pronounces': pronounces,
                    'translate': translate,
                    'web_translate': web_translate
                }
            else:
                return None, None



if __name__ == '__main__':
    # print Spider(source='youdao').deploy('William Faulkner')
    print Spider(source='iciba').deploy('Den Haag')
    # print Spider(source='haici').deploy('William Faulkner')
    # print Spider(source='bing').deploy('William Faulkner')
