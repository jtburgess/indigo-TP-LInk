#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
import indigo
from tplink_relayswitch_protocol import tplink_relayswitch_protocol

# relay (aka smart plug, power strip) device-specific functions needed by the plugin
# almost all functions are stubbed; some may not be used

# outside the class because it may be needed to determine the class
relayswitchModels = {
    "HS210", # three way non-dimming wall switch
    "HS220"  # dimmer wall switch
}

class tplink_relayswitch():

  def __init__(self, logger, pluginPrefs, tpLink_self):
    """ this independent class sometimes needs access to the tpLink device's stuff """
    self.logger = logger
    self.pluginPrefs = pluginPrefs
    self.tpLink_self = tpLink_self
    return

  def validateDeviceConfigUi(self, valuesDict, typeId, devId):
    """ seems redundant with initializeDev ??? """
    self.logger.debug("called with typeId={}, devId={}, and address={}.".format(typeId, devId, valuesDict['address']))
    #I don't believe this is necessary

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
    self.logger.debug(" called with: %s." % (valuesDict, ) )
    valuesDict['mac'] = data['system']['get_sysinfo']['mac']
    return valuesDict

  def actionControlDevice (self, action, dev, cmd, logOnOff=True, bright=100):
    """ called on send Success to update state, etc. """
    self.logger.debug('sent "{}" {}'.format(dev.name, cmd))

    # tell the Indigo Server to update the state.
    if cmd == "off":
        state = False
        dev.updateStateOnServer(key="onOffState", value=0)
        dev.updateStateOnServer(key="brightnessLevel", value=0)
        if logOnOff:
            self.logger.info("%s set to %s" % (dev.name, cmd) )
    elif cmd == "on":
        state = True
        if logOnOff:
            self.logger.info("%s set to %s" % (dev.name, cmd) )
            self.logger.info("%s brightness set to %s" % (dev.name, str(bright)) )
        dev.updateStateOnServer(key="onOffState", value=state)
        dev.updateStateOnServer(key="brightnessLevel", value=bright)
    elif cmd=="setBright":
        dev.updateStateOnServer(key="brightnessLevel", value=bright)
        if logOnOff:
            self.logger.info("%s brightness set to %s" % (dev.name, str(bright)) )
