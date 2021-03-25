from HabiticaAPI import Client
from HabiticaAPI.Exceptions import *
import json

if __name__ == '__main__':
    with open('AppData.json', 'rt', encoding='utf8') as file:
        appdata = json.load(file)

    try:
        with Client(appdata['author_uid'], appdata['application_name'], 30, language='en') as client:
            acc = client.connect(appdata['user_id'], appdata['token'])

            pass

    except NotAuthorized as ex:
        breakpoint()
    except ArgumentsNotAccepted as ex:
        breakpoint()
    except BadResponseFormat as ex:
        breakpoint()
