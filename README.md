# pve-setup
PVE安装之后，用于部署和服务的基础配置脚本和说明

## Primary Config & Mirrors 

### PVE Mirror help ###
* [TUNA Mirror](https://mirrors.tuna.tsinghua.edu.cn/help/proxmox/)
* [USTC Mirror](https://mirrors.ustc.edu.cn/help/proxmox.html)

### Turnkey-Linux Mirror help ###
* [USTC Turnkey-Linux Mirror](https://mirrors.ustc.edu.cn/help/turnkeylinux.html)


### SSH key Config
[How to Set Up SSH Keys on Debian 11](https://www.digitalocean.com/community/tutorials/how-to-set-up-ssh-keys-on-debian-11)
```sh
cat ~/.ssh/id_rsa.pub | ssh username@remote_host "mkdir -p ~/.ssh && touch ~/.ssh/authorized_keys && chmod -R go= ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

### Misc

[PVE Bootloader & Grub Recover](https://pve.proxmox.com/wiki/Recover_From_Grub_Failure)

## Software

### Useful tools

```
apt install git htop iotop tree zip unzip uuid-runtime debsums
```

### Thrid-party software
* [fd-find](https://github.com/sharkdp/fd/releases/latest) 文件快速查找
* [ripgrep](https://github.com/BurntSushi/ripgrep/releases/latest) 文本快速搜多
* [dust](https://github.com/bootandy/dust/releases/latest) 目录空间占用统计
* [rathole](https://github.com/rapiz1/rathole/releases/latest) 网络服务打洞穿透
* [bandwhich](https://github.com/imsnif/bandwhich/releases/latest) 带宽监控



### Software config

#### Rathole SSH Passthrough

server config
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

## Filesystem Maintenance

文件系统维护的基本命令

### BTRFS

* btrfs的subvolume名称直接通过mv即可修改
* btrfs的挂载参数不能指定`uid`和`gid`，直接使用`chown`命令修改`/tmp/btrfs-full/<vol_name>`即可

#### Example
```sh

mkfs.btrfs -L <label> /dev/sda # base
mkfs.btrfs -L <label> -d raid1 -m raid1 -f /dev/sda /dev/sdb # raid1

mount --mkdir /dev/sda /tmp/btrfs-full # mount btrfs root
btrfs subvol create /tmp/btrfs-full/<vol_name>
mount --mkdir /dev/sda -o rw,relatime,compress=zstd:3,subvol=<vol_name> /mnt

# 通过inode查找定位文件地址
btrfs inspect-internal inode-resolve <inode_num>
```

#### 参考文档
* [Btrfs doc](https://btrfs.readthedocs.io/en/latest/btrfs.html)
* [Btrfs RAID](https://cn.linux-console.net/?p=16437)
* [Arch Linux+btrfs](https://blog.azurezeng.com/archlinux-with-btrfs-simple-guide/)

### ZFS

* `zpool`用于管理顶层的存储池
* `zfs`管理zfs文件系统和卷，权限，创建子卷
* zfs可以直接使用pve web界面也可以创建
* zfs import之后默认会自动挂载到根目录，自动递归挂载子卷


#### Example
```sh
zpool import # 显示所有未加载zfs磁盘
zpool import <pool_name> # 主机导入zfs存储池，导入一次永久导入
zpool import -f <pool_name> # 从其他主机导入
zpool list # 显示所有已经导入的存储池
zpool export <pool_name> # 弹出存储池
zpool status # 显示zpool存储池的状态
```

#### 参考文档
* [Oracle Create&Destory ZFS pool](https://docs.oracle.com/cd/E26926_01/html/E25826/zfsover-1.html)
* [Open ZFS](https://openzfs.github.io/openzfs-docs/Getting%20Started/index.html)

### LVM

    TODO


## [Disk-Mount](Mount-Disk.md)

