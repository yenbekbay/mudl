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

from __future__ import division
from future import standard_library
from future.utils import PY3
standard_library.install_aliases()
from builtins import input
from builtins import str
from builtins import range
from past.builtins import basestring
from past.utils import old_div
from builtins import object

from clint.textui import puts, colored
from clint import resources
from configparser import ConfigParser
from difflib import SequenceMatcher
from mutagen.id3 import ID3, TPE1, TIT2, APIC, TDRC, TRCK, TALB
from mutagen.mp3 import MP3
from urllib.parse import urlparse
from furl import furl
import http.client
if PY3:
    import html
    parser = html
else:
    from HTMLParser import HTMLParser
    parser = HTMLParser()
import json
import musicbrainzngs
import os
import re
import soundcloud
import sys
import time
import urllib.request, urllib.error, urllib.parse

class TrackQuery(object):
    def __init__(self, query):
        self.raw_query = query
        self.is_remix = (any(x in query.lower() for x in ('remix', 'mix', 'edit', 'mash')) and\
            not any(x in query.lower() for x in ('(original', '(extended', '(radio', '(dub')))
        self.components = [comp.strip() for comp in query.replace(u'\u2013', '-').split(' - ')]
        self.raw_artist = self.components[0]
        self.raw_title = self.components[1]
        self.title, self.feat = self.process_title()
        self.artist = self.process_artist()
        self.clean_query = ' '.join(u'{0} - {1}'.format(self.artist.strip(),\
            self.title.strip()).split())
        self.bare_query = ' '.join(u'{0} - {1}'.format(self.bare_artist().strip(),\
            self.bare_title().strip()).split()).lower()

    def process_artist(self):
        artist = TrackQuery.make_replacements(self.raw_artist)
        if ':' in artist:
            lindex = artist.find(':')
            artist = artist[lindex+1:].strip()
        if self.feat:
            artist += u' {0}'.format(self.feat)
        return artist

    def process_title(self):
        title = TrackQuery.make_replacements(self.raw_title)
        feat = None
        # Lowercase each word except the first in title if it is not in English.
        if not TrackQuery.is_english(title):
            words = title.split()
            for i in range(len(words)):
                if i != 0:
                    words[i] = words[i].lower()
            title = ' '.join(words)
        if any(x in title for x in (' feat.', '(feat.')):
            if '(feat.' in title:
                lindex = title.find('(feat.')
                rindex = title.find(')', lindex)
                feat = title[lindex+1:rindex].rstrip()
            else:
                lindex = title.find('feat.')
                rindex = title.find('(', lindex)
                if rindex == -1:
                    feat = title[lindex:].rstrip()
                else:
                    feat = title[lindex:rindex].rstrip()
            if rindex == -1:
                title = title[0:lindex]
            else:
                if title[lindex-1] == ' ':
                    lindex -= 1
                if rindex != -1 and rindex < len(title) - 1:
                    if title[rindex+1] == ' ':
                        rindex += 1
                title = title[0:lindex] + ' ' + title[rindex+1:]
        # Check the insides of all parentheses in the string.
        for a in re.compile(r'\([^()]*\)').findall(title):
            if not any(b in a.lower() for b in ('mix', 'remix', 'bootleg', 'edit', 'remake',\
                'cover', 'mash')):
                title = title.replace(a, '') # Remove redundant information.
            else:
                # Capitalize words inside parentheses.
                c = a.split('(', 1)[1].split(')')[0]
                if c:
                    title = title.replace(c, re.sub(r'(^|\s)(\S)', lambda x: x.group(1) +\
                        x.group(2).upper(), c))
        if ')' in title:
            index = title.rfind(')')
            title = title[:index+1]
        if 'www' in title.lower():
            index = title.lower().find('www')
            title = title[:index]
        title = title.strip()
        return title, feat

    def bare_artist(self):
        artist = self.artist
        if 'feat.' in artist:
            index = artist.find('feat')
            artist = artist[0:index-1]
        return TrackQuery.remove_separators(artist)

    def bare_title(self):
        title = self.title
        if any(x in title for x in ('(Original Mix)', '(Original Edit)', '(Dub mix)',\
            '(Radio mix)', '(Radio Edit)')):
            index = title.find('(')
            title = title[:index].strip()
        elif any(x in title for x in ('Remix', 'Mix', 'Mashup', 'Edit')):
            title = re.sub(r' (Remix|Mix|Mashup|Edit)', '', title)
        return TrackQuery.remove_separators(title)

    def albumize(self):
        title = self.title
        index = title.find('(')
        if index != -1:
            title = title[:index].strip()
        return title

    @classmethod
    def remove_separators(cls, s):
        return ' '.join(re.sub(r'(,|\.|&|/)', '', s).split())

    @classmethod
    def make_replacements(cls, s):
        s = s.replace('[', '(').replace(']', ')').replace('/', ' & ')
        s = re.sub(r'(^|\s)(\S)', lambda x: x.group(1) + x.group(2).upper(), s)
        s = re.sub(r'[Ff](eat|t)(uring |\. |\s)', 'feat. ', s)
        s = re.sub(r'(V|v)(ersus|s)\.?', ' vs. ', s)
        s = re.sub(r' (A|a)nd ', ' & ', s)
        s = re.sub(r'(D|d)j ', 'DJ ', s)
        s = re.sub(r'(R|r)(emix|mx)', 'Remix', s)
        s = re.sub(r'(M|m)ash(up)?\)', 'Mashup)', s)
        return s

    @classmethod
    def is_english(cls, s):
        try:
            s.encode('ascii')
        except UnicodeEncodeError:
            return False
        return True


