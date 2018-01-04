from typing import Union
import regex
from pathlib import Path

from globalvars import GlobalVars
from helpers import log
from helios import HeliosEndpoint, BlacklistType
import requests
import os


def load_blacklists():
    GlobalVars.bad_keywords = Blacklist(Blacklist.KEYWORDS).parse()
    GlobalVars.blacklisted_websites = Blacklist(Blacklist.WEBSITES).parse()
    GlobalVars.blacklisted_usernames = Blacklist(Blacklist.USERNAMES).parse()
    GlobalVars.watched_keywords = Blacklist(Blacklist.WATCHED_KEYWORDS).parse()


class BlacklistParser:
    def __init__(self, filename):
        self._filename = filename

    def parse(self):
        return None

    def add(self, item):
        pass

    def remove(self, item):
        pass

    def exists(self, item):
        pass


class HeliosParser(BlacklistParser):
    def parse(self):
        endpoint = "{}{}".format(HeliosEndpoint['BLACKLISTS'], self._filename)
        response = requests.get(endpoint)
        items = [r for r in response.json()['items']]

        # Check if we have any local failures
        failed_items = []
        filename = "add-{}".format(self._filename)
        error_updating = False
        if Path(filename).is_file():
            log("info", "{} exists. Merging into {} memory".format(filename, self._filename))
            with open(filename, 'r', encoding='utf-8') as f:
                for lineno, line in enumerate(f, 1):
                    if regex.compile('^\s*(?:#|$)').match(line):
                        continue
                    pattern = requestor = profile = None
                    try:
                        pattern, requestor, profile = line.rstrip().split('\t')
                        failed_items.append(pattern)
                    except ValueError as err:
                        log('error', '{0}:{1}:{2}'.format(self._filename, lineno, err))
                        continue

                    if pattern:
                        res = self.add(item=pattern, requestor=requestor, chat_link=profile, force_update=False)
                        if res[0] is False:
                            error_updating = True
                            log("error", "Error occurred while merging previous failures.")
                            log("error", "Error: {}".format(res[1]))
            if not error_updating:
                os.remove(filename)

        return items + failed_items

    def add(self, item: str, **kwargs):
        requestor = kwargs.get('requestor', None)
        chat_link = kwargs.get('chat_link', None)
        force_update = kwargs.get('force_update', True)
        endpoint = "{}{}".format(HeliosEndpoint['BLACKLISTS'], self._filename)
        if GlobalVars.helios_key:
            params = {'pattern': item, 'request_user': requestor, 'chat_link': chat_link}
            response = requests.post(endpoint, json=params, headers={'Authorization': GlobalVars.helios_key})
            pattern = item
            if response.status_code == 403 or response.json()['error_type']:
                log("error", "Error occurred while adding pattern to Helios")
                log("error", "Pattern: {}".format(item))
                log("error", "Response from Helios: {}".format(response.json()))

                # Save our failed record to local error file
                if force_update:
                    filename = "add-{}".format(self._filename)
                    with open(filename, 'a+', encoding='utf-8') as f:
                        log("error", "Saving pattern {} to {}".format(item, self._filename))
                        item = '{}\t{}\t{}'.format(item, requestor, chat_link)
                        last_char = f.read()[-1:]
                        if last_char not in ['', '\n']:
                            item = '\n' + item
                        f.write(item + '\n')

                return (False, "Helios: Problem adding pattern {}.".format(pattern))
            else:
                return (True, "Helios: Successfully added {}".format(pattern))
        else:   # Handle case where a key isn't set
            filename = "add-{}".format(self._filename)
            with open(filename, 'a+', encoding='utf-8') as f:
                log("error", "Saving pattern {} to {}".format(item, self._filename))
                item = '{}\t{}\t{}'.format(item, requestor, chat_link)
                last_char = f.read()[-1:]
                if last_char not in ['', '\n']:
                    item = '\n' + item
                f.write(item + '\n')
            return (True, "Local cache (no Helios key set): Successfully added {}".format(pattern))

    def remove(self, item: str):
        endpoint = "{}{}".format(HeliosEndpoint['BLACKLISTS'], self._filename)
        if GlobalVars.helios_key:
            params = {'pattern': item}
            response = requests.delete(endpoint, json=params, headers={'Authorization': GlobalVars.helios_key})
            log("info", "Response: {}".format(response.json()))
            if response.status_code == 403 or response.json()['error_type']:
                log("error", "Error occurred while deleting pattern from Helios")
                log("error", "Pattern: {}".format(item))
                log("error", "{}".format(response.json()))

                # If we have an error file, check if this pattern is in it
                filename = "add-{}".format(self._filename)
                if Path(filename).is_file():
                    with open(filename, 'r+', encoding='utf-8') as f:
                        items = f.readlines()
                        items = [x for x in items if item not in x]
                        f.seek(0)
                        f.truncate()
                        f.writelines(items)

                filename = "remove-{}".format(self._filename)
                with open(filename, 'r+', encoding='utf-8') as f:
                    items = f.readlines()
                    items = [x for x in items if item not in x]
                    f.seek(0)
                    f.truncate()
                    f.writelines(items)

                return (False, "Helios: Problem deleting pattern {}.".format(item))
            else:
                return (True, "Helios: Successfully removed {}".format(item))
        else:   # Handle case where a key isn't set
            # If we have an error file, check if this pattern is in it
            filename = "add-{}".format(self._filename)
            if Path(filename).is_file():
                with open(filename, 'r+', encoding='utf-8') as f:
                    items = f.readlines()
                    items = [x for x in items if item not in x]
                    f.seek(0)
                    f.truncate()
                    f.writelines(items)

            filename = "remove-{}".format(self._filename)
            with open(filename, 'r+', encoding='utf-8') as f:
                items = f.readlines()
                items = [x for x in items if item not in x]
                f.seek(0)
                f.truncate()
                f.writelines(items)

            return (True, "Local cache (no Helios key set): Successfully removed {}".format(item))

    def exists(self, item: str):
        if self._filename == "watch-keyword":
            return item in GlobalVars.watched_keywords, "Memory Check"
        elif self._filename == "blacklist-website":
            return item in GlobalVars.blacklisted_websites, "Memory Check"
        elif self._filename == "blacklist-username":
            return item in GlobalVars.blacklisted_usernames, "Memory Check"
        elif self._filename == "blacklist-keyword":
            return item in GlobalVars.bad_keywords, "Memory Check"
        else:
            return False, -1


class Blacklist:
    KEYWORDS = (BlacklistType['KEYWORD'], HeliosParser)
    WEBSITES = (BlacklistType['WEBSITE'], HeliosParser)
    USERNAMES = (BlacklistType['USERNAME'], HeliosParser)
    WATCHED_KEYWORDS = (BlacklistType['WATCH'], HeliosParser)

    def __init__(self, type):
        self._filename = type[0]
        self._parser = type[1](self._filename)

    def parse(self):
        return self._parser.parse()

    def add(self, item, **kwargs):
        return self._parser.add(item, **kwargs)

    def remove(self, item):
        return self._parser.remove(item)

    def exists(self, item):
        return self._parser.exists(item)
