# -*- coding: utf-8 -*-
from dictionary import *

oxford = Dicts(source=OXFORD8)
collinyh = Dicts(source=COLLINYH)
yhdcd = Dicts(source=YHDCD)
lodce = Dicts(source=LODCE)
sjdnyhhysjcd = Dicts(source=SJDNYHHYSJCD)
jqgjyhsjcd = Dicts(source=JQGJYHSJCD)


if __name__ == '__main__':
    print OXFORD8
    oxford.set_phrase('china')
    print oxford.executor()
