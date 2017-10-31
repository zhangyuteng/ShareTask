# coding=utf-8
__author__ = 'zhangyuteng'

OXFORD8 = 'oxford8'  # 牛津高阶英汉双解词典(简体) 第 8 版
COLLINYH = 'collinyh'  # 柯林斯英汉双解大词典
YHDCD = 'yhdcd'  # 英汉大词典（第二版）陆谷孙
LODCE = 'lodce'  # 朗文当代英语大词典(英汉汉英)第4版
SJDNYHHYSJCD = '21sjdnyhhysjcd'  # 21世紀電腦英漢漢英雙向辭典
JQGJYHSJCD = 'jqgjyhsjcd'  # 剑桥高阶英汉双解词典（第3版）

POS_N = 'n'  # 名词
POS_V = 'v'  # 动词
POS_A = 'a'  # 形容词
POS_D = 'd'  # 副词
POS_P = 'p'  # 介词
POS_DET = 'det'  # 限定词
POS_PRON = 'r'  # 代词
POS_QUN = 'q'  # 数量关系词
POS_M = 'm'  # 数量词
POS_ABBR = 'abbr'  # 缩写
POS_SYMBOL = 's'  # 象征
POS_E = 'e'  # 叹词
POS_L = 'l'  # 习用语
POS_PREP = 'prep'  # 柯林斯词典中出现的，不知道什么意思
POS_NONE = ''  # 没有词性

OXFORD8_MDX_FILE = u'/home/zero/tools/GoldenDict/Oxford Dictionary 8/牛津高阶8简体.mdx'  # 牛津高阶英汉双解词典(简体) 第 8 版
COLLINYH_MDX_FILE = u'/home/zero/Downloads/MDict/[英-汉] 柯林斯有道20170106/col.mdx'  # 柯林斯英汉双解大词典
YHDCD_MDX_FILE = u'/home/zero/Downloads/MDict/英汉大词典（第二版）陆谷孙紧凑版/英汉大词典（第二版）陆谷孙.mdx'  # 英汉大词典（第二版）陆谷孙
LODCE_MDX_FILE = u'/home/zero/Downloads/MDict/朗文当代英语大词典(英汉汉英)第4版.mdx'  # 朗文当代英语大词典(英汉汉英)第4版
SJDNYHHYSJCD_MDX_FILE = u'/home/zero/Downloads/MDict/21世紀電腦英漢漢英雙向辭典/21世紀電腦英漢漢英雙向辭典.mdx'  # 21世紀電腦英漢漢英雙向辭典
JQGJYHSJCD_MDX_FILE = U'/home/zero/Downloads/MDict/%5B英-汉%5D+剑桥高阶英汉双解词典（第3版简体版）7.3最后更新.mdx'  # 剑桥高阶英汉双解词典（第3版）

from .dictionary import Dicts
