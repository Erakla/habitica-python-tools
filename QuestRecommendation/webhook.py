import flask
from HabiticaAPI import Client
from HabiticaAPI.Exceptions import *
import json
from flask import Flask
from flask import request
from threading import Thread
import requests
import time
import os
import copy

app = Flask(__name__)

# registration evaluation #

class RegistrationEvaluator:
    def __init__(self, max_ticks):
        self._max_ticks = max_ticks
        row_member_entry = {'quests': 0, 'missed ticks': [0 for i in range(max_ticks)]}
        if os.path.exists('QuestAcceptScore.json'):
            with open('QuestAcceptScore.json', 'rt', encoding='utf8') as file:
                self._scores = json.load(file)
        else:
            self._scores = {member: copy.deepcopy(row_member_entry) for member in acc.party['quest']['members']}
        length_difference = max_ticks - len(list(self._scores.values())[0]['missed ticks'])
        if length_difference:
            for member in self._scores:
                self._scores[member]['missed ticks'] += [0 for i in range(length_difference)]

        for member in acc.party.members.ids:
            if member not in self._scores:
                self._scores[member] = copy.deepcopy(row_member_entry)

        for member in self._scores:
            self._scores[member]['quests'] += 1
        self._current_tick = -1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for member in self._scores:
            missed_ticks = self._scores[member]['missed ticks']
            # calculate average ticks
            differences = [missed_ticks[i] - missed_ticks[i + 1] for i in range(0, max_ticks - 1)]
            average = 0
            for i in [differences[i] * (i + 1) for i in range(0, max_ticks - 1)]:
                average += i
            attended_quests = self._scores[member]['quests'] - missed_ticks[-1]
            if attended_quests:
                average /= attended_quests
            self._scores[member]['average ticks taken'] = average

            abs_attendance = 1 - self._scores[member]['missed ticks'][-1] / (self._scores[member]['quests'])
            if self._scores[member]['average ticks taken']:
                probability_for_one_tick = 1 / self._scores[member]['average ticks taken'] * abs_attendance
            else:
                probability_for_one_tick = abs_attendance
            self._scores[member]['prop not attend per tick'] = 1 - probability_for_one_tick

        with open('QuestAcceptScore.json', 'wt', encoding='utf8') as file:
            json.dump(self._scores, file, indent=' ')

    def run_tick(self, limit: float = 0.5, least: float = 0.5):
        """
        calculates the average chance of all players that no one will participate until the next tick.
        returns true if limit is exceeded. use it as termination condition in for loop.

        :param limit:  highest accepted chance that nobody registers anymore. exceeding it results in a return of false
        :param least:  smallest number of players to take part before the waiting period can be canceled
        """
        if acc.party['quest']['active']:
            return False
        if not self._current_tick < 0:
            # raise missed counters
            states = acc.party['quest']['members']
            for member in self._scores:
                if not states.get(member, True):
                    self._scores[member]['missed ticks'][self._current_tick] += 1
        self._current_tick += 1
        if self._current_tick >= self._max_ticks:
            return False

        # accumulate chances for attendation until the next tick
        chancen = 1
        states = acc.party['quest']['members']
        not_attended = [member for member in self._scores if not states[member]]
        if len(states)*least < len(not_attended):
            return True
        for member in not_attended:
            chancen *= self._scores[member].get('prop not attend per tick', 0.5)
        return chancen <= limit


@app.route("/report", methods=['GET'])
def print_evaluation():
    """
    returns a json formated evaluation containing average passes per tick.
    calculates the average ticks each player takes to attend.
    :return: json formated evaluation string
    """
    if os.path.exists('QuestAcceptScore.json'):
        with open('QuestAcceptScore.json', 'rt', encoding='utf8') as file:
            scores = json.load(file)
    else:
        return "no data available"

    # remove not existing players
    allmembers = acc.party.members.ids
    cscores = scores.copy()
    for member in cscores:
        if member not in allmembers:
            del scores[member]

    with open('QuestAcceptScore.json', 'wt', encoding='utf8') as file:
        json.dump(scores, file)


    ticks = len(list(cscores.values())[0]['missed ticks'])
    for member in cscores:
        missed_ticks = cscores[member]['missed ticks']
        # calculate average ticks
        differences = [missed_ticks[i] - missed_ticks[i+1] for i in range(0, ticks-1)]
        average = 0
        for i in [differences[i] * (i+1) for i in range(0, ticks-1)]:
            average += i
        attended_quests = cscores[member]['quests'] - missed_ticks[-1]
        if attended_quests:
            average /= attended_quests
        cscores[member]['average ticks taken'] = average
        cscores[member]['profile name'] = acc.get_profile_by_id(member)['profile']['name']

    out = f'tick duration: {"%5.1f" % (tick_duration/60)} min' \
          '<tr><th>profile name</th><th>participation</th><th>average ticks taken</th><th>attend per tick probability</th></tr>'
    for member in cscores:
        abs_quests = cscores[member]["quests"]
        missed = cscores[member]["missed ticks"][-1]
        out += f'<tr><td class="left">{cscores[member]["profile name"]}</td>' \
               f'<td>{abs_quests - missed}/{abs_quests}</td>' \
               f'<td>{"%4.1f" % cscores[member]["average ticks taken"]}</td>' \
               f'<td>{1-cscores[member]["prop not attend per tick"]}</td></tr>'

    return "<!DOCTYPE html><head><style>" \
           "td {text-align: center;font-family:'Courier New';}" \
           "td.left {text-align: left;}" \
           "table, th, td {border:1px solid black;border-collapse:collapse}" \
           "</style></head>" \
           f"<body><table>{out}</table></body>"

