# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **Indigo Home Automation plugin** for controlling TP-Link smart devices (plugs, power strips, wall switches, and smart bulbs) that use the Kasa app. The plugin communicates with devices over TCP port 9999 using TP-Link's proprietary XOR-encrypted JSON protocol.

**Plugin Version:** 1.0.1.18 (Python 3 compatible, requires Indigo 2022.1+)

## Architecture

### Device Sub-Types
The plugin supports three distinct device categories, each with different behaviors, attributes, and JSON protocols:

| Sub-Type | Device Type | Indigo Base | Model Prefixes |
|----------|-------------|-------------|----------------|
| `tplinkSmartPlug` (Relay) | Smart plugs, power strips | `relay` | HS, EP, KP |
| `tplinkSmartBulb` (Dimmer) | Smart bulbs | `dimmer` | KL |
| `tplinkSmartSwitch` (RelaySwitch) | Dimmable wall switches | hybrid | HS |

### Core Class Structure
Because Indigo only calls the main `Plugin` class, sub-type specific functionality uses an "inverted" pattern:

```
plugin.py (entry point)
├── tplink_relay_plugin.py      # Relay-specific logic + relayModels set
├── tplink_dimmer_plugin.py     # Dimmer-specific logic + dimmerModels set
├── tplink_relayswitch_plugin.py # Switch-specific logic + relayswitchModels set

protocol.py (base protocol with encrypt/decrypt)
├── tplink_relay_protocol.py    # Relay JSON commands
├── tplink_dimmer_protocol.py   # Dimmer JSON commands
├── tplink_relayswitch_protocol.py # Switch JSON commands

tpl_polling.py (base polling thread)
├── tpl_relay_poll.py           # Relay polling (includes energy monitoring)
├── tpl_dimmer_poll.py          # Dimmer polling
├── tpl_relayswitch_poll.py     # Switch polling
```

### Key Plugin Methods
- `getSubType(model)` - Maps device model to sub-type string
- `getSubClass(deviceTypeId)` - Returns appropriate plugin sub-class instance
- `getSubProtocol(dev)` - Returns appropriate protocol instance for device
- `getPollClass(dev)` - Returns appropriate polling thread class
- `devOrPluginParm(dev, attribute, default)` - Cascading config lookup (device → plugin → default)

### Protocol
- TCP socket on port 9999
- XOR Autokey Cipher with starting key = 171
- JSON commands with 4-byte length prefix
- Multi-plug devices use `context.child_ids` wrapper

## Plugin File Structure

```
TP-Link-Device.indigoPlugin/
└── Contents/
    ├── Info.plist           # Plugin metadata
    ├── Resources/           # Icons, images
    └── Server Plugin/
        ├── plugin.py        # Main entry point
        ├── protocol.py      # Base protocol + encrypt/decrypt
        ├── tpl_polling.py   # Base polling thread
        ├── Actions.xml      # Custom action definitions
        ├── Devices.xml      # Device type definitions
        ├── MenuItems.xml    # Plugin menu items
        ├── PluginConfig.xml # Plugin preferences UI
        └── tplink_*.py      # Sub-type implementations
```

## Command Line Testing

Use `tplink_test.py` from the plugin root directory:

```bash
cd /Users/alastair/Developer/indigo-TP-LInk/TP-Link-Device.indigoPlugin
python ./tplink_test.py -t <IP_ADDRESS> -c <command> [-r|-b|-s]
```

**Required flags:**
- `-t <IP>` - Target device IP address
- `-c <cmd>` - Validated command (info, on, off, reset, schedule, discover, reboot)
- `-C <cmd>` - Unvalidated device-specific command
- `-j <json>` - Raw JSON command

**Device type flags:**
- `-r` / `--relay` - Smart plugs
- `-b` / `--bulb` - Smart bulbs
- `-s` / `--switch` - Dimmable switches

**Discovery (finds all devices on LAN):**
```bash
python ./tplink_test.py -t 255.255.255.255 -c discover
```

## Adding Support for New Device Models

1. Identify the correct sub-type for the device (Relay, Dimmer, or RelaySwitch)
2. Add the model prefix (first 5 characters) to the appropriate `*Models` set:
   - `relayModels` in `tplink_relay_plugin.py`
   - `dimmerModels` in `tplink_dimmer_plugin.py`
   - `relayswitchModels` in `tplink_relayswitch_plugin.py`
3. If the device has unique features, extend the protocol commands in the corresponding `*_protocol.py`

## Logging

The plugin uses Python logging with custom level `THREADDEBUG` (below DEBUG). Log levels can be set at:
- Global default
- Plugin configuration
- Individual device override

File logging goes to the plugin's log file; Indigo log respects the configured level. DEBUG/THREADDEBUG levels only write to file, not Indigo log.
