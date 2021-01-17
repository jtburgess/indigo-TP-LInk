#!/usr/bin/env python
#
# protocol subclass for the Plug/Switch (relay) device type

from protocol import tplink_protocol

class tplink_relay_protocol(tplink_protocol):

  # all functions not defined here revert to the super(), i.e., base class

  # Predefined Smart Plug Commands
  def commands(self):
    relay_cmds = {
      'on'       : '{"system":{"set_relay_state":{"state":1}}}',
      'off'      : '{"system":{"set_relay_state":{"state":0}}}',
      'cloudinfo': '{"cnCloud":{"get_info":{}}}',
      'countdown': '{"count_down":{"get_rules":{}}}',
      'antitheft': '{"anti_theft":{"get_rules":{}}}',
      'e+i'      : '{"emeter": { "get_realtime": {} }, "system": { "get_sysinfo": {} } }',
      'energy'   : '{"emeter":{"get_realtime":{}}}',
      'time'     : '{"time":{"get_time":{}}}',
      'wlanscan' : '{"netif":{"get_scaninfo":{"refresh":0}}}',
    }

    relay_cmds.update( super(tplink_relay_protocol, self).commands() )
    return relay_cmds

  def getErrorCode(self, result_dict):
    """ the JSON for relay and dimmer is different.
        find and return the error code from the result
    """
    return result_dict["system"]["set_relay_state"]["err_code"]
