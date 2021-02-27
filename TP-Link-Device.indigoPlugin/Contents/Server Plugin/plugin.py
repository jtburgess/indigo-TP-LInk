#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# import indigo

# import inspect				# Not needed once we convert logging to use format
import json
import logging
from os import path
import pdb
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
    def __init__(self, displayName, level=logging.NOTSET, debug=False):
        super(IndigoLogHandler, self).__init__(level)
        self.displayName = displayName
        self.debug = debug
        return

    def setLogLevel(self, loglevel):
        self.loglevel = loglevel
        # indigo.server.log("Received log level {}".format(self.loglevel))
        return

    def emit(self, record):
        """ not used by this class; must be called independently by indigo """
        level = record.levelname
        is_error = False
        if level == 'THREADDEBUG' and self.loglevel == 'debug':	# 5
            logmessage = '({}:{}:{}): {}'.format(path.basename(record.pathname), record.funcName, record.lineno, record.getMessage())
        elif level == 'DEBUG' and (self.loglevel == 'trace' or self.loglevel == "debug"):	# 10
            logmessage = '({}:{}:{}): {}'.format(path.basename(record.pathname), record.funcName, record.lineno, record.getMessage())
        elif level == 'INFO':		# 20
            logmessage = record.getMessage()
        elif level == 'WARNING':	# 30
            logmessage = '({}:{}:{}): {}'.format(path.basename(record.pathname), record.funcName, record.lineno, record.getMessage())
        elif level == 'ERROR':		# 40
            logmessage = '({}:{}:{}): {}'.format(path.basename(record.pathname), record.funcName, record.lineno, record.getMessage())
            is_error = True
        else:
            return

        indigo.server.log(message=logmessage, type=self.displayName, isError=is_error)
        return


