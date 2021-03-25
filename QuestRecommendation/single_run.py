from HabiticaAPI import Client
from HabiticaAPI.Exceptions import *
import json


def determine_best_equip_for_main_stat(main_stats, con_gear, members):
    for member in acc.party.member:
        stat = main_stats[member['stats']['class']]
        own_gear = member['items']['gear']['owned']
        best_items = {}
        for key in own_gear:
            if con_gear[key][stat] > best_items.get(con_gear[key]['type'], ('', 0))[1]:
                best_items[con_gear[key]['type']] = (key, con_gear[key][stat])
        members[member['id']] = {'bestitems': best_items, 'name': member['profile']['name']}

def enumerate_owned_party_quests(party_quests):
    for member in acc.party.member:
        for quest in member['items']['quests']:
            if member['items']['quests'][quest] > 0:
                if quest not in party_quests:
                    party_quests[quest] = {'owner': [member['id']]}
                else:
                    party_quests[quest]['owner'].append(member['id'])

def determine_quest_item_stats(party_quests, con_gear):
    # determine stat type and value of gear for each quest
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
    for quest in party_quests:
        party_quests[quest]['stat_advantage'] = []
        party_quests[quest]['achievements'] = []
        for member in acc.party.member:
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
    return best_quest, 'new best item belonging to stat bonuses'

def determine_best_achievement_quest(party_quests):
    best_quest = ''
    for quest in party_quests:
        if best_quest == '':
            best_quest = quest
        elif len(party_quests[best_quest]['achievements']) < len(party_quests[quest]['achievements']):
            best_quest = quest
    return best_quest, 'most achievements'

def determine_quest_owners(best_quest):
    owner = []
    for member in acc.party.member:
        if member['items']['quests'].get(best_quest, 0) > 0:
            owner.append(member['id'])
    return owner

def determine_quest_type(best_quest, objects):
    if 'collect' in objects['quests'][best_quest]:
        type_ = 'collect'
    elif 'boss' in objects['quests'][best_quest]:
        type_ = 'boss'
    else:
        type_ = 'unknown'
    return type_

def build_message(party_quests, best_quest, members, owner, decision, type_):
    users_with_bonus_adv = ''
    if party_quests[best_quest]['stat_advantage']:
        for id_, value in party_quests[best_quest]['stat_advantage']:
            users_with_bonus_adv += f"{members[id_]['name']}(+{value}), "

    users_with_new_achiev = ''
    for id_ in party_quests[best_quest]['achievements']:
        users_with_new_achiev += f"{members[id_]['name']}, "

    ownersline = ''
    for id_ in owner:
        ownersline += f"[@{members[id_]['name']}](/profile/{id_}), "

    out = "# quest recommendation\n"
    out += f"decision made according to {decision}\n"
    out += f"## {acc.objects['quests'][best_quest]['text']}\n"
    out += f"{type_}\n"
    if party_quests[best_quest]['stat_advantage']:
        out += f"### users with stat bonus advantages(+{party_quests[best_quest]['stat_improvement_sum']}):\n"
        out += f"{users_with_bonus_adv[:-2]}\n"
    out += f"### users with new achievements({len(party_quests[best_quest]['achievements'])}):\n"
    out += f"{users_with_new_achiev[:-2]}\n"
    out += "### owners:\n"
    out += f"{ownersline[:-2]}\n"
    return out

def recommend_next_quest():
    # I would primarily go for higher items for main attributes of the respective class (that will rarely be the case)
    # secondly to achivement. So how many people have not yet completed a quest.

    main_stats = {'warrior': 'str', 'rogue': 'per', 'wizard': 'int', 'healer': 'con'}
    con_gear = acc.objects['gear']['flat']
    members = {}
    party_quests = {}

    determine_best_equip_for_main_stat(main_stats, con_gear, members)
    enumerate_owned_party_quests(party_quests)
    determine_quest_item_stats(party_quests, con_gear)
    determine_quest_advantages(party_quests, main_stats, members)
    # if users have advantages, determine the amount of bonuses per quest
    # and find the quest with the largest sum
    best_quest, decision = determine_best_stat_quest(party_quests)
    # otherwise determine the quest with the most achievement advantages
    if not best_quest:
        best_quest, decision = determine_best_achievement_quest(party_quests)
    owners = determine_quest_owners(best_quest)
    type_ = determine_quest_type(best_quest, acc.objects)
    out = build_message(party_quests, best_quest, members, owners, decision, type_)

    # print(out)
    acc.party.chat.send_message(out, False)

    if acc.user_id in owners:
        acc.quest_invite_group('party', best_quest, False)
        pass


if __name__ == '__main__':
    with open('AppData.json', 'rt', encoding='utf8') as file:
        appdata = json.load(file)

    try:
        with Client(appdata['author_uid'], appdata['application_name'], 30, language='en') as client:
            acc = client.connect(appdata['user_id'], appdata['token'])
            recommend_next_quest()

    except NotAuthorized as ex:
        breakpoint()
    except ArgumentsNotAccepted as ex:
        breakpoint()
    except BadResponseFormat as ex:
        breakpoint()
