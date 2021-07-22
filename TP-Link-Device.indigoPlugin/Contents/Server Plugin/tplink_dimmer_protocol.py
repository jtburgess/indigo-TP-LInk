#!/usr/bin/env python
#
# protocol subclass for the lightbulb dimmer device type

import sys
from protocol import tplink_protocol

class tplink_dimmer_protocol(tplink_protocol):

  def __init__(self, address, port, deviceID = None, childID = None, logger = None, arg2=1000):
    super(tplink_dimmer_protocol, self).__init__(address, port, deviceID=deviceID, childID=childID, logger=logger)

    self.arg2 = arg2 # default, because dev[] is not available

  # all functions not defined here revert to the super(), i.e., base class

  # Predefined Dimmer Commands
  #   XXX and YYY are replaced in send() to change color or Brightness or rampTime
  def commands(self):
    dimmer_cmds = {
      'on'       : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":YYY,"mode":"normal","brightness":100,"on_off":1}}}',
      'off'       : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":YYY,"mode":"normal","brightness":0,"on_off":0}}}',
      'light_state' : '{"smartlife.iot.smartbulb.lightingservice":{"get_light_state":""}}',
      'light_details' : '{"smartlife.iot.smartbulb.lightingservice":{"get_light_details":""}}',

      # set brightness level
      'setBright' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state": {"ignore_default":1,"transition_period":YYY,"brightness":XXX,"color_temp":0,"on_off":1}}}',

      # set HSV - requires 3 parameters: Hue, Sat, (brightness) Value as arg1, 2, 3 <=> XXX, YYY, ZZZ
      'set_HSV' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"mode":"normal","hue":XXX,"saturation":YYY,"brightness":ZZZ,"color_temp":0}}}',
      # set color temp has one parameter
      'set_ColorTemp' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"mode":"normal","color_temp":XXX}}}',

      'getParam'  : '{"smartlife.iot.dimmer": {"get_dimmer_parameters": {}}}',

      # generic command, customized above...
      'transition_light_state' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":YYY,"mode":"normal","on_off":1,"hue":120,"saturation":65,"color_temp":0,"brightness":10}}}',
    }

    dimmer_cmds.update( super(tplink_dimmer_protocol, self).commands() )
    return dimmer_cmds

  def getErrorCode(self, result_dict):
    """ the JSON for relay and dimmer is different.
        find and return the error code from the result
    """
    return result_dict["smartlife.iot.smartbulb.lightingservice"]["transition_light_state"]["err_code"]

  def send(self, request, arg1=None, arg2=None):
    # it doesn't hurt to have a default if YYY is undefined
    if arg2 == None:
      arg2 = self.arg2

    self.debugLog("arg1={}, arg2={}".format(arg1, arg2))
    return super(tplink_dimmer_protocol, self).send(request, str(arg1), str(arg2))
