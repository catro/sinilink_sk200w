# Sinilink SK200W for Home Assistant

Home Assistant 自定义集成：通过 **Modbus RTU over UDP** 读取 Sinilink XY-SK200W 可调电源的各项数值，
并支持在 HA 中设置输出电压 / 电流。

[中文](#中文) | [English](#english)

> [!WARNING]
> 本项目为社区自定义集成，非官方支持。设备协议可能随固件版本变化而改变，请自行评估风险。

## 中文

### 功能

- 通过 Modbus RTU over UDP（`pymodbus` + `FramerType.RTU`）连接指定 IP 的设备。
- 可配置 **读取间隔**，并可在集成选项中随时修改。
- 设备创建后生成一个 **「数据更新」开关**：打开后按间隔轮询设备，关闭后完全停止 Modbus 通信
  （保留最后一次读数）。
- 布尔状态 binary sensor：输出状态、恒流模式、恒压模式、保护状态、通信状态。
- 数值 sensor：输出电压 / 电流 / 功率、输入电压、温度、外部温度、电池容量 / 能量。
- 可写的 number：设定电压、设定电流。

### 安装

#### 通过 HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=catro&repository=sinilink_sk200w&category=integration)

#### 手动安装

1. 将 `sinilink_sk200w` 目录复制到 Home Assistant 配置目录下的 `custom_components/`。
2. 重启 Home Assistant。
3. 参考下方「添加到 Home Assistant」。

> [!WARNING]
> 手动安装时，如需收到新版本提醒，请订阅本仓库的 Releases。

### 添加到 Home Assistant

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=sinilink_sk200w)

> [!TIP]
> 如果上面的按钮无法使用，请手动操作：
> 1. 进入 **设置 → 设备与服务**（Settings → Devices & Services）。
> 2. 点击右下角的 **+ 添加集成**（+ ADD INTEGRATION）。
> 3. 搜索 `Sinilink SK200W`。

### 配置项

| 配置项 | 说明 | 默认值 |
| --- | --- | --- |
| Host | 设备 IP 地址 | — |
| Port | UDP 端口 | `1024` |
| Modbus slave address | Modbus 从站地址 | `1` |
| Update interval | 读取间隔（秒） | `5` |

> 需要在设备侧配置 Modbus RTU over UDP 的网关 / 桥接模块（例如 XY-WFPOW），使其监听对应 UDP 端口。

### 实体

- **binary_sensor**：`输出状态`、`恒流模式`、`恒压模式`、`保护状态`、`通信状态`。
  `输出状态` 的附加属性包含全部测量数值。
- **sensor**：`输出电压`、`输出电流`、`输出功率`、`输入电压`、`温度`、`外部温度`、
  `电池容量`、`电池能量`。
- **number**（可写）：`设定电压`（0 – `MAX_VOLTAGE_SET` V）、`设定电流`（0 – `MAX_CURRENT_SET` A）。
- **switch**：`数据更新` —— 开始 / 停止 Modbus 轮询。

### 寄存器映射（Holding Registers）

| 寄存器 | 含义 | 缩放 |
| --- | --- | --- |
| `0x0000` | 设定电压 | ×0.01 V |
| `0x0001` | 设定电流 | ×0.001 A |
| `0x0002` | 输出电压 | ×0.01 V |
| `0x0003` | 输出电流 | ×0.001 A |
| `0x0004` | 输出功率 | ×0.01 W |
| `0x0005` | 输入电压 | ×0.01 V |
| `0x0006` | 电池容量（32 位，低字在前） | ×0.001 Ah |
| `0x0008` | 电池能量（32 位，低字在前） | ×0.001 Wh |
| `0x000A`–`0x000C` | 输出时长 时 / 分 / 秒 | 1 |
| `0x000D` | 内部温度（有符号） | ×0.1 °C |
| `0x000E` | 外部温度（有符号） | ×0.1 °C |
| `0x0010` | 保护状态 | 位域 |
| `0x0011` | 恒流 / 恒压 模式（bit0：1 = 恒流） | 位域 |
| `0x0012` | 输出使能（bit0） | 位域 |

所有寄存器在一次连续读取（`0x0000` 起，共 19 个）中获取。

### 说明与注意事项

- 电流缩放默认按 `0.001 A / 单位` 处理。若实际读数相差 10 倍，请调整 `const.py` 中的 `CURRENT_SCALE`。
- 未连接温度探头时，设备返回哨兵值（原始 `8888`，即 `888.8 °C`），集成会将其识别为「未知」。
- 设定电压 / 电流的上限由 `const.py` 中的 `MAX_VOLTAGE_SET` / `MAX_CURRENT_SET` 决定（默认 60 V / 20 A），
  请按你的机型修改。
