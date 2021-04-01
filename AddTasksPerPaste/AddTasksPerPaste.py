from HabiticaAPI import Client
from HabiticaAPI.Exceptions import *
import json

def terminal_create_todos():
    print("go on!")
    queue = []
    # title
    title = input()
    while title:
        # input
        task = {'tasktype': 'todo', 'checklist': []}
        items = []
        line = input()
        while line:
            if line[0] == '[' and line[1:-1].find(']') != -1:
                arg = line.split(']', 1)[0][1:]
                value = line[len(arg)+2:]
                if arg in ["tags", "reminders", "days_of_month", "weeks_of_month"]:
                    if arg == "item":
                        task['checklist'].append({'text': value})
                    elif arg not in task:
                        task[arg] = []
                    else:
                        task[arg].append(value)
                else:
                    task[arg] = value
            else:
                task['checklist'].append({'text': line})
            line = input()

        # processing
        tag_ids = []
        for arg in ["every_x", "streak", "value"]:
            if arg in task:
                task[arg] = int(task[arg])
        for arg in ['priority']:
            if arg in task:
                task[arg] = float(task[arg])
        for arg in ["up", "down", "collapse_check_list"]:
            if arg in task:
                task[arg] = bool(task[arg])
        if 'tags' in task:
            for tagname in task['tags']:
                for tag_id in acc.profile['tags']:
                    if acc.profile['tags'][tag_id] == tagname:
                        tag_ids.append(tag_id)
                        break
            task['tags'] = tag_ids
        task['text'] = title
        task['queued'] = False
        queue.append(task)
        title = input()

    # send
    for task in queue.__reversed__():
        acc.task_create_for_user(**task)
        print(f"created: {task['text']}")


if __name__ == '__main__':
    with open('AppData.json', 'rt', encoding='utf8') as file:
        appdata = json.load(file)

    try:
        with Client(appdata['author_uid'], appdata['application_name'], 30, language='en') as client:
            acc = client.connect(appdata['user_id'], appdata['token'])

            terminal_create_todos()

    except NotAuthorized as ex:
        breakpoint()
    except ArgumentsNotAccepted as ex:
        breakpoint()
    except BadResponseFormat as ex:
        breakpoint()

