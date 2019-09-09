Indigo-TP-LInk
==============
Overview
--------

The TP-Link Device plugin makes Wifi-based SmartPlugs appear as Relay (on/off) devices.
This plugin supports all known TP-Link smart plugs, including single, dual and 6 outlet plug strips.

Simply install the plug-in in indigo 7, then add a new device with type **TP-Link Device** and Model **TP-Link Smart plug (all versions)**.
There will be a short (4 second) delay while the plugin looks for any smart plugs on the local network. You will then see a window with a pull-down menu. Here you will find any plugs that were discovered and the option to enter the plug information manually. If you select manual entry, yopu will then be prompted for the IP Address of the device, enter that and click Continue. 

If you don't know the IP Address, you can get from your DHCP server (i.e., router).
You might also want to make the DHCP address assignment a static mapping, so that you won't have to change indigo should the IP address change,
which can happen, for example, if you lose power.

Next, whether you selected the device from the menu, or entered its IP Address manually, you will see a window with information about the plug.
Here you can change the default settings:
* For dual-plugs and plug strips you can select the outlet number.
* You can enable polling of the device. Polling is required if you want Indigo to track changes made locally at the device, or via the kasa app. Polling is also required if you want energy data from an energy reporting capable device.
* For single plugs you can set the polling frequency. There are two settings, for when the plug is off, and when it is on. Polling more often than every 5 seconds may affect your comoputer's performance. For dual-plugs and plug strips, the polling frequency is controlled by the plugin's Config settings.

Click Save and then simply click on or off on your device.  

A command line tool for manually querying TP-Link smart plug devices, **tplink_smartplug.py** is contained in the Plugins Server Plugin folder.
