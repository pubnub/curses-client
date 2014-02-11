=======================
PubNub Curses Client
=======================

The PubNub Curses Client provides easy terminal access to the
PubNub API. It allows you to publish, subscribe, see presence,
and see history right from a terminal window.

PubNub is a globally scaled real-time network. We provide real-time
as a service to developers across the globe. Check out http://pubnub.com
to try it out for free today!

Usage
-----
Simply run the tool from the command line: ::

  pubnub-curses <options>

--help            See the help information
-p, --pubkey      PubNub account publish key (default demo)
-s, --subkey      PubNub account subscribe key (default demo)
-c, --channel     PubNub channel to listen and publish to (default my_channel)
-o, --origin      Origin to publish and subscribe to (default pubsub.pubnub.com)

Contributing
------------
All the source code is on our github page: https://github.com/pubnub/curses-client

Issues and pull requests are welcome!

License
-------

MIT licensed. See the LICENSE file for more deatils: https://github.com/pubnub/curses-client/blob/master/LICENSE
