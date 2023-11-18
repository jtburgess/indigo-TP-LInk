# Indigo TP-Link

Version 0.9.9 and newer are Python 3 compatible, and have been tested with Indigo 2022.1

## Overview

This Indigo plugin is for TP-link Devices: plugs, power strips, wall switches, and smart light bulbs. The intent is
to support all devices controlled by the __kasa__ app.  Note that there are many WiFi-controlled smart devices from many manufacturers.
There is no standard protocol for them. If your device doesn't work with _kasa_, it won't work with this plug-in.

Also, TP-link frequently puts out new devices with new features and variants on the protocol. The original version of this plugin only supported plugs; then multi-plug devices were added, and now dimmable smart bulbs and light switches.
If you find a device that doesn't work, and you have some python experience, please contribute and add support for your new device. Or, if its too much work, let me know and I'll see what I can do.

__Relays__ mostly have model names beginning with "HS".
Starting with version 0.9.3, two additional sub-types are supported: __Dimmers__ and __RelaySwitches__ (more below). These have very different features and protocol structure.  __Dimmers__ seem to have model names beginning with "KL".  __RelaySwitches__ seem to have model names beginning with "HS".
The plugin has a list of known devices, by sub-type.

I have only tested with the basic HS105 plug, and the KL110 dimmable bulb. Other users have helped me develop and test the other device types.  See above to enable support for new models, if the current version doesn't work correctly. It should be easier now that the base logic for supporting multiple sub-types has been added.

## Configuration

Double-click the plugin to install it in indigo 7 or higher. Then add a new device with type **TP-Link Device** and Model **TP-Link Smart plug (all versions)** or **TP-Link Smart Dimmer Switch** or **TP-Link Smart (dimming) bulb**.
There will be a short (4 second) delay while the plugin searches for TP-link devices on the local network. You will then see a window with a pull-down menu. Here you will find any devices that were discovered with its model type and recognized device type, or the option to enter the plug information manually. If you select manual entry, you will be prompted for the IP Address of the device, enter that and click Continue. 

If you get a device with type "unknown" it means the plugin doesn't recognize that model.
You'll have to go into the python code and add it to the proper list. ... and perhaps add support for its unique features.  And let me know, so I can add it to the base code!

Because the plugin works off the device's IP address, you will want to make the DHCP IP-address assignment permanent, with a static mapping. By doing this you won't have to change indigo should the plug's IP address change, which can happen, for example, if you lose power.

Next, whether you selected the device from the menu, or entered its IP Address manually, you will see a window with information and settings for the device.

### Common Device Settings (Polling)
All device types support status polling, through five configuration options, each of which can be left as global default, or set at the plugin level, or overridden at any individual device. The global defaults are shown below in (). Leave a value empty when configuring to use the default.
* _Enable / disable polling_ of the device. Polling is required if you want Indigo to track changes made locally at the device, or through Alexa, or via the __kasa__ app. Polling is also required if you want to access energy data from a device with energy reporting capability.
* _polling interval_. There are two settings: the interval when the device is _off_ (30 sec), and when it is _on_ (10 sec).  For energy reporting plugs, you will probably want a faster polling time when the plug is on. Also, if a change in device status triggers other actions, you'll want it checked often.  Otherwise you can set both settings to the same interval. Note that polling more often than every 5 seconds may affect your computer's performance.
* If a device stops reponding to polls (e.g. there is a network problem or the device is unplugged), you'll get a _warning message after every N (5) missed polls_.
* After each such warning, the _polling is slowed by N_ (1 second). Setting to 0 keeps the polling the same, increasing this value can drastically slow the polling rate. When a successful poll is received the rate goes back to its original setting.
* You can have _device communications shut down_ after N (20) missed polls. Sometimes this is inconvenient, so you can set this value to a very large number to more-or-less prevent it from happening.

The "Send Status Request" button on the Indigo device page now prints ALL settings to the log, and for these values indicates whether the value came from a global "default", the "plugin" configuration, or the "dev(ice)" configuration override.

### Smart Plug (aka Relay) Config details
Here you can change the default device settings:
* polling, as above
* For dual-plugs and plug strips you'll need to select the outlet number (1-2 or 1-6).

There is one other setting you may wish to enable, __on__/__off__ logging. This is set in the plugin's Config settings. If this setting is enabled Indigo will create a log entry each time a plug is turned on or off in Indigo.  If polling is enabled, the plugin will also log each time an __on__/__off__ change is detected that was not initiated from Indigo.

