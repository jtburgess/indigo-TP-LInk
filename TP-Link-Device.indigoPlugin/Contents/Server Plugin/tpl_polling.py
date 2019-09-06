#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

import indigo
import os
import sys
import json
from threading import Event
from threading import Thread
from Queue import Queue
from tplink_smartplug import tplink_smartplug
import time
import inspect
import logging
import pdb
# import threading

# Note the "indigo" module is automatically imported and made available inside
# our global name space by the host process.

class myThread(Thread):
	def __init__(self, logger, dev, pluginPrefs):
		Thread.__init__(self)
		self.logger = logger
		func = inspect.stack()[0][3]
		self.logger.debug(u"%s: called for: %s." % (func, dev.name))
		self.dev = dev
		self.name = dev.name
		self.lastState = 1
		self.lastMultiPlugOnCount = 0
		self.pluginPrefs = pluginPrefs

		self.outlets = {}
		outletNum = dev.pluginProps['outletNum']
		self.logger.debug(u"outlet num: %s multiPlug %s" % (dev.name, self.dev.pluginProps['multiPlug']))

		# Here we deal with multi plug devices. We will just store the entire device in a dictionary indexed by the outlet number
		self.multiPlug = dev.pluginProps['multiPlug']
		if self.multiPlug:
			self.onPoll = int(self.pluginPrefs['onPoll'])
			self.offPoll = int(self.pluginPrefs['offPoll'])
			self.outlets[outletNum] = self.dev
			self.logger.debug(u"outlet dict =%s" % (self.outlets))					
		else:
			self.onPoll = int(dev.pluginProps['onPoll'])
			self.offPoll = int(dev.pluginProps['offPoll'])
			
		# self.configured = self.dev.configured

		self.onOffState = dev.states['onOffState']
		if self.onOffState:
			self.pollFreq = self.onPoll
		else:
			self.pollFreq = self.offPoll
		self.deviceId = dev.pluginProps['deviceId']
		self.changed = False
		# self.logger.debug(u"Initializing: %s:%s" % (dev.name, self.offPoll))
		self._is_running = True
		self.start()

	def interupt(self, state=None, dev=None, action=None):
		func = inspect.stack()[0][3]
		self.logger.debug(u"%s: called for %s with action=%s, state=%s" % (func, self.dev.id, action, state))

		# self.logger.debug(u"%s: Before, poll freq is %s" % (dev.name, self.pollFreq))
		if action == 'state' and state:
			if self.multiPlug:
				self.pollFreq = self.pluginPrefs['onPoll']
			else:
				self.pollFreq = self.dev.pluginProps['onPoll']
		elif action == 'state' and not state:
			if self.multiPlug:
				self.pollFreq = self.pluginPrefs['offPoll']
			else:
				self.pollFreq = self.dev.pluginProps['offPoll']
		elif action == 'dev':
			outletNum = dev.pluginProps['outletNum']
			self.outlets[outletNum] = dev
			self.dev = dev
		elif action == 'status':
			self.dev = dev
		else:
			self.logger.error(u"%s: called for %s with action=%s, state=%s" % (func, self.dev.id, action, state))
			return

		time.sleep(0.5)
		self.changed = True
		return(True)
			
	def stop(self):
		self.logger.debug(u"from: %s  time to quit" % (self.name))
		self._is_running = False

	def run(self):
		func = inspect.stack()[0][3]
		self.logger.debug(u"%s: called for: %s." % (func, self.dev))
		dev = self.dev
		devType = dev.deviceTypeId
		energyCapable = dev.pluginProps['energyCapable']

		# if dev.address == "":
		# 	devAddr = dev.pluginProps['addressManual']
		# else:
		devAddr = dev.address
		devPort = 9999
		self.logger.debug(u"%s multiPlug is %s" % (dev.name, self.multiPlug))
		
		self.logger.debug(u"Starting data refresh for %s :%s:%s: with %s" % (dev.name, devType, devAddr, self.offPoll))

		tplink_dev_states = tplink_smartplug(devAddr, devPort)
		lastState = 0
		lastStateMulti = {}
		error_counter = 2

		while True:
			try:
				self.logger.debug(u"%s: Starting polling loop with interval %s\n", self.name, self.pollFreq)
				result = tplink_dev_states.send('info')
				data = json.loads(result)
				self.logger.debug(u"%s: finished state data collection with %s" % (self.name, data))

				# Check if we got an error back
				if 'error' in data:
					self.logger.error(u"Polling error for device \"%s\": %s" % (self.name, data['error']))
				else:
					# First, we check the onOff state of each plug
					if self.multiPlug:
						self.logger.debug(u"%s: entered multiPlug state block" % (self.name))
						multiPlugOnCount = 0
						elements = data['system']['get_sysinfo']['children']

						self.logger.debug(u"%s: Elements %s" % (self.name, elements))
						for element in elements:
							multiPlugOnCount += int(element['state'])
							outletName = element['alias']
							outletNum = element['id'][-2:]
							# self.logger.error(u"%s: on count = %s last on count was %s for %s" % (func, multiPlugOnCount, self.lastMultiPlugOnCount, self.dev.address))
							devState = bool(element['state'])
							self.logger.debug(u"%s: Starting new element... id=%s, outletNum=%s, element=%s" % (outletName, element['id'], outletNum, element))
							for outlet in self.outlets:
								self.logger.debug(u"%s: Outlet=%s and id=%s id=%s" % (outletName, outlet, element['id'], element['id'][-2:]))
								if outlet == outletNum: #element['id'][-2:] == outlet:
									self.logger.debug(u"%s: YES %s" % (outletName, outletNum))
									# self.logger.debug(u"%s: indigo device onOffState is %s, actual is %s", outletName, lastStateMulti[outletNum], devState)
									if not outletNum in lastStateMulti:
										lastStateMulti[outletNum] = 2

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
										self.logger.debug(u"%s: Polling found %s set to %s", func, self.name, logState)



						# Before we go, check to see if we need to update the polling interval
						if self.lastMultiPlugOnCount == 0 and multiPlugOnCount > 0:
							# we have transitioned from all plugs off to at least one plug on
							self.logger.debug(u"%s: Changing polling interval to on for %s" % (func, self.dev.address))
							self.interupt(state=True, action='state')
						elif self.lastMultiPlugOnCount > 0 and multiPlugOnCount == 0:
							# we have transitioned from at least one plug on to all plugs off
							self.logger.debug(u"%s: Changing polling interval to on for %s" % (func, self.dev.address))
							self.interupt(state=False, action='state')
						self.lastMultiPlugOnCount = multiPlugOnCount
						
					else:  # we have a single outlet device
						# self.logger.debug(u"%s: Got Here 0 with %s" % (self.name, data))
						devState = data['system']['get_sysinfo']['relay_state']
						self.logger.debug(u"%s: single outlet device 1 state= %s, lastState=%s" % (self.name, devState, lastState))
						
						if devState != lastState:
							if devState:
								state = True
								logState = "On"
								self.interupt(state=True, action='state')
							else:
								state = False
								logState = "Off"
								self.interupt(state=False, action='state')
							lastState = devState	

							self.logger.debug(u"%s: 2 state= %s, lastState=%s : %s" % (self.name, devState, lastState, state))

							alias = data['system']['get_sysinfo']['alias']
							rssi = data['system']['get_sysinfo']['rssi']
							state_update_list = [
								{'key':'onOffState', 'value':state},
								{'key':'rssi', 'value':rssi},
								{'key':'alias', 'value':alias}
								]
							dev.updateStatesOnServer(state_update_list)
							self.logger.debug(u"%s: Polling found %s set to %s", func, self.name, logState)
							self.logger.debug(u"%s: %s, updated state on server to %s (%s, %s)", func, self.name, state, rssi, alias)
					
					self.logger.debug(u"%s: finished state update %s" % (self.name, data))

					# Now we start looking for energy data... if the plug is capable
					if energyCapable:
						if self.multiPlug:
							self.logger.debug(u"Starting energy query for devices at %s", devAddr)
							deviceId = self.deviceId

							for element in elements:
								# self.logger.debug(u"Starting energy update for %s: id=%s, element:%s" % (self.name, element['id'], element))
								childId = element['id'][-2:]
								if childId in self.outlets:
									indigoDevice = self.outlets[childId]
									self.logger.debug(u"Found entry for outlet %s devId is %s", childId, indigoDevice.id)

									state = element['state']
									self.logger.debug(u"Ready to check energy for outlet %s, state %s" % (childId, state))
									if bool(state):
										self.logger.debug(u"Getting energy for %s %s %s %s state %s" % (devAddr, devPort, deviceId, childId, state))
										tplink_dev_energy = tplink_smartplug (devAddr, devPort, deviceId, childId)
										result = tplink_dev_energy.send('energy')
										data = json.loads(result)
										self.logger.debug("%s: data=%s" % (self.name, data))
										curWatts = data['emeter']['get_realtime']['power_mw']/1000
										curVolts = data['emeter']['get_realtime']['voltage_mv']/1000
										curAmps  = data['emeter']['get_realtime']['current_ma']/1000
										totWatts = data['emeter']['get_realtime']['total_wh']/1000

										state_update_list = [
											{'key':'curWatts', 'value':curWatts},
											{'key':'totWatts', 'value':totWatts},
											{'key':'curVolts', 'value':curVolts},
											{'key':'curAmps', 'value':curAmps},
											{'key':"curEnergyLevel", 'value':curWatts, 'uiValue':str(curWatts) + " w"},
											{'key':'accumEnergyTotal', 'value':totWatts, 'uiValue':str(totWatts) + " kwh"}
											]
										indigoDevice.updateStatesOnServer(state_update_list)

									else:
										self.logger.debug("Outlet %s:%s was off. No data collected", self.name, childId)
										state_update_list = [
											{'key':'curWatts', 'value':0},
											{'key':'curVolts', 'value':0},
											{'key':'curAmps', 'value':0},
											{'key':"curEnergyLevel", 'value':0, 'uiValue':str(0) + " w"}
											]
										indigoDevice.updateStatesOnServer(state_update_list)
									
							else:
								self.logger.debug(u"Outlet %s: outlet=%s not configured. No energy usage collected" % (self.name, childId))
							
						else:    # we have a single outlet device
							tplink_dev_energy = tplink_smartplug (devAddr, devPort, None, None)
							result = tplink_dev_energy.send('energy')
							data = json.loads(result)
							self.logger.debug("Received result: |%s|" % (result))
							curWatts = data['emeter']['get_realtime']['power_mw']/1000
							curVolts = data['emeter']['get_realtime']['voltage_mv']/1000
							curAmps  = data['emeter']['get_realtime']['current_ma']/1000
							totWatts = data['emeter']['get_realtime']['total_wh']/1000

							state_update_list = [
								{'key':'curWatts', 'value':curWatts},
								{'key':'totWatts', 'value':totWatts},
								{'key':'curEnergyLevel', 'value':curWatts, 'uiValue':str(curWatts) + " w"},
								{'key':'accumEnergyTotal', 'value':totWatts, 'uiValue':str(totWatts) + " kwh"},
								{'key':'curVolts', 'value':curVolts},
								{'key':'curAmps', 'value':curAmps}
								]
							dev.updateStatesOnServer(state_update_list)

							self.logger.debug("Received results for %s @ %s secs: %s, %s, %s: change = %s" % (dev.name, self.pollFreq, curWatts, curVolts, curAmps, self.changed))
				indigo.debugger()
				self.logger.debug(u"%s: In the loop - finished data gathering. Will now pause for %s" % (self.name, self.pollFreq))
				pTime = 0.5
				cTime = float(self.pollFreq)
			
				error_counter = 0
				while cTime > 0:
					# self.logger.debug(u"%s: Looping Timer = %s", self.name, cTime)
					if self.changed or not self._is_running:
						# self.logger.debug(u"Device change for %s" % (self.name))
						self.changed = False
						cTime = 0
					else:
						# self.logger.debug(u"starting mini sleep for %6.4f" % (pTime))
						time.sleep(pTime)
						cTime = cTime - pTime
						# self.logger.debug(u"Timer = %6.4f" % (cTime))

					# self.logger.debug(u"Timer loop finished for %s", self.name)
				if not self._is_running:
					break
				
				self.logger.debug(u"%s: Back in the loop - timer ended" % (self.name))

			except Exception as e:
				if error_counter == 10:
					self.logger.error("Unable to update %s: after 10 attempts. Polling for this device will now shut down. (%s)" % (self.name, str(e)))
					return
				else:
					error_counter += 1
					self.logger.error("Error attempting to update %s: %s. Will try again in %s seconds" % (self.name, str(e), self.pollFreq))
				

