import re
from configparser import ConfigParser, SectionProxy
from itertools import chain
from os import getenv
from typing import Any

import yaml


class GeorchestraConfig:
    def __init__(self) -> None:
        self.sections: dict[str, dict[str, Any] | SectionProxy] = {}
        self.datadirpath: str = (
            getenv("GEORCHESTRA_DATADIR", "/etc/georchestra") or "/etc/georchestra"
        )

        self.read_default()
        self.read_gateway_routes()

    def read_default(self) -> None:
        parser = ConfigParser()
        with open(f"{self.datadirpath}/default.properties") as lines:
            lines = chain(("[section]",), lines)  # This line does the trick.
            parser.read_file(lines)

        self.sections["default"] = parser["section"]
        self.sections["default"]["datadirpath"] = self.datadirpath

    def read_gateway_routes(self) -> None:
        with open(f"{self.datadirpath}/gateway/routes.yaml") as lines:
            self.sections["gateway_routes"] = dict()
            lines2 = yaml.safe_load(lines)
            # only get the targets lines https://github.com/georchestra/datadir/blob/docker-master/gateway/routes.yaml#L76
            for service_target in lines2["georchestra.gateway.services"]:
                self.sections["gateway_routes"][service_target] = lines2[
                    "georchestra.gateway.services"
                ][service_target]

    def tostr(self) -> str:
        result = ""
        for key in self.sections:
            result += key + ":\r\n<br>"
            for key2 in self.sections[key]:
                result += " \t&emsp;" + key2 + " : "
                if self.sections[key][key2] == self.get(key2, section=key):
                    result += " \t&emsp;" + str(self.sections[key][key2]) + "\r\n<br> "
                else:
                    result += (
                        " \t&emsp;"
                        + str(self.sections[key][key2])
                        + " = "
                        + str(self.get(key2, section=key))
                        + "\r\n<br> "
                    )
        return result

    def get(self, key: str, section: str = "default") -> str:
        if section not in self.sections:
            return ""
        value = self.sections[section].get(key, None)
        if value is None:
            value = ""
        if value:
            # this is to catch ${ENV_VAR}
            search_env = re.match("^\\${(.*)}$", value)
            # this is for url using env var http://${ENV_VAR}/geonetwork/..etc?params
            search_env2 = re.match("(.*)\\${(.*)}(.*)", value)
            search_env3 = re.match("(.*)\\${(.*):.*}(.*)", value)

            if search_env:
                env_value = getenv(search_env.group(1))
                if env_value:
                    value = env_value  # type: ignore[arg-type]
            elif search_env3:
                env_value = getenv(search_env3.group(2))
                if env_value:
                    value = search_env3.group(1) + env_value + search_env3.group(3)
            elif search_env2:
                env_value = getenv(search_env2.group(2))
                if env_value:
                    value = search_env2.group(1) + env_value + search_env2.group(3)

        return value