#    self.tpThreads[dev.address].interupt(dev=dev, action='status')
    return

  def getInfo(self, pluginAction, dev):
    return

  #CHECK THIS
  def actionControlUniversal(self, action, dev): #PROBABLY DELETE
    ###### ENERGY UPDATE ######
    ###### ENERGY RESET ######
    return

  def getDeviceStateList(self, dev, statesDict):
    self.logger.threaddebug(" called for: %s." % (statesDict, ))
    fadeOnTime  = self.tpLink_self.getDeviceStateDictForNumberType("fadeOnTime", "fadeOnTime", "fadeOnTime")
    fadeOffTime  = self.tpLink_self.getDeviceStateDictForNumberType("fadeOffTime", "fadeOffTime", "fadeOffTime")
    minThreshold  = self.tpLink_self.getDeviceStateDictForNumberType("minThreshold", "minThreshold", "minThreshold")
    gentleOnTime  = self.tpLink_self.getDeviceStateDictForNumberType("gentleOnTime", "gentleOnTime", "gentleOnTime")
    gentleOffTime  = self.tpLink_self.getDeviceStateDictForNumberType("gentleOffTime", "gentleOffTime", "gentleOffTime")
    rampRate  = self.tpLink_self.getDeviceStateDictForNumberType("rampRate", "rampRate", "rampRate")
    hardOn  = self.tpLink_self.getDeviceStateDictForNumberType("hardOn", "hardOn", "hardOn")
    softOn  = self.tpLink_self.getDeviceStateDictForNumberType("softOn", "softOn", "softOn")
    longPress  = self.tpLink_self.getDeviceStateDictForNumberType("longPress", "longPress", "longPress")
    doubleClick  = self.tpLink_self.getDeviceStateDictForNumberType("doubleClick", "doubleClick", "doubleClick")
    statesDict.append(fadeOnTime)
    statesDict.append(fadeOffTime)
    statesDict.append(minThreshold)
    statesDict.append(gentleOnTime)
    statesDict.append(gentleOffTime)
    statesDict.append(rampRate)
    statesDict.append(hardOn)
    statesDict.append(softOn)
    statesDict.append(longPress)
    statesDict.append(doubleClick)

    #MAY WANT TO REPURPOSE THIS FOR STATES - add the states for dimmer @@@@@@@@@
    return statesDict

  def selectTpDevice(self, valuesDict, typeId, devId):
    address = valuesDict['address']

    self.logger.debug("called for: %s, %s, %s." % (typeId, devId, address))

    sys_info = self.tpLink_self.deviceSearchResults[address]['system']['get_sysinfo']
    valuesDict['childId']   = None
    valuesDict['mac']       = sys_info['mac']
    # add an initial description from the dev_name, if it exists
    if 'dev_name' in sys_info:
        valuesDict['description'] = sys_info['dev_name']

    self.logger.debug("returning valuesDict: %s" % valuesDict)
    return valuesDict

  ########################################
  # Menu callbacks defined in Actions.xml
  # So far, These actions are specific to the RelaySwitch type
  ########################################
  def SetDoubleClickAction(self, pluginAction, dev):
      tplink_dev_states = tplink_relayswitch_protocol(dev.address, 9999)

      thechoice=int(pluginAction.props.get("dbMode"))-1
      thepreset=int(pluginAction.props.get("dbPreset"))-1
      arg1=['instant_on_off', 'gentle_on_off', 'customize_preset', 'none']
      arg2=["1","2","3","4"]
      result = tplink_dev_states.send('setDouble',arg1[thechoice],arg2[thepreset])

      indigo.server.log("Set doubleclick action " + dev.name + " to " +arg1[thechoice])
      return(result)

  def SetLongPressAction(self, pluginAction, dev):
      tplink_dev_states = tplink_relayswitch_protocol(dev.address, 9999)

      thechoice=int(pluginAction.props.get("lpMode"))-1
      thepreset=int(pluginAction.props.get("lpPreset"))-1
      arg1=['instant_on_off', 'gentle_on_off', 'customize_preset', 'none']
      arg2=["1","2","3","4"]
      result = tplink_dev_states.send('setLpress',arg1[thechoice],arg2[thepreset])

      indigo.server.log("Set long press action " + dev.name + " to " +arg1[thechoice])
      return(result)

  def set_gentle_off_time(self, pluginAction, dev):
      tplink_dev_states = tplink_relayswitch_protocol(dev.address, 9999)

      thechoice=pluginAction.props.get("setGOT")
      result = tplink_dev_states.send('setGentleoff',str(thechoice),"")
      indigo.server.log("Set Gentle Off Time " + dev.name + " to " +thechoice)
      return(result)

  def set_gentle_on_time(self, pluginAction, dev):
      tplink_dev_states = tplink_relayswitch_protocol(dev.address, 9999)

      thechoice=pluginAction.props.get("setGOnT")
      result = tplink_dev_states.send('setGentleon',thechoice,"")

      indigo.server.log("Set Gentle On Time " + dev.name + " to " +thechoice)
      return(result)

  def set_fade_on_time(self, pluginAction, dev):
      tplink_dev_states = tplink_relayswitch_protocol(dev.address, 9999)

      thechoice=str(pluginAction.props.get("setFOnT"))

      result = tplink_dev_states.send('setFadeOn',thechoice,"")
      indigo.server.log("Set Fade On Time " + dev.name + " to " +thechoice)
      return(result)

  def set_fade_off_time(self, pluginAction, dev):
      tplink_dev_states = tplink_relayswitch_protocol(dev.address, 9999)

      thechoice=pluginAction.props.get("setFOT")

      result = tplink_dev_states.send('setFadeOff',thechoice,"")

      indigo.server.log("Set Fade Off Time " + dev.name + " to " +thechoice)
      return(result)

  def set_HSV(self, pluginAction, dev):
      indigo.server.log("set_HSV only applies to colored dimmer bulbs ")
      return(None)

  def set_ColorTemp(self, pluginAction, dev):
      indigo.server.log("set_ColorTemp only applies to dimmer bulbs ")
      return(None)
