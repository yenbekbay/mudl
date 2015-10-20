#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of mudl.
# Copyright (C) 2015 Ayan Yenbekbay
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

from future import standard_library
from future.utils import PY3
standard_library.install_aliases()

import http.cookiejar
import urllib.request
import urllib.error
import urllib.parse
from urllib.parse import urlparse
from html.parser import HTMLParser
if PY3:
    request = urllib.request
else:
    import urllib2
    request = urllib2

class FormParser(HTMLParser):
    """
    Parsing forms
    """
    def __init__(self):
        HTMLParser.__init__(self)
        self.url = None
        self.params = {}
        self.in_form = False
        self.form_parsed = False
        self.method = 'GET'

    def handle_starttag(self, tag, attrs):
        """
        First form.
        :param tag: name of the form
        :param attrs: names and values
        """
        tag = tag.lower()
        if tag == 'form':
            if self.form_parsed:
                raise RuntimeError('Second form on page')
            if self.in_form:
                raise RuntimeError('Already in form')
            self.in_form = True
        if not self.in_form:
            return
        attrs = {name.lower(): value for name, value in attrs}
        if tag == 'form':
            self.url = attrs['action']
            if 'method' in attrs:
                self.method = attrs['method'].upper()
        elif tag == 'input' and 'type' in attrs and 'name' in attrs:
            if attrs['type'] in ['hidden', 'text', 'password']:
                self.params[attrs['name']] = attrs['value'] if 'value' in attrs else ''

    def handle_endtag(self, tag):
        """
        Last form.
        :param tag: name of the form
        """
        tag = tag.lower()
        if tag == 'form':
            if not self.in_form:
                raise RuntimeError('Unexpected end of <form>')
            self.in_form = False
            self.form_parsed = True


class VKAuth(object):
    """
    Getting access_token for VK.com
    """
    def __init__(self, email, password, client_id, scope):
        self.email = email
        self.password = password
        self.client_id = client_id
        if not isinstance(scope, list):
            scope = [scope]
        self.scope = scope
        self.opener = request.build_opener(
            request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
            request.HTTPRedirectHandler())
        self.doc, self.url = self.auth_user()

    def __call__(self):
        if urlparse(self.url).path != '/blank.html':
            # Need to give access to requested scope
            self.url = VKAuth.give_access(self.doc, self.opener)
        if urlparse(self.url).path != '/blank.html':
            raise RuntimeError('Expected success here')
        answer = dict(self.split_key_value(kv_pair) for kv_pair in urlparse(self.url)\
            .fragment.split('&'))
        if 'access_token' not in answer or 'user_id' not in answer:
            raise RuntimeError('Missing some values in answer')
        return answer['access_token'], answer['user_id']

    @classmethod
    def split_key_value(cls, kv_pair):
        """
        Splitting key-value pair (needed for urlbar parsing)
        :param kv_pair: 'attr=value' string
        :return: (attr, value)
        """
        kv = kv_pair.split('=')
        return kv[0], kv[1]

    # Authorization form
    def auth_user(self):
        """
        :return: access_token and ID of user
        """
        access_url = 'https://oauth.vk.com/oauth/authorize?redirect_uri=https://oauth.vk.com' +\
            '/blank.html&response_type=token&client_id={}&scope={}&display=wap'\
            .format(self.client_id, ','.join(self.scope))
        response = self.opener.open(access_url)
        doc = response.read()
        parser = FormParser()
        parser.feed(doc.decode('utf-8'))
        parser.close()
        if not parser.form_parsed or parser.url is None or 'pass' not in parser.params or\
            'email' not in parser.params:
            raise RuntimeError('Something wrong')
        parser.params['email'] = self.email
        parser.params['pass'] = self.password
        if parser.method == 'POST':
            if PY3:
                params = bytes(urllib.parse.urlencode(parser.params), encoding='utf-8')
            else:
                params = urllib.parse.urlencode(parser.params)
            response = self.opener.open(parser.url, params)
        else:
            raise NotImplementedError(u'Method "{}"'.format(parser.method))
        return response.read(), response.geturl()

    # Permission request form
    @classmethod
    def give_access(cls, doc, opener):
        """
        Pressing button to give access.
        :param doc: HTML page
        :param opener: urllib opener
        :return: current URL
        """
        parser = FormParser()
        parser.feed(doc.decode('utf-8'))
        parser.close()
        if not parser.form_parsed or parser.url is None:
            raise RuntimeError('Something wrong')
        if parser.method == 'POST':
            if PY3:
                params = bytes(urllib.parse.urlencode(parser.params), encoding='utf-8')
            else:
                params = urllib.parse.urlencode(parser.params)
            response = opener.open(parser.url, params)
        else:
            raise NotImplementedError(u'Method "{}"'.format(parser.method))
        return response.geturl()
