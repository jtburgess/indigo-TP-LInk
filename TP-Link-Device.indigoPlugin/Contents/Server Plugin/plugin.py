#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# import indigo

# import inspect				# Not needed once we convert logging to use format
import json
import logging
from os import path
import pdb
try:
  # python 3
  from queue import Queue
except:
  # python 2
  from Queue import Queue

import socket
from plugin_base import IndigoLogHandler

from tplink_dimmer_plugin import tplink_dimmer, dimmerModels
from tplink_relay_plugin import tplink_relay, relayModels
from tplink_relayswitch_plugin import tplink_relayswitch, relayswitchModels

# this is the generic protocol, no device specific commands
from protocol import tplink_protocol
# with sub classes for the two device types.
from tplink_dimmer_protocol import tplink_dimmer_protocol
from tplink_relay_protocol import tplink_relay_protocol
from tplink_relayswitch_protocol import tplink_relayswitch_protocol

# ditto for the polling thread
# from tpl_polling import pollingThread
from tpl_dimmer_poll import dimmer_poll
from tpl_relay_poll import relay_poll
from tpl_relayswitch_poll import relayswitch_poll


# Method to verify existance of an accessable TP-Link plug
def check_server(address):
    # Create a TCP socket
    s = socket.socket()
    s.settimeout(2.0)
    port = 9999
    # Check availability of port at address
    try:
        s.connect((address, port))
        return True
    except socket.error:
        return False
    finally:
        s.close()


################################################################################
class MyDebugHandler(IndigoLogHandler, object):
    ########################################
    """ define a log handler to format log messages by level """
    def __init__(self, displayName, level=logging.INFO, debug=False):
        super(IndigoLogHandler, self).__init__(level)
        self.displayName = displayName
        self.debug = debug
        # self.plugin_file_handler = IndigoLogHandler.plugin_file_handler
        return

    def setLogLevel(self, loglevel):
        if loglevel == logging.DEBUG or loglevel == logging.THREADDEBUG:
            # send debug messages ONLY to the plugin specific log at: /Library/Application Support/Perceptive Automation/Indigo 7/Logs/your.plugin.id/plugin.log
            self.plugin_file_handler.loglevel = loglevel
            self.logger.info("Log level set to {}. Debug messages go to {}/plugin.log ONLY.".format(self.loglevel,
                indigo.server.getLogsFolderPath(pluginId='com.JohnBurgess.indigoplugin.TP-Link-Device')))
        else:
            # self.plugin_file_handler.loglevel = loglevel
            self.loglevel = loglevel
        # indigo.server.log("Received log level {}".format(self.loglevel))
        return

    def emit(self, record):
        """ not used by this class; must be called independently by indigo """
        level = record.levelname
        is_error = False
        if level == logging.INFO:		# 20
            logmessage = record.getMessage()
        elif level == logging.ERROR or level == logging.CRITICAL:		# 40, 50
            logmessage = '({}:{}:{}): {}'.format(path.basename(record.pathname), record.funcName, record.lineno, record.getMessage())
            is_error = True
        else:
            logmessage = '({}:{}:{}): {}'.format(path.basename(record.pathname), record.funcName, record.lineno, record.getMessage())

        return


