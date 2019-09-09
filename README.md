Indigo-TP-LInk
==============
Overview
--------

The TP-Link Device plugin makes Wifi-based SmartPlugs appear as Relay (on/off) devices.
This plugin supports all known TP-Link smart plugs, including single, dual and 6 outlet plug strips.

Double-click the plugin to install it in indigo 7 or higher. Then add a new device with type **TP-Link Device** and Model **TP-Link Smart plug (all versions)**.
There will be a short (4 second) delay while the plugin looks for any smart plugs on the local network. You will then see a window with a pull-down menu. Here you will find any plugs that were discovered and the option to enter the plug information manually. If you select manual entry, you will be prompted for the IP Address of the device, enter that and click Continue. 

If you don't know the IP Address, you can get from your DHCP server (probably your router).
You might also want to make the DHCP address assignment a static mapping, so that you won't have to change indigo should the IP address change,
which can happen, for example, if you lose power.

Next, whether you selected the device from the menu, or entered its IP Address manually, you will see a window with information about the plug device.
Here you can change the default settings:
* For dual-plugs and plug strips you can select the outlet number.
* You can enable or disable polling of the device. Polling is required if you want Indigo to track changes made locally at the device, or via the __kasa__ app. Polling is also required if you want to access energy data from a device with energy reporting capability.
* For single plugs you can set the polling frequency. There are two settings, for when the plug is off, and when it is on. Polling more often than every 5 seconds may affect your computer's performance. For dual-plugs and plug strips, the polling frequency is controlled by the plugin's Config settings.

There is one other setting you may wish to enable, __on__/__off__ logging. This can be set in the plugin's Config settings. If this setting is enabled Indigo will create a log entry each time you turn a plug on or off or, if polling is enabled, when a change is detected.

Click __Save__ and then simply click __on__ or __off__ on your device. _Toggle_ is supported. 

A command line tool for manually querying TP-Link smart plug devices, **tplink_smartplug.py** is contained in the Plugins Server Plugin folder.
