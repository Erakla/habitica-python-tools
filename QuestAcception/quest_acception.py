from flask import request
from HabiticaAPI import Client, Exceptions

"""
This file is part of a modularized web server. It provides the required paths and associated functions for the respective project
"""

# WebhookService
def on_quest_invite(token):
    from vigenere import decrypt
    data = request.json
    if data['webhookType'] == 'questActivity' and data['type'] == 'questInvited':
        with open('settings/key.txt', encoding='utf8') as file:
            key = file.read()
        token = decrypt(token[::-1], key)
        client.connect(data['user']['_id'], token).quest_accept_pending(data['group']['id'])
    return {'status': 'success', 'message': 'thank you'}

def accept_quest_register_webhook():
    from vigenere import encrypt
    uid = request.form['uid']
    token = request.form['token']
    with open('settings/key.txt', encoding='utf8') as file:
        key = file.read()
    tokenkey = encrypt(token, key)[::-1]
    try:
        client.connect(uid, token).send('post', 'api/v3/user/webhook', queued=False, data={
            'url': f"http://eratech.ch/habitica/acceptquest/{tokenkey}",
            'label': 'automatic quest acceptance - just delete this entry if you want to stop',
            'type': 'questActivity',
            'options': {
                'questInvited': True
            }
        })
        return 'webhook added'
    except Exceptions.NotAuthorized as ex:
        return str(ex)

def accept_quest_get_page():
    # check provided data level
    uid, token = request.cookies.get('auth', '/').split('/')

    with open('website/habitica_quest_acception.html') as file:
        page = file.read()
    page = page.replace('<!-- uidinput show state -->', 'none' if uid else 'table-row')
    page = page.replace('<!-- uid -->', uid)
    page = page.replace('<!-- tokeninput show state -->', 'none' if token else 'table-row')
    page = page.replace('<!-- token -->', token)
    return page

client: Client

bindings = [
    # WebhookService
    {
        'path': '/habitica/acceptquest/<token>',
        'func': on_quest_invite,
        'methods': ['POST']
    },
    {
        'label': 'QuestAcception',
        'topic': 'habitica',
        'lvl': [0, 1, 2],
        'path': '/habitica/acceptquest',
        'func': accept_quest_get_page,
        'methods': ['GET']
    },
    {
        'path': '/habitica/acceptquest',
        'func': accept_quest_register_webhook,
        'methods': ['POST']
    }
]
