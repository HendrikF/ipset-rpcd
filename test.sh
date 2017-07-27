#!/bin/sh

# Script to test the correct working of ipset-rpcd
# 1. Start this with --server to start ipset-rpcd in test mode
# 2. Run this without arguments to send requests to ipset-rpcd

python="python2"
port=9091
testlog="test.log"
testconfig="test-ipsets.conf"

if [ "$#" -ge 1 ]; then
    if [ "$1" = "--server" ]; then
        # setup config
        cat > "$testconfig" <<EOF
[ipsets]
role-default = {ip},{mac}

[roles]
default = role-default

[users]
TESTUSER = service-1, service-2
EOF
        # start ipset-rpcd in test mode and let it call this script
        $python ipset-rpcd.py --port "$port" --config "$testconfig" --test "$0"
        [ -f "$testconfig" ] && rm "$testconfig"
    else
        # called by ipset-rpcd
        echo "$@" >> "$testlog"
    fi
    exit 0
fi

[ -f "$testlog" ] && rm "$testlog"

# Start
echo "Testing Start:" >> "$testlog"
curl -d '{"jsonrpc":"2.0","method":"Start","params":{"user":"TESTUSER","mac":"00:11:22:33:44:55","ip":"1.2.3.4","role":"default","timeout":86400},"id":42}' "http://localhost:$port"
echo ""

# Update
echo "Testing Update:" >> "$testlog"
curl -d '{"jsonrpc":"2.0","method":"Update","params":{"user":"TESTUSER","mac":"00:11:22:33:44:55","ip":"1.2.3.4","role":"default","timeout":86400},"id":42}' "http://localhost:$port"
echo ""

# Stop
echo "Testing Stop:" >> "$testlog"
curl -d '{"jsonrpc":"2.0","method":"Stop","params":{"user":"TESTUSER","mac":"00:11:22:33:44:55","ip":"1.2.3.4","role":"default","timeout":86400},"id":42}' "http://localhost:$port"
echo ""

# Expected log content
cat > "$testlog.expected" <<EOF
Testing Start:
add -exist role-default 1.2.3.4,00:11:22:33:44:55 timeout 86400 comment TESTUSER
add -exist service-1 1.2.3.4 timeout 86400 comment TESTUSER
add -exist service-2 1.2.3.4 timeout 86400 comment TESTUSER
Testing Update:
add -exist role-default 1.2.3.4,00:11:22:33:44:55 timeout 86400 comment TESTUSER
add -exist service-1 1.2.3.4 timeout 86400 comment TESTUSER
add -exist service-2 1.2.3.4 timeout 86400 comment TESTUSER
Testing Stop:
remove -exist role-default 1.2.3.4,00:11:22:33:44:55
remove -exist service-1 1.2.3.4
remove -exist service-2 1.2.3.4
EOF

diff "$testlog.expected" "$testlog"
status="$?"
if [ "$status" -ne 0 ]; then
    echo "Failed"
    exit 1
else
    rm "$testlog.expected"
    rm "$testlog"
    echo "Passed"
    exit 0
fi
