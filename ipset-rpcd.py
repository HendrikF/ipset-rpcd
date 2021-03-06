from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer
import six
import subprocess
import logging
import argparse
from six.moves import configparser

EXIT_OK = ["OK"]  # We need to always return an array
EXIT_ERROR = ["Error"]


def start(user, mac, ip, role, timeout):
    logging.info((
        'Updating entries for {user} ({mac}, {ip}, {role}) '
        'with timeout {timeout}').format(
        user=user, mac=mac, ip=ip, role=role, timeout=timeout))

    action = 'add'
    okay = update_user(**locals())

    return EXIT_OK if okay else EXIT_ERROR


def stop(user, mac, ip, role, timeout):
    logging.info((
        'Removing entries for {user} ({mac}, {ip}, {role}) '
        ).format(
        user=user, mac=mac, ip=ip, role=role))

    action = 'remove'
    okay = update_user(**locals())

    return EXIT_OK if okay else EXIT_ERROR


def update_user(action, user, mac, ip, role, timeout):
    args = locals().copy()

    try:
        roles = [role.strip() for role in config.get('roles', role).split(',')]
    except (configparser.NoOptionError, configparser.NoSectionError), e:
        roles = []

    try:
        services = [user.strip() for user in config.get('users', user).split(',')]
    except (configparser.NoOptionError, configparser.NoSectionError), e:
        services = []

    okay = True
    for ipset in roles + services:
        args.update({'ipset': ipset})
        if not update_ipset(**args):
            okay = False
    return okay


def update_ipset(ipset, action, user, mac, ip, role, timeout):
    if action not in ['add', 'remove']:
        logging.error('Unknown action {}'.format(action))
        return False

    try:
        items = config.get('ipsets', ipset)
    except (configparser.NoOptionError, configparser.NoSectionError), e:
        items = "{ip}"

    logging.debug((
        'User {user}: {action} ipset {ipset} with items {items}').format(
        user=user, action=action, ipset=ipset, items=items))

    args = [
        "sudo", "-n", "ipset",
        str(action), "-exist", str(ipset),
        items.format(ip=ip, mac=mac)
        ]

    if action == 'add':
        args = args + [
            "timeout", str(timeout),
            "comment", str(user)
            ]

    ret = subprocess.call(args)
    return ret == 0


if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(level=logging.DEBUG)

    # Parse commandline
    parser = argparse.ArgumentParser(
        description='JSON-RPC daemon',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--bind', default='127.0.0.1',
                        help='the ip address to bind to')
    parser.add_argument('--port', type=int, default='9090',
                        help='the port to listen on')
    parser.add_argument('--config', default='ipset.conf',
                        help='config file to read ipset mapping from')
    args = parser.parse_args()

    # Init config file
    config = configparser.ConfigParser()
    if not config.read(args.config):
        logging.warn("No config file was loaded")

    # Start server
    logging.info("Starting JSON-RPC daemon at {bind}:{port}...".format(
        bind=args.bind,
        port=args.port,
    ))
    server = SimpleJSONRPCServer((args.bind, args.port))
    server.register_function(start, 'Start')
    server.register_function(start, 'Update')
    server.register_function(stop, 'Stop')
    server.serve_forever()
