# 用户指南 · LA AGUJA Rescue Disk

[Website](https://aguja.transcendenceia.net/zh/docs) · [English](../en/USER-GUIDE.md) · [Español](../es/USER-GUIDE.md)


## 小小入口，完整掌控

LA AGUJA 是从 USB 启动的 x86-64 Linux 救援系统，在已安装系统之前运行。Flash Imager 在正常工作的 Windows/Linux 电脑上准备 USB；Rescue Disk 在待检查电脑上运行。启动不会自动挂载、修复或写入内部磁盘。可在本地或通过 SSH 工作，也可选用自己的 Tailscale/Headscale。云端 AI 需要互联网和自己的提供商账户，传统工具可以离线使用。无 LA AGUJA 账户或中央中继。项目仍属实验性质，不保证兼容所有硬件。

[↗](https://aguja.transcendenceia.net/zh/docs#que-es)

## 准备第一个 USB

先备份容量足够的 USB。下载 Imager，从签名目录选择镜像。保留以太网 DHCP，设置语言、键盘、主机名和自己的 SSH 密码或公钥。首次测试可关闭 AI 和私有网络。配置含机密时请加密，并把解锁口令保存在 USB 之外。写入前核对型号、容量和序列号；等待完整回读验证。通过固件菜单从 USB 启动，必要时解锁配置。看到面板并识别磁盘即完成首次练习，无需登录 AI 或恢复文件。

```sh
aguja status
aguja doctor
lsblk -o NAME,SIZE,MODEL,FSTYPE,LABEL,MOUNTPOINTS
```

[↗](https://aguja.transcendenceia.net/zh/docs#primer-usb)

## 常见术语

Live 系统无需安装即可启动。可配置 IMG 和启动 ISO 在 Imager 中不可互换。磁盘是整个设备，分区是其中区域，挂载使文件可访问；/dev/sda 等名称可能变化。DHCP 自动分配地址；SSH 提供加密终端和服务器指纹。Root/sudo 是管理员权限，不是只读沙箱。节点注册密钥、API 密钥、SSH 密码和配置口令用途不同。SHA-256 验证字节，不保证启动兼容性。配置口令无法解锁 BitLocker/LUKS。

[↗](https://aguja.transcendenceia.net/zh/docs#glosario)

## 开始前：硬件、许可与备份

确认 x86-64、USB 启动和固件支持。提供 BIOS/UEFI 路径，但不保证 ARM、所有 Wi-Fi 芯片或通用已签名 Secure Boot。取得设备和数据的授权，选择独立恢复目标。故障磁盘应考虑先制作镜像。写入会替换 USB 内容。Windows 暂无内置 USB 备份，请使用外部工具；Linux 提供可选完整验证备份，默认关闭，需要空间和权限。这不是内部磁盘备份。加密卷仍需要所有者正确的 BitLocker/LUKS 密钥。

[↗](https://aguja.transcendenceia.net/zh/docs#preparacion)

## 下载并打开 Imager

从官网选择 Windows 10/11 EXE、Linux AppImage、Debian/Ubuntu DEB 或便携压缩包。核对 SHA-256，在准备电脑上运行。EXE/AppImage 不是要写入 USB 的救援镜像，无需 LA AGUJA 账户。Windows 包目前没有受认可的 Authenticode 签名；AppImage 可能需要执行权限，便携包是另一选择。设备写入需要本地提权。应用能打开不证明 USB 已准备或能启动。

[↗](https://aguja.transcendenceia.net/zh/docs#descargas)

## 步骤 1 · 选择兼容镜像

使用签名目录或本地 .img。目录检查 Ed25519 和哈希，并合并分卷。手动导入 .img.zst 前先解压。私人配置生成新文件，不修改公开镜像。目前 Imager 为 0.9.2，救援镜像为 0.9.0。选项取决于镜像支持；不含 tailscale-profile-v1 的镜像会拒绝私有网络注册配置。核对实际容量，而非 USB 商业标签。

[↗](https://aguja.transcendenceia.net/zh/docs#imagen)

## 步骤 2 · 网络、语言与主机名

选择 Live 语言、键盘布局及变体；Imager 界面语言独立设置。使用可识别的主机名。以太网 DHCP 是最简单的起点；保存的 Wi-Fi 会在启动时连接，无网络时可交互选择。导入 Wi-Fi 密码可能需要本地许可。企业网络或门户可能需要手动配置 NetworkManager。分别检查网络、DNS、HTTPS 和时间；本地诊断仍可离线进行。

[↗](https://aguja.transcendenceia.net/zh/docs#red)

## 步骤 3 · SSH 访问

使用唯一密码或获授权操作者的公钥，切勿粘贴私钥。默认端口 22；使用实际 IP 并核对主机指纹。改端口不能代替身份验证。出厂用户和公开密码都是 aguja。个人密码优先；空密码配公钥为仅公钥访问，没有公钥时保持出厂访问兼容性。账户拥有无限 sudo。aguja password 把新密码保存在 USB；sudo passwd aguja 只改变当前会话。

```sh
ssh aguja@IP
```

[↗](https://aguja.transcendenceia.net/zh/docs#ssh)

## 步骤 4 · 准备 AI

支持 Codex CLI、OpenCode、Claude Code 和 Antigravity 集成：自己的 API 密钥、选择性导入兼容便携会话，或启动后登录。CLI 安装检查不证明登录或推理成功。不会复制整个密钥库、历史、钩子或 MCP 配置。便携会话可能已过期。费用、配额和发送数据由提供商决定。可以不配置 AI 凭据；不承诺云端 AI 离线工作。

[↗](https://aguja.transcendenceia.net/zh/docs#ia-preparacion)

## 步骤 5 · 自己的 Tailscale/Headscale

远程访问可选。启用私有网络并提供授权 auth/pre-auth 密钥，可选节点名。Headscale URL 留空使用官方 Tailscale，否则填写自己的 HTTPS 服务。Live 在网络可用、配置解锁后注册，不注册准备电脑。客户端必须属于授权网络并满足策略。注册密钥不是 SSH 密码。注册成功不证明 ACL 允许连接，应从授权客户端测试真实 SSH。身份保存在 RAM，重启后重新注册。

[↗](https://aguja.transcendenceia.net/zh/docs#tailnet)

## OpenSSH 与 Tailscale SSH

默认是私有网络上的普通 OpenSSH，仍需密码/公钥、指纹和允许访问的网络 ACL。Tailscale SSH 是高级选项，需要兼容服务和明确 SSH 策略。遇到问题要区分注册、节点连通性、TCP 端口和身份验证，不要为掩盖认证错误而开放公网端口或扩大 ACL。参考实际部署版本的文档。

[↗](https://aguja.transcendenceia.net/zh/docs#politicas)

## 机密与加密边界

私人配置可能包含 Wi-Fi、SSH、AI 和节点注册密钥。加密配置胶囊，单独保存口令，启动时先本地解锁。可复用 .aguja 模板及备份同样敏感。胶囊并不加密整个 AGUJA_DATA，也无法在解锁后防止 root 读取。persistent_home=no 重启丢失 HOME/令牌；yes 在 USB 上明文保存。明文 aguja.conf 可被物理读取。不要公开私人镜像、配置或密钥。

[↗](https://aguja.transcendenceia.net/zh/docs#secretos)

## Windows · 理解 BitLocker

启动 Linux 不会移除 BitLocker。向所有者取得与目标卷对应的恢复密钥。配置口令和 SSH 密码不是 BitLocker 密钥，LA AGUJA 不破解加密。Windows Imager 可检查可用密钥，并仅在明确选择后加入私人镜像。保护配置并另存恢复副本。显示密钥不证明卷已解锁。Windows 截图是历史 0.8.1 证据，不是新的原生 0.9.2 执行。

[↗](https://aguja.transcendenceia.net/zh/docs#bitlocker)

## 步骤 6 · 准备、写入与验证

检查镜像、保护模式及摘要。创建私人镜像只生成文件；准备并写入 USB 还会写目标设备。在原生确认中比较型号、序列号、实际容量；不确定就取消。仅对预期操作授权 UAC/Polkit。等待完整写入和回读，不要拔出 USB，并检查结果。字节验证不代表所有固件兼容，应测试目标硬件。Windows USB 备份必须事先外部完成。

[↗](https://aguja.transcendenceia.net/zh/docs#grabar)

## 启动、解锁并连接

在制造商启动菜单选择 USB，面板显示网络/SSH。加密配置在本地控制台执行 aguja profile unlock。硬件不支持图形时可回退到文字控制台。使用实际 IP；.local 依赖 mDNS/组播，重名时可能改变。无需 tailnet 也能在局域网 SSH。核对指纹后检查状态和磁盘。看到面板不代表内部磁盘已被挂载或修复。

```sh
aguja profile unlock
aguja status
```

[↗](https://aguja.transcendenceia.net/zh/docs#arranque)

## 重启：临时网络身份

Tailnet 状态位于 RAM。重启后需要网络、配置解锁和重新注册。一次性密钥可能首次启动后就失效；多次启动应使用有效、受限、可复用密钥。这个身份与 USB 的 SSH 主机密钥和 HOME 持久化不同。结束后清理旧节点并撤销不再需要的密钥。旧连接成功不证明当前注册或策略状态。

[↗](https://aguja.transcendenceia.net/zh/docs#reinicios)

## 本地浏览器中的 AI 登录

aguja login codex、claude 或 antigravity 可打开有沙箱的 Chromium 官方登录及同一 PTY 控制台。复制仅聚焦控制台，使用 Ctrl+Shift+V 明确粘贴；关闭返回原终端。不使用 QR，不自动授权。OpenCode 保持 opencode auth login。SSH、串口、无屏幕使用原生方法，远程 localhost 回调不自动转发。API 与会话导入是不同途径。合成截图不证明真实登录或推理。

```sh
aguja login codex
aguja login claude
aguja login antigravity
opencode auth login
```

[↗](https://aguja.transcendenceia.net/zh/docs#ia-login)

## 首次诊断：先理解再修复

提出具体问题，收集状态、设备身份、文件系统和挂载。运行 aguja doctor 与下方清单。按型号、大小、标识符识别 USB、源和目标，不猜设备字母。访问文件前检查只读挂载及文件系统日志行为。修改前保存观察结果。故障磁盘可能需要 ddrescue 镜像与映射文件，而不是反复修复原盘。

```sh
aguja doctor
lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,LABEL,MOUNTPOINTS
findmnt
```

[↗](https://aguja.transcendenceia.net/zh/docs#primer-diagnostico)

## 与智能体协作

明确目标、具体电脑/磁盘、授权操作、备份位置和停止条件。先要求实时状态和证据，再修改。独立验证恢复文件或启动结果。aguja 有完整 root/sudo；默认启动器使用全权限机制，只读指令不是强制沙箱。agent_mode=ask 保留工具审批，不移除 root。检查破坏性操作并保留回滚副本。

[↗](https://aguja.transcendenceia.net/zh/docs#trabajo-ia)

## 救援工具与命令

aguja tools 展示工具。ddrescue 制作带映射的镜像；TestDisk/PhotoRec 恢复；rsync 复制；smartctl/nvme-cli 检查硬件。卷和加密工具仍需正确设备及密钥。下方命令用于了解状态。不要对猜测设备格式化、安装引导器或写分区。参考工具手册，必要时在副本上工作。传统工具无需云端 AI，但不保证恢复所有数据。

```sh
aguja tools
aguja status --disks
aguja status --json
aguja context
aguja help
```

[↗](https://aguja.transcendenceia.net/zh/docs#herramientas)

## 十种实际流程

1. 清点无法启动的电脑。2. 把授权文件复制到独立目标。3. ddrescue 镜像与映射。4. TestDisk 写入前检查分区。5. PhotoRec 恢复到另一设备。6. SMART/NVMe 检查。7. 备份后诊断 UEFI/引导器。8. 用正确密钥访问 BitLocker/LUKS。9. 授权 SSH 支持。10. 仅在明确批准的目标安装 OS。这些是可调整流程，不是自动修复或保证。先识别源、目标与回滚，再验证结果；不要把恢复数据写回源。

[↗](https://aguja.transcendenceia.net/zh/docs#casos)

## 专业流程：证据与可重复性

记录许可、硬件、版本/哈希、初始状态、磁盘和计划。尽可能使用副本，为证据标注并保留与原件关联。对不稳定介质保留映射及停止条件。小步修改，记录目的和结果；验证数据/启动，而非仅退出码。可复用 .aguja 配置应加密并检查过期凭据。不得把客户数据或密钥放进公开问题或演示。

[↗](https://aguja.transcendenceia.net/zh/docs#profesional)

## 按层排查问题

无法启动：架构、完整性、固件、文字控制台。无网络：链路/Wi-Fi、DHCP、DNS、HTTPS、时间。无 SSH：IP/端口、服务、策略、认证。无 tailnet：密钥、URL、有效期、一次性密钥已用。无 AI：方法、账户、网络、回调。配置未加载：镜像功能/解锁。磁盘未见：先检查控制器和清单，勿写入。doctor 正常不证明 ACL、OAuth 或全部硬件兼容。

[↗](https://aguja.transcendenceia.net/zh/docs#problemas)

## 结束时不要遗留访问

总结观察、修改和验证，关闭会话，完成写入并正常关机。检查目标文件，保留原盘及备份直到所有者接受。删除临时节点并撤销无用密钥，检查 USB 持久令牌。按已授权、可恢复流程处理私人镜像/配置；不撤销无关所有者访问，也不销毁证据。说明剩余限制。

[↗](https://aguja.transcendenceia.net/zh/docs#terminar)

## 已验证范围与限制

公开版无 LA AGUJA 账户或专有中继。准备、软件包和 VM 测试覆盖特定路径，不认证每台电脑。Imager 0.9.2 修复七种界面语言标题，救援镜像仍为 0.9.0。历史截图保留真实版本。回读不是通用启动；面板/CLI/便携会话不是 AI 登录；本地注册不证明 SSH 策略。Windows 暂无集成 USB 备份或受认可的 Authenticode 签名，也无通用已签名 Secure Boot。

[↗](https://aguja.transcendenceia.net/zh/docs#validacion)

## 参考与下一步

顶部链接提供下载和代码。西班牙语详细参考保留原始 26 章，本指南以简体中文覆盖相同操作阶段。截图保留历史版本与合成测试来源。打印本页可保存中文 PDF；另行发布的历史 PDF 为西班牙语。查看实际版本的 OpenSSH、Tailscale/Headscale、ddrescue、TestDisk 和 Microsoft BitLocker 官方文档。项目代码 GPL-3.0-or-later，第三方保留自身许可。问题报告附版本和脱敏现象，不附密码、令牌、私钥或私人镜像。

[↗](https://aguja.transcendenceia.net/zh/docs#referencias)
