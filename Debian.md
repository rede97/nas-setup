# debian setup

Debian 建立NAS服务的一些操作记录和避坑

## Base Software

debian的基础软件包比较简单，需要较多的配置，openssh server也需要手动安装

```sh
# base tools
apt install ssh pipx wget axel htop iotop git tree attr net-tools udevil zip unzip uuid-runtime debsums psmisc 

apt install samba smbclient cifs-utils wsdd
# nfs server
apt install nfs-kernel-server

# Nvidia driver base
apt install build-essential pkg-config libglvnd-dev

# mate desktop open terminal
apt install caja-open-terminal
```


### systemd 挂载

* [systemd.mount](https://www.jinbuguo.com/systemd/systemd.mount.html)

### incus & lxc-mirror 容器工具

incus用于取代pve的容器管理工具，Debian 12软件源需要打开`backports`

* [incus](https://linuxcontainers.org/incus/)
* [lxc-mirror](https://mirrors.tuna.tsinghua.edu.cn/help/lxc-images/)

### 无脑nas部署 CasaOS
基于docker，目前功能尚不成熟
* [CasaOS](https://casaos.io/)


## 部署Samba

Samba 建议本地部署最为方便，docker中的turnkeylinux已经停止更新，不需要向虚拟机使用virtio-fs映射目录或者docker映射目录，同时权限管理也最为简单。文件传输效率更高，开销更低。

* Samba的用户在本地模式下，需要与Unix用户对应，基于安全考虑建议设置独立的密码
* [smb.conf doc](https://www.samba.org/samba/docs/current/man-html/smb.conf.5.html)
* [smb.conf recycle doc](https://www.samba.org/samba/docs/current/man-html/vfs_recycle.8.html)

```ini
#/etc/samba/smb.conf
;client min protocol = NT1
;server min protocol = NT1

# 错误的账户会被映射到guest
map to guest = bad user
# 错误的用户和密码不能登录，不允许映射到guest
map to guest = Never

# 共享子项是否默认允许guest用户
usershare allow guests = no

[homes]
   comment = Home Directories
# 共享使能
   available = yes
# 显示homes目录、与用户名相同
   browseable = no
   read only = yes
   create mask = 0700
   directory mask = 0700
# 支持username、@表示NIS group -> unix group、+表示 unix group、&表示NIS group
# %S用于访问用户名的home目录
   valid users = %S
# 禁止访问该共享的用户
   invalid users = 
# 支持写操作的用户，覆盖read only操作
   write list = 
   guest ok = no

[data]
    comment = Data dir
# 共享路径
    path = /srv/storage/data
    read only = no
    valid users = @users
# 继承目录的user owner
    inherit owner = no
# 强制owner group
    force group = users
# 载入Samba用于回收站功能的模块recycle.so
    vfs object = recycle
	recycle:repository = .recycle/%U
	recycle:keeptree = yes
	recycle:versions = yes
    recycle:maxsixe = 0

[upload_only]
    # 上传的文件继承父目录的所有者, 而不是使用登录的账号名
    inherit owner = Yes
    # 允许上传操作
    writable = Yes      
    # 上传的文件没有写权限
    create mask = 1774
    # 上传的目录具有所有权限
    directory mask = 1777
     # 上传的目录设置 t 标志
    force directory mode = 1000
```


### 测试

```sh
# samba 参数设置
testparm /etc/samba/smb.conf
systemctl restart smb
# 列出samba共享的子项
smbclient -L localhost -U user%password
# 连接smaba到共享目录
smbclient //localhost/data -U user%password
```

## 启动网络发现

Windows 10开始禁用Samba v1的发现功能，建议使用Web Service Discovery，Debian 建议使用wsdd开启网络发现功能，从Debian12开始内置。
```sh
sudo systemctl start wsdd && sudo systemctl enable wsdd
```

## 部署webdav

