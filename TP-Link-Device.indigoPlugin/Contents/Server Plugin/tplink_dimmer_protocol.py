#!/usr/bin/env python
#
# protocol subclass for the lightbulb dimmer device type

from protocol import tplink_protocol


class tplink_dimmer_protocol(tplink_protocol):

  # all functions not defined here revert to the super(), i.e., base class

  # Predefined Dimmer Commands
  def commands(self):
    dimmer_cmds = {
      'on'       : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":10,"mode":"normal","brightness":100,"on_off":1}}}',
      'off'       : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":10,"mode":"normal","brightness":0,"on_off":0}}}',
      'light_state' : '{"smartlife.iot.smartbulb.lightingservice":{"get_light_state":""}}',
      'light_details' : '{"smartlife.iot.smartbulb.lightingservice":{"get_light_details":""}}',
      # FYI this needs arguments filled in before using to change color or Brightness (see below)
      'transition_light_state' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":150,"mode":"normal","hue":120,"on_off":1,"saturation":65,"color_temp":0,"brightness":10}}}',
    }

    dimmer_cmds.update( super(tplink_dimmer_protocol, self).commands() )
    return dimmer_cmds

  def setBrightness(self, brightness, transition_period = '1'):
    """ construct the full json string
        'ramp time' aka 'transition period' can be supplied as optional second parameter
    """

    return "{\"smartlife.iot.smartbulb.lightingservice\":" +\
          "{\"transition_light_state\": {\"ignore_default\":1" +\
          ",\"transition_period\":" + transition_period +\
          ",\"brightness\":" + str(brightness) + ",\"color_temp\":0,\"on_off\":1}}}"
          ## or use saturation??

  def getErrorCode(self, result_dict):
    """ the JSON for relay and dimmer is different.
        find and return the error code from the result
    """
    return result_dict["smartlife.iot.smartbulb.lightingservice"]["transition_light_state"]["err_code"]
