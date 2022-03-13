#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
import indigo
from tplink_dimmer_protocol import tplink_dimmer_protocol

# dimmer (aka light bulb, light switch) device-specific functions needed by the plugin
# almost all functions are stubbed; some may not be used

# outside the class because it may be needed to determine the class
dimmerModels = {
    "KL100", # lightbulb (if not dimmable, does it follow Relay properties and commands?)
    "KL110", # dimmable bulb
    "KL120", # tunable-white bulb
    "KL130", # multicolor bulb
    "KL430", # multicolor bulb
}

class tplink_dimmer():

  def __init__(self, logger, pluginPrefs, tpLink_self):
    self.logger = logger
    self.pluginPrefs = pluginPrefs
    self.tpLink_self = tpLink_self
    return

  def validateDeviceConfigUi(self, valuesDict, typeId, devId):
    self.logger.debug("called with typeId={}, devId={}, and address={}.".format(typeId, devId, valuesDict['address']))
    dev = indigo.devices[devId]
    dev.pluginProps['rampTime'] = valuesDict['rampTime']
    return valuesDict

  def validatePrefsConfigUi(self, valuesDict):
    return(True, valuesDict)

  def deviceStartComm(self, dev):
    # Update the model display column
    # description is the Notes Field. Jay requested to only set this on initilaiztion
    # where is a better place to do this, so it only happens when a device is FIRST set up?
    if len(dev.description) == 0 and 'description' in dev.pluginProps:
      dev.description = dev.pluginProps['description']
    return

  def deviceStopComm(self, dev):
    return

  def initializeDev(self, valuesDict, data):
    self.logger.debug(" called with: %s." % (valuesDict, ) )
    valuesDict['mac'] = data['system']['get_sysinfo']['mic_mac']
    valuesDict['SupportsColor'] = valuesDict['isColor'] = (data['system']['get_sysinfo']['is_color'] == 1)
    valuesDict['isDimmable'] = (data['system']['get_sysinfo']['is_dimmable'] == 1)

    return valuesDict

  def actionControlDevice (self, action, dev, cmd, logOnOff=True, bright=None):
    """ called on send Success to update state, etc. """
    self.logger.debug('sent "{}" {}'.format(dev.name, cmd))

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
        self.logger.info("%s brightness set to %s" % (dev.name, brightnessLevel) )
      else:
        self.logger.info("%s set to %s" % (dev.name, cmd) )
    #self.tpThreads[dev.address].interupt(dev=dev, action='status')
    return

  def getInfo(self, pluginAction, dev):
    props = dev.pluginProps
    if 'colorTemp' in props:
      self.logger.info("        Color Temp: {}".format(props['colorTemp']))
    self.logger.info("    Supports Color: {}".format(props['isColor']))
    if props['isColor']:
      self.logger.info("               Hue: {}".format(props['Hue']))
      self.logger.info("        Saturation: {}".format(props['Saturation']))
    return

  def actionControlUniversal(self, action, dev):
    return

  def getDeviceStateList(self, dev, statesDict):
    self.logger.debug(" called for: %s." % statesDict)

    # brightness level is pre-defined. No need to add it here
    hue = self.tpLink_self.getDeviceStateDictForNumberType("hue", "hue", "hue")
    statesDict.append(hue)

    return statesDict

  def selectTpDevice(self, valuesDict, typeId, devId):
    address = valuesDict['address']
    # This sub-method gets called in the device configuration process, once address resolution is successful
    self.logger.debug("called for: %s, %s, %s." % (typeId, devId, address))

    sys_info = self.tpLink_self.deviceSearchResults[address]['system']['get_sysinfo']
    valuesDict['mac']  = sys_info['mic_mac']

    valuesDict['isColor'] = (sys_info['is_color'] == 1)
    valuesDict['isDimmable'] = (sys_info['is_dimmable'] == 1)
    valuesDict['description'] = sys_info['description']
    valuesDict['energyCapable'] = False

    dev = indigo.devices[devId]
    if 'rampTime' in dev.pluginProps:
      valuesDict['rampTime'] = dev.pluginProps['rampTime']
    else:
      valuesDict['rampTime'] = 1000 # default to 1 second

    self.logger.debug("returning valuesDict: %s" % valuesDict)
    return valuesDict

  def displayButtonPressed(self, dev, valuesDict):
    props = dev.pluginProps
    valuesDict['isDimmable']  = props['isDimmable']
    valuesDict['isColor']     = props['isColor']
    valuesDict['rampTime']    = props['rampTime']
    return(valuesDict)

  def printToLogPressed(self, valuesDict, rpt_fmt):

    return rpt_fmt.format("Supports Dimming:", valuesDict['isDimmable']) + \
           rpt_fmt.format("Supports Color:", valuesDict['isColor'])


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
      rampTime = str(pluginAction.props.get("setFOnT"))
      newProps = dev.pluginProps
      newProps['rampTime'] = rampTime
      dev.replacePluginPropsOnServer(newProps)
      indigo.server.log("set_fade_on_time: set the Ramp Time to {} ".format(rampTime))
      return(None)

  def set_fade_off_time(self, pluginAction, dev):
      rampTime = str(pluginAction.props.get("setFOT"))
      newProps = dev.pluginProps
      newProps['rampTime'] = rampTime
      dev.replacePluginPropsOnServer(newProps)
      indigo.server.log("set_fade_off_time: set the Ramp Time to {} ".format(rampTime))
      return(None)

  ##### for color bulbs only - set the color using HSV
  # int hue: hue in degrees
  # int saturation: saturation in percentage [0,100]
  # int value: brightness in percentage [0, 100]
  def set_HSV(self, pluginAction, dev):
    hue  = int(pluginAction.props.get("Hue"))
    sat  = int(pluginAction.props.get("Sat"))
    val  = int(pluginAction.props.get("Val"))

    errors = 0
    if hue < 0 or hue > 360:
      indigo.server.log("set_HSV Error: hue={}; must be between 0 and 360".format(hue))
      errors += 1
    if sat < 0 or sat > 100:
      indigo.server.log("set_HSV Error: saturation={}; must be between 0 and 100".format(sat))
      errors += 1
    if val < 0 or val > 100:
      indigo.server.log("set_HSV Error: value={}; must be between 0 and 100".format(val))
      errors += 1
    if not ('isColor' in dev.pluginProps and dev.pluginProps['isColor'] != 0):
      indigo.server.log("set_HSV Error: device {} does not support color".format(dev.name))
      errors += 1
    if errors > 0:
      return(None)

    tplink_dev_states = tplink_dimmer_protocol(dev.address, 9999)
    result = tplink_dev_states.send('set_HSV', str(hue), str(sat), str(val))

    # update HSV in device state
    newProps = dev.pluginProps
    newProps['Hue'] = hue
    newProps['Saturation'] = sat
    newProps['brightnessLevel'] = val
    dev.replacePluginPropsOnServer(newProps)

  # int value: value in percentage [0, 100]
  def set_ColorTemp(self, pluginAction, dev):
    temp  = int(pluginAction.props.get("Temp"))

    # what is valid range to check for??
    errors = 0
    if temp < 0 or temp > 9999:
      indigo.server.log("set_ColorTemp Error: Temp={}; must be between 0 and 9999".format(temp))
      errors += 1
    if errors > 0:
      return(None)

    tplink_dev_states = tplink_dimmer_protocol(dev.address, 9999)
    result = tplink_dev_states.send('set_ColorTemp', str(temp))
    # indigo.server.log("setColorTemp result: {}".format(result))

    # update HSV in device state
    newProps = dev.pluginProps
    newProps['colorTemp'] = temp
    dev.replacePluginPropsOnServer(newProps)
