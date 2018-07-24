# indigo-TP-LInk
# Overview

The TP-Link Device plugin makes Wifi-based SmartPlugs appear as Relay (on/off) devices.
Find the source here [1].

Simply install the plug-in in indigo 7, then add a new device with type SmartPlug.
You'll need to know its IP address, which you can get from your DHCP server (i.e., router).
You might want to make it a static mapping, so that you won't have to change indigo should the IP address change,
which can happen, for example, if you lose power.

Then simply click on or off.  

I implemented the default "status" request as "information". This returns an object with lots of details about the device, which is printed to the indigo log.

I decided to implement this as a plug-in, rather than a Virtual Device [3], because it makes it easier for the user, embeds the IP address as the device address, and allowed me to implement the "info" command in place of "status".

[1]: https://github.com/IndigoDomotics/TP-Link
[2]: http://wiki.indigodomo.com/doku.php?id=indigo_7_documentation:virtual_devices_interface#virtual_on_off_devices
