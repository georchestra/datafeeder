import re
from configparser import ConfigParser
from itertools import chain
from os import getenv

import yaml


class GeorchestraConfig:
    def __init__(self):
        self.sections = dict()
        self.datadirpath = getenv("georchestradatadir", "/etc/georchestra")

        self.read_default()
        self.read_gateway_routes()

    def read_default(self):
        parser = ConfigParser()
        with open(f"{self.datadirpath}/default.properties") as lines:
            lines = chain(("[section]",), lines)  # This line does the trick.
            parser.read_file(lines)

        self.sections["default"] = parser["section"]
        self.sections["default"]["datadirpath"] = self.datadirpath

    def read_gateway_routes(self):
        with open(f"{self.datadirpath}/gateway/routes.yaml") as lines:
            self.sections["gateway_routes"] = dict()
            lines2 = yaml.safe_load(lines)
            # only get the targets lines https://github.com/georchestra/datadir/blob/docker-master/gateway/routes.yaml#L76
            for service_target in lines2["georchestra.gateway.services"]:
                self.sections["gateway_routes"][service_target] = lines2[
                    "georchestra.gateway.services"
                ][service_target]

    def tostr(self):
        str = ""
        for key in self.sections:
            str += key + ":\r\n<br>"
            for key2 in self.sections[key]:
                str += " \t&emsp;" + key2 + " : "
                if self.sections[key][key2] == self.get(key2, section=key):
                    str += " \t&emsp;" + self.sections[key][key2] + "\r\n<br> "
                else:
                    str += (
                        " \t&emsp;"
                        + self.sections[key][key2]
                        + " = "
                        + self.get(key2, section=key)
                        + "\r\n<br> "
                    )
        return str

    def get(self, key, section="default"):
        if section not in self.sections:
            return None
        value = self.sections[section].get(key, None)
        if value:
            # this is to catch ${ENV_VAR}
            search_env = re.match("^\\${(.*)}$", value)
            # this is for url using env var http://${ENV_VAR}/geonetwork/..etc?params
            search_env2 = re.match("(.*)\\${(.*)}(.*)", value)
            search_env3 = re.match("(.*)\\${(.*):.*}(.*)", value)

            if search_env:
                if getenv(search_env.group(1)):
                    value = getenv(search_env.group(1))
            elif search_env3:
                if getenv(search_env3.group(2)):
                    value = (
                        search_env3.group(1) + getenv(search_env3.group(2)) + search_env3.group(3)
                    )
            elif search_env2:
                if getenv(search_env2.group(2)):
                    value = (
                        search_env2.group(1) + getenv(search_env2.group(2)) + search_env2.group(3)
                    )
        return value
