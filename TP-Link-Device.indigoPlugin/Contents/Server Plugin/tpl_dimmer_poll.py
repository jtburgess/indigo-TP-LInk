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

    tplink_dev_states = tplink_dimmer_protocol(devAddr, devPort, self.deviceId)
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
          if pollErrors == 5:
            self.logger.error(u"5 consecutive polling error for device \"%s\": %s" % (self.name, data['error']))
            self.pollFreq += 1
          elif pollErrors == 10:
            self.logger.error(u"8 consecutive polling error for device \"%s\": %s" % (self.name, data['error']))
            self.pollFreq += 1
          elif pollErrors >= 15:
            self.logger.error(u"Unable to poll device \"%s\": %s after 15 attempts. Polling for this device will now shut down." % (self.name, data['error']))
            indigo.device.enable(dev.id, value=False)
            return

        else:
          # First, we check the onOff state
          if pollErrors > 0:
            pollErrors = 0
            # reset pollFreq in case increaded due to errors
            if self.onOffState:
              self.pollFreq = self.onPoll
            else:
              self.pollFreq = self.offPoll
          # self.logger.threaddebug(u"%s: Got Here 0 with %s" % (self.name, data))
          devState = data['system']['get_sysinfo']['light_state']['on_off']
          self.logger.threaddebug(u"%s: smartBulb device 1 state= %s, lastState=%s" % (self.name, devState, lastState))
          if not firstRun:  # set the logOnOff msg to reflect a first pass in the poll
            firstRun = True
            foundMsg = 'found'
          else:
            foundMsg = 'remotely'

          if devState != lastState:
            # the device state changed; update indigo states
            if devState == 0:
              state = False
              logState = "Off"
              # self.interupt(state=True, action='state')
            else: # on or dimmed
              state = True
              logState = "On"
              # self.interupt(state=False, action='state')
            lastState = devState

            self.logger.threaddebug(u"%s: state= %s, lastState=%s : %s" % (self.name, devState, lastState, state))

            alias = data['system']['get_sysinfo']['alias']
            rssi = data['system']['get_sysinfo']['rssi']
            state_update_list = [
                {'key':'onOffState', 'value':state, 'uiValue':logState},
                {'key':'rssi',  'value':rssi},
                {'key':'alias', 'value':alias},
              ]
            dev.updateStatesOnServer(state_update_list)
            self.logger.debug(u"{}, updated state on server: onOff={}, alias={}".format(self.name, state, alias))

            self.logger.threaddebug(u"%s is now %s: localOnOff=%s, logOnOff=%s", self.name, logState, self.localOnOff, self.logOnOff)

            if not self.localOnOff:
              if self.logOnOff:
                self.logger.info(u"{} {} set to {}".format(self.name, foundMsg, logState))

            if state:
              # only get brightness from the device if the bulb is on (or dimmed)
              # the data returned by 'info' has several different formats...
              ### ToDo - what other properties SHOULD be saved??
              if "dft_on_state" in  data['system']['get_sysinfo']['light_state']:
                brightness = data['system']['get_sysinfo']['light_state']["dft_on_state"]['brightness']
                fromObject = 'dft_on_state'
                # hue        = data['system']['get_sysinfo']['light_state']["dft_on_state"]['hue']
              elif "brightness" in  data['system']['get_sysinfo']['light_state']:
                brightness = data['system']['get_sysinfo']['light_state']['brightness']
                fromObject = 'light_state'
                # hue        = data['system']['get_sysinfo']['light_state']['hue']
              else:
                self.logger.debug(u"{}, brightness not in light_state data: {}".format(self.name, data['system']['get_sysinfo']['light_state']))
                brightness = None

              if brightness is not None:
                state_update_list = [
                    {'key':'brightnessLevel', 'value':brightness},
                    # {'key':'hue',   'value':hue}
                  ]
                dev.updateStatesOnServer(state_update_list)
                self.logger.debug(u"{}, updated state on server: brightnessLevel={} from {}".format(self.name, brightness, fromObject))

            else:
                # if the bulb is off, just set to 0
                state_update_list = [
                    {'key':'brightnessLevel', 'value':0},
                    {'key':'hue',   'value':0}
                  ]
                dev.updateStatesOnServer(state_update_list)

            self.interupt(state=state, action='state')
            self.localOnOff = False

            self.logger.threaddebug(u"Polling %s %s set to %s", (self.name, foundMsg, logState))

          elif devState and "dft_on_state" in data['system']['get_sysinfo']['light_state']:
            # if the device is on, update the brighness - maybe we didn't get it last time
            brightness = data['system']['get_sysinfo']['light_state']["dft_on_state"]['brightness']
            hue        = data['system']['get_sysinfo']['light_state']["dft_on_state"]['hue']

            state_update_list = [
                {'key':'brightnessLevel', 'value':brightness},
                {'key':'hue',   'value':hue}
              ]
            dev.updateStatesOnServer(state_update_list)
            self.logger.debug(u"{}, no state change; update state on server: brightnessLevel={}, hue={}".format(self.name, brightness, hue))

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

