#!/usr/bin/env bash

# Copyright 2025 Genesis Corporation
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

set -eu
set -x
set -o pipefail

[[ "$EUID" == 0 ]] || exec sudo -s "$0" "$@"

SERVER_NAME=server

GC_PATH="/opt/genesis_dns"
GC_CFG_DIR=/etc/genesis_dns
VENV_PATH="$GC_PATH/.venv"

GC_PG_USER="genesis_dns"
GC_PG_PASS="pass"
GC_PG_DB="genesis_dns"

SYSTEMD_SERVICE_DIR=/etc/systemd/system/

apt update
apt install -y \
    postgresql \
    libev-dev \
    python3.12-venv \
    python3-dev

# Default creds for genesis notification services
sudo -u postgres psql -c "CREATE ROLE $GC_PG_USER WITH LOGIN PASSWORD '$GC_PG_PASS';"
sudo -u postgres psql -c "CREATE DATABASE $GC_PG_USER OWNER $GC_PG_DB;"

# Install service
mkdir -p $GC_CFG_DIR
cp "$GC_PATH/etc/genesis_dns/genesis_dns.conf" $GC_CFG_DIR/
cp "$GC_PATH/etc/genesis_dns/logging.yaml" $GC_CFG_DIR/

mkdir -p "$VENV_PATH"
python3 -m venv "$VENV_PATH"
source "$GC_PATH"/.venv/bin/activate
pip install pip --upgrade
pip install -r "$GC_PATH"/requirements.txt
pip install -e "$GC_PATH"

# Apply migrations
ra-apply-migration --config-dir "$GC_CFG_DIR/" --path "$GC_PATH/migrations"
deactivate

# Create links to venv
ln -sf "$VENV_PATH/bin/genesis-dns-user-api" "/usr/bin/genesis-dns-user-api"

# Install Systemd service files
cp "$GC_PATH/etc/systemd/genesis-dns-user-api.service" $SYSTEMD_SERVICE_DIR

# Enable genesis notification services
systemctl enable \
    genesis-dns-user-api

# Prepare powerdns

# Install packages
apt update
apt install pdns-backend-pgsql pdns-server -y

rm /etc/powerdns/pdns.d/bind.conf
cp "$GC_PATH/etc/powerdns/genesis.conf" /etc/powerdns/pdns.d/genesis.conf
