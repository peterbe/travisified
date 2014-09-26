#!/usr/bin/env python
import json
import os
import ConfigParser
import socket
import random

import requests

from flask import Flask, request, make_response, jsonify, send_file
from flask.views import MethodView


DEBUG = os.environ.get('DEBUG', False) in ('true', '1', 'y', 'yes')
GITHUB_OAUTH_TOKEN = os.environ.get('GITHUB_OAUTH_TOKEN')

app = Flask(__name__)

IRC_NICK = 'travisified'

INI_LOCATION = os.path.join(
    os.path.dirname(__file__),
    'projects.ini'
)

@app.route('/')
def index_html():
    return send_file('index.html')


def random_positive_emoji():
    return random.choice((
        ':green_heart:',
        ':+1:',
        ':star:',
        ':smiley:',
        ':metal:',
        ':clap:',
        ':sparkles:',
    ))


def random_negative_emoji():
    return random.choice((
        ':-1:',
        ':suspect:',
        ':rage1:',
        ':thumbsdown:',
        ':shit:',
        ':broken_heart:',
        ':boom:',
        ':weary:',
    ))


class WebhookView(MethodView):

    def post(self):

        config = ConfigParser.RawConfigParser(allow_no_value=True)
        config.read(INI_LOCATION)

        payload = json.loads(request.form['payload'])

        assert payload['type'] == 'pull_request', payload['type']
        author_email = payload['author_email']
        build_url = payload['build_url']
        compare_url = payload['compare_url']

        repo_name = payload['repository']['name']  # e.g. socorro
        repo_owner = payload['repository']['owner_name']  # e.g. mozilla
        commit_msg = payload['message']  # e.g. "fixes bug 12345 - something"

        result = payload['result']
        result_message = payload['result_message']

        section_key = '%s/%s' % (repo_owner, repo_name)
        if not config.has_section(section_key):
            return make_response('No section called %s' % section_key, 400)
        try:
            irc = config.get(section_key, 'irc')
            if irc.startswith('#'):
                irc = 'irc.mozilla.org' + irc
        except ConfigParser.NoOptionError:
            irc = None
        try:
            config.get(section_key, 'github')
            github = True
        except ConfigParser.NoOptionError:
            github = False

        if not (irc or github):
            return make_response('Neither IRC or GitHub notifications :(', 400)
        print (irc, github)

        if irc:
            print "IRC does not work yet"
            # server = irc.split('#')[0]
            # if ':' in server:
            #     server, port = server.split(':')
            # else:
            #     port = 6667
            # channel = '#' + irc.split('#')[1]
            # self._send_irc_message(
            #     server,
            #     port,
            #     channel,
            #     "The test results are in: %s" % result_message
            # )
        if github:
            pull_request_number = payload['pull_request_number']
            if result > 0:
                # it failed
                msg = "[Build %s](%s) unfortunately **failed**\n" % (
                    payload['number'],
                    payload['build_url']
                )
                msg += random_negative_emoji()
            else:
                # it succeeded
                msg = "[Build %s](%s) finished **successfully**!\n" % (
                    payload['number'],
                    payload['build_url']
                )
                msg += random_positive_emoji()

            self._send_pr_comment(
                repo_owner,
                repo_name,
                pull_request_number,
                msg
            )

        return make_response('OK')

    def _send_pr_comment(self, owner, repo, pull, message):
        url = 'https://api.github.com/repos/%s/%s/issues/%s/comments' % (
            owner,
            repo,
            pull
        )
        print url
        r = requests.post(
            url,
            data=json.dumps({
                'body': message
            }),
            headers={
                'Authorization': 'token %s' % GITHUB_OAUTH_TOKEN
            }
        )
        if r.status_code != 201:
            print r.status_code
            print r.content
            raise Exception("Failed to post to GitHub: %s (%r)" % (
                r.status_code,
                r.content
            ))


    # def _send_irc_message(self, server, port, channel, message):
    #     sock = socket.socket()
    #     sock.connect((server, port))
    #
    #
    #     def send(msg):
    #         sock.send(msg + '\r\n')
    #
    #     send("NICK %s" % IRC_NICK)
    #     send("USER %(nick)s %(nick)s %(nick)s :%(nick)s" % {'nick': IRC_NICK})
    #     send("PRIVMSG R : Login <>")
    #     send("MODE %s +x" % IRC_NICK)
    #     send("JOIN %s" % channel)
    #     send("PRIVMSG %s :%s" % (channel, message))
    #



app.add_url_rule('/webhook', view_func=WebhookView.as_view('webbook'))


if __name__ == '__main__':
    app.debug = DEBUG
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    app.run(host=host, port=port)
