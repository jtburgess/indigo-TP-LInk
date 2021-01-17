#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

import indigo
import inspect
import json
import pdb
from threading import Thread
from time import sleep

# only works for Relay devices
from tplink_dimmer_protocol import tplink_dimmer_protocol
from tpl_polling import pollingThread

################################################################################
class dimmer_poll(pollingThread):
  ####################################################################
  def __init__(self, logger, dev, logOnOff, pluginPrefs):
    super(dimmer_poll, self).__init__(logger, dev, logOnOff, pluginPrefs)
    self.logger.debug(u"called for: %s." % (dev.name))
    self.multiPlug = False # needed for interrupt()

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

# use super() for these
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

    tplink_dev_states = tplink_dimmer_protocol(devAddr, devPort)
    lastState = 2
    lastStateMulti = {}
    firstRun = False
    error_counter = 0
    pollErrors = 0

    while True:
      try:
        self.logger.threaddebug(u"%s: Starting polling loop with interval %s\n", self.name, self.pollFreq)
        try:
          result = tplink_dev_states.send('info')
          self.logger.threaddebug("%s connection received (%s)" % (self.name, result))
          data = json.loads(result)
        except Exception as e:
          self.logger.error("%s connection failed with (%s)" % (self.name, str(e)))

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
          # First, we check the onOff state
          pollErrors = 0
          # self.logger.threaddebug(u"%s: Got Here 0 with %s" % (self.name, data))
          devState = data['system']['get_sysinfo']['light_state']['on_off']
          self.logger.threaddebug(u"%s: smartBulb device 1 state= %s, lastState=%s" % (self.name, devState, lastState))
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

            alias = data['system']['get_sysinfo']['alias']
            rssi = data['system']['get_sysinfo']['rssi']
            ### ToDo - what other properties SHOULD be saved??
            ### do I need to send a 'light_state' command
            brightness = data['system']['get_sysinfo']['light_state']["dft_on_state"]['brightness']
            hue        = data['system']['get_sysinfo']['light_state']["dft_on_state"]['hue']
            state_update_list = [
                {'key':'onOffState', 'value':state},
                {'key':'rssi',  'value':rssi},
                {'key':'alias', 'value':alias},
                {'key':'brightnessLevel', 'value':brightness},
                {'key':'hue',   'value':hue}
              ]
            dev.updateStatesOnServer(state_update_list)

            self.logger.threaddebug(u"%s is now %s: localOnOff=%s, logOnOff=%s", self.name, logState, self.localOnOff, self.logOnOff)

            if not self.localOnOff:
              if self.logOnOff:
                self.logger.info(u"{} {} set to {}".format(self.name, foundMsg, logState))

            self.interupt(state=state, action='state')
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
        if not self._is_running:
          break

        self.logger.debug(u"%s: Back in the loop - timer ended" % (self.name))

      except Exception as e:
        if error_counter == 10:
          self.logger.error("Unable to update %s: after 10 attempts. Polling for this device will now shut down. (%s)" % (self.name, str(e)))
          indigo.device.enable(dev.id, value=False)
          return
        else:
          error_counter += 1
          self.logger.error("Error attempting to update %s: %s. Will try again in %s seconds" % (self.name, str(e), self.pollFreq))

