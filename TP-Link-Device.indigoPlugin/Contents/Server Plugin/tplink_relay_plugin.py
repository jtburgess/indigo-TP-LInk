#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
import indigo

# relay (aka smart plug, power strip) device-specific functions needed by the plugin
# almost all functions are stubbed; some may not be used

# outside the class because it may be needed to determine the class
relayModels = {
    "HS100",
    "HS103",
    "HS105", # original plug-in
    "HS107", # 2 port plug-in
    "HS110",
    "KP200", #2 port wall outlet
    "HS300", # 6 port power strip
    "KP303", # 3 port power strip
    "KP400", # outdoor
}

class tplink_relay():

  def __init__(self, logger, pluginPrefs, tpLink_self):
    """ this independent class sometimes needs access to the tpLink device's stuff """
    self.logger = logger
    self.pluginPrefs = pluginPrefs
    self.tpLink_self = tpLink_self
    return

  def validateDeviceConfigUi(self, valuesDict, typeId, devId):
    """ initialize first, then validate """
    self.logger.debug(u"called with typeId={}, devId={}, and address={}.".format(typeId, devId, valuesDict['address']))

    if 'childId' not in valuesDict or not valuesDict['childId'] or valuesDict['childId'] == None or valuesDict['childId'] == "":
        valuesDict['childId']   = str(valuesDict['deviceId']) + valuesDict['outletNum']
    self.logger.threaddebug(u"left with typeId=%s, devId=%s, and valuesDict=%s.", typeId, devId, valuesDict)

    if 'energyCapable' not in valuesDict or not valuesDict['energyCapable']:
        valuesDict['SupportsEnergyMeter'] = False
        valuesDict['SupportsEnergyMeterCurPower'] = False
    return valuesDict

  def validatePrefsConfigUi(self, valuesDict):
    return(True, valuesDict)

  def deviceStartComm(self, dev):
    # Update the model display column
    # description is the Notes Field. Jay requested to only set this on initilaiztion
    if len(dev.description) == 0:
      dev.description = description
    return

  def deviceStopComm(self, dev):
    return

  def initializeDev(self, valuesDict, data):
    self.logger.debug(u" called with: %s.", (valuesDict))

    valuesDict['mac'] = data['system']['get_sysinfo']['mac']

    if 'child_num' in data['system']['get_sysinfo']:
        self.logger.debug(u"%s has child_id", valuesDict['address'])
        valuesDict['childId'] = str(valuesDict['deviceId']) + valuesDict['outletNum']
        valuesDict['multiPlug'] = True
        valuesDict['outletsAvailable'] = data['system']['get_sysinfo']['child_num']
    else:
        self.logger.debug(u"%s does not have child_id", valuesDict['address'])
        valuesDict['childId'] = str(valuesDict['deviceId'])
        valuesDict['multiPlug'] = False
        valuesDict['outletsAvailable'] = 1

    if 'ENE' in data['system']['get_sysinfo']['feature']:
        valuesDict['energyCapable'] = True
    else:
        valuesDict['energyCapable'] = False
    return valuesDict

  def actionControlDevice (self, action, dev, cmd, logOnOff=True, bright=None):
    """ called on send Success to update state, etc. """
    self.logger.debug(u'sent "{}" {}'.format(dev.name, cmd))

    # tell the Indigo Server to update the state.
    if cmd == "off":
        state = False
    else:
        state = True
    dev.updateStateOnServer(key="onOffState", value=state)

    if logOnOff:
      self.logger.info(u"%s set to %s", dev.name, cmd)
    #self.tpThreads[dev.address].interupt(dev=dev, action='status')
    return

  def getInfo(self, pluginAction, dev):
    return

  def actionControlUniversal(self, action, dev):
    ###### ENERGY UPDATE ######
    if action.deviceAction == indigo.kUniversalAction.EnergyUpdate:
        if dev.pluginProps['energyCapable'] == True :
            self.logger.info("Energy Status Update Requested for " + dev.name)
            self.getInfo("", dev)
        else: self.logger.info("Device " + dev.name + " not energy capable.")

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
    return

  def getDeviceStateList(self, dev, statesDict):
    self.logger.debug(u" called for: %s." % (statesDict, ))

    # if we actually have a device here and the device does energy reporting
    if 'energyCapable' in dev.pluginProps and dev.pluginProps['energyCapable']:
        # Add the energy reporting states

        #accuWattHrs = self.getDeviceStateDictForNumberType(u"accuWattHrs", u"accuWattHrs", u"accuWattHrs")
        curWatts = self.tpLink_self.getDeviceStateDictForNumberType(u"curWatts", u"curWatts", u"curWatts")
        totWattHrs = self.tpLink_self.getDeviceStateDictForNumberType(u"totWattHrs", u"totWattHrs", u"totWattHrs")
        curVolts = self.tpLink_self.getDeviceStateDictForNumberType(u"curVolts", u"curVolts", u"curVolts")
        curAmps = self.tpLink_self.getDeviceStateDictForNumberType(u"curAmps", u"curAmps", u"curAmps")

        #statesDict.append(accuWattHrs)
        statesDict.append(curWatts)
        statesDict.append(totWattHrs)
        statesDict.append(curVolts)
        statesDict.append(curAmps)
    return statesDict

  def selectTpDevice(self, valuesDict, typeId, devId):
    address = valuesDict['address']

    self.logger.debug(u"called for: %s, %s, %s." % (typeId, devId, address))

    if valuesDict['addressSelect'] != 'manual':
        valuesDict['childId']   = str(valuesDict['deviceId']) + valuesDict['outletNum']
        valuesDict['mac']       = self.tpLink_self.deviceSearchResults[address]['system']['get_sysinfo']['mac']

    if 'child_num' in self.tpLink_self.deviceSearchResults[address]['system']['get_sysinfo']:
        self.logger.debug(u"%s has child_id", address)
        valuesDict['multiPlug'] = True
        valuesDict['outletsAvailable'] = self.tpLink_self.deviceSearchResults[address]['system']['get_sysinfo']['child_num']
        valuesDict['outletNum'] = valuesDict['outletsAvailable']
    else:
        self.logger.debug(u"%s does not have child_id", address)
        valuesDict['multiPlug'] = False
        valuesDict['outletsAvailable'] = 1
        valuesDict['outletNum'] = "00"

    if 'ENE' in self.tpLink_self.deviceSearchResults[address]['system']['get_sysinfo']['feature']:
        valuesDict['energyCapable'] = True
    else:
        valuesDict['energyCapable'] = False

    self.logger.debug("returning valuesDict: %s" % valuesDict)
    return valuesDict

  """
  since this is specific to this subclass, there's no need to subclass
  def selectTpOutlet(self, filter="", valuesDict=None, typeId="", targetId=0):
    return outletArray
  """

  def displayButtonPressed(self, dev, valuesDict):
    props = dev.pluginProps
    valuesDict['outletNum']     = int(props['outletNum'])+1
    valuesDict['multiPlug']     = props['multiPlug']
    valuesDict['energyCapable'] = props['energyCapable']
    return(valuesDict)

  def printToLogPressed(self, valuesDict, rpt_fmt):
    return rpt_fmt.format("Outlet Number:", valuesDict['outletNum']) + \
        rpt_fmt.format("Multiple Outlets:", valuesDict['multiPlug']) + \
        rpt_fmt.format("Energy reporting:", valuesDict['energyCapable'])

    return

  ########################################
  # Menu callbacks defined in Actions.xml
  # So far, These actions are specific to the RelaySwitch type
  ########################################

  def SetDoubleClickAction(self, pluginAction, dev):
      indigo.server.log("SetDoubleClickAction only applies to device type RelaySwitch ")
      return(None)

  def SetLongPressAction(self, pluginAction, dev):
      indigo.server.log("SetLongPressAction only applies to device type RelaySwitch ")
      return(None)

  def set_gentle_off_time(self, pluginAction, dev):
      indigo.server.log("set_gentle_off_time only applies to device type RelaySwitch ")
      return(None)

  def set_gentle_on_time(self, pluginAction, dev):
      indigo.server.log("set_gentle_on_time only applies to device type RelaySwitch ")
      return(None)

  def set_fade_on_time(self, pluginAction, dev):
      indigo.server.log("set_fade_on_time only applies to device type RelaySwitch ")
      return(None)

  def set_fade_off_time(self, pluginAction, dev):
      indigo.server.log("set_fade_off_time only applies to device type RelaySwitch ")
      return(None)
