import datetime
import enum
import random
import time
from json import load, dump
from typing import Dict, Collection, Any

import requests

CLUB_ID = 100013
DELTA = 6


class Field(enum.Enum):
    PASSWORD = 'password'
    LOGIN = 'login'
    ACCESS = "accessToken"
    REFRESH = "refreshToken"
    TOKEN_TYPE = "tokenType"
    EXPIRES_IN = "expiresIn"


class ValidationError(Exception):
    def __init__(self, message, resp, *args):
        self.resp = resp
        super().__init__(message, *args)


class Event:
    def __init__(self,
                 id: int,
                 startDate: str,
                 endDate: str,
                 maximumParticipants: int,
                 maximumSubstitutions: int,
                 instructor: dict,
                 participants: dict,
                 memberReservationDetails: dict,
                 **kwargs):
        self.id = id
        self.start_date = startDate
        self.end_date = endDate
        self.maximum_participants = maximumParticipants
        self.maximum_substitutions = maximumSubstitutions
        self.instructor = instructor['name']
        self.participants_ok = participants['participantsOk']
        self.participants_substituted = participants['participantsSubstituted']
        self.member_reservation_details = memberReservationDetails

    @property
    def pretty_format(self):
        return f'id:{self.id}\t| {self.start_date.replace("T", " ")}\t--- {self.end_date.replace("T", " ")}\t| ins: {self.instructor}'

    def __str__(self):
        return f'{self.id=} {self.start_date=} {self.end_date=} {self.maximum_participants=} {self.maximum_substitutions=} {self.instructor=} {self.participants_ok=} {self.participants_substituted=} {self.member_reservation_details=}'.replace(
            'self.', '')


class APIHelper:
    @staticmethod
    def _abstract_request_post(url: str, body: dict | None, headers: dict | None = None) -> \
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
            print(f"Error: {resp.json()['detail']}")
            raise ValidationError(f"Not permitted, {resp.status_code}", resp=resp)

        raise Exception("Unsupported Error Occurred! Most probably it's not ur fault ;)")

    @staticmethod
    def _abstract_authorized_request_post(credentials, url: str,
                                          body: dict | None,
                                          headers: dict | None = None,
                                          **kwargs):
        _headers = {
            "Authorization": f"{'Bearer' if 'bearer' == credentials[Field.TOKEN_TYPE.value] else ''} {credentials[Field.ACCESS.value]}"}

        if headers:
            _headers = {**_headers, **headers}

        return APIHelper._abstract_request_post(url, body, _headers)

    @staticmethod
    def _abstract_authorized_request_get(credentials, url: str, headers: dict | None = None) -> \
            Dict[str, Any] | Collection[Dict[str, Any]]:
        _headers = {"Content-Type": "application/json;charset=UTF-8",
                    "Authorization": f"{'Bearer' if 'bearer' == credentials[Field.TOKEN_TYPE.value] else ''} {credentials[Field.ACCESS.value]}"}
        if headers:
            _headers = {**_headers, **headers}
        resp = requests.get(url,
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

        return APIHelper._abstract_request_post(url, body)

    @staticmethod
    def reserve(credentials, event: Event):
        url = f"https://klubowicz.cityfit.pl/api/me/reservations/{event.id}"
        body = {"reservationDate": event.start_date.split('T')[0]}

        return APIHelper._abstract_authorized_request_post(credentials, url, body)

    @staticmethod
    def get_list(credentials) -> Collection[Dict[str, Any]]:
        now = datetime.datetime.today().strftime('%Y-%m-%d')
        future = (datetime.datetime.today() + datetime.timedelta(days=DELTA)).strftime('%Y-%m-%d')
        url = f"https://klubowicz.cityfit.pl/api/classes/schedule?dateFrom={now}&dateTo={future}&clubId={CLUB_ID}&clubSchedule=true"

        return APIHelper._abstract_authorized_request_get(credentials, url)


class Facade:
    def __init__(self, file_name=None):

        self.file_name = file_name or 'secrets.json'

        self._read_data_from_file()

        assert isinstance(self.credentials, dict), "Object was not read properly!"

        if Field.ACCESS.value not in self.credentials.keys() \
                or Field.REFRESH.value not in self.credentials.keys() \
                or Field.EXPIRES_IN.value not in self.credentials.keys() \
                or Field.TOKEN_TYPE.value not in self.credentials.keys():
            self._login()

    def _read_data_from_file(self):
        with open(self.file_name, 'r') as file:
            self.credentials = load(file)

    def _write_data_to_file(self):
        with open(self.file_name, 'w') as file:
            dump(self.credentials, file, )

    def _login(self):
        resp = APIHelper.login(self.credentials)

        for k, v in resp.items():
            self.credentials[k] = v

        self._write_data_to_file()

    def get_list(self):
        return [Event(**ob) for ob in APIHelper.get_list(self.credentials)]

    def print_list(self):
        print('\n'.join(str(x) for x in self.get_list()))

    def get_event_of_id(self, id: int) -> Event:
        return next(iter(filter(lambda x: x.id == id, self.get_list())))

    def reserve(self, event: Event):
        assert event is not None
        assert isinstance(event, Event)

        return APIHelper.reserve(self.credentials, event)


class ApplicationBot:
    def __init__(self, interval=1.0):
        self.facade = Facade()
        self.interval = interval

    @property
    def help(self):
        return \
            """Pomoc:
            1. Wypisanie zajęć.
            2. Dokonanie rezerwacji na id eventu.
            
            0. Wyjście.
            """

    def mainloop(self):
        self.print_help()

        while True:
            cmd = input(' ~ ')

            match cmd:
                case '0':
                    break
                case '1':
                    self.list()

                case '2':
                    self.reserve()
                case _:
                    self.print_help()
        return self

    def list(self):
        print(
            '\n'.join(x.pretty_format for x in self.facade.get_list())
        )

    def reserve(self):
        while True:
            try:
                val = int(input("Podaj id zajęć do rezerwacji, lub 0 by anulować: ~ "))
                break
            except ValueError:
                print("Nie podano poprawnego nr rezerwacji")
                continue

        if val == 0:
            print("ANULOWANO")
            self.print_help()
            return

        a = random.randint(1, 4)
        b = random.randint(1, 4)

        try:
            event = self.facade.get_event_of_id(val)
            validation = int(input(f"Czy jesteś pewny/a? Podaj wynik działania: {a} + {b} = "))
        except ValueError:
            print("ANULOWANO")
            self.print_help()
            return
        except StopIteration:
            print("ANULOWANO - NIEPOPRAWNE ID LUB ZAJĘCIA NIE ISTNIEJĄ")
            self.print_help()
            return

        if validation != a + b:
            print("ANULOWANO")
            self.print_help()
            return

        print("OK - przyjęte do realizacji!")

        while True:
            try:
                print(self.facade.reserve(event))
                print("Chyba się udało!")
                break
            except ValidationError as ve:
                if ve.resp.status_code == 403:
                    print(f'   {ve.resp.json()}')
                    print("kontynuuję...")
                    time.sleep(self.interval)
                    continue
        print("\nKONIEC!")
        self.print_help()

    def print_help(self):
        print(self.help)


def main():
    ab = ApplicationBot().mainloop()
    # ab.facade.print_list()


if __name__ == '__main__':
    main()