# add usertoken #

@app.route("/adduser", methods=['GET'])
def adduserform():
    with open('webpages/changeuserform.html', 'rt', encoding='utf8') as file:
        return file.read().replace('<--function-->', 'add user'), 200

@app.route("/adduser", methods=['POST'])
def adduserpost():
    with open('token.json', 'rt', encoding='utf8') as file:
        tokenlist = json.load(file)

    uuid = request.form.get('uuid', '')
    token = request.form.get('token', '')
    members = [member['id'] for member in acc.party.members]

    if uuid not in members:
        return f"user is not member of the party {acc.party['summary']}", 406
    if uuid in tokenlist:
        return "user already registrated", 406

    try:
        username = client.connect(uuid, token).profile['profile']['name']
        tokenlist[uuid] = token
        with open('token.json', 'wt', encoding='utf8') as file:
            json.dump(tokenlist, file, indent='\t')
        return f"{username} successfully added", 201
    except NotAuthorized as ex:
        return str(ex), 401

@app.route("/deluser", methods=['GET'])
def deluserform():
    with open('webpages/changeuserform.html', 'rt', encoding='utf8') as file:
        return file.read().replace('<--function-->', 'delete user'), 200

@app.route("/deluser", methods=['POST'])
def deluserpost():
    with open('token.json', 'rt', encoding='utf8') as file:
        tokenlist: dict = json.load(file)

    uuid = request.form.get('uuid', '')
    token = request.form.get('token', '')

    if uuid not in tokenlist:
        return "user not registered", 404
    if token != tokenlist[uuid]:
        return "wrong token", 401

    del tokenlist[uuid]
    with open('token.json', 'wt', encoding='utf8') as file:
        json.dump(tokenlist, file)
    return "user successfully deleted", 200

# quest recommendation #

def determine_best_equip_for_main_stat(main_stats, con_gear, members):
    # wer bekäme höhere ausrüstung?
    # bestimme für jedes mitglied die beste ausrüstung für ihr hauptattribut
    for member in acc.party.members:
        stat = main_stats[member['stats']['class']]
        own_gear = member['items']['gear']['owned']
        best_items = {}
        for key in own_gear:
            if con_gear[key][stat] > best_items.get(con_gear[key]['type'], ('', 0))[1]:
                best_items[con_gear[key]['type']] = (key, con_gear[key][stat])
        members[member['id']] = {'bestitems': best_items, 'name': member['profile']['name']}

def enumerate_owned_party_quests(party_quests, token: dict):
    with open("considered_quest_owner.json", "rt", encoding="utf8") as file:
        owner = json.load(file)
    for id in token:
        if id not in owner:
            owner.append(id)

    # erstelle eine liste aller in der party besessenen quests und ihrer besitzer
    for member in acc.ProfileList(owner):
        for quest in member['items']['quests']:
            if member['items']['quests'][quest] > 0:
                if quest not in party_quests:
                    party_quests[quest] = {'owner': []}

def determine_quest_item_stats(party_quests, con_gear):
    # bestimme für jede quest stat und value fürs gear
    for quest in party_quests:
        party_quests[quest]['stats'] = {}
        gear = [item['key'] for item in acc.objects['quests'][quest]['drop'].get('items', {}) if item['type'] == 'gear']
        if not gear:
            continue
        for item in gear:
            for stat in ['str', 'int', 'per', 'con']:
                # noinspection PyTypeChecker
                quest_stats = party_quests[quest]['stats']
                quest_stats: dict
                if con_gear[item][stat] > quest_stats.get(stat, 0):
                    # party_quests[quest]['stats'][stat] = (value, geartype)
                    quest_stats[stat] = (con_gear[item][stat], con_gear[item]['type'])

