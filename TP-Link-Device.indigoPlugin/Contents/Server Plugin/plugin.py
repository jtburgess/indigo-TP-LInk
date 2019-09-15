#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

import indigo				# Added here to stop pylint errors
# import inspect				# Not needed once we convert logging to use format
import json
import logging
from os import path
import pdb
from Queue import Queue
import socket
from tpl_polling import pollingThread
from tplink_smartplug import tplink_smartplug
from plugin_base import IndigoLogHandler


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

    def setLogLevel(self, loglevel):
        self.loglevel = loglevel
        # indigo.server.log("Received log level {}".format(self.loglevel))

    def emit(self, record):
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


    ########################################
    def startup(self):
        self.logger.debug(u"startup called")

    def shutdown(self):
        self.logger.debug(u"shutdown called")

    ########################################
    # Validation handlers
    ######################
    def validateDeviceConfigUi(self, valuesDict, typeId, devId):
        self.logger.debug(u"called with typeId={}, devId={}, and valuesDict=%s.".format(typeId, devId, valuesDict['address']))
        self.logger.threaddebug(u"for devId={} valuesDict={}.".format(devId, valuesDict))
        errorsDict = indigo.Dict()

        if not valuesDict['childId'] or valuesDict['childId'] == None or valuesDict['childId'] == "":
            valuesDict['childId']   = str(valuesDict['deviceId']) + valuesDict['outletNum']
        self.logger.threaddebug(u"left with typeId=%s, devId=%s, and valuesDict=%s.", typeId, devId, valuesDict)

        if not valuesDict['energyCapable']:
            valuesDict['SupportsEnergyMeter'] = False
            valuesDict['SupportsEnergyMeterCurPower'] = False

        # If we have been asked to re-initialize this device...
        if ('initialize' in valuesDict and valuesDict['initialize']):
            self.initializeDev(valuesDict)
        valuesDict['newDev'] = False
        valuesDict['initialize'] = False
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

        # get some data for local use from the device
        name      = dev.name
        address   = dev.address
        multiPlug = dev.pluginProps['multiPlug']
        if multiPlug:
            devPoll = self.pluginPrefs['devPoll']
        else:
            devPoll = dev.pluginProps['devPoll']

        # Update the model display column
        dev.model = dev.pluginProps['model']
        dev.description = "plug " + str(int(dev.pluginProps['outletNum'])+1)
        dev.replaceOnServer()

        # self.logger.debug("deviceStartComn starting %s" % (name), type="TP-Link", isError=False)
        if name in self.tpThreads:
            self.logger.debug("deviceStartComm error: Thread exists for %s , %s- %s" % (name, address, self.tpThreads[dev.name]))
            # self.tpThreads[address].interupt(None)
        elif not devPoll:
            self.logger.info("Polling thread not started for device  %s, %s. It has polling disabled", name, address)
        elif devPoll:
            # We start one thread per device ip address
            if address not in self.tpThreads:
                # Create a thread
                self.process = pollingThread(self.logger, dev, self.logOnOff, self.pluginPrefs)
                self.tpThreads[address] = self.process
                self.logger.debug("Polling thread started for device %s, %s", name, address)
                # ... and save a copy of the device that created this thread
                self.tpDevices[address] = dev
            elif address in self.tpThreads:
                self.logger.debug(u"deviceStartComm IN thread update %s, %s", name, address)
                myDeviceId  = dev.pluginProps['deviceId']
                if not myDeviceId:
                    self.logger.error("%s: Oops.No deviceId for %s", name, address)
                else:
                    self.logger.debug("%s: Already had deviceId  %s", name, myDeviceId)

                # self.logger.info(u"deviceStartComm related to device %s, %s", deviceId, "foio")
                # Since a thread already exists, this is probably a multiPlug
                self.tpThreads[address].interupt(dev=dev, action='dev')
            else:
                # something is horribly wrong
                self.logger.error(u"deviceStartComm error in thread creation %s, %s", name, address)
        # Since we got this far, we might as well tell someone
        self.logger.info(u"Polling started for %s@%s.", dev.name, dev.address)

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

    ########################################
    ########################################
    def initializeDev(self, valuesDict):
        self.logger.debug(u"called for: %s." % (valuesDict))

        self.logger.debug(u"2 called for: %s." % (valuesDict))
        devAddr = valuesDict['address']
        devName = "new device at " + devAddr
        devPort = 9999
        deviceId = None
        childId = None
        tplink_dev = tplink_smartplug (devAddr, devPort, deviceId, childId)
        result = tplink_dev.send('info')
        self.deviceSearchResults[devAddr] = result

        self.logger.debug(u"%s: InitializeDev 3 got %s" % (devName, result))
        data = json.loads(result)
        self.deviceSearchResults[devAddr] = data
        self.logger.debug(u"%s: InitializeDev 4 got %s" % (devName, data))
        valuesDict['deviceId'] = data['system']['get_sysinfo']['deviceId']
        valuesDict['childId'] = str(deviceId) + valuesDict['outletNum']
        valuesDict['mac'] = data['system']['get_sysinfo']['mac']
        valuesDict['model'] = data['system']['get_sysinfo']['model']

        if 'child_num' in data['system']['get_sysinfo']:
            self.logger.debug(u"%s has child_id", devName)
            valuesDict['multiPlug'] = True
            valuesDict['outletsAvailable'] = data['system']['get_sysinfo']['child_num']
        else:
            self.logger.debug(u"%s does not have child_id", devName)
            valuesDict['multiPlug'] = False
            valuesDict['outletsAvailable'] = 1

        if 'ENE' in data['system']['get_sysinfo']['feature']:
            valuesDict['energyCapable'] = True
        else:
            valuesDict['energyCapable'] = False

        valuesDict['initialize'] = False

        return valuesDict

    ########################################
    # Relay Action callback
    ######################
    def actionControlDimmerRelay(self, action, dev):
        self.logger.debug(u"called with: %s for %s." % (action, dev.name))
        addr = dev.address
        port = 9999
        if dev.pluginProps['multiPlug']:
            deviceId = dev.pluginProps['deviceId']
            childId = dev.pluginProps['outletNum']
        else:
            deviceId = None
            childId = None

        tplink_dev = tplink_smartplug (addr, port, deviceId, childId)
        self.logger.debug(u"tplink_dev set with: %s, %s, %s, %s." % (addr, port, deviceId, childId))

        ###### TURN ON ######
        if action.deviceAction == indigo.kDimmerRelayAction.TurnOn:
            cmd = "on"
            if dev.pluginProps['devPoll']:
                self.tpThreads[dev.address].interupt(state=True, action='state')
        ###### TURN OFF ######
        elif action.deviceAction == indigo.kDimmerRelayAction.TurnOff:
            cmd = "off"
            if dev.pluginProps['devPoll']:
                self.tpThreads[dev.address].interupt(state=False, action='state')
        ###### TOGGLE ######
        elif action.deviceAction == indigo.kDimmerRelayAction.Toggle:
            if dev.onState:
                cmd = "off"
                if dev.pluginProps['devPoll']:
                    self.tpThreads[dev.address].interupt(state=False, action='state')
            else:
                cmd = "on"
                if dev.pluginProps['devPoll']:
                    self.tpThreads[dev.address].interupt(state=True, action='state')
        else:
            self.logger.error("Unknown command: {}".format(indigo.kDimmerRelayAction))
            return

        result = tplink_dev.send(cmd)
        sendSuccess = False
        try:
            result_dict = json.loads(result)
            error_code = result_dict["system"]["set_relay_state"]["err_code"]
            if error_code == 0:
                sendSuccess = True
            else:
                self.logger.error("turn {} command failed (error code: {})".format(cmd, error_code))
        except:
            pass
        indigo.debugger()
        if sendSuccess:
            # If success then log that the command was successfully sent.
            self.logger.debug(u'sent "{}" {}'.format(dev.name, cmd))

            # And then tell the Indigo Server to update the state.
            if cmd == "on":
                state = True
            else:
                state = False
            dev.updateStateOnServer(key="onOffState", value=state)
            if self.logOnOff:
                self.logger.info(u"%s set to %s", dev.name, cmd)
            #self.tpThreads[dev.address].interupt(dev=dev, action='status')

        else:
            # Else log failure but do NOT update state on Indigo Server.
            self.logger.error(u'send "{}" {} failed with result "{}"'.format(dev.name, cmd, result))

    # The 'status' callback
    def getInfo(self, pluginAction, dev):
        self.logger.debug(u"%called for: %s." % (dev.name))
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
        self.logger.debug(u"%s: \action: %s for device: %s." % (action, dev.name))
        ###### ENERGY UPDATE ######
        if action.deviceAction == indigo.kUniversalAction.EnergyUpdate:
            if dev.pluginProps['energyCapable'] == True :
                self.logger.info("Energy Status Update Requested for " + dev.name)
                self.getInfo("", dev)
            else: self.logger.info("Device " + dev.name + " not energy capable.")

        ###### STATUS REQUEST ######
        elif action.deviceAction == indigo.kUniversalAction.RequestStatus:
            self.getInfo("", dev)

        ###### ENERGY RESET ######
        elif action.deviceAction == indigo.kUniversalAction.EnergyReset:
            self.logger.info("energy reset for Device: %s", dev.name)

            # Get the plugionProps, modify them, and save them back
            pluginProps = dev.pluginProps
            accuUsage = float(pluginProps['totAccuUsage'])
            curTotEnergy = float(dev.states['totWattHrs'])
            accuUsage += curTotEnergy
            pluginProps['totAccuUsage'] = accuUsage
            dev.replacePluginPropsOnServer(pluginProps)

            # and now reset the Indigo Device Detail display
            dev.updateStateOnServer("accumEnergyTotal", 0.0)


    ########################################
    # Device ConfigUI Callbacks
    ######################
    def getDeviceStateList(self, dev):
        """Dynamically create/update the states list for each device"""
        self.logger.debug(u"called for: %s." % (dev.name))
        self.logger.threaddebug(u"called for: %s." % (dev))

        statesDict = indigo.PluginBase.getDeviceStateList(self, dev)
        rssi  = self.getDeviceStateDictForNumberType(u"rssi", u"rssi", u"rssi")
        alias = self.getDeviceStateDictForNumberType(u"alias", u"alias", u"alias")
        statesDict.append(rssi)
        statesDict.append(alias)

        if len(dev.pluginProps) >0: # We actually have a device here...
            if dev.pluginProps['energyCapable']: # abd the device does energy reporting
                # Add the energy reporting states

                #accuWattHrs = self.getDeviceStateDictForNumberType(u"accuWattHrs", u"accuWattHrs", u"accuWattHrs")
                curWatts = self.getDeviceStateDictForNumberType(u"curWatts", u"curWatts", u"curWatts")
                totWattHrs = self.getDeviceStateDictForNumberType(u"totWattHrs", u"totWattHrs", u"totWattHrs")
                curVolts = self.getDeviceStateDictForNumberType(u"curVolts", u"curVolts", u"curVolts")
                curAmps = self.getDeviceStateDictForNumberType(u"curAmps", u"curAmps", u"curAmps")

                #statesDict.append(accuWattHrs)
                statesDict.append(curWatts)
                statesDict.append(totWattHrs)
                statesDict.append(curVolts)
                statesDict.append(curAmps)

        return statesDict

    def getTpDevice(self, filter="", valuesDict=None, typeId="", targetId=0):
        self.logger.debug(u"called for: %s, %s, %s." % (filter, typeId, targetId))
        self.logger.threaddebug(u"called for: %s, %s, %s, %s." % (filter, typeId, targetId, valuesDict))

        deviceArray = []
        if indigo.devices[targetId].configured:
            return deviceArray
        else:
            tplink_discover = tplink_smartplug(None, None)
            try:
                self.deviceSearchResults = tplink_discover.discover()
            except Exception as e:
                self.logger.error("Discovery connection failed with (%s)" % (str(e)))

            self.logger.debug(u"received %s" % (self.deviceSearchResults))

            for address in self.deviceSearchResults:
                model = self.deviceSearchResults[address]['system']['get_sysinfo']['model']
                menuText = model + " @ " + address
                menuEntry = (address, menuText)
                deviceArray.append(menuEntry)
            menuEntry = ('manual', 'manual entry')
            deviceArray.append(menuEntry)

            return deviceArray

    def selectTpDevice(self, valuesDict, typeId, devId):
        # This method gets called at several different times in the device configuration process.
        # The first if/else block sorts all that out
        self.logger.debug(u"called for: %s, %s, %s." % (typeId, devId, valuesDict['address']))
        self.logger.threaddebug(u"called for: %s, %s." % (devId, valuesDict))

        if valuesDict['addressSelect'] != 'manual':  # A plug from the discovery list has been selected, so we can continue
            self.logger.debug("%s -- %s\n" % (valuesDict['addressSelect'], valuesDict['manualAddressResponse']))
            valuesDict['address'] = valuesDict['addressSelect']
            address = valuesDict['address']
            valuesDict['deviceId']  = self.deviceSearchResults[address]['system']['get_sysinfo']['deviceId']
            valuesDict['childId']   = str(valuesDict['deviceId']) + valuesDict['outletNum']
            valuesDict['mac']       = self.deviceSearchResults[address]['system']['get_sysinfo']['mac']
            valuesDict['model']     = self.deviceSearchResults[address]['system']['get_sysinfo']['model']
            valuesDict['displayOk'] = True
            valuesDict['displayManAddress'] = True

        elif valuesDict['manualAddressResponse']:  # An ip address has been manually entered, so we can continue
            self.logger.threaddebug("%s -- %s\n" % (valuesDict['address'], valuesDict['manualAddressResponse']))
            # First, make sure there is actually a plug we can talk to at this address
            if not check_server(valuesDict['address']):
                # Bail out
                errorsDict = indigo.Dict()
                errorsDict["showAlertText"] = "Could not find a TP-Link plug device at this address"
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
        if 'child_num' in self.deviceSearchResults[address]['system']['get_sysinfo']:
            self.logger.debug(u"%s has child_id", address)
            valuesDict['multiPlug'] = True
            valuesDict['outletsAvailable'] = self.deviceSearchResults[address]['system']['get_sysinfo']['child_num']
        else:
            self.logger.debug(u"%s does not have child_id", address)
            valuesDict['multiPlug'] = False
            valuesDict['outletsAvailable'] = 1
            valuesDict['outletNum'] = "00"

        if 'ENE' in self.deviceSearchResults[address]['system']['get_sysinfo']['feature']:
            valuesDict['energyCapable'] = True
        else:
            valuesDict['energyCapable'] = False

        self.logger.debug("returning valuesDict: %s" % valuesDict)

        return valuesDict

    def selectTpOutlet(self, filter="", valuesDict=None, typeId="", targetId=0):
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
                self.logger.debug(u"outlets 2 avail %s" % (valuesDict['outletsAvailable']))
                for outlet in range(0, int(valuesDict['outletsAvailable'])):
                    self.logger.debug(u"loop %s" % (outlet))
                    internalOutlet = int(outlet)
                    menuEntry = (str(internalOutlet).zfill(2), outlet+1)
                    outletArray.append(menuEntry)

        self.logger.debug(u"returned: OA=%s" % (outletArray))
        return outletArray

    ########################################
    # Menu callbacks defined in MenuItems.xml
    ########################################

    ########################################
    # Device reporting
    def dumpDeviceInfo(self, valuesDict, clg_func):
        self.logger.debug("called for targetDevice {} from ".format(valuesDict['targetDevice'], clg_func))
        self.logger.threaddebug("called with {}".format(valuesDict['targetDevice']))
        return(True)

    def displayButtonPressed(self, valuesDict, clg_func):
        self.logger.debug("called for targetDevice {} from ".format(valuesDict['targetDevice'], clg_func))
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
        valuesDict['devPoll']       = props['devPoll']
        valuesDict['deviceId']      = props['deviceId']
        valuesDict['energyCapable'] = props['energyCapable']
        valuesDict['mac']           = props['mac']
        valuesDict['model']         = props['model']
        valuesDict['multiPlug']     = props['multiPlug']
        valuesDict['offPoll']       = props['offPoll']
        valuesDict['onPoll']        = props['onPoll']
        valuesDict['outletNum']     = int(props['outletNum'])+1
        valuesDict['alias']         = dev.states['alias']
        valuesDict['displayOk']     = True

        self.logger.threaddebug("Device info = %s", valuesDict)

        return(valuesDict)

    def printToLogPressed(self, valuesDict, clg_func):
        self.logger.debug("called for dev {} from {}".format(valuesDict['targetDevice'], clg_func))
        self.logger.threaddebug("Received {}".format(valuesDict))
        devNumber = int(valuesDict['targetDevice'])
        dev = indigo.devices[devNumber]

        rpt_fmt = "            {0:<25s}{1:s}\n"
        report = "Tp-Link plugin device report\n" + \
            rpt_fmt.format("Indigo Device Name:", dev.name) + \
            rpt_fmt.format("IP Address:", valuesDict['address']) + \
            rpt_fmt.format("Device ID:", valuesDict['deviceId']) + \
            rpt_fmt.format("Alias:", valuesDict['alias']) + \
            rpt_fmt.format("Outlet Number:", valuesDict['outletNum']) + \
            rpt_fmt.format("Model:", valuesDict['model']) + \
            rpt_fmt.format("On state polling freq:", valuesDict['onPoll']) + \
            rpt_fmt.format("Off state polling freq:", valuesDict['offPoll']) + \
            rpt_fmt.format("MAC Address:", valuesDict['mac']) + \
            rpt_fmt.format("Polling enabled:", str(valuesDict['devPoll'])) + \
            rpt_fmt.format("Multiple Outlets:", str(valuesDict['multiPlug'])) + \
            rpt_fmt.format("Energy reporting:", str(valuesDict['energyCapable']))

        self.logger.info("%s", report)

        return