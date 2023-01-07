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
  def __init__(self, tpLink_self, dev):
    super(relayswitch_poll, self).__init__(tpLink_self, dev)
    self.logger.debug("called for: %s." % (dev.name, ))

    self.onPoll = int(self.tpLink_self.devOrPluginParm(dev, 'onPoll', 10)[0])
    self.offPoll = int(self.tpLink_self.devOrPluginParm(dev, 'offPoll', 30)[0])
    self.onOffState = dev.states['onOffState']
    if self.onOffState:
      self.pollFreq = self.onPoll
    else:
      self.pollFreq = self.offPoll
    self.logger.debug("poll init at interval %s (on=%s, off=%s)" % (self.pollFreq, self.onPoll, self.offPoll))
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
    self.deviceId = dev.pluginProps['deviceId']

    self.logger.threaddebug("Starting data refresh for %s :%s:%s: with %s" % (dev.name, devType, devAddr, self.offPoll))

    tplink_dev_states = tplink_relayswitch_protocol(devAddr, devPort)
    lastState = 2
    firstRun = False
    self.exceptCount = 0
    self.pollErrors = 0

    while True:
      try:
        self.logger.threaddebug("%s: Starting polling loop with interval %s" % (self.name, self.pollFreq) )
        try:
          result = tplink_dev_states.send('info',"","")
          self.logger.threaddebug("%s connection 1 received (%s)" % (self.name, result))
          data = json.loads(result)
        except Exception as e:
          self.logger.error("%s connection failed with (%s)" % (self.name, str(e)))

        try:
          result = tplink_dev_states.send('getParam',"","")
          self.logger.threaddebug("%s connection 2 received (%s)" % (self.name, result))
          data1 = json.loads(result)
          result = tplink_dev_states.send('getBehave',"","")
          self.logger.threaddebug("%s connection 3 received (%s)" % (self.name, result))
          data2 = json.loads(result)
        except Exception as e:
          self.logger.error("{} error getting RelaySwitch data. Is this the right device type?".format(self.name))
          self.logger.error("    error was '{}'".format(str(e)))
          self.logger.error("    Polling for this device will now shut down.")
          indigo.device.enable(dev.id, value=False)
          return

        self.logger.threaddebug("%s: finished state data collection with %s" % (self.name, data))

        # Check if we got an error back
        if 'error' in data or 'error' in data1 or 'error' in data2:
          self.pollErrors += 1
          # put the error in one place no matter which command failed
          if 'error' in data:
            error = data['error']
          elif 'error' in data1:
            error = data1['error']
          elif 'error' in data2:
            error = data2['error']

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
              if self.pollErrors >  self.tpLink_self.devOrPluginParm(dev, 'WarnInterval', 5)[0]:
                # only issue Resume, if a Warning was previously given
                self.logger.info("Normal polling resuming for device {}".format(self.name))
              self.pollErrors = 0
              # reset pollFreq in case increaded due to errors
              if self.onOffState:
                self.pollFreq = self.onPoll
              else:
                self.pollFreq = self.offPoll
            # self.logger.threaddebug(u"%s: Got Here 0 with %s" % (self.name, data))
            devState = data['system']['get_sysinfo']['relay_state']
            bright = data['system']['get_sysinfo']['brightness']
            self.logger.threaddebug("%s: switch state= %s, lastState=%s, brightness=%s" % (self.name, devState, lastState, str(bright)))
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
            self.logger.threaddebug("%s: state= %s, lastState=%s : %s" % (self.name, devState, lastState, state))
            try:
              alias = data['system']['get_sysinfo']['alias']
              rssi = data['system']['get_sysinfo']['rssi']
              data1 = data1['smartlife.iot.dimmer']['get_dimmer_parameters']
              fadeOnTime = data1['fadeOnTime']
              fadeOffTime = data1['fadeOffTime']
              minThreshold = data1['minThreshold']
              gentleOnTime = data1['gentleOnTime']
              gentleOffTime = data1['gentleOffTime']
              rampRate = data1['rampRate']
              data2 = data2['smartlife.iot.dimmer']['get_default_behavior']
              hardOn=data2['hard_on']['mode']
              softOn=data2['soft_on']['mode']
              longPress=data2['long_press']['mode']
              doubleClick=data2['double_click']['mode']
            except:
              self.logger.error("{} error parsing RelaySwitch data. Is this the right device type?".format(self.name))
              self.logger.error("    error was '{}'".format(str(e)))
              self.logger.error("    Polling for this device will now shut down.")
              indigo.device.enable(dev.id, value=False)
              return

#           indigo,server.log("update state:"+str(state))
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

            self.logger.threaddebug("%s is now %s: localOnOff=%s, logOnOff=%s" % (self.name, logState, self.localOnOff, self.logOnOff) )

            if not self.localOnOff:
                if self.logOnOff:
                  self.logger.info("{} {} set to {}".format(self.name, foundMsg, logState))
#                 self.interupt(state=state, action='state')

            self.interupt(state=state, action='state')
            self.localOnOff = False

            self.logger.threaddebug("Polling found %s set to %s" % (self.name, logState) )
            self.logger.threaddebug("%s, updated state on server to %s (%s, %s)" % (self.name, state, rssi, alias) )

        self.logger.debug("%s: finished state update %s" % (self.name, data))

        indigo.debugger()
        self.logger.threaddebug("%s: In the loop - finished data gathering. Will now pause for %s" % (self.name, self.pollFreq))
        pTime = 1.0
        cTime = float(self.pollFreq)

        self.exceptCount = 0
        while cTime > 0:
          # self.logger.threaddebug(u"%s: Looping Timer = %s" % (self.name, cTime) )
          if self.changed or not self._is_running:
            # self.logger.threaddebug(u"Device change for %s" % (self.name, ))
            self.changed = False
            cTime = 0
          else:
            # self.logger.threaddebug(u"starting mini sleep for %6.4f" % (pTime, ))
            sleep(pTime)
            cTime = cTime - pTime
            # self.logger.threaddebug(u"Timer = %6.4f" % (cTime, ))

          # self.logger.threaddebug(u"Timer loop finished for %s" % (self.name, ))
        if not self._is_running:
          break

        self.logger.debug("%s: Back in the loop - timer ended" % (self.name, ))

      except Exception as e:
        if self.exceptCount == 10:
          self.logger.error("Unable to update %s: after 10 attempts. Polling for this device will now shut down. (%s)" % (self.name, str(e)))
          indigo.device.enable(dev.id, value=False)
          return
        else:
          self.exceptCount += 1
          self.logger.error("Error attempting to update %s: %s. Will try again in %s seconds" % (self.name, str(e), self.pollFreq))
