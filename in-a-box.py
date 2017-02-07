# coding=utf-8
from __future__ import print_function
import os
import socket
import sys
import distutils.spawn
from string import Template
from subprocess import check_output, call, STDOUT, PIPE
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse


if 'raw_input' not in dir():
    raw_input = input


dockerTemplate = '''
version: '2'
services:
    api:
        image: screwdrivercd/screwdriver:stable
        ports:
            - 9001:80
        volumes:
            - /var/run/docker.sock:/var/run/docker.sock:rw
        environment:
            PORT: 80
            URI: http://${ip}:9001
            ECOSYSTEM_UI: http://${ip}:9000
            ECOSYSTEM_STORE: http://${ip}:9002
            DATASTORE_PLUGIN: sequelize
            DATASTORE_SEQUELIZE_DIALECT: sqlite
            EXECUTOR_PLUGIN: docker
            SECRET_WHITELIST: "[]"
            EXECUTOR_DOCKER_DOCKER: |
                {
                    "socketPath": "/var/run/docker.sock"
                }
            SECRET_OAUTH_CLIENT_ID: ${oauth_id}
            SECRET_OAUTH_CLIENT_SECRET: ${oauth_secret}
            SECRET_JWT_PRIVATE_KEY: |
${private_key}
            SECRET_JWT_PUBLIC_KEY: |
${public_key}
    ui:
        image: screwdrivercd/ui:stable
        ports:
            - 9000:80
        environment:
            ECOSYSTEM_API: http://${ip}:9001

    store:
        image: screwdrivercd/store:stable
        ports:
            - 9002:80
        environment:
            URI: http://${ip}:9002
            SECRET_JWT_PUBLIC_KEY: |
${public_key}
'''


def get_ip_address():
    """
    Check IP locally if running in a docker-machine from docker-toolbox
    otherwise, get IP by poking at Google's DNS.

    Note
    ----
    docker-for-mac does not set DOCKER environment variables
    """
    if os.environ.get('DOCKER_HOST'):
        url = urlparse(os.environ['DOCKER_HOST'])
        return url.hostname
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]


def pad_lines(lines, length):
    """
    Left pad set of lines with spaces
    """
    return '\n'.join(map((lambda row: ''.rjust(length, ' ') + row), lines.split('\n')))


# Generate a new JWT
def generate_jwt():
    junk = check_output(['openssl', 'genrsa', '-out', 'jwt.pem', '1024'], stderr=STDOUT)
    junk = check_output(['openssl', 'rsa', '-in', 'jwt.pem', '-pubout', '-out', 'jwt.pub'], stderr=STDOUT)
    jwtPrivate = open('jwt.pem', 'r').read()
    jwtPublic = open('jwt.pub', 'r').read()
    junk = check_output(['rm', 'jwt.pem', 'jwt.pub'], stderr=STDOUT)

    return {
        'public_key': pad_lines(jwtPublic, 16),
        'private_key': pad_lines(jwtPrivate, 16)
    }


# Generate OAuth credentials from GitHub.com
def generate_oauth(ip):
    print(Template('''
    Please create a new OAuth application on GitHub.com
    Go to https://github.com/settings/applications/new to start the process
    For 'Homepage URL' put http://${ip}:9000
    For 'Authorization callback URL' put http://${ip}:9001/v4/auth/login
    When done, please provide the following values:
    ''').substitute(ip=ip))

    id = raw_input('    Client ID: ');
    secret = raw_input('    Client Secret: ');

    print('')
    return {
        'oauth_id': id,
        'oauth_secret': secret
    }


def check_component(component):
    if distutils.spawn.find_executable(component) == None:
        print('💀   Could not find {0}, please install and set path to {0}'.format(component))
        sys.exit(1)


def main():
    fields = {
        'ip': get_ip_address()
    }
    print('🎁   Boxing up Screwdriver')

    print('👀   Checking prerequisites')
    check_component('docker')
    check_component('docker-compose')
    check_component('openssl')

    print('🔐   Generating signing secrets')
    fields = dict(fields, **generate_jwt())

    print('📦   Generating OAuth credentials')
    fields = dict(fields, **generate_oauth(fields['ip']))

    print('💾   Writing Docker Compose file')
    compose = Template(dockerTemplate).substitute(fields)
    open('docker-compose.yml', 'w').write(compose)

    print('🚀   Screwdriver is ready to launch!')
    print(
        Template('''
    Just run the following commands to get started!
      $ docker-compose pull
      $ docker-compose -p screwdriver up -d
      $ open http://${ip}:9000
    ''').safe_substitute(fields)
    )
    prompt = raw_input('    Would you like to run them now? (y/n) ')
    if prompt.lower() == 'y':
        call('docker-compose pull', shell=True)
        call('docker-compose -p screwdriver up -d', shell=True)
        call(Template('open http://${ip}:9000').safe_substitute(fields), shell=True)
        print('\n👍   Launched!')
    else:
        print('\n👍   Skipping launch (for now)')

    print('''
    A few more things to note:
      - To stop/reset Screwdriver
        $ docker-compose -p screwdriver down
      - If your internal IP changes, update the docker-compose.yml and your GitHub OAuth application
      - In-a-box does not support Webhooks including PullRequests for triggering builds
      - For help with this and more, find us on Slack at https://slack.screwdriver.cd

❤️   Screwdriver Crew
    ''')


if __name__ == "__main__":
    main()