def determine_quest_advantages(party_quests, main_stats, members):
    # bestimme für jede quest die user mit stat bonus und
    # bestimme für jede quest die useranzahl mit achivementvorteil
    for quest in party_quests:
        party_quests[quest]['stat_advantage'] = []
        party_quests[quest]['achievements'] = []
        for member in acc.party.members:
            stat = main_stats[member['stats']['class']]
            quest_item_stat = party_quests[quest]['stats'].get(stat, (0, ''))
            if quest_item_stat[1] == stat:
                member_main_stat = members[member['id']]['best_items'][quest_item_stat[1]]
                if member_main_stat < quest_item_stat[0]:
                    # party_quests[quest]['stat_advantage'] = [(member_id, i_improvement)]
                    party_quests[quest]['stat_advantage'].append((member['id'], quest_item_stat[0] - member_main_stat))

            if member['achievements']['quests'].get(quest, 0) == 0:
                party_quests[quest]['achievements'].append(member['id'])

def determine_best_stat_quest(party_quests):
    # wenn user vorteile haben, bestimme die summe an boni pro quest
    # und ermittel die quest mit der größten summe
    best_quest = ''
    for quest in party_quests:
        party_quests[quest]['stat_improvement_sum'] = 0
        for elem in party_quests[quest]['stat_advantage']:
            party_quests[quest]['stat_improvement_sum'] += elem[1]
        if party_quests[quest]['stat_improvement_sum']:
            if best_quest == '':
                best_quest = quest
            elif party_quests[best_quest]['stat_improvement_sum'] < party_quests[quest]['stat_improvement_sum']:
                best_quest = quest
    if best_quest:
        return [best_quest], 'new best item belonging to stat bonuses'
    return [], ''

def determine_best_achievement_quests(party_quests):
    # sonst bestimme die quest mit dem größten achievementvorteil
    best_quest = []
    for quest in party_quests:
        if not len(best_quest) or len(party_quests[best_quest[0]]['achievements']) < len(party_quests[quest]['achievements']):
            best_quest = [quest]
        elif len(party_quests[best_quest[0]]['achievements']) == len(party_quests[quest]['achievements']):
            best_quest.append(quest)
    return best_quest, 'most achievements'

def determine_quest_owners(party_quests):
    # bestimme, welche user diese quest besitzen
    for member in acc.party.members:
        for quest in party_quests:
            if member['items']['quests'].get(quest, 0) > 0:
                party_quests[quest]['owner'].append(member['id'])

def determine_quest_type(quest, objects):
    if 'collect' in objects['quests'][quest]:
        type_ = 'collect'
    elif 'boss' in objects['quests'][quest]:
        type_ = 'boss'
    else:
        type_ = 'unknown'
    return type_

def build_message(party_quests, objects, best_quests, members, decision):
    # und sende die nachricht

    out = "# quest recommendation\n"
    out += f"decision made according to {decision}\n"

    for quest in best_quests:
        out += f"## {acc.objects['quests'][quest]['text']}\n"
        out += f"{determine_quest_type(quest, objects)}\n"

        users_with_bonus_adv = ''
        if party_quests[quest]['stat_advantage']:
            for id_, value in party_quests[quest]['stat_advantage']:
                users_with_bonus_adv += f"{members[id_]['name']}(+{value}), "
        if party_quests[quest]['stat_advantage']:
            out += f"### users with stat bonus advantages(+{party_quests[quest]['stat_improvement_sum']}):\n"
            out += f"{users_with_bonus_adv[:-2]}\n"

        users_with_new_achiev = ''
        for id_ in party_quests[quest]['achievements']:
            users_with_new_achiev += f"{members[id_]['name']}, "
        out += f"### users with new achievements({len(party_quests[quest]['achievements'])}):\n"
        out += f"{users_with_new_achiev[:-2]}\n"

        out += "### owners:\n"
        ownersline = ''
        for id_ in party_quests[quest]['owner']:
            ownersline += f"[@{members[id_]['name']}](/profile/{id_}), "
        out += f"{ownersline[:-2]}\n"
    return out

