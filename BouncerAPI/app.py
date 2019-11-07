#! usr/env/python3

from flask import Flask, json, request, render_template, jsonify
import requests

application = Flask(__name__)


def login(username, password):
    endpoint = f"https://lalu.sirsi.net/lalu_ilsws/rest/security/loginUser?clientID=DS_CLIENT&login={username}&password={password}&json=True"
    s = requests.session()
    r = s.post(endpoint)
    return s, json.loads(r.text)["sessionToken"]


def pick_an_endpoint(userid, session_token):
    if not userid:
        endpoint = None
    elif len(userid) == 17:
        endpoint = f"https://lalu.sirsi.net/lalu_ilsws/rest/patron/lookupPatronInfo?clientID=DS_CLIENT&sessionToken={session_token}&userID={userid}&includePatronStatusInfo=True&includePatronInfo=True&json=True"
    elif len(userid) == 9 and userid[:2] == "89":
        endpoint = f"https://lalu.sirsi.net/lalu_ilsws/rest/patron/lookupPatronInfo?clientID=DS_CLIENT&sessionToken={session_token}&alternateID={userid}&includePatronStatusInfo=True&includePatronInfo=True&json=True"
    else:
        # userid isn't an 89 number or a 17-digit account number
        endpoint = None
    return endpoint


def parse_response(r):
    try:
        expiration = json.loads(r.text)["patronStatusInfo"]["datePrivilegeExpires"]
    except KeyError:
        expiration = "1900-01-01"
    try:
        user = json.loads(r.text)["patronInfo"]["displayName"]
    except KeyError:
        user = "Unknown user"
    return {"user": user, "expiration": expiration}


def get_userinfo(session, session_token, userid):
    endpoint = pick_an_endpoint(userid, session_token)
    if not endpoint:
        return {"user": "Unknown user", "expiration": "1900-01-01"}
    print(endpoint)
    response = session.post(endpoint)
    return parse_response(response)


def parse_secrets():
    with open("user_pass.json", "r") as f:
        info = json.load(f)
    return info["user"], info["password"]


@application.route("/")
def index():
    username, password = parse_secrets()
    session, session_token = login(username, password)
    userid = request.args.get("id")
    userinfo = get_userinfo(session, session_token, userid)
    return jsonify(userinfo)


if __name__ == "__main__":
    application.run(host="127.0.0.1", port=8000)
