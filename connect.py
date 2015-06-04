#/usr/bin/env python3
"""
Internet connections
"""

from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from parser import SearchParser, GoogleParser, parse_dpage
import os.path as osp
from time import time, mktime, strptime, timezone

def search(what):
    r=Request('http://ex.ua/search?%s' % urlencode([('s', what),
                                                    ('per', 100)]))
    o=urlopen(r)
    sp=SearchParser(o.read().decode())
    del o
    if sp.found:
        return sp.found
    founds = []
    for start in range(0,100, 10):
        url = 'http://www.google.com.ua/search?%s' % \
            urlencode([('hl', 'ok'), ('source', 'hp'), ('ie', 'utf-8'),
                       ('q', '%s site:ex.ua' % what), ('btnG', 'Пошук Google'),
                       ('start', start)])
        r=Request(url)
        r.add_header('User-agent', 'Mozilla/5.0 (X11; Linux x86_64; rv:18.0) Gecko/20100101 Firefox/18.1')
        try:
            o=urlopen(r)
        except Exception:
            print(r.headers)
            print(r.get_full_url())
            print(r.get_host())
            print(r.header_items())
            print(r.__dict__)
        text = o.read().decode()
        sp=GoogleParser(text)
        if not sp.found:
            break
        founds += sp.found
    return founds


def dp_get(index):
    r = Request('http://www.ex.ua' + index)
    o = urlopen(r)
    return parse_dpage(o.read().decode())

    
def load_file(url, outfile, wwp):
    req = Request(url)
    if osp.isfile(outfile):
        res_len = osp.getsize(outfile)
    else:
        res_len = 0
    open_mode = 'wb'
    if res_len > 0:
        req.add_header('Range', 'bytes=%d-' % res_len)
        open_mode = 'ab'
    wwp('Connecting...')
    lwt=time()
    try:
        hdata = urlopen(req)
        cont_len = int(hdata.info().get('Content-Length', 0))
        m_time = mktime(strptime(hdata.info().get('Last-Modified'),
                                  '%a, %d %b %Y %H:%M:%S %Z')) - timezone
    except (HTTPError,) as err:
        if err.code == 416:
            wwp('Nothing to do')
            return
        if err.code < 500 or err.code >= 600:
            raise
    written = 0
    if cont_len == 0:
        return
    start = time()
    block_size = min(1024, cont_len)
    with open(outfile, open_mode) as fo:
        while written < cont_len:
            before = time()
            d_bl = hdata.read(block_size)
            written += len(d_bl)
            if len(d_bl) == 0:
                break
            fo.write(d_bl)
            after = time()
            block_size = best_block_size(after-before, len(d_bl))
            if after - lwt >= 1:
                wwp("%0.2f%%" % (written/cont_len*100,))
                lwt = after
    osp.os.utime(outfile, (time(), m_time))
    return cont_len - written
    # print(hdata.info())


def best_block_size(elapsed_time, bytes):
    new_min = max(bytes / 2.0, 1.0)
    new_max = min(max(bytes * 2.0, 1.0), 4194304) # Do not surpass 4 MB
    if elapsed_time < 0.001:
        return int(new_max)
    rate = bytes / elapsed_time
    if rate > new_max:
        return int(new_max)
    if rate < new_min:
        return int(new_min)
    return int(rate)