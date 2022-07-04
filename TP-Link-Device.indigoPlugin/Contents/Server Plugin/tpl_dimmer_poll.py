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
  def __init__(self, tpLink_self, dev):
    super(dimmer_poll, self).__init__(tpLink_self, dev)
    self.logger.debug("called for: %s." % (dev.name))
    self.multiPlug = False # needed for interrupt()

    self.onPoll = int(self.tpLink_self.devOrPluginParm(dev, 'onPoll', 10)[0])
    self.offPoll = int(self.tpLink_self.devOrPluginParm(dev, 'offPoll', 30)[0])
    self.onOffState = dev.states['onOffState']
    if self.onOffState:
      self.pollFreq = self.onPoll
    else:
      self.pollFreq = self.offPoll
    self.logger.debug("poll init at interval %s (on=%s, off=%s)" % (self.pollFreq, self.onPoll, self.offPoll))
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
    self.logger.debug("called for: %s." % (self.dev, ))
    dev = self.dev
    devType = dev.deviceTypeId
    devAddr = dev.address
    devPort = 9999

    self.logger.threaddebug("Starting data refresh for %s :%s:%s: with %s" % (dev.name, devType, devAddr, self.offPoll))

    tplink_dev_states = tplink_dimmer_protocol(devAddr, devPort, self.deviceId)
    lastState = 2
    lastStateMulti = {}
    firstRun = False
    self.exceptCount = 0
    self.pollErrors = 0

    while True:
      try:
        self.logger.threaddebug("%s: Starting polling loop with interval %s\n" % (self.name, self.pollFreq) )
        try:
          result = tplink_dev_states.send('info',"","")
          self.logger.threaddebug("%s connection 1 received (%s)" % (self.name, result))
          data = json.loads(result)
        except Exception as e:
          self.logger.error("%s connection failed with (%s)" % (self.name, str(e)))

        self.logger.threaddebug("%s: finished state data collection with %s" % (self.name, data))

        # Check if we got an error back
        if 'error' in data or 'error' in data1:
          self.pollErrors += 1
          if self.pollErrors >= self.tpLink_self.devOrPluginParm(dev, 'StopPoll', 20)[0]:
            self.logger.error("Unable to poll device \"{}\": {} after {} errors. Polling for this device will now shut down.".format(self.name, data['error'], self.pollErrors))
            indigo.device.enable(dev.id, value=False)
            return

          if (self.pollErrors % self.tpLink_self.devOrPluginParm(dev, 'WarnInterval', 5)[0]) == 0:
            self.pollFreq += int(self.tpLink_self.devOrPluginParm(dev, 'SlowDown', 1)[0])
            self.logger.error("{} consecutive polling errors for device {}: error {}. Polling internal now {}".format (self.pollErrors, self.name, data['error'], self.pollFreq))

        else:
          # No error!; reset error count and set poll Freq based on on/off state
          if self.pollErrors > 0:
            self.logger.info("Normal polling resuming for device {}".format(self.name))
            self.pollErrors = 0

            # reset pollFreq in case increaded due to errors
            if self.onOffState:
              self.pollFreq = self.onPoll
            else:
              self.pollFreq = self.offPoll
          # self.logger.threaddebug(u"%s: Got Here 0 with %s" % (self.name, data))
          devState = data['system']['get_sysinfo']['light_state']['on_off']
          self.logger.threaddebug("%s: smartBulb device 1 state= %s, lastState=%s" % (self.name, devState, lastState))
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

            self.logger.threaddebug("%s: state= %s, lastState=%s : %s" % (self.name, devState, lastState, state))

            alias = data['system']['get_sysinfo']['alias']
            rssi = data['system']['get_sysinfo']['rssi']
            bright = data['system']['get_sysinfo']['brightness']

            data1 = data1['smartlife.iot.dimmer']['get_dimmer_parameters']
            state_update_list = [
                {'key':'onOffState', 'value':state, 'uiValue':logState},
                {'key':'brightnessLevel', 'value':bright},
                {'key':'rssi',  'value':rssi},
                {'key':'alias', 'value':alias},
              ]
            dev.updateStatesOnServer(state_update_list)
            self.logger.debug("{}, updated state on server: onOff={}, alias={}".format(self.name, state, alias))

            self.logger.threaddebug("%s is now %s: localOnOff=%s, logOnOff=%s" % (self.name, logState, self.localOnOff, self.logOnOff) )

            if not self.localOnOff:
              if self.logOnOff:
                self.logger.info("{} {} set to {}".format(self.name, foundMsg, logState))
            self.localOnOff = False

            if state:
              # only get HSV parameters from the device if the bulb is on (or dimmed)
              # the data returned by 'info' has several different formats...
              if "dft_on_state" in  data['system']['get_sysinfo']['light_state']:
                brightness = data['system']['get_sysinfo']['light_state']["dft_on_state"]['brightness']
                hue        = data['system']['get_sysinfo']['light_state']["dft_on_state"]['hue']
                sat        = data['system']['get_sysinfo']['light_state']["dft_on_state"]['saturation']
                temp       = data['system']['get_sysinfo']['light_state']["dft_on_state"]['color_temp']
                fromObject = 'dft_on_state'
              elif "brightness" in  data['system']['get_sysinfo']['light_state']:
                brightness = data['system']['get_sysinfo']['light_state']['brightness']
                hue        = data['system']['get_sysinfo']['light_state']['hue']
                sat        = data['system']['get_sysinfo']['light_state']['saturation']
                temp       = data['system']['get_sysinfo']['light_state']['color_temp']
                fromObject = 'light_state'
              else:
                self.logger.debug("{}, brightness not in light_state data: {}".format(self.name, data['system']['get_sysinfo']['light_state']))
                brightness = None

              if brightness is not None:
                state_update_list = [
                    {'key':'brightnessLevel', 'value':brightness},
                    {'key':'Hue',        'value':hue},
                    {'key':'Saturation', 'value':sat},
                    {'key':'colorTemp',  'value':temp},
                  ]
                dev.updateStatesOnServer(state_update_list)
                self.logger.debug("{}, updated state on server: Dimmer States={} from {}".format(self.name, state_update_list, fromObject))

            else:
                # if the bulb is off, just set to 0
                state_update_list = [
                    {'key':'brightnessLevel', 'value':0},
                    # leave other parameters alone
                  ]
                dev.updateStatesOnServer(state_update_list)

            self.interupt(state=state, action='state')

            self.logger.threaddebug("Polling %s %s set to %s" % ((self.name, foundMsg, logState)) )

          elif devState and "dft_on_state" in data['system']['get_sysinfo']['light_state']:
            # if the device is on, update the brighness - maybe we didn't get it last time
            brightness = data['system']['get_sysinfo']['light_state']["dft_on_state"]['brightness']
            hue        = data['system']['get_sysinfo']['light_state']["dft_on_state"]['hue']
            sat        = data['system']['get_sysinfo']['light_state']["dft_on_state"]['saturation']
            temp       = data['system']['get_sysinfo']['light_state']["dft_on_state"]['color_temp']

            state_update_list = [
                {'key':'brightnessLevel', 'value':brightness},
                {'key':'Hue',        'value':hue},
                {'key':'Saturation', 'value':sat},
                {'key':'colorTemp',  'value':temp},
              ]
            dev.updateStatesOnServer(state_update_list)
            self.logger.debug("{}, no state change; update state on server: Dimmer States={}".format(self.name, state_update_list))

          self.logger.debug("%s: finished state update %s" % (self.name, data))

        indigo.debugger()
        self.logger.threaddebug("%s: In the loop - finished data gathering. Will now pause for %s" % (self.name, self.pollFreq))
        pTime = 0.5
        cTime = float(self.pollFreq)

        self.exceptCount = 0
        while cTime > 0:
          # self.logger.threaddebug(u"%s: Looping Timer = %s" % (self.name, cTime) )
          if self.changed or not self._is_running:
            # self.logger.threaddebug(u"Device change for %s" % (self.name))
            self.changed = False
            cTime = 0
          else:
            # self.logger.threaddebug(u"starting mini sleep for %6.4f" % (pTime))
            sleep(pTime)
            cTime = cTime - pTime
            # self.logger.threaddebug(u"Timer = %6.4f" % (cTime))

          # self.logger.threaddebug(u"Timer loop finished for %s" % (self.name) )
        if not self._is_running:
          break

        self.logger.debug("%s: Back in the loop - timer ended" % (self.name))

      except Exception as e:
        if self.exceptCount == 10:
          self.logger.error("Unable to update %s: after 10 attempts. Polling for this device will now shut down. (%s)" % (self.name, str(e)))
          indigo.device.enable(dev.id, value=False)
          return
        else:
          self.exceptCount += 1
          self.logger.error("Error attempting to update %s: %s. Will try again in %s seconds" % (self.name, str(e), self.pollFreq))
