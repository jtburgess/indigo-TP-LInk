#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
import indigo

# relay (aka smart plug, power strip) device-specific functions needed by the plugin
# almost all functions are stubbed; some may not be used

# outside the class because it may be needed to determine the class
relayModels = {
    "HS100", # basic 1-outlet
    "HS103", # plug "lite"
    "HS105", # original plug "mini"
    "HS107", # 2-outlet plug
    "HS110", # plug with energy monitor
    "HS200", # one way non-dimming wall switch
    "HS300", # 6-outlet power strip
    "KP100", # plug "slim edition"
    "KP200", # 2-outlet wall outlet
    "KP303", # 3-outlet power strip
    "KP400", # 2-outlet outdoor
}

class tplink_relay():

  def __init__(self, logger, pluginPrefs, tpLink_self):
    """ this independent class sometimes needs access to the tpLink plugin's stuff """
    self.logger = logger
    self.pluginPrefs = pluginPrefs
    self.tpLink_self = tpLink_self
    return

  def validateDeviceConfigUi(self, valuesDict, typeId, devId):
    """ initialize first, then validate """
    self.logger.debug("called with typeId={}, devId={}, and address={}.".format(typeId, devId, valuesDict['address']))

    if 'childId' not in valuesDict or not valuesDict['childId'] or valuesDict['childId'] == None or valuesDict['childId'] == "":
        valuesDict['childId']   = str(valuesDict['deviceId']) + valuesDict['outletNum']
    self.logger.threaddebug("left with typeId=%s, devId=%s, and valuesDict=%s.", typeId, devId, valuesDict)

    if 'energyCapable' not in valuesDict or not valuesDict['energyCapable']:
        valuesDict['SupportsEnergyMeter'] = False
        valuesDict['SupportsEnergyMeterCurPower'] = False
    return valuesDict

  def validatePrefsConfigUi(self, valuesDict):
    return(True, valuesDict)

  def deviceStartComm(self, dev):
    # Update the model display column
    # description is the Notes Field. Jay requested to only set this on initilaiztion
    if len(dev.description) == 0 and 'description' in dev.pluginProps:
      dev.description = dev.pluginProps['description']
    return

  def deviceStopComm(self, dev):
    return

  def initializeDev(self, valuesDict, data):
    self.logger.debug(" called with: %s.", (valuesDict))

    valuesDict['mac'] = data['system']['get_sysinfo']['mac']

    if 'child_num' in data['system']['get_sysinfo']:
        self.logger.debug("%s has child_id", valuesDict['address'])
        valuesDict['childId'] = str(valuesDict['deviceId']) + valuesDict['outletNum']
        valuesDict['multiPlug'] = True
        valuesDict['outletsAvailable'] = data['system']['get_sysinfo']['child_num']
    else:
        self.logger.debug("%s does not have child_id", valuesDict['address'])
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
    self.logger.debug('sent "{}" {}'.format(dev.name, cmd))

    # tell the Indigo Server to update the state.
    if cmd == "off":
        state = False
    else:
        state = True
    dev.updateStateOnServer(key="onOffState", value=state)

    if logOnOff:
      self.logger.info("%s set to %s", dev.name, cmd)
    #self.tpThreads[dev.address].interupt(dev=dev, action='status')
    return

  def getInfo(self, pluginAction, dev):
    if 'multiPlug' in dev.pluginProps and dev.pluginProps['multiPlug']:
      self.logger.info("Multiple Outlets: {}".format(dev.pluginProps['multiPlug']))
      self.logger.info("   Outlet Number: {}".format(dev.pluginProps['outletNum']))
    if 'energyCapable' in dev.pluginProps and dev.pluginProps['energyCapable']:
      self.logger.info("Energy reporting: {}".format(dev.pluginProps['energyCapable']))
      self.logger.info("   Current Watts: {}".format(self.tpLink_self.getDeviceStateDictForNumberType("curWatts", "curWatts", "curWatts")))
      self.logger.info("   Current Volts: {}".format(self.tpLink_self.getDeviceStateDictForNumberType("curVolts", "curVolts", "curVolts")))
      self.logger.info("   Current Amps : {}".format(self.tpLink_self.getDeviceStateDictForNumberType("curAmps", "curAmps", "curAmps")))
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
    self.logger.debug(" called for: %s." % (statesDict, ))

    # if we actually have a device here and the device does energy reporting
    if 'energyCapable' in dev.pluginProps and dev.pluginProps['energyCapable']:
        # Add the energy reporting states

        #accuWattHrs = self.getDeviceStateDictForNumberType(u"accuWattHrs", u"accuWattHrs", u"accuWattHrs")
        curWatts = self.tpLink_self.getDeviceStateDictForNumberType("curWatts", "curWatts", "curWatts")
        totWattHrs = self.tpLink_self.getDeviceStateDictForNumberType("totWattHrs", "totWattHrs", "totWattHrs")
        curVolts = self.tpLink_self.getDeviceStateDictForNumberType("curVolts", "curVolts", "curVolts")
        curAmps = self.tpLink_self.getDeviceStateDictForNumberType("curAmps", "curAmps", "curAmps")

        #statesDict.append(accuWattHrs)
        statesDict.append(curWatts)
        statesDict.append(totWattHrs)
        statesDict.append(curVolts)
        statesDict.append(curAmps)
    return statesDict

  def selectTpDevice(self, valuesDict, typeId, devId):
    # This sub-method gets called in the device configuration process, once address resolution is successful
    address = valuesDict['address']

    self.logger.debug("called for: %s, %s, %s." % (typeId, devId, address))

    sys_info = self.tpLink_self.deviceSearchResults[address]['system']['get_sysinfo']
    if valuesDict['addressSelect'] != 'manual':
        valuesDict['childId']   = str(valuesDict['deviceId']) + valuesDict['outletNum']
        valuesDict['mac']       = sys_info['mac']

    if 'child_num' in sys_info:
        self.logger.debug("%s has child_id", address)
        valuesDict['multiPlug'] = True
        valuesDict['outletsAvailable'] = sys_info['child_num']
        valuesDict['outletNum'] = valuesDict['outletsAvailable']
    else:
        self.logger.debug("%s does not have child_id", address)
        valuesDict['multiPlug'] = False
        valuesDict['outletsAvailable'] = 1
        valuesDict['outletNum'] = "00"

    if 'ENE' in sys_info['feature']:
        valuesDict['energyCapable'] = True
    else:
        valuesDict['energyCapable'] = False

    # add an initial description from the dev_name, if it exists
    if 'dev_name' in sys_info:
        valuesDict['description'] = sys_info['dev_name']
    self.logger.debug("returning valuesDict: %s" % valuesDict)
    return valuesDict

  """
  since this is specific to this subclass, there's no need to subclass
  def selectTpOutlet(self, filter="", valuesDict=None, typeId="", targetId=0):
    return outletArray
  """

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

  def set_HSV(self, pluginAction, dev):
      indigo.server.log("set_HSV only applies to colored dimmer bulbs ")
      return(None)

  def set_ColorTemp(self, pluginAction, dev):
      indigo.server.log("set_ColorTemp only applies to dimmer bulbs ")
      return(None)
