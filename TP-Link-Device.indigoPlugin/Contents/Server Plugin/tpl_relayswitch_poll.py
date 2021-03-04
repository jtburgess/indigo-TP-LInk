#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

import indigo
import inspect
import json
import pdb
from threading import Thread
from time import sleep

# only works for Relayswitch devices
from tplink_relayswitch_protocol import tplink_relayswitch_protocol
from tpl_polling import pollingThread

################################################################################
class relayswitch_poll(pollingThread):
  ####################################################################
  def __init__(self, logger, dev, logOnOff, pluginPrefs):
    super(relayswitch_poll, self).__init__(logger, dev, logOnOff, pluginPrefs)
    self.logger.debug(u"called for: %s." % (dev.name))

    self.onPoll = int(dev.pluginProps['onPoll'])
    self.offPoll = int(dev.pluginProps['offPoll'])

    self.onOffState = dev.states['onOffState']
    if self.onOffState:
      self.pollFreq = self.onPoll
    else:
      self.pollFreq = self.offPoll
    self.deviceId = dev.pluginProps['deviceId']
    self.changed = False
    # self.logger.threaddebug(u"Initializing: %s:%s" % (dev.name, self.offPoll))
    self._is_running = True
    self.start()

# use super()
#  def interupt(self, state=None, dev=None, action=None):
#  def start(self)
#  def stop(self):

  def run(self):
    self.logger.debug(u"called for: %s." % (self.dev))
    dev = self.dev
    devType = dev.deviceTypeId
    devAddr = dev.address
    devPort = 9999

    self.logger.threaddebug(u"Starting data refresh for %s :%s:%s: with %s" % (dev.name, devType, devAddr, self.offPoll))

    tplink_dev_states = tplink_relayswitch_protocol(devAddr, devPort)
    lastState = 2
    firstRun = False
    error_counter = 0
    pollErrors = 0

    while True:
      try:
        self.logger.threaddebug(u"%s: Starting polling loop with interval %s\n", self.name, self.pollFreq)
        try:
          result = tplink_dev_states.send('info',"","")
          self.logger.threaddebug("%s connection received (%s)" % (self.name, result))
          data = json.loads(result)
        except Exception as e:
          self.logger.error("%s connection failed with (%s)" % (self.name, str(e)))

        try:
          result = tplink_dev_states.send('getParam',"","")
          self.logger.threaddebug("%s connection received (%s)" % (self.name, result))
          data1 = json.loads(result)
          result = tplink_dev_states.send('getBehave',"","")
          self.logger.threaddebug("%s connection received (%s)" % (self.name, result))
          data2 = json.loads(result)['smartlife.iot.dimmer']['get_default_behavior']
        except Exception as e:
          self.logger.error("{} error getting RelaySwitch data. Is this the right device type?".format(self.name))
          self.logger.error("    error was '{}'".format(str(e)))
          self.logger.error("    Polling for this device will now shut down.")
          indigo.device.enable(dev.id, value=False)
          return

        self.logger.threaddebug(u"%s: finished state data collection with %s" % (self.name, data))

        # Check if we got an error back
        if 'error' in data:
          pollErrors += 1
          if pollErrors == 2:
            self.logger.error(u"2 consecutive polling error for device \"%s\": %s" % (self.name, data['error']))
          elif pollErrors == 5:
            self.logger.error(u"5 consecutive polling error for device \"%s\": %s" % (self.name, data['error']))
          elif pollErrors == 8:
            self.logger.error(u"8 consecutive polling error for device \"%s\": %s" % (self.name, data['error']))
          elif pollErrors >= 10:
            self.logger.error(u"Unable to poll device \"%s\": %s after 10 attempts. Polling for this device will now shut down." % (self.name, data['error']))
            indigo.device.enable(dev.id, value=False)
            return

        else:
            pollErrors = 0
            # self.logger.threaddebug(u"%s: Got Here 0 with %s" % (self.name, data))
            devState = data['system']['get_sysinfo']['relay_state']
            devBright = data['system']['get_sysinfo']['brightness']
            self.logger.threaddebug(u"%s: switch state= %s, lastState=%s, brightness=%s" % (self.name, devState, lastState, str(devBright)))
            if not firstRun:  # set the logOnOff msg to reflect a first pass in the poll
                firstRun = True
                foundMsg = 'found'
            else:
                foundMsg = 'remotely'

            if devState != lastState:
                if devState:
                    state = True
                    logState = "On"
                    # self.interupt(state=True, action='state')
                else:
                    state = False
                    logState = "Off"
                    # self.interupt(state=False, action='state')
            lastState = devState

            self.logger.threaddebug(u"%s: state= %s, lastState=%s : %s" % (self.name, devState, lastState, state))