################################################################################
class Plugin(indigo.PluginBase):
    ########################################
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        self.my_debug_handler = MyDebugHandler(pluginDisplayName, logging.DEBUG)
        self.logger.addHandler(self.my_debug_handler)
        self.logger.removeHandler(self.indigo_log_handler)

        self.loglevel = pluginPrefs.get("logLevel", "info")
        self.my_debug_handler.setLogLevel(self.loglevel)
        self.logger.info("Log level init to {}".format(self.loglevel))
        self.logOnOff = pluginPrefs.get('logOnOff', False)
        self.tpThreads = {}
        self.tpDevices = {}
        self.tpQueue = Queue()
        self.deviceSearchResults = {}

        # self.logger.threaddebug(u"{} {} {} plugin 5".format('1', '2', '3'))
        # self.logger.debug(u"{} {} {} plugin 10".format('1', '2', '3'))
        # self.logger.info(u"{} {} {} plugin 20".format('foo', 'bar', 'baz'))
        # self.logger.error(u"{} {} {} plugin 40".format('1', '2', '3'))
        return

    def getSubType(self, model):
      """ translate model names to module sub-type strings, which are then used for sub-classes """
      model = model[:5]  # ingore the (US) in  for example, HS105(US)
      if model in relayModels:
        return 'tplinkSmartPlug'
      elif model in relayswitchModels:
        return 'tplinkSmartSwitch'
      elif model in dimmerModels:
        return 'tplinkSmartBulb'
      else:
        self.logger.error("model '%s' is not recognised" % model)
        return 'unknown'

    def getSubClass(self, deviceTypeId):
      """ device-type specific functionality is broken out into sub-classes;
          unfortunately, indigo wont directly call the subclass, so I have to hack it
      """
      if deviceTypeId == 'tplinkSmartPlug':
        return tplink_relay(self.logger, self.pluginPrefs, self)
      elif deviceTypeId == 'tplinkSmartSwitch':
        return tplink_relayswitch(self.logger, self.pluginPrefs, self)
      elif deviceTypeId == 'tplinkSmartBulb':
        return tplink_dimmer(self.logger, self.pluginPrefs, self)
      else:
        self.logger.error("deviceTypeId '%s' is not recognised" % deviceTypeId)
        # this will cause things to crash
        return None

    def getPollClass(self, dev):
      """ similarly, the polling function has device-type specific functionality """
      if dev.deviceTypeId == 'tplinkSmartPlug':
        return relay_poll(self, dev)
      elif dev.deviceTypeId == 'tplinkSmartSwitch':
        return relayswitch_poll(self, dev)
      elif dev.deviceTypeId == 'tplinkSmartBulb':
        return dimmer_poll(self, dev)
      else:
        self.logger.error("deviceTypeId '%s' is not recognised" % dev.deviceTypeId)
        # this will cause things to crash
        return None

    def getSubProtocol(self, dev):
      """ to start with, just some of the commands are different,
          but this allows other protocol things to be sub-type specific
      """
      addr = dev.address
      port = 9999

      if dev.deviceTypeId == 'tplinkSmartPlug':
        if 'multiPlug' in dev.pluginProps and dev.pluginProps['multiPlug']:
          # a sub-type of tplinkSmartPlug
          deviceId = dev.pluginProps['deviceId']
          childId = dev.pluginProps['outletNum']
        else:
          deviceId = None
          childId = None
        self.logger.debug("called with tplink_relay addr: {}, deviceID {}, chlldID {}".format(addr, deviceId, childId))
        return tplink_relay_protocol(addr, port, deviceId, childId, logger=self.logger)
      elif dev.deviceTypeId == 'tplinkSmartSwitch':
        self.logger.debug("called with tplink_relayswitch addr: {}".format(addr))
        return tplink_relayswitch_protocol(addr, port, None, None, logger=self.logger)
      elif dev.deviceTypeId == 'tplinkSmartBulb':
        self.logger.debug("called with tplink_dimmer addr: {}".format(addr))

        dimmer_proto = tplink_dimmer_protocol(addr, port, None, None, logger=self.logger)
        if 'rampTime' in dev.pluginProps:
          dimmer_proto.setArg2 (dev.pluginProps['rampTime'])
        else:
          dimmer_proto.setArg2 ( 1000 ) # default 1 second

        return dimmer_proto
      else:
        self.logger.error("deviceTypeId '%s' is not recognised" % dev.deviceTypeId);
        # this will cause things to crash, later
        return None

    ########################################
    def startup(self):
        self.logger.debug("startup called")
        return

    def shutdown(self):
        self.logger.debug("shutdown called")
        return

    # method to return a device parameter, or plugin default for that parameter, or a global default
    def devOrPluginParm(self, dev, attribute, default):
      result = None
      if attribute in dev.pluginProps and dev.pluginProps[attribute] != '':
        result = [dev.pluginProps[attribute], 'dev']
      elif attribute in  self.pluginPrefs and self.pluginPrefs[attribute] != '':
        result = [self.pluginPrefs[attribute], 'plugin']
      else:
        result = [default, "default"]

      if int(result[0]) > 1000000000:
        self.logger.info("{} max exceeded (). using 1000000000".format(attribute, result[0]))
        result[0] = '1000000000'
      self.logger.threaddebug("for attribute {}, using {}".format(attribute, result))
      return result

    ########################################
    # Validation handlers
    ######################
    def validateDeviceConfigUi(self, valuesDict, typeId, devId):
        self.logger.debug("called with typeId={}, devId={}, and address={}.".format(typeId, devId, valuesDict['address']))
        self.logger.threaddebug("for devId={} valuesDict={}.".format(devId, valuesDict))
        errorsDict = indigo.Dict()

        # If we have been asked to re-initialize this device...
        if ('initialize' in valuesDict and valuesDict['initialize']):
            self.initializeDev(valuesDict)

        # newDev is an invidible checkbox to enable a re-initialize button in the Device UI
        valuesDict['newDev'] = False
        valuesDict['initialize'] = False

        # do any device-type specific config
        subType = self.getSubClass(indigo.devices[devId].deviceTypeId)
        valuesDict = subType.validateDeviceConfigUi(valuesDict, typeId, devId)

        return (True, valuesDict, errorsDict)

    ######################
    def validatePrefsConfigUi(self, valuesDict):
        """set the log level dynamically"""
        self.logger.debug("Current log level:{} new log level={}".format(self.loglevel, valuesDict['logLevel']))
        self.loglevel = valuesDict['logLevel']
        self.pluginPrefs["logLevel"] = self.loglevel
        self.my_debug_handler.setLogLevel(self.loglevel)
        self.logger.info("Changed log level to {}".format(self.loglevel))

        return(True, valuesDict)


    ########################################
    # Starting and stopping devices
    ######################
    def deviceStartComm(self, dev):
        self.logger.debug("called for: %s@%s." % (dev.name, dev.address) )
        # Called for each device on startup
        # Commit any state changes
        dev.stateListOrDisplayStateIdChanged()

        # get some data for local use from the device
        name      = dev.name
        address   = dev.address
        subType = self.getSubClass(dev.deviceTypeId)
        subType.deviceStartComm(dev)

        devPoll = self.devOrPluginParm(dev, 'devPoll', False)[0]

        # self.logger.debug("deviceStartComn starting %s" % (name), type="TP-Link" % (isError=False) )
        if name in self.tpThreads:
            self.logger.debug("deviceStartComm error: Thread exists for %s , %s- %s" % (name, address, self.tpThreads[name]))
            # self.tpThreads[address].interupt(None)
        elif not devPoll:
            self.logger.info("Polling thread is disabled for %s, %s." % (name, address) )
        elif devPoll:
            # We start one thread per device ip address
            if address not in self.tpThreads:
                # Create a polling thread
                if not 'deviceId' in dev.pluginProps:
                    self.logger.error("%s: Oops. No deviceId for %s in deviceStartComm" % (name, address) )
                self.process = self.getPollClass(dev)
                self.tpThreads[address] = self.process
                self.logger.debug("Polling thread started for device %s, %s" % (name, address) )
                # ... and save a copy of the device that created this thread
                self.tpDevices[address] = dev
            elif address in self.tpThreads:
                self.logger.debug("deviceStartComm IN thread update %s, %s" % (name, address) )

                # self.logger.info(u"deviceStartComm related to device %s, %s" % (deviceId, "foio") )
                # Since a thread already exists, this is probably a multiPlug
                self.tpThreads[address].interupt(dev=dev, action='dev')
            else:
                # something is horribly wrong
                self.logger.error("deviceStartComm error in thread creation %s, %s" % (name, address) )

        # Since we got this far, we might as well tell someone
        dev.replaceOnServer()
        if devPoll:
          self.logger.info("Polling started for %s@%s." % (name, address) )
        return

    def deviceStopComm(self, dev):
        # Called when communication with the hardware should be shutdown.
        # get some data for local use from the device
        name      = dev.name
        address   = dev.address

        self.logger.debug("deviceStopComn entered %s, %s" % (name, address))
        if address in self.tpThreads:  # We don't want to waste time if a polling thread was never started
            self.logger.debug("deviceStopComn ending %s, %s" % (name, address))
            self.tpThreads[address].stop()
            del self.tpThreads[address]
        return

    ########################################
    ########################################
    def initializeDev(self, valuesDict):
        self.logger.debug(" called with: %s." % ((valuesDict)) )

        devAddr = valuesDict['address']
        devName = "new device at " + devAddr
        devPort = 9999
        deviceId = valuesDict['deviceId']
        childId = None

        # dont know the device type, so use generic protocol, and only generic commands
        tplink_dev = tplink_protocol (devAddr, devPort, deviceId, childId, logger=self.logger)
        result = tplink_dev.send('info')
        # self.deviceSearchResults[devAddr] = result

        self.logger.debug("%s: InitializeDev 3 got %s" % (devName, result))
        data = json.loads(result)
        self.deviceSearchResults[devAddr] = data
        self.logger.debug("%s: InitializeDev 4 got %s" % (devName, data))
        valuesDict['deviceId'] = data['system']['get_sysinfo']['deviceId']
        valuesDict['model'] = data['system']['get_sysinfo']['model']

        subType = self.getSubClass(self.getSubType(valuesDict['model']))
        valuesDict =  subType.initializeDev(valuesDict, data)

        valuesDict['initialize'] = False

        return valuesDict

    ########################################
    # Relay Action callback
    ######################
    ### (deprecated) def actionControlDimmerRelay(self, action, dev):
    def actionControlDevice (self, action, dev):
        self.logger.debug("called with: {} for {}.".format(action.deviceAction, dev.name))

        arg1 = action.actionValue
        arg2 = None

        ###### TURN ON ######
        if action.deviceAction == indigo.kDeviceAction.TurnOn:
            cmd = "on"
            # why not set to 100 for smart light switch?
            if dev.deviceTypeId == 'tplinkSmartSwitch': arg1 = dev.brightness
        ###### TURN OFF ######
        elif action.deviceAction == indigo.kDeviceAction.TurnOff:
            cmd = "off"
        ###### TOGGLE ######
        elif action.deviceAction == indigo.kDeviceAction.Toggle:
            if dev.onState:
                cmd = "off"
            else:
                cmd = "on"
        ###### SET BRIGHTNESS  ######
        elif action.deviceAction == indigo.kDimmerRelayAction.SetBrightness:
            # ToDo: is different logic needed when the bulb is only on/off?  What about color?
            # trim the edge cases to pure on/off
            if action.actionValue <= 1:
              cmd = "off"
              arg1 = 0
            elif action.actionValue >= 99:
              cmd = "on"
              arg1 = 100
            else:
              cmd = "setBright"

            self.logger.debug("set Brightness to {}, cmd=<{}>".format(arg1, cmd))
        else:
            self.logger.error("Unknown command: {}".format(action.deviceAction))
            return

        # even though the command is the same, the JSON may be different for different devices
        # and some (set brghtness) require parameters
        tplink_dev = self.getSubProtocol (dev)
        result = tplink_dev.send(cmd, str(arg1), arg2)
        sendSuccess = False
        try:
            result_dict = json.loads(result)
            self.logger.debug("send({}) result: {}".format(cmd, result_dict))
            error_code = tplink_dev.getErrorCode(result_dict)
            if error_code == 0:
                sendSuccess = True
            else:
                self.logger.error("turn {} command failed (error code: {})".format(cmd, error_code))
        except:
            pass

        indigo.debugger()
        if sendSuccess:
            # If success then log that the command was successfully sent, and update state vars
            subType = self.getSubClass(dev.deviceTypeId)
            subType.actionControlDevice (action, dev, cmd, logOnOff=self.logOnOff, bright=arg1)
            dev.stateListOrDisplayStateIdChanged()

        else:
            # Else log failure but do NOT update state on Indigo Server.
            self.logger.error('send "{}" "{}"" failed with result "{}"'.format(dev.name, cmd, result))
            return

        # force a poll if everything went well
        if self.devOrPluginParm(dev, 'devPoll', False)[0] and dev.address in self.tpThreads:
            self.tpThreads[dev.address].interupt(state=True, action='state')
        return

    # The 'status' callback, now takes on the old Device Info plugin Menu item functionality (sort of)
    def getInfo(self, pluginAction, dev):
        address = dev.address

        self.logger.info("Device Info for: {}".format(dev.name))
        self.logger.info("    TPlink device type: {}".format(dev.deviceTypeId))
        self.logger.info("    TP Link model: {}".format(dev.pluginProps['model']))
        self.logger.info("    IP address: {}".format(dev.address))
        self.logger.info("    MAC address: {}".format(dev.pluginProps['mac']))
        self.logger.info("    Device ID: {}".format(dev.pluginProps['deviceId']))
        if 'rssi' in dev.pluginProps: self.logger.info("    WiFi Signal Strength: {}".format(dev.pluginProps['rssi']))
        self.logger.info("    alias : {}".format(dev.states['alias']))
        self.logger.info("    description: {}".format(dev.description))

        devPoll = self.devOrPluginParm(dev, 'devPoll', False)
        self.logger.info("    Polling enabled: {}".format(devPoll))
        if devPoll:
          self.logger.info("      On state polling freq: {}".format(self.devOrPluginParm(dev, 'onPoll', 10)))
          self.logger.info("      Off state polling freq: {}".format(self.devOrPluginParm(dev, 'offPoll', 30)))
          self.logger.info("      Poll Warning interval: {}".format(self.devOrPluginParm(dev, 'WarnInterval', 5)))
          self.logger.info("      SlowDown {} seconds at each warning".format(self.devOrPluginParm(dev, 'SlowDown', 1)))
          self.logger.info("      Shutdown after {} errors".format(self.devOrPluginParm(dev, 'StopPoll', 20)))

        try:
            if address in self.tpThreads:
              if dev.enabled == False:
                self.logger.info("    Device communication is disabled.")
              elif self.tpThreads[address].interupt(dev=dev, action='status'):
                self.logger.info("    Device polling and states updated.".format(dev.name))
              # else error message logged in tpThreads.interrupt
            else:
              self.logger.info("   Device polling is disabled.")

            if dev.displayStateId == "onOffState":
              curState =  'on' if dev.states['onOffState'] else 'off'
            elif "brightnessLevel" in dev.states:
              curState = "brightness=" + str(dev.states["brightnessLevel"])
            else:
              curState = self.displayStateId
            self.logger.info("    current state: {}".format(curState))

            # see if the particular device has anything to add...
            subType = self.getSubClass(dev.deviceTypeId)
            subType.getInfo(pluginAction, dev)

        except Exception as e:
            self.logger.error("%s: Device not reachable and states could not be updated. %s" % (dev.name, str(e)) )

        return

    ########################################
    # General Action callback
    ######################

    # Energy and Status callback
    def actionControlUniversal(self, action, dev):
        self.logger.debug("Action: %s for device: %s." % (action.deviceAction, dev.name))

        if action.deviceAction == indigo.kUniversalAction.RequestStatus:
            self.getInfo("", dev)
        else:
          subType = self.getSubClass(dev.deviceTypeId)
          subType.actionControlUniversal(action, dev)

        return

    ########################################
    # Device ConfigUI Callbacks
    ######################
    def getDeviceStateList(self, dev):
        """Dynamically create/update the states list for each device"""
        self.logger.debug("called for: '%s'." % (dev.name))
        self.logger.threaddebug("   dev: %s." % (dev))

        statesDict = indigo.PluginBase.getDeviceStateList(self, dev)
        rssi  = self.getDeviceStateDictForNumberType("rssi", "rssi", "rssi")
        alias = self.getDeviceStateDictForStringType("alias", "alias", "alias")
        statesDict.append(rssi)
        statesDict.append(alias)

        subType = self.getSubClass(dev.deviceTypeId)
        return subType.getDeviceStateList(dev, statesDict)

    def getTpDevice(self, filter="", valuesDict=None, typeId="", targetId=0):
        """ discover TP-Link devices on the network,
                (ToDo? Restrict to the matching deviceTypeID already selected
                 or not, so you can see if you picked the wrong deviceType)
            a callback in Devices.xml to return a list
        """
        self.logger.debug("called for: %s, %s, %s." % (filter, typeId, targetId))
        self.logger.threaddebug("called for: %s, %s, %s, %s." % (filter, typeId, targetId, valuesDict))

        deviceArray = []
        if indigo.devices[targetId].configured:
            return deviceArray
        else:
            tplink_discover = tplink_protocol(None, None)
            try:
                self.deviceSearchResults = tplink_discover.discover()
            except Exception as e:
                self.logger.error("Discovery connection failed with (%s)" % (str(e)))
                return deviceArray

            self.logger.debug("received %s" % (self.deviceSearchResults))

            # This is discovery; part of which is determining which type it is.
            for address in self.deviceSearchResults:
                model = self.deviceSearchResults[address]['system']['get_sysinfo']['model'] #[:5]
                devSubType = self.getSubType(model)
                self.logger.debug("getSubType for model %s returned %s" % (model, devSubType))
                menuText = model + " @ " + address + "("+devSubType+")"
                menuEntry = (address, menuText)
                deviceArray.append(menuEntry)
            menuEntry = ('manual', 'manual entry')
            deviceArray.append(menuEntry)

            return deviceArray

    def selectTpDevice(self, valuesDict, typeId, devId):
        """ This method gets called at several different times in the device configuration process.
            (See Devices.xml)
            The first if/elif/else blocks sort all that out
        """
        self.logger.debug("called for: %s, %s, %s." % (typeId, devId, valuesDict['address']))
        self.logger.threaddebug("called for: %s, %s." % (devId, valuesDict))

        # most of this is the same for all sub types
        if valuesDict['addressSelect'] != 'manual':
            self.logger.debug("%s -- %s\n" % (valuesDict['addressSelect'], valuesDict['manualAddressResponse']))
            valuesDict['address'] = valuesDict['addressSelect']
            address = valuesDict['address']
            valuesDict['deviceId']  = self.deviceSearchResults[address]['system']['get_sysinfo']['deviceId']
            valuesDict['model']     = self.deviceSearchResults[address]['system']['get_sysinfo']['model']
            valuesDict['displayOk'] = True
            valuesDict['displayManAddress'] = True

        elif valuesDict['manualAddressResponse']:  # An ip address has been manually entered, so we can continue
            self.logger.  threaddebug("%s -- %s\n" % (valuesDict['address'], valuesDict['manualAddressResponse']))
            # First, make sure there is actually a plug we can talk to at this address
            if not check_server(valuesDict['address']):
                # Bail out
                errorsDict = indigo.Dict()
                errorsDict["showAlertText"] = "Could not find a TP-Link device at this address"
                errorsDict['address'] = "Address not reachable"
                return(valuesDict, errorsDict)
            # Ok, we can continue
            valuesDict = self.initializeDev(valuesDict)
            valuesDict['displayOk'] = True
            valuesDict['displayManAddressButton'] = False

        elif valuesDict['addressSelect'] == 'manual':  # They want to enter an ip address manually, so we display a textfield & return
            valuesDict['displayManAddress'] = True
            valuesDict['displayManAddressButton'] = True
            valuesDict['manualAddressResponse'] = True
            return valuesDict

        # Since we got here, we must have a valid address
        address = valuesDict['address']

        # validate actual discovered device type vs that indicated by user
        devTypeID = indigo.devices[devId].deviceTypeId
        discoveredTypeID = self.getSubType(valuesDict['model'])
        if devTypeID != discoveredTypeID:
            self.logger.error("Error: selected and actual Device types don't match ({} vs {})".format(devTypeID, discoveredTypeID))
            self.logger.error("    Delete and try again.")
            valuesDict['devPoll'] = False
            return valuesDict

        # device level overrides to polling parameters
        if valuesDict['devPoll'] != '':
          indigo.devices[devId].pluginProps['devPoll'] = valuesDict['devPoll'] # for use by devOrPluginParm()

        try:
            subType = self.getSubClass(devTypeID)
            valuesDict = subType.selectTpDevice( valuesDict, typeId, devId)
        except Exception as e:
            self.logger.error("Error getting Device Info. Are you sure you picked the right device Type({})".format(devTypeID))
            self.logger.error("    error was '{}'".format(str(e)))
            valuesDict['devPoll'] = False

        return valuesDict

    def selectTpOutlet(self, filter="", valuesDict=None, typeId="", targetId=0):
        ### specific to the Relay type; dont bother subclassing (see Devices.xml)
        self.logger.debug("called for: %s, %s, %s." % (filter, typeId, targetId))
        self.logger.threaddebug("called for: %s, %s, %s, %s." % (filter, typeId, targetId, valuesDict))

        outletArray = []

        if 'newDev' in valuesDict and 'address' in valuesDict:
            address = valuesDict['address']
            if address in self.deviceSearchResults:
                self.logger.debug("1 in dictoutlets avail %s" % (valuesDict['outletsAvailable']))
                # if valuesDict['addressSelect'] == 'manual':
                self.logger.debug("2 in dictoutlets avail %s" % (valuesDict['outletsAvailable']))
                if 'child_num' in self.deviceSearchResults[address]['system']['get_sysinfo']:
                    self.logger.debug("3 in dictoutlets avail %s" % (valuesDict['outletsAvailable']))
                    maxOutlet = int(self.deviceSearchResults[address]['system']['get_sysinfo']['child_num'])+1
                    address = valuesDict['address']

                    for outlet in range(1, maxOutlet):
                        internalOutlet = int(outlet)-1
                        menuEntry = (str(internalOutlet).zfill(2), outlet)
                        outletArray.append(menuEntry)
                else:
                    self.logger.debug("not in dict outlets avail %s" % (valuesDict['outletsAvailable']))
                    for outlet in range(0, int(valuesDict['outletsAvailable'])):
                        self.logger.debug("loop %s" % (outlet))
                        internalOutlet = int(outlet)
                        menuEntry = (str(internalOutlet).zfill(2), outlet+1)
                        outletArray.append(menuEntry)

            elif int(valuesDict['outletsAvailable']) > 0:
                self.logger.debug("outlets avail: %s" % (valuesDict['outletsAvailable']))
                for outlet in range(0, int(valuesDict['outletsAvailable'])):
                    self.logger.debug("loop %s" % (outlet))
                    internalOutlet = int(outlet)
                    menuEntry = (str(internalOutlet).zfill(2), outlet+1)
                    outletArray.append(menuEntry)

        self.logger.debug("returned: OA=%s" % (outletArray))
        return outletArray

    ########################################
    # Menu callbacks defined in MenuItems.xml
    # I haven't been able to figure out how to make these calls soecific to the device Type
    ########################################

    """
    ########################################
    # Device reporting
    def displayButtonPressed(self, valuesDict, clg_func):
        " " " callback to prepare the data for the "display device information" configUI display
             (See MenuItems.xml)
        " " "
        self.logger.debug("called for targetDevice {} from {}".format(valuesDict['targetDevice'], clg_func))
        self.logger.threaddebug("called with valuesDict={}".format(valuesDict))

        try:
            devNumber = int(valuesDict['targetDevice'])
            dev = indigo.devices[devNumber]
        except:
            errorsDict = indigo.Dict()
            errorsDict['targetDevice'] = "You must select a device"
            errorsDict["showAlertText"] = "You must select a device"
            return(valuesDict, errorsDict)

        props = dev.pluginProps
        self.logger.threaddebug("pluginPropsr=%s" % (props) )

        valuesDict['address']       = props['address']
        valuesDict['alias']         = dev.states['alias']
        valuesDict['deviceTypeId']  = dev.deviceTypeId
        valuesDict['model']         = props['model']
        valuesDict['description']   = dev.description
        valuesDict['deviceId']      = props['deviceId']
        valuesDict['mac']           = props['mac']
        valuesDict['devPoll']       = props['devPoll']
        valuesDict['offPoll']       = props['offPoll']
        valuesDict['onPoll']        = props['onPoll']
        valuesDict['displayOk']     = True

        subType = self.getSubClass(dev.deviceTypeId)
        valuesDict = subType.displayButtonPressed(dev, valuesDict)
        self.logger.threaddebug("Device info = %s" % (valuesDict) )

        return(valuesDict)

    def printToLogPressed(self, valuesDict, clg_func):
        " " " callback to prepare the report for display in the log
             (See MenuItems.xml)
        " " "
        self.logger.debug("called for dev {} from {}".format(valuesDict['targetDevice'], clg_func))
        self.logger.threaddebug("Received {}".format(valuesDict))

        devNumber = int(valuesDict['targetDevice'])
        dev = indigo.devices[devNumber]
        rpt_fmt = "            {0!s:25}{1!s}\n"
        subType = self.getSubClass(dev.deviceTypeId)

        report = "Tp-Link device report\n" + \
            rpt_fmt.format("TP-link Device Type:", dev.deviceTypeId) + \
            rpt_fmt.format("Indigo Device Name:", dev.name) + \
            rpt_fmt.format("IP Address:", valuesDict['address']) + \
            rpt_fmt.format("MAC Address:", valuesDict['mac']) + \
            rpt_fmt.format("Device ID:", valuesDict['deviceId']) + \
            rpt_fmt.format("Alias:", valuesDict['alias']) + \
            rpt_fmt.format("Model:", valuesDict['model'])
        devPoll = self.devOrPluginParm(dev, 'devPoll', False)
        report += rpt_fmt.format("Polling enabled:", devPoll)
        if devPoll[0]:
          report +=
            rpt_fmt.format("On state polling freq:", self.devOrPluginParm(dev, 'onPoll', 10)) + \
            rpt_fmt.format("Off state polling freq:", self.devOrPluginParm(dev, 'offPoll', 30)) + \
            rpt_fmt.format("Poll Warning interval:", self.devOrPluginParm(dev, 'WarnInterval', 5)) + \
            subType.printToLogPressed( valuesDict, rpt_fmt)

        self.logger.info("%s" % (report, ) )
        return
    """

    ########################################
    # Menu callbacks defined in Actions.xml
    # I haven't been able to figure out how to make these calls soecific to the device Type
    ########################################
    def reEnableComms(self, pluginAction, dev):
      self.logger.info("Device Communications (re-)enabled")
      indigo.device.enable(dev.id, value=True)
      return

    def SetDoubleClickAction(self, pluginAction, dev):
      subType = self.getSubClass (dev.deviceTypeId)
      return subType.SetDoubleClickAction(pluginAction, dev)

    def SetLongPressAction(self, pluginAction, dev):
      subType = self.getSubClass (dev.deviceTypeId)
      return subType.SetLongPressAction(pluginAction, dev)

    def set_gentle_off_time(self, pluginAction, dev):
      subType = self.getSubClass (dev.deviceTypeId)
      return subType.set_gentle_off_time(pluginAction, dev)

    def set_gentle_on_time(self, pluginAction, dev):
      subType = self.getSubClass (dev.deviceTypeId)
      return subType.set_gentle_on_time(pluginAction, dev)

    def set_fade_on_time(self, pluginAction, dev):
      subType = self.getSubClass (dev.deviceTypeId)
      return subType.set_fade_on_time(pluginAction, dev)

    def set_fade_off_time(self, pluginAction, dev):
      subType = self.getSubClass (dev.deviceTypeId)
      return subType.set_fade_off_time(pluginAction, dev)

    def set_HSV(self, pluginAction, dev):
      subType = self.getSubClass (dev.deviceTypeId)
      return subType.set_HSV(pluginAction, dev)

    def set_ColorTemp(self, pluginAction, dev):
      subType = self.getSubClass (dev.deviceTypeId)
      return subType.set_ColorTemp(pluginAction, dev)
