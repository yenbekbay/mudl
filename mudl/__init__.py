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

from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import input
from builtins import object

from clint import resources
from clint.textui import puts, colored
from collections import defaultdict
from configparser import ConfigParser
from getpass import getpass
from mudl.vk_auth import VKAuth
from mudl.vk_downloader import VKDownloader
import argparse
import os
import re
import socket
import sys

class Arguments(object):
    def __init__(self):
        self.quality = defaultdict(int, high=320, medium=256, low=128)
        self.parser = argparse.ArgumentParser(
            description='Downloads the mp3 file for the given query if the track can be found on ' +
            'VK in the given quality'
        )
        self.parser.add_argument(
            'query', nargs='?', help='The track title to look for (Artist - Title)'
        )
        self.parser.add_argument(
            '-q', '--quality', dest='min_quality', choices=list(self.quality.keys()),
            help='minimum quality for the downloaded track, where high = 320kbps, medium = ' +
            '256kbps, and low = 128kbps (default is high)'
        )
        self.parser.add_argument(
            '--skipmatch', dest='skip_match', action='store_true',
            help='skip matching for track (decreases accuracy)'
        )
        self.parser.add_argument(
            '--configure', dest='configure', action='store_true',
            help='edit the configuration'
        )

    def parse(self, args):
        args = self.parser.parse_args(args)
        return {
            'query': args.query,
            'min_quality': self.quality[args.min_quality],
            'skip_match': args.skip_match,
            'configure': args.configure
        }

    def help(self):
        return self.parser.format_help()


class Configuration(object):
    def __init__(self):
        resources.init('yenbekbay', 'mudl')
        self.config = ConfigParser()
        if not os.path.exists(resources.user.path):
            os.makedirs(resources.user.path)
        self.config_path = os.path.join(resources.user.path, 'config.ini')
        self.config.read(self.config_path)
        if not self.config.has_section('general'):
            self.config.add_section('general')
        self.iterator = 0

    def get(self, key):
        if self.config.has_option('general', key):
            return self.config.get('general', key)
        else:
            return None

    def set(self, key, value):
        self.config.set('general', key, value)

    def save(self):
        with open(self.config_path, 'w') as config_file:
            self.config.write(config_file)

    def configure(self, force=False):
        if not self.get('saving_path') or force:
            self.iterator += 1
            while True:
                saving_path = input('{0}. '.format(self.iterator) + u'Where should files be ' +\
                    u'saved?\nDrag the directory in the window: ').replace('\\', '').strip()
                is_valid = os.path.exists(saving_path)
                if is_valid:
                    self.set('saving_path', saving_path)
                    break
                else:
                    puts(colored.yellow(u'Please enter an existing directory'))
        if not self.get('min_quality') or force:
            self.iterator += 1
            while True:
                min_quality = input('{0}. '.format(self.iterator) + u'What minimum quality do ' +\
                    u'you want your music files to be?\nSelect from 320, 256, or 128 or return ' +\
                    u'to keep 320: ')
                if not min_quality:
                    self.set('min_quality', '320')
                    break
                elif min_quality in ('320', '256', '128'):
                    self.set('min_quality', min_quality)
                    break
                else:
                    puts(colored.yellow(u'Please choose from these: 320, 256, 128'))
        if not self.get('skip_match') or force:
            self.iterator += 1
            while True:
                skip_match = input('{0}. '.format(self.iterator) + u'Do you want to skip ' +\
                    u'matching by default?\nEnter "yes" or return to keep matching: ')
                if len(skip_match) > 0:
                    if skip_match == 'yes':
                        self.set('skip_match', 'true')
                        break
                    else:
                        puts(colored.yellow(u'Please enter "yes" or return'))
                else:
                    self.set('skip_match', 'false')
                    break
        self.saving_path = self.get('saving_path')
        self.min_quality = int(self.get('min_quality'))
        self.skip_match = self.get('skip_match') == 'true'
        self.save()

    def connect(self):
        if self.get('vk_email') and self.get('vk_password'):
            is_valid_ip = False
            if self.get('last_ip'):
                is_valid_ip = Configuration.getIp() == self.get('last_ip')
            if self.get('auth_token') and self.get('user_id') and is_valid_ip:
                auth_token = self.get('auth_token')
                user_id = self.get('user_id')
            else:
                vk_email = self.get('vk_email')
                vk_password = self.get('vk_password')
                try:
                    auth_token, user_id = VKAuth(vk_email, vk_password, '3607693',\
                        ['offline', 'audio'])()
                    self.set('auth_token', auth_token)
                    self.set('user_id', user_id)
                    self.set('last_ip', Configuration.getIp())
                except (RuntimeError, NotImplementedError) as e:
                    puts(colored.yellow(u'Something went wrong: ' + colored.yellow(e.message)))
                self.save()
        else:
            self.iterator += 1
            puts('{0}. '.format(self.iterator) + u'We need to configure your VK account for ' +\
                u'access to music search')
            while True:
                while True:
                    vk_email = input(u'Please enter your VK email: ')
                    is_valid = re.match(r'[^@]+@[^@]+\.[^@]+', vk_email)
                    if is_valid:
                        break
                    else:
                        puts(colored.yellow(u'Please enter a valid email'))
                vk_password = getpass(u'Please enter your VK password: ')
                self.set('vk_email', vk_email)
                self.set('vk_password', vk_password)
                try:
                    auth_token, user_id = VKAuth(vk_email, vk_password, '3607693',\
                        ['offline', 'audio'])()
                    self.set('auth_token', auth_token)
                    self.set('user_id', user_id)
                    self.set('last_ip', Configuration.getIp())
                    break
                except (RuntimeError, NotImplementedError) as e:
                    puts(u'Please try again: ' + colored.yellow(e.message))
            self.save()
        return auth_token, user_id

    @classmethod
    def getIp(cls):
        return [l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not\
            ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 80)), s.getsockname()[0],\
            s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]])\
            if l][0][0]


class MusicDownloader(object):
    @classmethod
    def main(cls):
        arguments = Arguments()
        configuration = Configuration()
        args = arguments.parse(sys.argv[1:])
        if args['configure']:
            configuration.configure(True)
            sys.exit(0)
        if not args['query']:
            puts(arguments.help())
            sys.exit(1)
        elif len(args['query'].replace(u'\u2013', '-').split(' - ')) < 2:
            puts(colored.red('Please provide query in format "Artist - Title"'))
            sys.exit(1)
        configuration.configure()
        if not args['min_quality']:
            args['min_quality'] = configuration.min_quality
        if not args['skip_match']:
            args['skip_match'] = configuration.skip_match
        access_token, user_id = configuration.connect()
        vk_downloader = VKDownloader(access_token, user_id)
        vk_downloader.process(args['query'], args['min_quality'], args['skip_match'])

def main():
    try:
        MusicDownloader.main()
    except KeyboardInterrupt:
        puts(u'\nBye')
        sys.exit(0)

if __name__ == '__main__':
    main()