def recommend_next_quest():
    # I would primarily go for higher items for main attributes of the respective class (that will rarely be the case)
    # secondly to achivement. So how many people have not yet completed a quest.

    with open('token.json', 'rt', encoding='utf8') as file:
        token = json.load(file)
    main_stats = {'warrior': 'str', 'rogue': 'per', 'wizard': 'int', 'healer': 'con'}
    con_gear = acc.objects['gear']['flat']
    members = {}
    party_quests = {}

    determine_best_equip_for_main_stat(main_stats, con_gear, members)
    enumerate_owned_party_quests(party_quests, token)
    determine_quest_item_stats(party_quests, con_gear)
    determine_quest_advantages(party_quests, main_stats, members)
    # wenn user vorteile haben, bestimme die summe an boni pro quest
    # und ermittel die quest mit der größten summe
    best_quests, decision = determine_best_stat_quest(party_quests)
    # sonst bestimme die quest mit dem größten achievementvorteil
    if not len(best_quests):
        best_quests, decision = determine_best_achievement_quests(party_quests)
    determine_quest_owners(party_quests)
    out = build_message(party_quests, acc.objects, best_quests, members, decision)

    # print(out)
    acc.party.chat.send_message(out, False)

    for quest in best_quests:
        for uid in token:
            try:
                if uid in party_quests[quest]['owner']:
                    log(f"invite with {acc.get_profile_by_id(uid)['profile']['name']} to quest: {acc.objects['quests'][quest]['text']}")
                    client.connect(uid, token[uid]).quest_invite_group('party', quest, False)
                    return
            except NotAuthorized:
                wrong_userdata_handler(uid)

# webhook functions #

def wrong_userdata_handler(uid):
    with open('token.json', 'rt', encoding='utf8') as file:
        tokenlist = json.load(file)
    del tokenlist[uid]
    with open('token.json', 'wt', encoding='utf8') as file:
        json.dump(tokenlist, file)
    acc.user_send_private_message("## QuestRecommendation\n"
                                  "user removed: invalid token\n"
                                  "you can register again with a valid token at:\n"
                                  "http://eratech.ch:1082/adduser\n", uid)

def log(msg: str):
    print(f"{9*'- '}{time.strftime('[%d/%b/%Y %H:%M:%S]')} {msg}")

def quest_invited():
    log("quest invited")
    log("accept pending quest")
    with open('token.json', 'rt', encoding='utf8') as file:
        token = json.load(file)

    unattended = [uid for uid in acc.party['quest']['members'] if not acc.party['quest']['members'][uid]]
    for uid in token:
        if uid not in unattended:
            continue
        try:
            client.connect(uid, token[uid]).quest_accept_pending('party', False)
        except ArgumentsNotAccepted:
            pass
        except NotAuthorized:
            wrong_userdata_handler(uid)

    with RegistrationEvaluator(max_ticks) as eva:
        while eva.run_tick():
            time.sleep(tick_duration)

    if not acc.party['quest']['active']:
        if acc.party['quest']['leader'] == acc.user_id:
            acc.quest_force_start_pending_quest(acc.party['id'])
        else:
            acc.party.chat.send_message("I think we should start the quest")

def quest_started():
    log("quest started")
    log("cast spell tools of trade")
    requests.post('https://habitica.com/api/v3/user/class/cast/toolsOfTrade', headers=acc.send.header)
    time.sleep(5)
    log("run cron")
    acc.cron_run()

def quest_finished():
    log("quest finished")
    log("make recommendation")
    recommend_next_quest()

def process(logdata: json):
    # log
    filename = "log/requests_in/%s.json" % time.strftime("%Y-%m-%d")

    if os.path.exists(filename):
        with open(filename, "rt") as file:
            fdata = json.load(file)
    else:
        fdata = {}
    with open(filename, "wt") as file:
        fdata.update({time.strftime("%H:%M:%S"): logdata})
        file.write(json.dumps(fdata, indent="\t"))

    # process
    data = logdata['data']
    if data['webhookType'] == 'questActivity':
        if data['type'] == 'questInvited':
            Thread(target=quest_invited).start()
        if data['type'] == 'questStarted':
            Thread(target=quest_started).start()
        if data['type'] == 'questFinished':
            Thread(target=quest_finished).start()

@app.route("/favicon.ico", methods=['GET'])
def favicon():
    return flask.send_from_directory('static', 'favicon.ico')

@app.route("/webhook", methods=['POST'])
def webhook():
    data = request.json
    Thread(target=process, args=(
        {
            'ip': request.remote_addr,
            'route': request.access_route,
            'path': request.path,
            'form': request.form,
            'cookies': request.cookies,
            'args': request.args,
            'data': data
        },
    )).start()
    return {'success': True, 'message': 'thank you', "data": data}


if __name__ == '__main__':
    max_ticks = 36
    tick_duration = 60*30

    with open('AppData.json', 'rt', encoding='utf8') as file:
        appdata = json.load(file)

    try:
        with Client(appdata['author_uid'], appdata['application_name'], 30, language='en', logfolder='log/requests_out') as client:
            acc = client.connect(appdata['user_id'], appdata['token'])
            app.run(host='0.0.0.0', port=1082)

    except NotAuthorized as ex:
        log(str(ex))
    except ArgumentsNotAccepted as ex:
        log(str(ex))
    except BadResponseFormat as ex:
        log(str(ex))
