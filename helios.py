from configparser import NoOptionError, RawConfigParser
from helpers import log
from enum import Enum
from globalvars import GlobalVars
import os
import requests
import blacklists


HeliosEndpoint = {
    'BLACKLISTS': "{}{}".format(GlobalVars.helios_endpoint, "blacklists/"),
    'NOTIFICATIONS': "{}{}".format(GlobalVars.helios_endpoint, "notifications/"),
}


BlacklistType = {
    'WATCH': "watch-keyword",
    'watch_keyword': "watch-keyword",
    'WEBSITE': "blacklist-website",
    'website': "blacklist-website",
    'USERNAME': "blacklist-username",
    'username': "blacklist-username",
    'KEYWORD': "blacklist-keyword",
    'keyword': "blacklist-keyword",
}


class Helios:
    endpoint_blacklist = HeliosEndpoint['BLACKLISTS']
    endpoint_notification = HeliosEndpoint['NOTIFICATIONS']
    key = GlobalVars.helios_key
    write_access = True if GlobalVars.helios_key else False
    if write_access:
        headers = {'Authorization': key}
    else:
        headers = None

    @classmethod
    def add_blacklist(cls, **kwargs):
        """
        Blacklist a specific pattern on a specific list
        """
        blacklist = kwargs.get('blacklist_type', None)
        pattern = kwargs.get('pattern', None)
        requestor = kwargs.get('request_user', None)
        profile_link = kwargs.get('chat_link', None)
        log("info", "Blacklist list: {}".format(blacklist))
        log("info", "Pattern: {}".format(pattern))
# TODO: Add check if exists first

        try:
            if blacklist == "keyword":
                GlobalVars.bad_keywords.append(pattern)
                blacklist_type = blacklists.Blacklist.KEYWORDS
            if blacklist == "username":
                GlobalVars.blacklisted_usernames.append(pattern)
                blacklist_type = blacklists.Blacklist.USERNAMES
            if blacklist == "website":
                GlobalVars.blacklisted_websites.append(pattern)
                blacklist_type = blacklists.Blacklist.WEBSITES
            if blacklist == "watch_keyword":
                GlobalVars.watched_keywords.append(pattern)
                blacklist_type = blacklists.Blacklist.WATCHED_KEYWORDS
        except KeyError:
            # Just checking all bases, but blacklist_file_name *might* have empty value
            # if we don't address it here.
            return (False, "Invalid blacklist type specified, something has broken badly!")
        blacklister = blacklists.Blacklist(blacklist_type)
        if cls.write_access:
            status, response = blacklister.add(pattern, requestor=requestor, chat_link=profile_link)
            return (status, response)
        else:
            return (False, "Helios key is not set. Writing disabled")