Click __Save__ and then simply click __on__ or __off__ on your device. _Toggle_ is supported. 

### Smart Relay Dimmer Switch (aka RelaySwitch) Config Details
This device type is for wall switches with dimming capabiulity. They are sort of a cross between a Relay and a Dimmer, but since the protocol is unique, they represent a different sub-type.  They also have some advanced features (see Actions, bwlow).

There are no __RelaySwitch__ -specific configuration settings.

### Smart Bulb (aka Dimmer) Config Details
Smart bulbs typically have model names beginning with 'KL'. You'll want to select **TP-Link Smart (dimming) bulb** as you initially configure the device.

The only option is to enable __on/off__ polling, as above.
In the future, I'll add an option to specify how long it should take to transition to a new brighjtness level, aka the "ramp time". The API already supports this, so if you write your own python code to set the brightness, you can specify the ramp time.

---
## Programmable Actions
The default actions of __on/off/set brightness__ are always available.
The actions below were added for the __RelaySwitch__ subtype, which has extra settings in the device itself.  Two have been co-opted for the __Dimmer__ type, which has a fade time (aka rampTime) as an Indigo device setting.
### Set_fade_on_time
For a __RelaySwitch__, sets the time it takes to increase brightness, in milliseconds (msec).

For a __Dimmer__ , it sets the rampTime, in msec. This timer is used for all operations (__on/off/set brightness__). It it an alternative to setting the rampTime in the Device config, but take effect immediately, so it can be used in a complex multi-step Action to do interesting things.

### Set_fade_off_time
For a __RelaySwitch__, sets the time it takes to decrease brightness, in msec.

For a __Dimmer__, it sets the rampTime, in msec. This timer is used for all operations ( __on/off/set brightness__ ).
It does the same thing as Set_fade_on_time.

### SetDoubleClickAction
Sets the behaviour when you double-click the device to one of these:
1. Instant on/off
1. Gentle on/off
1. Play Preset
1. None (do nothing)

### SetLongPressAction
Sets the behaviour when you "long-press" the device to one those same options -- I assume. I can't find this documented anywhere...

### Set_gentle_off_time
Sets the time it takes to decrease brightness gently, in milliseconds (msec).
See the documentation for the device.

### Set_gentle_on_time
Sets the time it takes to increase brightness gently, in milliseconds (msec).

---
*New Color Actions in 0.9.8*. 
These apply only to Dimmer devices.
### set_HSV
Sets the Hue Saturation and Value (brightness).
Only applies to devices that have the 'isColor' property.

### set_ColorTemp
Sets the white color temp in degrees-Kelvin.
I don't know what the allowable range is, so it lets you use any number between 0 and 9999.
Let me know if *you know* the allowed values, so I can update my code to properly validate.

---
## Command Line Testing
A command line tool for manually querying TP-Link smart devices, **tplink_test.py** is included with the Plugin. You'll find it in the top-level directory of the plugin. In a terminal window,

    cd "/Library/Application Support/Perceptive Automation/Indigo 7.5/Plugins/TP-Link-Device.indigoPlugin"
    python ./tplink_test.py --options 

(Substitute Indigo 7.4, 7.3, etc as appropriate for your system.)

There are command line options to pick which TP-link device type (i.e., which protocol command set) to use:
+ -b (--bulb) for smart light bulbs.
+ -r (--relay) for smart plugs, power strips, etc.
+ -s (--switch) for dimmable light switches

If you dont specify a device type, you get only the default, common command set.

You must specify a command in one of three variations:
+ -c (--command) is from the validated list of shared commands: info, on, off, reset, schedule, discover, reboot
+ -C (--CMD) is for unvalidated, device-specific commands, e.g., time, light_details and more
+ -j (--json) allows you to specify the actual JSON, assuming you know what you're doing.

Discover (-c discover) may be the most useful command. it searches your LAN for all TP-link devices of all types.

For other commands, you'll need to specify the IP address of the target wirth -t (--target).

For power strips and other multi-port devices, you may also need to specify -d (--deviceID) and -c (--childID).

If you get this response, especially when using "-C":

    Received: 
    { "error": {
      "cmd": "whatever",
      "python error": "unpack requires a string argument of length 4"
      }
    }


it probably means you picked the wrong device type. Try one of the others.
Or maybe the command wasn't recognized.

As is normal with command line tools, -h (--help) will print a list of all options.
