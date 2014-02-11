#!/usr/bin/env python

from distutils.core import setup

setup(
  name='pubnub_curses',
  version='1.2',
  description='PubNub Curses Terminal Client',
  long_description=read('README.rst'),
  license=read('LICENSE'),
  author='Dan Ristic',
  author_email='danr@pubnub.com',
  url='http://pubnub.com',
  packages=['pubnub_curses'],
  scripts=['bin/pubnub-curses']
)