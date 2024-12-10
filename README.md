# pve-setup
PVE安装之后，用于部署和服务配置脚本和说明

## Primary Config & Mirrors 

### SSH key Config
[How to Set Up SSH Keys on Debian 11](https://www.digitalocean.com/community/tutorials/how-to-set-up-ssh-keys-on-debian-11)
```sh
cat ~/.ssh/id_rsa.pub | ssh username@remote_host "mkdir -p ~/.ssh && touch ~/.ssh/authorized_keys && chmod -R go= ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

### PVE Mirror help ###
* [TUNA Mirror](https://mirrors.tuna.tsinghua.edu.cn/help/proxmox/)
* [USTC Mirror](https://mirrors.ustc.edu.cn/help/proxmox.html)

### Turnkey-Linux Mirror help ###
* [USTC Turnkey-Linux Mirror](https://mirrors.ustc.edu.cn/help/turnkeylinux.html)

## Software

### Useful tools

```
sudo apt install git htop tree zip unzip uuid-runtime
```

### Thrid-party software
* [fd-find](https://github.com/sharkdp/fd/releases/latest)
* [ripgrep](https://github.com/BurntSushi/ripgrep/releases/latest)
* [rathole](https://github.com/rapiz1/rathole/releases/latest)



### Software config

#### SSH Passthrough

server config:
```toml
# server.toml
[server]
bind_addr = "0.0.0.0:LISTEN_PORT" # `LISTEN_PORT` specifies the port that rathole listens for clients

[server.services.my_ssh]
token = "UUID" # Token that is used to authenticate the client for the service. Change to an arbitrary value.
bind_addr = "0.0.0.0:SERVICE_PORT" # `SERVER_PORT` specifies the port that exposes `my_ssh` to the Internet
```

client config
```toml
# /etc/client.toml
[client]
remote_addr = "SERVER_IP:LISTEN_PORT" # The address of the server. The port must be the same with the port in `server.bind_addr`

[client.services.my_ssh]
token = "UUID" # Must be the same with the server to pass the validation
local_addr = "127.0.0.1:22" # The address of the service that needs to be forwarded
```

systemd service template
```
#/etc/systemd/system/rathole.service 
[Unit]
Description=rathole tunnel service
Wants=network-online.target
After=network.target network-online.target ssh.service

[Service]
Type=simple
Restart=always
RestartSec=5
Nice=-20
IOSchedulingClass=realtime
ExecStart=/usr/bin/rathole /etc/config.toml

[Install]
WantedBy=multi-user.target
```

## Disk Maintenance tools

### BTRFS

### ZFS
