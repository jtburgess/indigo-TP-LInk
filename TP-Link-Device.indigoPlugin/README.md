Indigo-TP-LInk
==============
Overview
--------

The TP-Link Device plugin makes TP-Link Wi-fi-based SmartPlugs appear as __Relay__ (on/off) devices in Indigo.
This plugin supports all known TP-Link smart plugs, including single, dual and 6 outlet plug strips.
These mostly have model names beginning with "HS".

NEW on 0.9.x, it now supports dimmable TP-Link smart light bulbs, which have very different features and protocol structure.  These mostly have model names beginning with "KL".
NOTE: I have only tested with the KL110 dimmable, white-only blub.

Double-click the plugin to install it in indigo 7 or higher. Then add a new device with type **TP-Link Device** and Model **TP-Link Smart plug (all versions)** or **TP-Link Smart (dimming) bulb**.
There will be a short (4 second) delay while the plugin searches for TP-link devices on the local network. You will then see a window with a pull-down menu. Here you will find any devices that were discovered with its model type and recognized type, and the option to enter the plug information manually. If you select manual entry, you will be prompted for the IP Address of the device, enter that and click Continue. 

If you get a device with type "unknown" it means the plugin doesn't recognize that model.
You'll have to go into the python code and add it to the proper list.

If you don't know the IP Address, you can get from your DHCP server (probably your router).
You might also want to make the DHCP address assignment permanent, with a static mapping. By doing this you won't have to change indigo should the plug's IP address change, which can happen, for example, if you lose power.

Next, whether you selected the device from the menu, or entered its IP Address manually, you will see a window with information about the device.

**Smart Plug Config details**
Here you can change the default settings:
* For dual-plugs and plug strips you can select the outlet number (1-2 or 1-6).
* You can enable or disable polling of the device. Polling is required if you want Indigo to track changes made locally at the device, or via the __kasa__ app. Polling is also required if you want to access energy data from a device with energy reporting capability.
* For single plugs you can set the polling frequency. There are two settings, for when the plug is off, and when it is on.  For energy reporting plugs, you will probably want a faster polling time when the plug is on. Otherwise you can set both settings to the same interval. For dual-plugs and plug strips, the polling frequency is controlled by the plugin's Config settings. Note that polling more often than every 5 seconds may affect your computer's performance.

There is one other setting you may wish to enable, __on__/__off__ logging. This can be set in the plugin's Config settings. If this setting is enabled Indigo will create a log entry each time a plug is turned on or off in Indigo.  If polling is enabled, the plugin will also log each time an __on__/__off__ change is detected that was not initiated from Indigo.

Click __Save__ and then simply click __on__ or __off__ on your device. _Toggle_ is supported. 


**Command Line Testing**
A command line tool for manually querying TP-Link smart devices, **tplink_test.py** is included with the Plugin.

As with the above, there are two command line options to pick which TP-link device type (i.e., which protocol command set) to use:
+ -r (--relay) for smart plugs, power strips, etc. 
+ -b (--bulb) for smart lights.
If you pick neither, you get only the default, common command set.

You must specify a command in one of three variations:
+ -c is from the validated list of shared commands: info,reset,schedule,discover,reboot
+ -C is for unvalidated, device-specific commands, e.g., on, off, time, light_details and more
+ -j allows you to specify the actual JSON, assuming you know what you're doing.

Discover (-c discover) may be the most useful command. it searches your LAN for all TP-link devices, of all types.

For other commands, you'll need to specify the IP address of the target (-t or --target).

For power strips and other multi-port devices, you may need to specify -d (--deviceID) and -c (--childID).

If you get the response, especially when using "-C":
Received: 
{
  "error": "TP-Link error: unpack requires a string argument of length 4"
}
it probably means you picked the wrong device type 
