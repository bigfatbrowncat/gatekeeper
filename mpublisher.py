#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# mpublisher.py - Avahi/mDNS name publisher.
#
# Copyright (c) 2014, SAPO
#


from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals
from __future__ import absolute_import

import logging

import dbus
#import exceptions


# If the system-provided library isn't available, use a bundled copy instead.
# Necessary for CentOS 6/7 where there's no available "avahi-python" package.
try:
    import avahi
except ImportError:
    import _avahi as avahi


# From "/usr/include/avahi-common/defs.h"
AVAHI_DNS_CLASS_IN = 0x01
AVAHI_DNS_TYPE_CNAME = 0x05


class AvahiPublisher(object):
    """Publish mDNS records to Avahi, using D-BUS."""

    def __init__(self, record_ttl=60):
        """Initialize the publisher with fixed record TTL value (in seconds)."""

        self.bus = dbus.SystemBus()

        path_server_proxy = self.bus.get_object(avahi.DBUS_NAME, avahi.DBUS_PATH_SERVER)
        self.server = dbus.Interface(path_server_proxy, avahi.DBUS_INTERFACE_SERVER)

        self.hostname = self.server.GetHostNameFqdn()
        self.record_ttl = record_ttl
        self.published = {}

        logging.debug("Avahi mDNS publisher for: %s", self.hostname)


    def __del__(self):
        """Remove all published records from mDNS."""

        try:
            for group in self.published.values():
                group.Reset()
        except dbus.exceptions.DBusException as e:  # ...don't spam on broken connection.
            if e.get_dbus_name() != "org.freedesktop.DBus.Error.ServiceUnknown":
                raise


    def _fqdn_to_rdata(self, fqdn):
        """Convert an FQDN into the mDNS data record format."""

        data = []
        splitted = fqdn.split(".")
        splenc = [ x.encode("ascii") for x in splitted ]
        for part in splenc:
            if part:
                data.append(chr(len(part)))
                data.append(part.decode("ascii"))

        return ("".join(data) + "\0").encode("ascii")


    def count(self):
        """Return the number of records currently being published."""

        return len(self.published)


    def resolve(self, name):
        """Lookup the current owner for "name", using mDNS."""

        try:
            # TODO: Find out if it's possible to manipulate (shorten) the timeout...
            response = self.server.ResolveHostName(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC,
                                                   name.encode("ascii"), avahi.PROTO_UNSPEC,
                                                   dbus.UInt32(0))
            return response[2]  #.decode("ascii")
        except (NameError, dbus.exceptions.DBusException):
            return None


    def publish_cname(self, cname, force=False):
        """Publish a CNAME record."""

        if not force:
            # Unfortunately, this takes a few seconds in the expected case...
            logging.info("Checking for '%s' availability...", cname)
            current_owner = self.resolve(cname)

            if current_owner:
                if current_owner != self.hostname:
                    logging.error("DNS entry '%s' is already owned by '%s'", cname, current_owner)
                    return False

                # We may have discovered ourselves, but this is not a fatal problem...
                logging.warning("DNS entry '%s' is already being published by this machine", cname)

        entry_group_proxy = self.bus.get_object(avahi.DBUS_NAME, self.server.EntryGroupNew())
        group = dbus.Interface(entry_group_proxy, avahi.DBUS_INTERFACE_ENTRY_GROUP)

        logging.info("Adding record")
        group.AddRecord(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC, dbus.UInt32(0), cname.encode("ascii"),
                        AVAHI_DNS_CLASS_IN, AVAHI_DNS_TYPE_CNAME, self.record_ttl,
                        self._fqdn_to_rdata(self.hostname))

        group.Commit()
        self.published[cname] = group

        return True


    def publish_address(self, cname, address, force):
        """Publish a CNAME record."""

        if not force:
            # Unfortunately, this takes a few seconds in the expected case...
            logging.info("Checking for '%s' availability...", cname)
            current_owner = self.resolve(cname)

            if current_owner:
                if current_owner != self.hostname:
                    logging.error("DNS entry '%s' is already owned by '%s'", cname, current_owner)
                    return False

                # We may have discovered ourselves, but this is not a fatal problem...
                logging.warning("DNS entry '%s' is already being published by this machine", cname)

        entry_group_proxy = self.bus.get_object(avahi.DBUS_NAME, self.server.EntryGroupNew())
        group = dbus.Interface(entry_group_proxy, avahi.DBUS_INTERFACE_ENTRY_GROUP)

        # avahi_entry_group_add_address(entry_group, AVAHI_IF_UNSPEC, AVAHI_PROTO_UNSPEC, config->no_reverse ? AVAHI_PUBLISH_NO_REVERSE : 0, config->name, &config->address

        no_reverse = True
        flags = avahi.PUBLISH_NO_REVERSE if no_reverse else 0
        #address = "192.168.1.104"

        logging.info("Adding name %s to address %s", cname, address)
        group.AddAddress(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC, dbus.UInt32(flags), cname.encode("ascii"), address.encode("ascii"))

        group.Commit()
        self.published[cname] = group

        return True


    def unpublish(self, name):
        """Remove a published record from mDNS."""

        self.published[name].Reset()
        del self.published[name]


    def available(self):
        """Check if the connection to Avahi is still available."""

        try:
            # This is just a dummy call to test the connection...
            self.server.GetVersionString()
        except dbus.exceptions.DBusException as e:
            if e.get_dbus_name() != "org.freedesktop.DBus.Error.ServiceUnknown":
                raise

            return False

        return True


# vim: set expandtab ts=4 sw=4:
