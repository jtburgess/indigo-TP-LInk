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
from tplink_relay_protocol import tplink_relay_protocol
from tpl_polling import pollingThread

# e.g. data['emeter']['get_realtime']['power_mw']
# OR   data['emeter']['get_realtime']['power']
def eitherOr (base, opt1, opt2):
  opt = ''
  if opt1 in base :
    opt = opt1
  elif opt2 in base:
    opt = opt2
  else:
    self.logger.error ("Neither {} nor {} found in {}, using 0".format(opt1, opt2, base))
    return 0

  if "_m" in opt or "_wh" in opt:
    # measured in "milli" (watts, amps, volts) or watt-hours (want KWh))
    return base[opt] / 1000
  else:
    return base[opt]


################################################################################
class relay_poll(pollingThread):
  ####################################################################
  def __init__(self, tpLink_self, dev):
    super(relay_poll, self).__init__(tpLink_self, dev)
    self.logger.debug("called for: %s." % (dev.name))
    self.lastMultiPlugOnCount = 0

    self.outlets = {}
    outletNum = dev.pluginProps['outletNum']
    self.logger.threaddebug("outlet: %s, multiPlug %s" % (dev.name, self.dev.pluginProps['multiPlug']))

    # Here we deal with multi plug devices. We will just store the entire device in a dictionary indexed by the outlet number
    self.multiPlug = dev.pluginProps['multiPlug']
    if self.multiPlug:
      self.outlets[outletNum] = self.dev
      self.logger.threaddebug("outlet dict =%s" % (self.outlets))

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
    energyCapable = dev.pluginProps['energyCapable']
    devAddr = dev.address
    devPort = 9999
    self.deviceId = dev.pluginProps['deviceId']
    self.logger.threaddebug("%s multiPlug is %s" % (dev.name, self.multiPlug))

    self.logger.threaddebug("Starting data refresh for %s :%s:%s: with %s" % (dev.name, devType, devAddr, self.offPoll))

    tplink_dev_states = tplink_relay_protocol(devAddr, devPort)
    lastState = 2
    lastStateMulti = {}
    firstRun = False
    self.exceptCount = 0
    self.pollErrors = 0

    while True:
      #TRY# try:
        self.logger.threaddebug("%s: Starting polling loop with interval %s" % (self.name, self.pollFreq) )
        try:
          result = tplink_dev_states.send('info')
          self.logger.threaddebug("%s connection received (%s)" % (self.name, result))
          data = json.loads(result)
        except Exception as e:
          self.logger.error("%s connection failed with (%s)" % (self.name, str(e)))

        self.logger.threaddebug("%s: finished state data collection with %s" % (self.name, data))

        # Check if we got an error back
        if 'error' in data:
          self.pollErrors += 1
          if self.pollErrors >= int(self.tpLink_self.devOrPluginParm(dev, 'StopPoll', 20)[0]):
            self.logger.error("Unable to poll device \"{}\": {} after {} errors. Polling for this device will now shut down.".format(self.name, data['error'], self.pollErrors))
            indigo.device.enable(dev.id, value=False)
            return

          if (self.pollErrors % int(self.tpLink_self.devOrPluginParm(dev, 'WarnInterval', 5)[0])) == 0:
            self.pollFreq += int(self.tpLink_self.devOrPluginParm(dev, 'SlowDown', 1)[0])
            self.logger.error("{} consecutive polling errors for device {}: error {}. Polling internal now {}".format (self.pollErrors, self.name, data['error'], self.pollFreq))

        else:
          # No error!; reset error count and set poll Freq based on on/off state
          if self.pollErrors > 0:
            self.logger.info("After {} timeouts - Normal polling resuming for device {} ".format(self.pollErrors, self.name))
            self.pollErrors = 0

            # reset pollFreq in case increaded due to errors
            if self.onOffState:
              self.pollFreq = self.onPoll
            else:
              self.pollFreq = self.offPoll
          # check the onOff state of each plug
          if self.multiPlug:
            self.logger.threaddebug("%s: entered multiPlug state block" % (self.name))
            multiPlugOnCount = 0
            elements = data['system']['get_sysinfo']['children']

            self.logger.threaddebug("%s: Elements %s" % (self.name, elements))
            for element in elements:
              multiPlugOnCount += int(element['state'])
              outletName = element['alias']
              outletNum = element['id'][-2:]
              # self.logger.error(u"on count = %s last on count was %s for %s" % (multiPlugOnCount, self.lastMultiPlugOnCount, self.dev.address))
              devState = bool(element['state'])
              self.logger.threaddebug("%s: Starting new element... id=%s, outletNum=%s, element=%s" % (outletName, element['id'], outletNum, element))
              for outlet in self.outlets:
                self.logger.threaddebug("%s: Outlet=%s and id=%s id=%s" % (outletName, outlet, element['id'], element['id'][-2:]))
                if outlet == outletNum: #element['id'][-2:] == outlet:
                  self.logger.threaddebug("%s: YES %s" % (outletName, outletNum))
                  # self.logger.threaddebug(u"%s: indigo device onOffState is %s, actual is %s" % (outletName, lastStateMulti[outletNum], devState) )
                  if not outletNum in lastStateMulti:
                    lastStateMulti[outletNum] = 2
                    foundMsg = 'found'
                  else:
                    foundMsg = 'remotely'

                  if devState != lastStateMulti[outletNum]:
                    if devState:
                      state = True
                      logState = "On"
                    else:
                      state = False
                      logState = "Off"
                    lastStateMulti[outletNum] = devState

                    alias = element['alias']
                    rssi = data['system']['get_sysinfo']['rssi']
                    state_update_list = [
                        {'key':'onOffState', 'value':state},
                        {'key':'rssi', 'value':rssi},
                        {'key':'alias', 'value':alias}
                      ]
                    self.outlets[outlet].updateStatesOnServer(state_update_list)

                    if not self.localOnOff:
                      if self.logOnOff:
                        self.logger.info("%s -%s %s set to %s" % (self.name, outletName, foundMsg, logState) )

                    self.logger.threaddebug("Polling found %s set to %s" % (self.name, logState) )

            # Before we go, check to see if we need to update the polling interval
            if self.lastMultiPlugOnCount == 0 and multiPlugOnCount > 0:
              # we have transitioned from all plugs off to at least one plug on
              self.logger.threaddebug("Changing polling interval to on for %s" % (self.dev.address))
              self.interupt(state=True, action='state')
            elif self.lastMultiPlugOnCount > 0 and multiPlugOnCount == 0:
              # we have transitioned from at least one plug on to all plugs off
              self.logger.threaddebug("Changing polling interval to on for %s" % (self.dev.address))
              self.interupt(state=False, action='state')
            self.lastMultiPlugOnCount = multiPlugOnCount
            self.localOnOff = False

          else:  # we have a single outlet device
            # self.logger.threaddebug(u"%s: Got Here 0 with %s" % (self.name, data))
            devState = data['system']['get_sysinfo']['relay_state']
            self.logger.threaddebug("%s: single outlet device 1 state= %s, lastState=%s" % (self.name, devState, lastState))
            if not firstRun:  # set the logOnOff msg to reflect a first pass in the poll
              firstRun = True
              foundMsg = 'found'
            else:
              foundMsg = 'remotely'

            if devState != lastState:
              if devState == 0:
                state = False
                logState = "Off"
                # self.interupt(state=False, action='state')
              else:
                state = True
                logState = "On"
                # self.interupt(state=True, action='state')
              lastState = devState
              if not self.localOnOff:
                if self.logOnOff:
                  self.logger.info("{} {} set to {}".format(self.name, foundMsg, logState))

              self.logger.threaddebug("%s: state= %s, lastState=%s : %s" % (self.name, devState, lastState, state))

              alias = data['system']['get_sysinfo']['alias']
              rssi = data['system']['get_sysinfo']['rssi']
              state_update_list = [
                  {'key':'onOffState', 'value':state},
                  {'key':'rssi', 'value':rssi},
                  {'key':'alias', 'value':alias}
                ]
              dev.updateStatesOnServer(state_update_list)

              self.logger.threaddebug("%s is now %s: localOnOff=%s, logOnOff=%s" % (self.name, logState, self.localOnOff, self.logOnOff) )


              self.interupt(state=state, action='state')
              self.localOnOff = False

              self.logger.threaddebug("Polling found %s set to %s" % (self.name, logState) )
              self.logger.threaddebug("%s, updated state on server to %s (%s, %s)" % (self.name, state, rssi, alias) )

          self.logger.debug("%s: finished state update %s" % (self.name, data))

          # Now we start looking for energy data... if the plug is capable
          if energyCapable:
            if self.multiPlug:
              self.logger.threaddebug("Starting energy query for devices at %s" % (devAddr) )
              deviceId = self.deviceId

              for element in elements:
                # self.logger.threaddebug(u"Starting energy update for %s: id=%s, element:%s" % (self.name, element['id'], element))
                childId = element['id'][-2:]
                if childId in self.outlets:
                  indigoDevice = self.outlets[childId]
                  # totAccuUsage = float(indigoDevice.pluginProps['totAccuUsage'])

                  self.logger.threaddebug("Found entry for outlet %s devId is %s" % (childId, indigoDevice.id) )

                  state = element['state']
                  self.logger.threaddebug("Ready to check energy for outlet %s, state %s" % (childId, state))
                  if bool(state):
                    self.logger.threaddebug("Getting energy for %s %s %s %s state %s" % (devAddr, devPort, deviceId, childId, state))
                    tplink_dev_energy = tplink_relay_protocol (devAddr, devPort, deviceID=deviceId, childID=childId)
                    result = tplink_dev_energy.send('energy')
                    data = json.loads(result)
                    self.logger.threaddebug("%s: data=%s" % (self.name, data))
                    curWatts = eitherOr (data['emeter']['get_realtime'], 'power_mw', 'power')
                    curVolts = eitherOr (data['emeter']['get_realtime'], 'voltage_mv', 'voltage')
                    curAmps  = eitherOr (data['emeter']['get_realtime'], 'current_ma', 'current')
                    totWattHrs = round( float( (eitherOr (data['emeter']['get_realtime'], 'total_wh', 'total'))), 1)


                    state_update_list = [
                        {'key':'curWatts', 'value':curWatts},
                        {'key':'totWattHrs', 'value':totWattHrs},
                        {'key':'curVolts', 'value':curVolts},
                        {'key':'curAmps', 'value':curAmps},
                        {'key':"curEnergyLevel", 'value':curWatts, 'uiValue':str(curWatts) + " w"},
                        {'key':'accumEnergyTotal', 'value':totWattHrs, 'uiValue':str(totWattHrs) + " kwh"}
                      ]
                    indigoDevice.updateStatesOnServer(state_update_list)

                  else:
                    self.logger.debug("Outlet %s:%s was off. No data collected" % (self.name, childId) )
                    state_update_list = [
                        {'key':'curWatts', 'value':0},
                        {'key':'curVolts', 'value':0},
                        {'key':'curAmps', 'value':0},
                        {'key':"curEnergyLevel", 'value':0, 'uiValue':str(0) + " w"}
                      ]
                    indigoDevice.updateStatesOnServer(state_update_list)

              else:
                self.logger.debug("Outlet %s: outlet=%s not configured. No energy usage collected" % (self.name, childId))

            else:    # we have a single outlet device
              tplink_dev_energy = tplink_relay_protocol (devAddr, devPort)
              result = tplink_dev_energy.send('energy')
              data = json.loads(result)
              self.logger.debug("Received result: |%s|" % (result))

              # totAccuUsage = float(dev.pluginProps['totAccuUsage'])
              curWatts = eitherOr (data['emeter']['get_realtime'], 'power_mw', 'power')
              curVolts = eitherOr (data['emeter']['get_realtime'], 'voltage_mv', 'voltage')
              curAmps  = eitherOr (data['emeter']['get_realtime'], 'current_ma', 'current')
              totWattHrs = round(float(eitherOr (data['emeter']['get_realtime'], 'total_wh', 'total')), 1)

              state_update_list = [
                  {'key':'curWatts', 'value':curWatts},
                  {'key':'totWattHrs', 'value':totWattHrs},
                  {'key':'curEnergyLevel', 'value':curWatts, 'uiValue':str(curWatts) + " w"},
                  {'key':'accumEnergyTotal', 'value':totWattHrs, 'uiValue':str(totWattHrs) + " kwh"},
                  {'key':'curVolts', 'value':curVolts},
                  {'key':'curAmps', 'value':curAmps}
                ]
              dev.updateStatesOnServer(state_update_list)

              self.logger.threaddebug("Received results for %s @ %s secs: %s, %s, %s: change = %s" % (dev.name, self.pollFreq, curWatts, curVolts, curAmps, self.changed))
        indigo.debugger()
        self.logger.threaddebug("%s: In the loop - finished data gathering. Will now pause for %s" % (self.name, self.pollFreq))
        pTime = 1.0
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

""" #TRY#
      except Exception as e:
        if self.exceptCount == 10:
          self.logger.error("Unable to update %s: after 10 attempts. Polling for this device will now shut down. (%s)" % (self.name, str(e)))
          indigo.device.enable(dev.id, value=False)
          return
        else:
          self.exceptCount += 1
          self.logger.error("Error attempting to update %s: %s. Will try again in %s seconds" % (self.name, str(e), self.pollFreq))
""" #TRY#
