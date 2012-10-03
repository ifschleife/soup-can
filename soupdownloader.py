#!/usr/bin/env python
"""
    @package    soup-can
    @file       soupdownloader.py
    @author     Daniel Rahier <daniel@rahier.biz>
"""
import logging
import urllib2
import xml.etree.ElementTree as ET

import soupparser as sp


logging.basicConfig(format='%(name)s : %(message)s', level=logging.INFO)
log = logging.getLogger('soup-can')


def store_meta_data(posts, filename, tree):
    for post in posts:
        r = ET.SubElement(tree.getroot(), 'post',
                          {'id': post.pid, 'type': post.ptype})
        ET.SubElement(r, 'source').text = post.source
        ET.SubElement(r, 'title').text = post.title
        if post.ptype == 'text':
            ET.SubElement(r, 'text').text = post.text
        elif post.ptype in ['image', 'video']:
            ET.SubElement(r, 'url').text = post.url

    # This does not work at all: toprettyxml will return a str not a unicode
    # and even more funny, it will insert newlines into elements that have
    # been made pretty before, in effect blowing up the file with whitespace.
    # Whoever wrote this: great job, really.
    # todo: look into the solution of python3
    #import codecs
    #import xml.dom.minidom as DOM
    #with codecs.open(filename, 'w', encoding='utf-8') as f:
    #    dom = DOM.parseString(ET.tostring(tree.getroot(), encoding='utf-8'))
    #    f.write(dom.toprettyxml(encoding='utf-8'))

    # write unreadeable xml file, but at least encoding works
    log.info('writing meta data to %s' % filename)
    tree.write(filename, encoding='utf-8', xml_declaration=True)


if __name__ == '__main__':

    soupuser = 'captain'
    url = baseurl = 'http://%s.soup.io' % soupuser
    all_posts = list()

    try:
        tree = ET.parse(soupuser + '.xml')
        last_post_id = tree.getroot().find('post').get('id')
    except (IOError, ET.ParseError):
        tree = ET.ElementTree(ET.Element('soup'))
        last_post_id = None

    # start parsing soup html pages
    while True:
        log.info('opening url %s' % url)
        page = urllib2.urlopen(url)
        page = page.read().decode('utf8')
        try:
            p = sp.SoupParser(page, last_post_id)
            if len(p.posts) == 0:
                break ## last page reached
        except sp.LastPostMatch:
            break ## soup parser found last post of xml file

        all_posts.extend(p.posts)
        # create url for next page to parse:
        url = baseurl + '/since/' + p.posts[-1].pid

    store_meta_data(all_posts, soupuser + '.xml', tree)
