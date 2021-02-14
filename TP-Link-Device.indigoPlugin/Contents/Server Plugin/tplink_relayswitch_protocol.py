#!/usr/bin/env python
#
# protocol subclass for the Plug/Switch (relay) device type

from protocol import tplink_protocol

class tplink_relayswitch_protocol(tplink_protocol):

  # all functions not defined here revert to the super(), i.e., base class

  # Predefined Smart Light Switch Commands
  def commands(self):
    relayswitch_cmds = {
      'on'        : '{"system":{"set_relay_state":{"state":1}}}',
      'off'       : '{"system":{"set_relay_state":{"state":0}}}',
      'cloudinfo' : '{"cnCloud":{"get_info":{}}}',
      'countdown' : '{"count_down":{"get_rules":{}}}',
      'antitheft' : '{"anti_theft":{"get_rules":{}}}',
      'time'      : '{"time":{"get_time":{}}}',
      'wlanscan'  : '{"netif":{"get_scaninfo":{"refresh":0}}}',
      'setBright' : '{"system": {"set_relay_state": {"state": 1}},"smartlife.iot.dimmer": {"set_brightness": {"brightness": XXX}}}',
      'getParam'  : '{"smartlife.iot.dimmer": {"get_dimmer_parameters": {}}}',
      'getBehave' : '{"smartlife.iot.dimmer": {"get_default_behavior": {}}}',
      'setTransit': '{"smartlife.iot.dimmer": {"set_dimmer_transition": {"brightness":XXX,"mode":"gentle_on_off", "duration":YYY}}}',
      'setDouble' : '{"smartlife.iot.dimmer": {"set_double_click_action": {"mode": "XXX","index":YYY}}}',
      'setFadeOff': '{"smartlife.iot.dimmer": {"set_fade_off_time":{"fadeTime":XXX}}}',
      'setFadeOn' : '{"smartlife.iot.dimmer": {"set_fade_on_time":{"fadeTime":XXX}}}',
      'setGentleoff':'{"smartlife.iot.dimmer": {"set_gentle_off_time":{"duration":XXX}}}',
      'setGentleon':'{"smartlife.iot.dimmer": {"set_gentle_on_time":{"duration":XXX}}}',
      'setLpress':  '{"smartlife.iot.dimmer": {"set_long_press_action": {"mode": "XXX","index":YYY}}}',
    }

    relayswitch_cmds.update( super(tplink_relayswitch_protocol, self).commands() )
    return relayswitch_cmds

  def getErrorCode(self, result_dict):
    """ the JSON for relay and dimmer is different.
        find and return the error code from the result
    """
    return result_dict["system"]["set_relay_state"]["err_code"]