class TrackInfo(object):
    def __init__(self, title, artist=None, source=None, duration=None, year=None, cover=None,\
        release=None, number=None):
        self.title = title
        self.artist = artist
        self.source = source
        self.duration = duration
        self.year = year
        self.cover = cover
        self.release = release
        self.number = number


class VKDownloader(object):
    def __init__(self, access_token, user_id):
        self.access_token = access_token
        self.user_id = user_id
        config = ConfigParser()
        config.read(os.path.join(resources.user.path, 'config.ini'))
        self.saving_path = config.get('general', 'saving_path')
        self.user_query = None
        self.track_feat = None
        self.match = None
        self.match_query = None

    def process(self, query, quality, skip_match):
        """
        Reads the given query, looks for matches and downloads the track to the given path if
        found in VK database.
        """
        self.user_query = TrackQuery(query)
        if not skip_match:
            self.match = self.get_match()
            if self.match:
                self.match_query = TrackQuery(u'{0} - {1}'.format(self.match.artist,\
                    self.match.title))
                search_query = self.match_query
            else:
                search_query = self.user_query
        else:
            search_query = self.user_query
        puts(u'Fetching results from VK music library')
        url = furl('https://api.vk.com/method/audio.search').add({
            'uids': str(self.user_id),
            'q': search_query.bare_query,
            'access_token': self.access_token
        }).url
        results = self.prepare_results(Helpers.open_url(url).read())
        sorted_results = self.sort_results(results, quality)
        self.download(sorted_results)

    def get_match(self):
        """
        Looks for matches in MusicBrainz and Soundcloud databases.
        If found any, compares them by similarity to the query and duration.
        Returns the best match.
        """
        puts(u'Looking for a match')
        matches = []
        # Search for matches on MusicBrainz.
        matches.extend(self.search_mb())
        matches = VKDownloader.filter_by_cover(self.sort_matches(matches))
        self.track_feat = self.get_feat(matches)
        if not matches or not matches[0].cover:
            # Search for matches on Soundcloud.
            matches.extend(self.search_soundcloud())
            matches = VKDownloader.filter_by_cover(self.sort_matches(matches))
            if self.track_feat == None:
                self.track_feat = self.get_feat(matches)
        # Find the longest match if not looking for a radio edit.
        if 'radio' not in self.user_query.title:
            matches.sort(key=lambda x: x.duration, reverse=True)
        if matches:
            puts(u'Match from {0}: {1} - {2} ({3})'.format(matches[0].source, matches[0].artist,\
                matches[0].title, Helpers.duration_string(matches[0].duration)))
            return matches[0]
        else:
            puts(colored.yellow(u'No match found'))
            return None

    def sort_matches(self, matches):
        """
        Sorts matches by similarity to the query.
        """
        for match in matches:
            match_query = TrackQuery(u'{0} - {1}'.format(match.artist, match.title))
            if self.user_query.bare_artist() in match_query.bare_artist():
                artist_ratio = 1.0
            else:
                artist_ratio = SequenceMatcher(None, self.user_query.bare_artist(),\
                    match_query.bare_artist()).ratio()
            title_ratio = SequenceMatcher(None, self.user_query.bare_title(),\
                match_query.bare_title()).ratio()
            match.ratio = round((artist_ratio + title_ratio) * 50, 1)
        matches.sort(key=lambda x: x.ratio, reverse=True)
        # Remove unrelated matches.
        to_remove = []
        for i in range(len(matches)):
            if matches[i].ratio < 92:
                to_remove.append(i)
        to_remove = sorted(to_remove, reverse=True)
        for junk in to_remove:
            matches.pop(junk)
        return matches

    @classmethod
    def filter_by_cover(cls, matches):
        with_cover = []
        for match in matches:
            if match.cover and match.duration:
                with_cover.append(match)
        if with_cover:
            return with_cover
        else:
            return matches

    def download(self, results):
        """
        Downloads the first good result from VK and updates the file's tags.
        """
        if results:
            # Create directory to save to if it doesn't already exist.
            if not os.path.exists(self.saving_path):
                os.makedirs(self.saving_path)
            track_info = results[0]
            if self.match:
                save_query = self.match_query
            else:
                save_query = self.user_query
            url = track_info['url']
            duration = track_info['duration']
            file_size = track_info['aid']
            file_name = save_query.clean_query + '.mp3'
            file_path = os.path.join(self.saving_path, file_name)
            kbps = int(64 * round(old_div(float(file_size * 8 / 1024 / int(duration)), 64)))
            if not os.access(file_path, os.F_OK) or os.stat(file_path).st_size < file_size:
                puts('Downloading: "%s" (%.2fMB, %s, %dkbps)' % (file_name,\
                    file_size / 1024 / 1024, Helpers.duration_string(duration), kbps))
                f = open(file_path, 'wb')
                progress = 0
                size_dl = 0
                block_sz = 8192
                u = Helpers.open_url(url)
                while True:
                    # Make a fancy progress bar.
                    progress = float(size_dl) / file_size * 100
                    if int(progress) % 2 == 0:
                        puts('[{0}{1}] {2}%'.format('#' * int(old_div(progress, 4)), ' ' *\
                            (25 - int(old_div(progress, 4))), int(progress)))
                        if progress != 100:
                            sys.stdout.write('\033[F') # Cursor up one line
                    download_buffer = u.read(block_sz)
                    if not download_buffer:
                        break
                    size_dl += len(download_buffer)
                    f.write(download_buffer)
                f.close()
                self.set_tags(save_query, file_path)
                puts(colored.green('Downloaded {0} successfully'.format(file_name)))
            else:
                puts(colored.yellow('File already exists'))

    def set_tags(self, track_query, file_path):
        """
        Update's the music file's tags using the information from either the match,
        the file itself, or the query.
        """
        audio = MP3(file_path, ID3=ID3)
        # Add ID3 tags if they doesn't exist.
        try:
            audio.add_tags()
        except Exception:
            pass
        audio.tags.update_to_v24() # Update the tags' version
        audio.tags.setall('TPE1', [TPE1(encoding=3, text=track_query.artist)]) # Set artist tag
        audio.tags.setall('TIT2', [TIT2(encoding=3, text=track_query.title)]) # Set title tag
        # Album
        if self.match and self.match.release:
            audio.tags.setall('TALB', [TALB(encoding=3, text=self.match.release)])
        # If the file doesn't have the album tag, just use the cleared title.
        elif not audio.tags.getall('TALB'):
            audio.tags.add(TALB(encoding=3, text=track_query.albumize()))
        # If the album tag is unrelated, replace it.
        elif track_query.albumize() not in audio.tags.getall('TALB')[0].text[0]:
            audio.tags.setall('TALB', [TALB(encoding=3, text=track_query.albumize())])
        else:
            audio.tags.setall('TALB', [TALB(encoding=3,\
                text=audio.tags.getall('TALB')[0].text[0])])
        audio.tags.delall('TPE2') # Clear album artist field
        audio.tags.delall('COMM') # Clear comment field
        audio.tags.delall('USLT') # Clear lyrics field
        audio.tags.delall('TIT1') # Clear grouping field
        audio.tags.delall('TCOM') # Clear composer field
        if self.match and self.match.number:
            # Set track number tag
            audio.tags.setall('TRCK', [TRCK(encoding=3, text=self.match.number)])
        elif not audio.tags.getall('TRCK') or audio.tags.getall('TRCK')[0].text[0] == '1':
            audio.tags.setall('TRCK', [TRCK(encoding=3, text=u'1/1')]) # Set track number tag
        # If the match has cover art, download it and add it to the file.
        if self.match and self.match.cover:
            audio.tags.setall('APIC', [APIC(encoding=3, mime='image/jpeg', type=3, desc=u'Cover',\
                data=Helpers.open_url(self.match.cover).read())]) # Set cover
        # If not year tag was found, set either the match's year or current year.
        if not audio.tags.getall('TDRC'):
            # Set year
            if self.match and self.match.year:
                audio.tags.setall('TDRC', [TDRC(encoding=3, text=str(self.match.year))])
            else:
                audio.tags.setall('TDRC', [TDRC(encoding=3, text=str(time.strftime('%Y')))])
        audio.save()

    def sort_results(self, results, min_kbps):
        """
        Sorts the results from VK by file size, bitrate, duration, and track version.
        """
        sorted_results = results[:]
        if sorted_results:
            total = len(sorted_results)
            correct_duration = None
            if self.match:
                # If not looking for a radio edit, use the match's duration as the correct one.
                if self.match.duration and (self.match.duration > 180 or\
                    any(x in self.match.title for x in ('radio edit', 'radio mix'))):
                    correct_duration = int(self.match.duration)
                    if min_kbps == 320:
                        step = 10
                    elif min_kbps == 256:
                        step = 25
                    else:
                        step = 40
            to_remove = []
            for i in range(total):
                track_info = sorted_results[i]
                duration = track_info['duration']
                name = ' '.join(u'{0} - {1}'.format(track_info['artist'].strip(),\
                    track_info['title'].strip().encode('utf-8')).split())
                size = track_info['aid']
                kbps = int(64 * round(old_div(float(size * 8 / 1024 / int(duration)), 64)))
                # Remove the file from list if it's too big.
                if size > 30000000:
                    to_remove.append(i)
                # Remove the file from list if it has too low quality.
                elif kbps < min_kbps:
                    to_remove.append(i)
                # Remove the file from list if its duration is wrong.
                elif correct_duration != None and min_kbps != 128:
                    if duration < correct_duration - step:
                        to_remove.append(i)
                # Remove the file from list if it's not the right mix.
                elif self.user_query.is_remix and\
                    (not any(x in name.lower() for x in ('mix', 'remix', 'rmx', 'edit', 'mash')) or\
                    any(x in name.lower()  for x in ('(original', '(extended', '(radio', '(dub'))):
                    to_remove.append(i)
                elif not self.user_query.is_remix and\
                    (any(x in name.lower() for x in ('mix', 'remix', 'rmx', 'edit', 'mash')) and\
                    not any(x in name.lower()  for x in ('(original', '(extended', '(radio',\
                    '(dub'))):
                    to_remove.append(i)
                # If this result is good, look no further.
                if i not in to_remove:
                    for k in range(i+1, total):
                        to_remove.append(k)
                    break
            to_remove = sorted(to_remove, reverse=True)
            for junk in to_remove:
                sorted_results.pop(junk)
            if min_kbps == 320 and not sorted_results: # If nothing was found, try lower quality.
                sorted_results = self.sort_results(results, 256)
                if not sorted_results:
                    puts(colored.red(u'Could not find anything for "{0}"'\
                        .format(self.user_query.bare_query)))
                    answer = input(u'Try without restrictions? (y/n) ').lower()
                    if answer == 'y':
                        sorted_results = self.sort_results(results, 192)
                        if not sorted_results:
                            sorted_results = self.sort_results(results, 128)
                            if not sorted_results:
                                puts(colored.red(u'Still nothing for "{0}"'\
                                    .format(self.user_query.bare_query)))
                                self.add_to_wishlist()
                    else:
                        self.add_to_wishlist()
        return sorted_results

    def prepare_results(self, json_data):
        """
        Retrieves the information for results from the list.
        """
        if PY3:
            data = json.loads(json_data.decode())
        else:
            data = json.loads(json_data)
        results = data['response']
        results.pop(0) # Remove first unusable item from the list.
        total = len(results)
        if total > 0:
            for i in range(total):
                puts('Analyzing {0}%'.format(int(float(i+1) / total * 100)))
                if i < total - 1:
                    sys.stdout.write('\033[F') # Cursor up one line
                url = results[i]['url']
                if url:
                    meta = Helpers.open_url(url).info()
                    results[i]['artist'] = parser.unescape(results[i]['artist'])
                    results[i]['title'] = parser.unescape(results[i]['title'])
                    results[i]['aid'] = int(meta.get('Content-Length')) # Set the file size
                else:
                    results[i] = None
        else:
            puts(colored.red('Could not find anything for "{0}"'\
                .format(self.user_query.bare_query)))
            self.add_to_wishlist()
        results = filter(None, results)
        return results

    def search_mb(self):
        musicbrainzngs.set_useragent('music-downloader', '0.1')
        criteria = {
            'artist': self.user_query.bare_artist(),
            'recording': self.user_query.bare_title()
        }
        try:
            recordings = musicbrainzngs.search_recordings(limit=10, **criteria)
            for recording in recordings['recording-list']:
                yield VKDownloader.get_mb_info(recording)
        except Exception as e:
            puts(colored.red(u'Something went wrong with the request: {0}'.format(e)))

    @classmethod
    def get_mb_info(cls, recording):
        track_number = None
        total_number = None
        info = TrackInfo(recording['title'])
        info.source = 'MusicBrainz'
        if recording.get('artist-credit'):
            artist_parts = []
            for el in recording['artist-credit']:
                if isinstance(el, basestring):
                    artist_parts.append(el)
                else:
                    artist_parts.append(el['artist']['name'])
            info.artist = ' '.join(artist_parts)
        if recording.get('length'):
            info.duration = old_div(int(recording['length']), (1000.0))
        if recording.get('release-list'):
            for release in recording.get('release-list'):
                if release.get('id'):
                    info.cover = VKDownloader.get_mb_cover(release['id'])
                if release.get('medium-list'):
                    for medium in release['medium-list']:
                        if medium.get('track-list'):
                            for track_list in medium['track-list']:
                                if track_list.get('number'):
                                    track_number = track_list.get('number')
                        if medium.get('track-count'):
                            total_number = medium.get('track-count')
                        if track_number and total_number:
                            break
                if release.get('title'):
                    info.release = release.get('title')
                if release.get('date'):
                    info.year = int(release.get('date').split('-')[0])
                if track_number and total_number:
                    info.number = u'{0}/{1}'.format(track_number, total_number)
                else:
                    info.number = '1/1'
                break
        return info

    @classmethod
    def get_mb_cover(cls, mbid):
        """
        Make a Cover Art Archive request.
        """
        # Construct the full URL for the request, including hostname and query string.
        path = ['release', mbid, 'front-500']
        url = musicbrainzngs.compat.urlunparse((
            'http',
            'coverartarchive.org',
            '/%s' % '/'.join(path),
            '',
            '',
            ''
        ))
        p = urlparse(url)
        conn = http.client.HTTPConnection(p.netloc)
        conn.request('HEAD', p.path)
        resp = conn.getresponse()
        if resp.status == 307:
            opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler)
            request = opener.open(url)
            return request.url
        else:
            return None

    def search_soundcloud(self):
        """
        Fetches results from Soundcloud for the given query.
        """
        # Create a client object with my app credentials.
        client = soundcloud.Client(client_id='2eaab453dce03a7bca4b475e4132a163')
        # Create a list of TrackInfo objects.
        matches = []
        try:
            # Find all sounds for the given query.
            tracks = client.get('/tracks', q=self.user_query.bare_query)
            # Stop after 10 results.
            if len(tracks) > 10:
                results = 10
            else:
                results = len(tracks)
            for i in range(results):
                words = [comp.strip() for comp in tracks[i].title\
                    .replace(u'\u2013', '-').split(' - ')]
                if len(words) > 1:
                    artist = words[0]
                    title = words[1]
                else:
                    artist = tracks[i].user['username']
                    title = tracks[i].title
                # If the sound has a release date, use it for the year attribute, else use the
                # date the sound was created.
                if tracks[i].release_year:
                    year = tracks[i].release_year
                else:
                    year = tracks[i].created_at.split('/')[0]
                match = TrackInfo(title, artist, 'Soundcloud', old_div(tracks[i].duration, 1000),\
                    year)
                if tracks[i].artwork_url:
                    match.cover = tracks[i].artwork_url.replace('large', 't500x500')
                matches.append(match)
            return matches
        except Exception as e:
            puts(colored.red(u'Something went wrong with the request: {0}'.format(e)))

    def get_feat(self, matches):
        """
        If the track is featuring someone, find out who that is to later add him to the best match.
        """
        for match in matches:
            if 'feat.' in match.artist:
                index = match.artist.find('feat')
                artist = match.artist[0:index-1]
                if artist in self.user_query.artist:
                    return match.artist[index:]
        return None

    def add_to_wishlist(self):
        path = os.path.join(self.saving_path, 'wishlist.txt')
        with open(path, 'a+') as wishlist:
            contents = open(path, 'r').read()
            if not self.user_query.raw_query in contents:
                puts(colored.yellow('Added to wishlist'))
                wishlist.write('\n' + self.user_query.raw_query)


class Helpers(object):
    @classmethod
    def open_url(cls, url):
        start_time = time.time()
        x = 0
        while True:
            delay = round(time.time() - start_time, 2)
            if delay < 10:
                try:
                    u = urllib.request.urlopen(url)
                    return u
                except urllib.error.HTTPError:
                    if x == 3:
                        x = 0
                    x += 1
                    puts('Please wait{0}{1}'.format('.' * x, ' ' * (3-x)))
                    sys.stdout.write('\033[F') # Cursor up one line
                    time.sleep(1)
            else:
                puts('Check your internet connection')
                sys.exit()

    @classmethod
    def duration_string(cls, seconds):
        if seconds:
            m, s = divmod(seconds, 60)
            if m == 0:
                return u'{0}s'.format(int(s))
            else:
                return u'{0}m{1}s'.format(int(m), int(s))
        else:
            return None
