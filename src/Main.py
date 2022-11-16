import enum
from json import load, dump
from typing import Dict, Collection

import requests


class Field(enum.Enum):
    PASSWORD = 'password'
    LOGIN = 'login'
    ACCESS = "accessToken"
    REFRESH = "refreshToken"
    TOKEN_TYPE = "tokenType"
    EXPIRES_IN = "expiresIn"


class ValidationError(Exception): pass


class APIHelper:
    @staticmethod
    def _abstract_request(url: str, body: dict | None, headers: dict | None = None) -> \
            Dict[str, str | Collection | int | float]:
        _headers = {"Content-Type": "application/json;charset=UTF-8", }
        if headers:
            _headers = {**_headers, **headers}
        resp = requests.post(url,
                             json=body,
                             headers=_headers)

        if 200 <= resp.status_code < 300:
            return resp.json()
        elif 400 <= resp.status_code < 500:
            raise ValidationError(f"Not permitted, {resp.status_code}")

        raise Exception("Unsupported Error Occurred! Most probably it's not ur fault ;)")

    @staticmethod
    def login(data):
        login, password = data[Field.LOGIN.value], data[Field.PASSWORD.value]

        assert login is not None
        assert password is not None

        body = {"email": login, "password": password}
        url = "https://klubowicz.cityfit.pl/api/tokens"

        return APIHelper._abstract_request(url, body)


class Facade:
    def __init__(self, file_name=None):

        self.file_name = file_name or 'secrets.json'

        self._read_data_from_file()

        assert isinstance(self.data, dict), "Object was not read properly!"

        if Field.ACCESS.value not in self.data.keys() \
                or Field.REFRESH.value not in self.data.keys() \
                or Field.EXPIRES_IN.value not in self.data.keys() \
                or Field.TOKEN_TYPE.value not in self.data.keys():
            self._login()

        self._update_secrets()

    def _read_data_from_file(self):
        with open(self.file_name, 'r') as file:
            self.data = load(file)

    def _write_data_to_file(self):
        with open(self.file_name, 'w') as file:
            dump(self.data, file, )

    def _login(self):
        resp = APIHelper.login(self.data)

        for k, v in resp.items():
            self.data[k] = v

        self._write_data_to_file()

    def _update_secrets(self):
        pass

def main():
    Facade()


if __name__ == '__main__':
    main()
