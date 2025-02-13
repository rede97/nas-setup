# pve setup
PVE安装之后，用于部署NAS等服务的基础配置脚本、说明和注意事项

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

### apt 安装历史记录
```sh
grep " install " /var/log/dpkg.log
```

### 检查文件目录占用
```sh
lsof /mnt
fuser /mnt
```

### 参考文档

* [PVE Bootloader & Grub Recover](https://pve.proxmox.com/wiki/Recover_From_Grub_Failure)
* [apt history](https://cn.linux-console.net/?p=15827)

## Software

### Useful tools

```sh
apt install git htop iotop tree zip unzip uuid-runtime debsums
```

### Thrid-party software
* [fd-find](https://github.com/sharkdp/fd/releases/latest) 文件快速查找
* [ripgrep](https://github.com/BurntSushi/ripgrep/releases/latest) 文本快速搜索
* [dust](https://github.com/bootandy/dust/releases/latest) 目录空间占用统计
* [bandwhich](https://github.com/imsnif/bandwhich/releases/latest) 带宽监控
* [rathole](https://github.com/rapiz1/rathole/releases/latest) 网络服务打洞穿透



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
```ini
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


如果是openwrt实用init.d启动rathole服务
```sh
#!/bin/sh /etc/rc.common
START=99
USE_PROCD=1

start_service() {
    procd_open_instance
    procd_set_param command /usr/bin/rathole /etc/client.toml
    procd_close_instance
}

```
```sh
ln -s /etc/init.d/rathole /etc/rc.d/
```

## Filesystem

文件系统维护的基本命令

### BTRFS

* btrfs的`subvolume`名称直接通过`mv /tmp/btrfs-full/<vol_name> /tmp/btrfs-full/<new_vol_name>`即可修改 
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


## 磁盘挂载
挂载磁盘的方法、配置以及注意事项

## 映射挂载点到容器

* 进行idmap映射，包括`/etc/subuid`和`/etc/subgid`还有`/etc/pve/lxc/<id>.conf`
* 如果希望将挂载点或者目录映射到`container`中必须保证至少一点：
    1. lxc的`mountpoint host`目录是磁盘的直接挂载点
    2. 如果lxc的`mountpoint host`目录是磁盘挂载点的`parent dir`，必须保证磁盘挂载行为发生在容器启动之后

* 在host中对第一次映射到容器的目录重新进行`chown`，才能正常完成映射，如果容器的id map变动，也必须重新chown


### 参考文档

* [proxmox-lxc-idmapper](https://github.com/ddimick/proxmox-lxc-idmapper)
* [Unprivileged LXC containers](https://pve.proxmox.com/wiki/Unprivileged_LXC_containers)

## systemd.mount方式
这种方式可以开机启动挂载，并且控制挂载的启动顺序，磁盘变动也不会影响fstab。

* 缺点是一次只能挂载一个磁盘，每个挂载任务一个文件，不方便集中管理。容器重启挂载点也需要重新跟随重启。
* 保证systemd.mount的文件名与`Where`挂载目录保持一致，`\`使用`-`替换

### Example
```ini
#/etc/systemd/system/srv-storage-data.mount
[Unit]
Description=Mount data disk

[Mount]
What=UUID=<uuid>
Where=/srv/storage/data
Type=btrfs
Options=defaults,rw,compress=zstd,subvol=data

[Install]
WantedBy=multi-user.target
```

## autofs（不推荐）
自动挂载文件系统，直接`cd`、`ls`到对应目录，文件系统才会挂载。支持网络文件系统smb、nfs、本地文件系统btrfs、ext4、exfat等等，超时后会自动卸载设备以节省资源。可以避免磁盘变更到导致fstab挂载失败，从而系统启动失败

* 这种挂载方式不能将磁盘映射到lxc容器中！

## USB自动挂载

折衷的办法是使用`udevil`，目前相对来说可以只用，可以将U盘挂载到用户下

```sh
apt install udevil
nano /etc/udevil/udevil.conf # 只允许USB挂载exfat ntfs只读，禁止btrfs等等文件系统

systemctl start devmon@jack.service
systemctl enable devmon@jack.service
```

#### 避坑
* udevil在挂载exfat磁盘的时候会导致挂载失败，原因是参数加入了`nonempty`，`mount`现在并不支持
* 如果容器重启，devmon.service任务必须重启或者usb设备重新拔插触发重新挂载

### 参考文档
* [automount-pve](https://github.com/theyo-tester/automount-pve) 该项目的自动挂载脚本与zfs自动挂载纯在冲突，谨慎使用

## 存储服务

建议使用`turnkeylinux-filesever`，可以提供webdav、nfs、samba等服务，同时支持域控服务。
* samba用户与unix用户是独立的，创建unix用户后需要进行用户转换，

* [TurnKey File Server](https://post.smzdm.com/p/avp42wn7/)


## 其他参考项目
* [Mount Volumes into Proxmox VMs with Virtio-fs](https://gist.github.com/Drallas/7e4a6f6f36610eeb0bbb5d011c8ca0be)
* [aquar-build-helper](https://github.com/firemakergk/aquar-build-helper)


## 总结

pve在个人、家庭`all in one`的场景中并不适用。每个用户的容器的权限映射和管理非常麻烦，PVE以及提供的turnkeylinux容器主要针对具有Linux AD域的如NIS、LDAP的企业服务场景。个人在Linux中使用`cockpit`是更好的选择。