#            indigo.server.log(u"%s: state= %s, lastState=%s : %s" % (self.name, devState, lastState, state))

            alias = data['system']['get_sysinfo']['alias']
            rssi = data['system']['get_sysinfo']['rssi']
            fadeOnTime = data1['smartlife.iot.dimmer']['get_dimmer_parameters']['fadeOnTime']
            fadeOffTime = data1['smartlife.iot.dimmer']['get_dimmer_parameters']['fadeOffTime']
            minThreshold = data1['smartlife.iot.dimmer']['get_dimmer_parameters']['minThreshold']
            gentleOnTime = data1['smartlife.iot.dimmer']['get_dimmer_parameters']['gentleOnTime']
            gentleOffTime = data1['smartlife.iot.dimmer']['get_dimmer_parameters']['gentleOffTime']
            rampRate = data1['smartlife.iot.dimmer']['get_dimmer_parameters']['rampRate']
            hardOn=data2['hard_on']['mode']
            softOn=data2['soft_on']['mode']
            longPress=data2['long_press']['mode']
            doubleClick=data2['double_click']['mode']

 #             indigo,server.log("update state:"+str(state))
            bright=devBright
            if state==False:
                  bright=0

            state_update_list = [
                  {'key':'onOffState', 'value':state},
                  {'key':'brightnessLevel', 'value':bright},
                  {'key':'rssi', 'value':rssi},
                  {'key':'alias', 'value':alias},
                  {'key':'fadeOnTime', 'value':fadeOnTime},
                  {'key':'fadeOffTime', 'value':fadeOffTime},
                  {'key':'minThreshold', 'value':minThreshold},
                  {'key':'gentleOnTime', 'value':gentleOnTime},
                  {'key':'gentleOffTime', 'value':gentleOffTime},
                  {'key':'hardOn', 'value':hardOn},
                  {'key':'softOn', 'value':softOn},
                  {'key':'longPress', 'value':longPress},
                  {'key':'doubleClick', 'value':doubleClick},
                ]
            dev.updateStatesOnServer(state_update_list)

            self.logger.threaddebug(u"%s is now %s: localOnOff=%s, logOnOff=%s", self.name, logState, self.localOnOff, self.logOnOff)

            if not self.localOnOff:
                if self.logOnOff:
#                    self.logger.info(u"{} {} set to {}".format(self.name, foundMsg, logState))

#              self.interupt(state=state, action='state')
                    self.localOnOff = False

            self.logger.threaddebug(u"Polling found %s set to %s", self.name, logState)
            self.logger.threaddebug(u"%s, updated state on server to %s (%s, %s)", self.name, state, rssi, alias)

        self.logger.debug(u"%s: finished state update %s" % (self.name, data))

        indigo.debugger()
        self.logger.threaddebug(u"%s: In the loop - finished data gathering. Will now pause for %s" % (self.name, self.pollFreq))
        pTime = 0.5
        cTime = float(self.pollFreq)

        error_counter = 0
        while cTime > 0:
          # self.logger.threaddebug(u"%s: Looping Timer = %s", self.name, cTime)
          if self.changed or not self._is_running:
            # self.logger.threaddebug(u"Device change for %s" % (self.name))
            self.changed = False
            cTime = 0
          else:
            # self.logger.threaddebug(u"starting mini sleep for %6.4f" % (pTime))
            sleep(pTime)
            cTime = cTime - pTime
            # self.logger.threaddebug(u"Timer = %6.4f" % (cTime))

          # self.logger.threaddebug(u"Timer loop finished for %s", self.name)

        self.logger.debug(u"%s: Back in the loop - timer ended" % (self.name))

      except Exception as e:
        if error_counter == 10:
          self.logger.error("Unable to update %s: after 10 attempts. Polling for this device will now shut down. (%s)" % (self.name, str(e)))
          indigo.device.enable(dev.id, value=False)
          return
        else:
          error_counter += 1
          self.logger.error("Error attempting to update %s: %s. Will try again in %s seconds" % (self.name, str(e), self.pollFreq))


