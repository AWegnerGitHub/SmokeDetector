from typing import Union
import regex

from globalvars import GlobalVars
from helpers import log
from helios import HeliosEndpoint, BlacklistType
import requests


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


class BasicListParser(BlacklistParser):
    def parse(self):
        with open(self._filename, 'r', encoding='utf-8') as f:
            return [line.rstrip() for line in f if len(line.rstrip()) > 0]

    def add(self, item: str):
        with open(self._filename, 'a+', encoding='utf-8') as f:
            last_char = f.read()[-1:]
            if last_char not in ['', '\n']:
                item = '\n' + item
            f.write(item + '\n')

    def remove(self, item: str):
        with open(self._filename, 'r+', encoding='utf-8') as f:
            items = f.readlines()
            items = [x for x in items if item not in x]
            f.seek(0)
            f.truncate()
            f.writelines(items)

    def exists(self, item: str):
        with open(self._filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, x in enumerate(lines):
                if item in x:
                    return True, i + 1

        return False, -1


class TSVDictParser(BlacklistParser):
    def parse(self):
        list = {}
        with open(self._filename, 'r', encoding='utf-8') as f:
            for lineno, line in enumerate(f, 1):
                if regex.compile('^\s*(?:#|$)').match(line):
                    continue
                try:
                    when, by_whom, what = line.rstrip().split('\t')
                except ValueError as err:
                    log('error', '{0}:{1}:{2}'.format(self._filename, lineno, err))
                    continue
                list[what] = {'when': when, 'by': by_whom}

        return list

    def add(self, item: Union[str, dict]):
        with open(self._filename, 'a+', encoding='utf-8') as f:
            if isinstance(item, dict):
                item = '{}\t{}\t{}'.format(item[0], item[1], item[2])
            last_char = f.read()[-1:]
            if last_char not in ['', '\n']:
                item = '\n' + item
            f.write(item + '\n')

    def remove(self, item: Union[str, dict]):
        if isinstance(item, dict):
            item = item[2]

        with open(self._filename, 'r+', encoding='utf-8') as f:
            items = f.readlines()
            items = [x for x in items if item not in x]
            f.seek(0)
            f.truncate()
            f.writelines(items)

    def exists(self, item: Union[str, dict]):
        if isinstance(item, dict):
            item = item[2]

        with open(self._filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, x in enumerate(lines):
                if item in x:
                    return True, i + 1

        return False, -1


class HeliosParser(BlacklistParser):
    def parse(self):
        endpoint = "{}{}".format(HeliosEndpoint['BLACKLISTS'], self._filename)
        response = requests.get(endpoint)
        return [r for r in response.json()['items']]

    def add(self, item: str, **kwargs):
        requestor = kwargs.get('requestor', None)
        chat_link = kwargs.get('chat_link', None)
        endpoint = "{}{}".format(HeliosEndpoint['BLACKLISTS'], self._filename)
        if GlobalVars.helios_key:
            params = {'pattern': item, 'request_user': requestor, 'chat_link': chat_link}
            response = requests.post(endpoint, json=params, headers={'Authorization': GlobalVars.helios_key})
            if response.json()['error_type']:
                log("error", "Error occurred while adding pattern to Helios")
                log("error", "Pattern: {}".format(item))
                log("error", "{}".format(response.json()['message']))
                return (False, "Problem adding pattern {}. Error type: {}".format(
                    item,
                    response.json()['error_type'])
                )
            else:
                return (True, "Successfully added {}".format(item))
                # TODO: Write to local file
        else:   # Handle case where a key isn't set
            raise NotImplementedError

    def remove(self, item: str):
        endpoint = "{}{}".format(HeliosEndpoint['BLACKLISTS'], self._filename)
        if GlobalVars.helios_key:
            params = {'pattern': item}
            response = requests.delete(endpoint, json=params, headers={'Authorization': GlobalVars.helios_key})
            if response.json()['error_type']:
                log("error", "Error occurred while deleting pattern from Helios")
                log("error", "Pattern: {}".format(item))
                log("error", "{}".format(response.json()['message']))
                return (False, "Problem deleting pattern {}. Error type: {}".format(
                    item,
                    response.json()['error_type'])
                )
            else:
                return (True, "Successfully removed {}".format(item))
                # TODO: Write to local file
        else:   # Handle case where a key isn't set
            raise NotImplementedError

    def exists(self, item: str):
        with open(self._filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, x in enumerate(lines):
                if item in x:
                    return True, i + 1

        return False, -1


class Blacklist:
    KEYWORDS = (BlacklistType['KEYWORD'], HeliosParser)
    WEBSITES = (BlacklistType['WEBSITE'], HeliosParser)
    USERNAMES = (BlacklistType['USERNAME'], HeliosParser)
    WATCHED_KEYWORDS = (BlacklistType['WATCH'], HeliosParser)

    def __init__(self, type):
        log("info", "Filename: {}".format(type[0]))
        log("info", "Parser: {}".format(type[1]))
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
