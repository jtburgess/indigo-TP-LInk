**Important**:
If you used the previous (0.2.0) release, be aware that you cannot use any devices from that version as is.  Please read this forum thread:
 [This is a Link](https://forums.indigodomo.com/viewtopic.php?f=132&t=17064&sid=00cd156d0db5ceb39414f90df3a673cb&start=75) .
Perhaps the simplest option is to delete the old devices, install the new version and let it auto-discover your devices.

Indigo-TP-LInk
==============
Overview
--------

The TP-Link Device plugin makes TP-Link Wi-fi-based SmartPlugs appear as __Relay__ (on/off) devices in Indigo.
This plugin supports all known TP-Link smart plugs, including single, dual and 6 outlet plug strips.

Double-click the plugin to install it in indigo 7 or higher. Then add a new device with type **TP-Link Device** and Model **TP-Link Smart plug (all versions)**.
There will be a short (4 second) delay while the plugin searches for smart plugs on the local network. You will then see a window with a pull-down menu. Here you will find any plugs that were discovered and the option to enter the plug information manually. If you select manual entry, you will be prompted for the IP Address of the device, enter that and click Continue. 

If you don't know the IP Address, you can get from your DHCP server (probably your router).
You might also want to make the DHCP address assignment permanent, with a static mapping. By doing this you won't have to change indigo should the plug's IP address change, which can happen, for example, if you lose power.

Next, whether you selected the device from the menu, or entered its IP Address manually, you will see a window with information about the plug device.
Here you can change the default settings:
* For dual-plugs and plug strips you can select the outlet number (1-2 or 1-6).
* You can enable or disable polling of the device. Polling is required if you want Indigo to track changes made locally at the device, or via the __kasa__ app. Polling is also required if you want to access energy data from a device with energy reporting capability.
* For single plugs you can set the polling frequency. There are two settings, for when the plug is off, and when it is on.  For energy reporting plugs, you will probably want a faster polling time when the plug is on. Otherwise you can set both settings to the same interval. For dual-plugs and plug strips, the polling frequency is controlled by the plugin's Config settings. Note that polling more often than every 5 seconds may affect your computer's performance.

There is one other setting you may wish to enable, __on__/__off__ logging. This can be set in the plugin's Config settings. If this setting is enabled Indigo will create a log entry each time a plug is turned on or off in Indigo.  If polling is enabled, the plugin will also log each time an __on__/__off__ change is detected that was not initiated from Indigo.

Click __Save__ and then simply click __on__ or __off__ on your device. _Toggle_ is supported. 

A command line tool for manually querying TP-Link smart plug devices, **tplink_smartplug.py** is included with the Plugin.