################################################################################
class Plugin(indigo.PluginBase):
    ########################################
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        self.my_debug_handler = MyDebugHandler(pluginDisplayName, logging.THREADDEBUG)
        self.logger.addHandler(self.my_debug_handler)
        self.logger.removeHandler(self.indigo_log_handler)

        self.loglevel = pluginPrefs.get("logLevel", "info")
        self.my_debug_handler.setLogLevel(self.loglevel)
        self.logger.info(u"Log level set to {}".format(self.loglevel))
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
        return relay_poll(self.logger, dev, self.logOnOff, self.pluginPrefs)
      elif dev.deviceTypeId == 'tplinkSmartSwitch':
        return relayswitch_poll(self.logger, dev, self.logOnOff, self.pluginPrefs)
      elif dev.deviceTypeId == 'tplinkSmartBulb':
        return dimmer_poll(self.logger, dev, self.logOnOff, self.pluginPrefs)
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
        self.logger.debug(u"called with tplink_relay addr: {}, deviceID {}, chlldID {}".format(addr, deviceId, childId))
        return tplink_relay_protocol(addr, port, deviceId, childId, logger=self.logger)
      elif dev.deviceTypeId == 'tplinkSmartSwitch':
        self.logger.debug(u"called with tplink_relayswitch addr: {}".format(addr))
        return tplink_relayswitch_protocol(addr, port, None, None, logger=self.logger)
      elif dev.deviceTypeId == 'tplinkSmartBulb':
        self.logger.debug(u"called with tplink_dimmer addr: {}".format(addr))
        if 'rampTime' in dev.pluginProps:
          arg2 = dev.pluginProps['rampTime']
        else:
          arg2 = 1000 # default 1 second
        return tplink_dimmer_protocol(addr, port, None, None, logger=self.logger, arg2=arg2)
      else:
        self.logger.error("deviceTypeId '%s' is not recognised" % dev.deviceTypeId);
        # this will cause things to crash, later
        return None

    ########################################
    def startup(self):
        self.logger.debug(u"startup called")
        return

    def shutdown(self):
        self.logger.debug(u"shutdown called")
        return

    ########################################
    # Validation handlers
    ######################
    def validateDeviceConfigUi(self, valuesDict, typeId, devId):
        self.logger.debug(u"called with typeId={}, devId={}, and address={}.".format(typeId, devId, valuesDict['address']))
        self.logger.threaddebug(u"for devId={} valuesDict={}.".format(devId, valuesDict))
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
        self.logger.debug(u"Current log level:{} received log level={}".format(self.loglevel, valuesDict['logLevel']))
        self.logger.threaddebug(u"Current:{} received valuesDict={}".format(self.loglevel, valuesDict))
        self.loglevel = valuesDict['logLevel']
        self.pluginPrefs["logLevel"] = self.loglevel
        self.my_debug_handler.setLogLevel(self.loglevel)
        self.logger.info("Changed log level to {}".format(self.loglevel))

        return(True, valuesDict)


    ########################################
    # Starting and stopping devices
    ######################
    def deviceStartComm(self, dev):
        self.logger.debug(u"called for: %s@%s.", dev.name, dev.address)
        # Called for each device on startup
        # Commit any state changes
        dev.stateListOrDisplayStateIdChanged()
        dev.model = dev.pluginProps['model']

        # get some data for local use from the device
        name      = dev.name
        address   = dev.address
        subType = self.getSubClass(dev.deviceTypeId)
        subType.deviceStartComm(dev)

        if 'multiPlug' in dev.pluginProps and dev.pluginProps['multiPlug']:
            # a sub-type of tplinkSmartPlug
            # why is this special??
            devPoll = self.pluginPrefs['devPoll']
        else:
            devPoll = dev.pluginProps['devPoll']

        # self.logger.debug("deviceStartComn starting %s" % (name), type="TP-Link", isError=False)
        if name in self.tpThreads:
            self.logger.debug("deviceStartComm error: Thread exists for %s , %s- %s" % (name, address, self.tpThreads[dev.name]))
            # self.tpThreads[address].interupt(None)
        elif not devPoll:
            self.logger.info("Polling thread is disabled for device  %s, %s.", name, address)
        elif devPoll:
            # We start one thread per device ip address
            if address not in self.tpThreads:
                # Create a polling thread
                self.process = self.getPollClass(dev)
                self.tpThreads[address] = self.process
                self.logger.debug("Polling thread started for device %s, %s", name, address)
                # ... and save a copy of the device that created this thread
                self.tpDevices[address] = dev
            elif address in self.tpThreads:
                self.logger.debug(u"deviceStartComm IN thread update %s, %s", name, address)
                deviceID  = dev.pluginProps['deviceId']
                if not deviceID:
                    self.logger.error("%s: Oops.No deviceId for %s", name, address)
                else:
                    self.logger.debug("%s: Already had deviceId  %s", name, address)

                # self.logger.info(u"deviceStartComm related to device %s, %s", deviceId, "foio")
                # Since a thread already exists, this is probably a multiPlug
                self.tpThreads[address].interupt(dev=dev, action='dev')
            else:
                # something is horribly wrong
                self.logger.error(u"deviceStartComm error in thread creation %s, %s", name, address)

        # Since we got this far, we might as well tell someone
        dev.replaceOnServer()
        self.logger.info(u"Polling started for %s@%s.", dev.name, dev.address)
        return

    def deviceStopComm(self, dev):
        # Called when communication with the hardware should be shutdown.
        # get some data for local use from the device
        name      = dev.name
        address   = dev.address

        self.logger.debug(u"deviceStopComn entered %s, %s" % (name, address))
        if address in self.tpThreads:  # We don't want to waste time if a polling thread was never started
            self.logger.debug("deviceStopComn ending %s, %s" % (name, address))
            self.tpThreads[address].stop()
            del self.tpThreads[address]
        return

    ########################################
    ########################################
    def initializeDev(self, valuesDict):
        self.logger.debug(u" called with: %s.", (valuesDict))

        devAddr = valuesDict['address']
        devName = "new device at " + devAddr
        devPort = 9999
        deviceId = None
        childId = None

        # dont know the device type, so use generic protocol, and only generic commands
        tplink_dev = tplink_protocol (devAddr, devPort, deviceId, childId, logger=self.logger)
        result = tplink_dev.send('info')
        # self.deviceSearchResults[devAddr] = result

        self.logger.debug(u"%s: InitializeDev 3 got %s" % (devName, result))
        data = json.loads(result)
        self.deviceSearchResults[devAddr] = data
        self.logger.debug(u"%s: InitializeDev 4 got %s" % (devName, data))
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
        self.logger.debug(u"called with: {} for {}.".format(action.deviceAction, dev.name))

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
            self.logger.error(u'send "{}" "{}"" failed with result "{}"'.format(dev.name, cmd, result))
            return

        # force a poll if everything went well
        if dev.pluginProps['devPoll']:
            self.tpThreads[dev.address].interupt(state=True, action='state')
        return

    # The 'status' callback
    def getInfo(self, pluginAction, dev):
        self.logger.debug(u"Called for: %s." % (dev.name))
        address = dev.address

        try:
            self.tpThreads[address].interupt(dev=dev, action='status')
            self.logger.info("%s: Device reachable and states updated.", dev.name)
        except Exception as e:
            self.logger.error("%s: Device not reachable and states could not be updated. %s", dev.name, str(e))

        return

    ########################################
    # General Action callback
    ######################

    # Energy and Status callback
    def actionControlUniversal(self, action, dev):
        self.logger.debug(u"Action: %s for device: %s." % (action.deviceAction, dev.name))

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
        self.logger.debug(u" called for: '%s'." % (dev.name))
        self.logger.threaddebug(u"called for dev: %s." % (dev))

        statesDict = indigo.PluginBase.getDeviceStateList(self, dev)
        rssi  = self.getDeviceStateDictForNumberType(u"rssi", u"rssi", u"rssi")
        alias = self.getDeviceStateDictForStringType(u"alias", u"alias", u"alias")
        statesDict.append(rssi)
        statesDict.append(alias)

        subType = self.getSubClass(dev.deviceTypeId)
        return subType.getDeviceStateList(dev, statesDict)

    def getTpDevice(self, filter="", valuesDict=None, typeId="", targetId=0):
        """ discover devices on the network, but restrict to the matching deviceTypeID already selected
            a callback in Devices.xml to return a list
        """
        self.logger.debug(u"called for: %s, %s, %s." % (filter, typeId, targetId))
        self.logger.threaddebug(u"called for: %s, %s, %s, %s." % (filter, typeId, targetId, valuesDict))

        deviceArray = []
        if indigo.devices[targetId].configured:
            return deviceArray
        else:
            tplink_discover = tplink_protocol(None, None)
            try:
                self.deviceSearchResults = tplink_discover.discover()
            except Exception as e:
                self.logger.error("Discovery connection failed with (%s)" % (str(e)))

            self.logger.debug(u"received %s" % (self.deviceSearchResults))

            # This is discovery; part of which is determining which type it is.
            for address in self.deviceSearchResults:
                model = self.deviceSearchResults[address]['system']['get_sysinfo']['model'] #[:5]
                devSubType = self.getSubType(model)
                self.logger.debug(u"getSubType for model %s returned %s" % (model, devSubType))
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
        self.logger.debug(u"called for: %s, %s, %s." % (typeId, devId, valuesDict['address']))
        self.logger.threaddebug(u"called for: %s, %s." % (devId, valuesDict))

        # most of this is the same for both relay and dimmer types
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

        subType = self.getSubClass(indigo.devices[devId].deviceTypeId)
        valuesDict = subType.selectTpDevice( valuesDict, typeId, devId)

        return valuesDict

    def selectTpOutlet(self, filter="", valuesDict=None, typeId="", targetId=0):
        ### specific to the Relay type; dont bother subclassing (see Devices.xml)
        self.logger.debug(u"called for: %s, %s, %s." % (filter, typeId, targetId))
        self.logger.threaddebug(u"called for: %s, %s, %s, %s." % (filter, typeId, targetId, valuesDict))

        outletArray = []

        if 'newDev' in valuesDict and 'address' in valuesDict:
            address = valuesDict['address']
            if address in self.deviceSearchResults:
                self.logger.debug(u"1 in dictoutlets avail %s" % (valuesDict['outletsAvailable']))
                # if valuesDict['addressSelect'] == 'manual':
                self.logger.debug(u"2 in dictoutlets avail %s" % (valuesDict['outletsAvailable']))
                if 'child_num' in self.deviceSearchResults[address]['system']['get_sysinfo']:
                    self.logger.debug(u"3 in dictoutlets avail %s" % (valuesDict['outletsAvailable']))
                    maxOutlet = int(self.deviceSearchResults[address]['system']['get_sysinfo']['child_num'])+1
                    address = valuesDict['address']

                    for outlet in range(1, maxOutlet):
                        internalOutlet = int(outlet)-1
                        menuEntry = (str(internalOutlet).zfill(2), outlet)
                        outletArray.append(menuEntry)
                else:
                    self.logger.debug(u"not in dict outlets avail %s" % (valuesDict['outletsAvailable']))
                    for outlet in range(0, int(valuesDict['outletsAvailable'])):
                        self.logger.debug(u"loop %s" % (outlet))
                        internalOutlet = int(outlet)
                        menuEntry = (str(internalOutlet).zfill(2), outlet+1)
                        outletArray.append(menuEntry)

            elif valuesDict['outletsAvailable'] > 0:
                self.logger.debug(u"outlets avail: %s" % (valuesDict['outletsAvailable']))
                for outlet in range(0, int(valuesDict['outletsAvailable'])):
                    self.logger.debug(u"loop %s" % (outlet))
                    internalOutlet = int(outlet)
                    menuEntry = (str(internalOutlet).zfill(2), outlet+1)
                    outletArray.append(menuEntry)

        self.logger.debug(u"returned: OA=%s" % (outletArray))
        return outletArray

    ########################################
    # Menu callbacks defined in MenuItems.xml
    # I haven't been able to figure out how to make these calls soecific to the device Type
    ########################################

    ########################################
    # Device reporting
    def displayButtonPressed(self, valuesDict, clg_func):
        """ callback to prepare the data for the "display device information" configUI display
             (See MenuItems.xml)
        """
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
        self.logger.threaddebug("pluginPropsr=%s", props)

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
        self.logger.threaddebug("Device info = %s", valuesDict)

        return(valuesDict)

    def printToLogPressed(self, valuesDict, clg_func):
        """ callback to prepare the report for display in the log
             (See MenuItems.xml)
        """
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
            rpt_fmt.format("Model:", valuesDict['model']) + \
            rpt_fmt.format("Polling enabled:", valuesDict['devPoll']) + \
            rpt_fmt.format("On state polling freq:", valuesDict['onPoll']) + \
            rpt_fmt.format("Off state polling freq:", valuesDict['offPoll']) + \
            subType.printToLogPressed( valuesDict, rpt_fmt)

        self.logger.info("%s", report)
        return

    ########################################
    # Menu callbacks defined in Actions.xml
    # I haven't been able to figure out how to make these calls soecific to the device Type
    ########################################

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

