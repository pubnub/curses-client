#!/usr/bin/env python

from distutils.core import setup

setup(
  name='pubnub_curses',
  version='1.1',
  description='PubNub Curses Terminal Client',
  long_description=open('README.txt').read(),
  author='Dan Ristic',
  author_email='danr@pubnub.com',
  url='http://pubnub.com',
  packages=['pubnub_curses'],
  scripts=['bin/pubnub-curses']
)