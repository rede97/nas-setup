# Mount Disk

挂载磁盘的方法、配置以及注意事项


## 映射挂载点到容器

* 进行idmap映射，包括`/etc/subuid`和`/etc/subgid`还有`/etc/pve/lxc/<id>.conf`
* 如果希望将挂载点或者目录映射到`container`中必须保证至少一点：
    1. lxc的`mountpoint host`目录是磁盘的直接挂载点
    2. 如果lxc的`mountpoint host`目录是磁盘挂载点的`parent dir`，必须保证磁盘挂载行为发生在容器启动之后

* 在host中对第一次映射到容器的目录重新进行`chown`，才能正常完成映射


### 参考文档

* [Unprivileged LXC containers](https://pve.proxmox.com/wiki/Unprivileged_LXC_containers)

## systemd.mount方式
这种方式可以开机启动挂载，并且控制挂载的启动顺序，磁盘变动也不会影响fstab。

* 缺点是一次只能挂载一个磁盘，每个挂载任务一个文件，不方便集中管理。容器重启挂载点也需要重新跟随重启。
* 保证systemd.mount的文件名与`Where`挂载目录保持一致，`\`使用`-`替换

### Example
```sh
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

## USB自动挂载


## autofs（不推荐）
自动挂载文件系统，直接`cd`、`ls`到对应目录，文件系统才会挂载。支持网络文件系统smb、nfs、本地文件系统btrfs、ext4、exfat等等，超时后会自动卸载设备以节省资源。可以避免磁盘变更到导致fstab挂载失败，从而系统启动失败

* 这种挂载方式不能将磁盘映射到lxc容器中！

