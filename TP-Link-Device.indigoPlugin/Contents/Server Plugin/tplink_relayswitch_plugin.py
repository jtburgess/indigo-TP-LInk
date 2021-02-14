#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
import indigo

# relay (aka smart plug, power strip) device-specific functions needed by the plugin
# almost all functions are stubbed; some may not be used

# outside the class because it may be needed to determine the class
relayswitchModels = {
    "HS200", # one way non-dimming wall switch
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
    self.logger.debug(u"called with typeId={}, devId={}, and address={}.".format(typeId, devId, valuesDict['address']))
    #I don't believe this is necessary

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
    return valuesDict

  def actionControlDevice (self, action, dev, cmd, logOnOff=True, bright=100):
    """ called on send Success to update state, etc. """
    self.logger.debug(u'sent "{}" {}'.format(dev.name, cmd))

    # tell the Indigo Server to update the state.
    if cmd == "off":
        state = False
        dev.updateStateOnServer(key="onOffState", value=0)
        if logOnOff:
            self.logger.info(u"%s set to %s", dev.name, cmd)
    elif cmd == "on":
        state = True
        if logOnOff:
            self.logger.info(u"%s set to %s", dev.name, cmd)
            self.logger.info(u"%s brightness set to %s", dev.name, str(bright))
        dev.updateStateOnServer(key="onOffState", value=state)
        dev.updateStateOnServer(key="brightnessLevel", value=bright)
    elif cmd=="setBright":
        dev.updateStateOnServer(key="brightnessLevel", value=bright)
        if logOnOff:
            self.logger.info(u"%s brightness set to %s", dev.name, str(bright))
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
    self.logger.debug(u" called for: %s." % (statesDict, ))
    fadeOnTime  = self.tpLink_self.getDeviceStateDictForNumberType(u"fadeOnTime", u"fadeOnTime", u"fadeOnTime")
    fadeOffTime  = self.tpLink_self.getDeviceStateDictForNumberType(u"fadeOffTime", u"fadeOffTime", u"fadeOffTime")
    minThreshold  = self.tpLink_self.getDeviceStateDictForNumberType(u"minThreshold", u"minThreshold", u"minThreshold")
    gentleOnTime  = self.tpLink_self.getDeviceStateDictForNumberType(u"gentleOnTime", u"gentleOnTime", u"gentleOnTime")
    gentleOffTime  = self.tpLink_self.getDeviceStateDictForNumberType(u"gentleOffTime", u"gentleOffTime", u"gentleOffTime")
    rampRate  = self.tpLink_self.getDeviceStateDictForNumberType(u"rampRate", u"rampRate", u"rampRate")
    hardOn  = self.tpLink_self.getDeviceStateDictForNumberType(u"hardOn", u"hardOn", u"hardOn")
    softOn  = self.tpLink_self.getDeviceStateDictForNumberType(u"softOn", u"softOn", u"softOn")
    longPress  = self.tpLink_self.getDeviceStateDictForNumberType(u"longPress", u"longPress", u"longPress")
    doubleClick  = self.tpLink_self.getDeviceStateDictForNumberType(u"doubleClick", u"doubleClick", u"doubleClick")
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

    self.logger.debug(u"called for: %s, %s, %s." % (typeId, devId, address))

    if valuesDict['addressSelect'] != 'manual':
        valuesDict['childId']   = None
        valuesDict['mac']       = self.tpLink_self.deviceSearchResults[address]['system']['get_sysinfo']['mac']

    self.logger.debug("returning valuesDict: %s" % valuesDict)
    return valuesDict

  ########################################
  # Menu callbacks defined in Actions.xml
  # So far, These actions are specific to the RelaySwitch type
  ########################################
  def SetDoubleClickAction(self, pluginAction, dev):

      devType = dev.deviceTypeId
      devAddr = dev.address
      devPort = 9999
      tplink_dev_states = tplink_relayswitch_protocol(devAddr, devPort)

      thechoice=int(pluginAction.props.get(u"dbMode"))-1
      thepreset=int(pluginAction.props.get(u"dbPreset"))-1
      arg1=['instant_on_off', 'gentle_on_off', 'customize_preset', 'none']
      arg2=["1","2","3","4"]
      result = tplink_dev_states.send('setDouble',arg1[thechoice],arg2[thepreset])

      indigo.server.log("Set doubleclick action " + dev.name + " to " +arg1[thechoice])
      return(result)

  def SetLongPressAction(self, pluginAction, dev):
      devType = dev.deviceTypeId
      devAddr = dev.address
      devPort = 9999
      tplink_dev_states = tplink_relayswitch_protocol(devAddr, devPort)

      thechoice=int(pluginAction.props.get(u"lpMode"))-1
      thepreset=int(pluginAction.props.get(u"lpPreset"))-1
      arg1=['instant_on_off', 'gentle_on_off', 'customize_preset', 'none']
      arg2=["1","2","3","4"]
      result = tplink_dev_states.send('setLpress',arg1[thechoice],arg2[thepreset])

      indigo.server.log("Set long press action " + dev.name + " to " +arg1[thechoice])
      return(result)

  def set_gentle_off_time(self, pluginAction, dev):
      devType = dev.deviceTypeId
      devAddr = dev.address
      devPort = 9999
      tplink_dev_states = tplink_relayswitch_protocol(devAddr, devPort)

      thechoice=pluginAction.props.get(u"setGOT")
      result = tplink_dev_states.send('setGentleoff',str(thechoice),"")
      indigo.server.log("Set Gentle Off Time " + dev.name + " to " +thechoice)
      return(result)

  def set_gentle_on_time(self, pluginAction, dev):
      devType = dev.deviceTypeId
      devAddr = dev.address
      devPort = 9999
      tplink_dev_states = tplink_relayswitch_protocol(devAddr, devPort)

      thechoice=pluginAction.props.get(u"setGOnT")
      result = tplink_dev_states.send('setGentleon',thechoice,"")

      indigo.server.log("Set Gentle On Time " + dev.name + " to " +thechoice)
      return(result)

  def set_fade_on_time(self, pluginAction, dev):
      devType = dev.deviceTypeId
      devAddr = dev.address
      devPort = 9999
      tplink_dev_states = tplink_relayswitch_protocol(devAddr, devPort)

      thechoice=str(pluginAction.props.get(u"setFOnT"))

      result = tplink_dev_states.send('setFadeOn',thechoice,"")
      indigo.server.log("Set Fade On Time " + dev.name + " to " +thechoice)
      return(result)

  def set_fade_off_time(self, pluginAction, dev):
      devType = dev.deviceTypeId
      devAddr = dev.address
      devPort = 9999
      tplink_dev_states = tplink_relayswitch_protocol(devAddr, devPort)

      thechoice=pluginAction.props.get(u"setFOT")

      result = tplink_dev_states.send('setFadeOff',thechoice,"")

      indigo.server.log("Set Fade Off Time " + dev.name + " to " +thechoice)
      return(result)
