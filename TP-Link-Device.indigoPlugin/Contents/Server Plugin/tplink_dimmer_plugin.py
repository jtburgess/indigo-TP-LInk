#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
import indigo

# dimmer (aka light bulb, light switch) device-specific functions needed by the plugin
# almost all functions are stubbed; some may not be used

# outside the class because it may be needed to determine the class
dimmerModels = {
    "KL100", # lightbulb (if not dimmable, does it follow Relay properties and commands?)
    "KL110", # dimmable bulb
    "KL120", # tunable-white bulb
    "KL130", # multicolor bulb
}

class tplink_dimmer():

  def __init__(self, logger, pluginPrefs, tpLink_self):
    self.logger = logger
    self.pluginPrefs = pluginPrefs
    self.tpLink_self = tpLink_self
    return

  def validateDeviceConfigUi(self, valuesDict, typeId, devId):
    return valuesDict

  def validatePrefsConfigUi(self, valuesDict):
    return(True, valuesDict)

  def deviceStartComm(self, dev):
    # Update the model display column
    # description is the Notes Field. Jay requested to only set this on initilaiztion
    # where is a better place to do this, so it only happens when a device is FIRST set up?
    if len(dev.description) == 0:
      dev.description = dev.pluginProps['description']
    return

  def deviceStopComm(self, dev):
    return

  def initializeDev(self, valuesDict, data):
    self.logger.debug(u" called with: %s.", (valuesDict))
    valuesDict['mac'] = data['system']['get_sysinfo']['mic_mac']
    valuesDict['SupportsColor'] = valuesDict['isColor'] = (data['system']['get_sysinfo']['is_color'] == 1)
    valuesDict['isDimmable'] = (data['system']['get_sysinfo']['is_dimmable'] == 1)

    return valuesDict

  def actionControlDevice (self, action, dev, cmd, logOnOff=True):
    """ called on send Success to update state, etc. """
    self.logger.debug(u'sent "{}" {}'.format(dev.name, cmd))

    # tell the Indigo Server to update states
    uiState = cmd
    if cmd == "off":
        state = False
        brightnessLevel = 0
    elif cmd == "on":
        state = True
        brightnessLevel = 100
    else:
        # must be the brightness slider
        state = True
        uiState = "On"
        brightnessLevel = action.actionValue

    state_update_list = [
        {'key':'onOffState', 'value':state, 'uiValue':uiState},
        {'key':'brightnessLevel', 'value':brightnessLevel},
        #{'key':'hue', 'value':TBD},
      ]
    dev.updateStatesOnServer(state_update_list)

    if logOnOff:
      if action.deviceAction == indigo.kDimmerRelayAction.SetBrightness:
        # because "cmd" is manipulated to be json, above
        self.logger.info(u"%s brightness set to %s", dev.name, brightnessLevel)
      else:
        self.logger.info(u"%s set to %s", dev.name, cmd)
    #self.tpThreads[dev.address].interupt(dev=dev, action='status')
    return

  def getInfo(self, pluginAction, dev):
    return

  def actionControlUniversal(self, action, dev):
    return

  def getDeviceStateList(self, dev, statesDict):
    self.logger.debug(u" called for: %s." % statesDict)

    # brightness level is pre-defined. No need to add it here
    #brightnessLevel = self.tpLink_self.getDeviceStateDictForNumberType(u"brightnessLevel", u"brightnessLevel", u"brightnessLevel")
    #statesDict.append(brightnessLevel)
    hue = self.tpLink_self.getDeviceStateDictForNumberType(u"hue", u"hue", u"hue")
    statesDict.append(hue)
    # brightnessLevel is bullt-in

    return statesDict

  def selectTpDevice(self, valuesDict, typeId, devId):
    # This sub-method gets called in the device configuration process, once address resolution is successful
    self.logger.debug(u"called for: %s, %s, %s." % (typeId, devId, valuesDict['address']))

    valuesDict['mac']  = self.tpLink_self.deviceSearchResults[valuesDict['address']]['system']['get_sysinfo']['mic_mac']

    valuesDict['isColor'] = (self.tpLink_self.deviceSearchResults[valuesDict['address']]['system']['get_sysinfo']['is_color'] == 1)
    valuesDict['isDimmable'] = (self.tpLink_self.deviceSearchResults[valuesDict['address']]['system']['get_sysinfo']['is_dimmable'] == 1)
    valuesDict['description'] = self.tpLink_self.deviceSearchResults[valuesDict['address']]['system']['get_sysinfo']['description']
    valuesDict['energyCapable'] = False

    self.logger.debug("returning valuesDict: %s" % valuesDict)
    return valuesDict

  def displayButtonPressed(self, dev, valuesDict):
    props = dev.pluginProps
    valuesDict['isDimmable']  = props['isDimmable']
    valuesDict['isColor']     = props['isColor']
    return(valuesDict)

  def printToLogPressed(self, valuesDict, rpt_fmt):

    return rpt_fmt.format("Supports Dimming:", valuesDict['isDimmable']) + \
        rpt_fmt.format("Supports Color:", valuesDict['isColor'])
