import json


def get_credentials(file_name):
    with open(file_name) as f:
        return json.load(f)
