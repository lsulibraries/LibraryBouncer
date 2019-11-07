#! usr/env/python3

from flask import Flask, json, request, render_template, jsonify
import requests

application = Flask(__name__)


def login(username, password):
    endpoint = f"https://lalu.sirsi.net/lalu_ilsws/rest/security/loginUser?clientID=DS_CLIENT&login={username}&password={password}&json=True"
    s = requests.session()
    r = s.post(endpoint)
    return s, json.loads(r.text)["sessionToken"]


def pick_an_endpoint(user_id, session_token):
    if len(user_id) == 17:
        endpoint = f"https://lalu.sirsi.net/lalu_ilsws/rest/patron/lookupPatronInfo?clientID=DS_CLIENT&sessionToken={session_token}&userID={user_id}&includePatronStatusInfo=True&json=True"
    elif len(user_id) == 9 and user_id[:2] == "89":
        endpoint = f"https://lalu.sirsi.net/lalu_ilsws/rest/patron/lookupPatronInfo?clientID=DS_CLIENT&sessionToken={session_token}&alternateID={user_id}&includePatronStatusInfo=True&json=True"
    else:
        # user_id isn't an 89 number or a 17-digit account number
        endpoint = None
    return endpoint


def get_expiration(session, session_token, user_id):
    endpoint = pick_an_endpoint(user_id, session_token)
    if not endpoint:
        return {"expiration": "1900-01-01"}
    r = session.post(endpoint)
    try:
        expiration = json.loads(r.text)["patronStatusInfo"]["datePrivilegeExpires"]
    except KeyError:
        expiration = "1900-01-01"
    return {"expiration": expiration}


def parse_secrets():
    with open("user_pass.json", "r") as f:
        info = json.load(f)
    return info["user"], info["password"]


@application.route("/")
def index():
    username, password = parse_secrets()
    session, session_token = login(username, password)
    user_id = request.args.get("id")
    user_info = get_expiration(session, session_token, user_id)
    return jsonify(user_info)


if __name__ == "__main__":
    application.run(host="127.0.0.1", port=8000)