- 依赖 `pymodbus`，由 Home Assistant 按 `manifest.json` 自动安装。

---

## English

Home Assistant custom integration that reads a Sinilink XY-SK200W adjustable power supply over
**Modbus RTU over UDP** and lets you set the output voltage / current.

> [!WARNING]
> This is a community custom integration, not officially supported. The device protocol may change
> between firmware versions; use it at your own risk.

### Features

- Connects to a device at a given IP over Modbus RTU over UDP (`pymodbus` + `FramerType.RTU`).
- Configurable **update interval**, adjustable later from the integration options.
- Creates an **"Modbus updates" switch**: turn it on to poll at the configured interval, turn it off
  to stop Modbus communication entirely (the last readings are kept).
- Binary sensors: output, constant current, constant voltage, protection, connectivity.
- Sensors: output voltage / current / power, input voltage, temperature, external temperature,
  battery capacity / energy.
- Writable numbers: voltage setpoint, current setpoint.

### Installation

#### With HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=catro&repository=sinilink_sk200w&category=integration)

#### Manual

1. Copy the `sinilink_sk200w` directory into the `custom_components/` directory of your Home Assistant
   configuration directory.
2. Restart Home Assistant.
3. Follow "Add to Home Assistant" below.

> [!WARNING]
> When installing manually, subscribe to this repository's releases to be notified about new versions.

### Add to Home Assistant

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=sinilink_sk200w)

> [!TIP]
> If you are unable to use the button above, follow the steps below:
> 1. Navigate to the Home Assistant Integrations page `(Settings --> Devices & Services)`.
> 2. Click the `+ ADD INTEGRATION` button in the lower right-hand corner.
> 3. Search for `Sinilink SK200W`.

### Configuration

| Option | Description | Default |
| --- | --- | --- |
| Host | Device IP address | — |
| Port | UDP port | `1024` |
| Modbus slave address | Modbus slave address | `1` |
| Update interval | Polling interval in seconds | `5` |

> A Modbus RTU over UDP gateway/bridge module (e.g. XY-WFPOW) must be configured on the device side to
> listen on the matching UDP port.

### Entities

- **binary_sensor**: `Output`, `Constant current mode`, `Constant voltage mode`, `Protection`,
  `Communication`. The `Output` entity carries all measurements as extra state attributes.
- **sensor**: `Output voltage`, `Output current`, `Output power`, `Input voltage`, `Temperature`,
  `External temperature`, `Battery capacity`, `Battery energy`.
- **number** (writable): `Voltage setpoint` (0 – `MAX_VOLTAGE_SET` V), `Current setpoint`
  (0 – `MAX_CURRENT_SET` A).
- **switch**: `Modbus updates` — start / stop polling.

### Register map (holding registers)

| Register | Meaning | Scale |
| --- | --- | --- |
| `0x0000` | Voltage setpoint | ×0.01 V |
| `0x0001` | Current setpoint | ×0.001 A |
| `0x0002` | Output voltage | ×0.01 V |
| `0x0003` | Output current | ×0.001 A |
| `0x0004` | Output power | ×0.01 W |
| `0x0005` | Input voltage | ×0.01 V |
| `0x0006` | Battery capacity (32-bit, low word first) | ×0.001 Ah |
| `0x0008` | Battery energy (32-bit, low word first) | ×0.001 Wh |
| `0x000A`–`0x000C` | Output on-time (h / m / s) | 1 |
| `0x000D` | Internal temperature (signed) | ×0.1 °C |
| `0x000E` | External temperature (signed) | ×0.1 °C |
| `0x0010` | Protection status | bitfield |
| `0x0011` | CV / CC regulation mode (bit0: 1 = constant current) | bitfield |
| `0x0012` | Output enable (bit0) | bitfield |

All registers are read in a single contiguous block (`0x0000`, 19 registers).

### Notes

- Current is scaled at `0.001 A / unit` by default. If the readings are off by 10×, adjust
  `CURRENT_SCALE` in `const.py`.
- When no temperature probe is connected the device returns a sentinel value (raw `8888`, i.e.
  `888.8 °C`); the integration reports it as unknown.
- Setpoint limits come from `MAX_VOLTAGE_SET` / `MAX_CURRENT_SET` in `const.py` (default 60 V / 20 A);
  adjust them for your model.
- Requires `pymodbus`, installed automatically by Home Assistant from `manifest.json`.