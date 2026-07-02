# Matrix Synapse Deployment on Debian 13

A production-ready Ansible playbook that deploys a Matrix homeserver on a fresh Debian 13 VPS with full SSH and server hardening.

## What This Does

| Role | Description |
|------|-------------|
| `base-hardening` | Updates packages, creates sudo user, locks SSH to key-only on a custom port, configures UFW firewall, fail2ban, sysctl kernel hardening, unattended security upgrades, NTP |
| `matrix-synapse` | Installs Synapse + PostgreSQL from Debian packages, creates database, generates signing key, deploys production `homeserver.yaml` with systemd sandboxing |
| `nginx-reverse-proxy` | Installs nginx + certbot, obtains Let's Encrypt TLS cert, configures reverse proxy to Synapse on 8008, serves `.well-known/matrix` delegation, auto-renews certs |

## Architecture

```
Internet ──443──→ nginx (TLS) ──8008──→ Synapse (localhost)
            └──8448──→ nginx (TLS) ──8008──→ Synapse (federation)
                              PostgreSQL (localhost:5432)
```

## Prerequisites

- A fresh Debian 13 VPS with root SSH access
- A domain name pointed at your VPS IP (A/AAAA records for `matrix.example.com`)
- Your SSH public key on your local machine
- Ansible installed on your local machine (`pip install ansible` or `apt install ansible-core`)

## Setup

### 1. Edit `group_vars/all.yml`

This is the fileglobals file. Every `CHANGE_ME` must be set:

```yaml
matrix_domain: matrix.example.com
matrix_server_name: example.com
matrix_homeserver_name: matrix.example.com
matrix_admin_user: "@liam:example.com"

deployer_ssh_public_key: "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIyourrealkey liam@workstation"
ssh_port: 2222
deployer_username: liam
deployer_password_hash: "$6$rounds=656000$..."  # Generate with: openssl passwd -6
matrix_db_password: "a-strong-random-password"
letsencrypt_email: "admin@example.com"
```

Generate the password hash locally:
```bash
openssl passwd -6
```

### 2. Edit `inventory/hosts.yml`

```yaml
all:
  hosts:
    matrix-vps:
      ansible_host: 203.0.113.10    # Your VPS IP
      ansible_user: root
```

### 3. Copy your SSH key to the VPS (first run only)

```bash
ssh-copy-id root@203.0.113.10
```

### 4. Run the playbook

```bash
# Dry run first
ansible-playbook site.yml --check

# Full deploy
ansible-playbook site.yml
```

If you restricted SSH to your IP range, make sure `allowed_ssh_networks` includes your current IP before you lock yourself out.

### 5. Point DNS and run

Make sure DNS for `matrix.example.com` resolves to your VPS before running — certbot needs that for Let's Encrypt verification.

### 6. Create your admin user

After deployment, SSH into the server and create your first admin user:

```bash
ssh -p 2222 liam@<your-vps-ip>
register_new_matrix_user -a -c /etc/matrix-synapse/homeserver.yaml https://localhost:8008
```

### 7. Connect a client

Use Element (https://app.element.io) or any Matrix client:
- Server: `https://matrix.example.com`
- Username: the admin user you created
- Password: the one you set

## Verification

After deployment, verify the server is reachable:

```bash
# Check the federation API
curl https://matrix.example.com/_matrix/federation/v1/version

# Should return something like:
# {"server":{"name":"Synapse","version":"1.x.x"}}

# Check .well-known delegation
curl https://matrix.example.com/.well-known/matrix/server
# Should return: {"m.server":"matrix.example.com:443"}

# Check client API
curl https://matrix.example.com/_matrix/client/versions
```

## Post-Deployment Checklist

- [ ] DNS records created for `matrix.example.com`
- [ ] Firewall allows ports 2222 (SSH), 80/443 (HTTP/HTTPS), 8448 (federation)
- [ ] TLS certificate obtained and auto-renewing
- [ ] Admin user created
- [ ] Test sending a message via a Matrix client
- [ ] Verify federation by joining a room on another homeserver (e.g., #test:matrix.org)
- [ ] Configure backups for `/var/lib/matrix-synapse` and PostgreSQL

## Security Features

| Feature | Status |
|---------|--------|
| SSH key-only auth | ✅ |
| Non-standard SSH port | ✅ |
| Root login disabled | ✅ |
| UFW firewall (deny by default) | ✅ |
| fail2ban (SSH + recidive jails) | ✅ |
| Kernel hardening (sysctl) | ✅ |
| Unattended security upgrades | ✅ |
| Synapse systemd sandboxing | ✅ |
| TLS 1.2/1.3 via Let's Encrypt | ✅ |
| HSTS header | ✅ |
| Passwordless sudo for deployer | ✅ |

## File Structure

```
matrix-ansible-deploy/
├── ansible.cfg
├── site.yml                 # Main playbook — runs roles in order
├── group_vars/
│   └── all.yml             # All configuration variables (edit this)
├── inventory/
│   └── hosts.yml           # Target VPS connection details
└── roles/
    ├── base-hardening/
    │   ├── defaults/main.yml
    │   ├── handlers/main.yml
    │   ├── tasks/main.yml
    │   └── templates/
    │       ├── sshd_config.j2
    │       ├── jail.local.j2
    │       ├── sysctl-hardening.conf.j2
    │       └── 50unattended-upgrades.j2
    ├── matrix-synapse/
    │   ├── defaults/main.yml
    │   ├── handlers/main.yml
    │   ├── tasks/main.yml
    │   ├── files/
    │   │   └── generate_signing_key.py
    │   └── templates/
    │       ├── homeserver.yaml.j2
    │       └── log.config.j2
    └── nginx-reverse-proxy/
        ├── defaults/main.yml
        ├── handlers/main.yml
        ├── tasks/main.yml
        └── templates/
            ├── nginx-http-only.conf.j2
            └── nginx-matrix.conf.j2
```

## Notes

- **Debian 13**: Ships `matrix-synapse` natively. If you need a newer version, switch to the matrix.org APT repo or run Synapse in a container.
- **PostgreSQL**: Runs locally on the same host. For higher scale, move PostgreSQL to a separate server and update the `database.host` in the homeserver template.
- **Federation port 8448**: This is the legacy federation port. Modern Matrix clients use `.well-known` delegation to route federation over 443. Keep 8448 open for backward compatibility with older homeservers.
- **Registration**: Disabled by default. Set `enable_registration: true` and create a strong `registration_shared_secret` if you want open registration (not recommended for personal servers).

## Troubleshooting

### Can't SSH after hardening
The playbook changes the SSH port and disables password auth. Connect with:
```bash
ssh -p 2222 liam@<your-vps-ip>
```

### certbot fails
DNS must resolve to your VPS before running. Verify with:
```bash
dig matrix.example.com
```

### Synapse won't start
Check the logs:
```bash
journalctl -u matrix-synapse -n 50 --no-pager
```

### Database connection errors
Verify PostgreSQL is running and the user exists:
```bash
sudo -u postgres psql -c "\du synapse"
sudo -u postgres psql -c "\l synapse"
```