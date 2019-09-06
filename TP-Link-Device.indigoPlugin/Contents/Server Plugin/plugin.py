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
# import threading
from tplink_smartplug import tplink_smartplug
import time
import inspect
import logging
import pdb
from tpl_polling import myThread

# Note the "indigo" module is automatically imported and made available inside
# our global name space by the host process.

""" class myThread(Thread):
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
		error_counter = 0
		pollErrors = 0

		while True:
			try:
				self.logger.debug(u"%s: Starting polling loop with interval %s\n", self.name, self.pollFreq)
				result = tplink_dev_states.send('info')
				data = json.loads(result)
				self.logger.debug(u"%s: finished state data collection with %s" % (self.name, data))

				# Check if we got an error back
				if 'error' in data:
					if pollErrors < 10:
						self.logger.error(u"Polling error for device \"%s\": %s" % (self.name, data['error']))
						pollErrors += 1
					else:
						self.logger.error(u"Unable to polling device \"%s\": %s after 10 attempts. Polling for this device will now shut down." % (self.name, data['error']))
						self.stop()
				else:
					# First, we check the onOff state of each plug
					pollErrors = 0
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
										lastStateMulti[outletNum] = 0

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

										state_update_list = [
											{'key':'curWatts', 'value':curWatts},
											{'key':'curVolts', 'value':curVolts},
											{'key':'curAmps', 'value':curAmps},
											{'key':"curEnergyLevel", 'value':curWatts, 'uiValue':str(curWatts) + " w"}
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

							state_update_list = [
								{'key':'curWatts', 'value':curWatts},
								{'key':'curEnergyLevel', 'value':curWatts, 'uiValue':str(curWatts) + " w"},
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
					self.logger.error("Error attempting to update %s: %s. Will try again in %s seconds" % (self.name, str(e), self.pollFreq)) """
				

################################################################################
class Plugin(indigo.PluginBase):
	########################################
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		# self.indigo_log_handler.setFormatter(logging.Formatter('%(levelname)-10s\t%(name)s.%(funcName)-28s %(msg)s'))
		self.debug = pluginPrefs.get("showDebugInfo", False)

		self.offUpFreq = 30   # interval in secs between updates when the plug is off should be <= 30
		self.onUpFreq  =  2   # interval in secs between updates when the plug is on
		self.logOnOff = pluginPrefs.get('logOnOff', False)
		self.updateFreq = self.offUpFreq
		self.tpThreads = {}
		self.tpDevices = {}
		self.tpQueue = Queue()
		self.deviceSearchResults = {}

	########################################
	def startup(self):
		self.logger.debug(u"startup called")

	def shutdown(self):
		self.logger.debug(u"shutdown called")

	########################################
	# Validation handlers
	######################
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		func = inspect.stack()[0][3]
		self.logger.debug(u"%s: called with typeId=%s, devId=%s, and valuesDict=%s.", func, typeId, devId, valuesDict)
		errorsDict = indigo.Dict()

		# if not valuesDict['outletNum'] or valuesDict['outletNum'] == None or valuesDict['outletNum'] == "":
		# 	valuesDict['outletNum']   = "00"
		# 	self.logger.debug(u"%s: GOT HERE 1", func)

		if not valuesDict['childId'] or valuesDict['childId'] == None or valuesDict['childId'] == "":
			valuesDict['childId']   = str(valuesDict['deviceId']) + valuesDict['outletNum']
		self.logger.debug(u"%s: left with typeId=%s, devId=%s, and valuesDict=%s.", func, typeId, devId, valuesDict)


		if not valuesDict['energyCapable']:
			valuesDict['SupportsEnergyMeter'] = False
			valuesDict['SupportsEnergyMeterCurPower'] = False

		# cmd = "/sbin/ping -c1 -t5 -q " + valuesDict['address'] + " >/dev/null 2>&1" 
		# response = os.system(cmd)
		# self.logger.info("Response: %s " % (response))
		
		# #and then check the response...
		# if int(response) != 0:
		# 	self.logger.info(u"%s is not reachable" % valuesDict['address'])
		# 	errorsDict["address"] = "Host unreachable"
		# 	return (False, valuesDict, errorsDict)
			
		# If we have been asked to re-initialize this device...
		if ('initialize' in valuesDict and valuesDict['initialize']):
			self.initializeDev(valuesDict)
		valuesDict['newDev'] = False
		valuesDict['initialize'] = False
		self.logger.debug(u"%s: GOT HERE 2", func)
		return (True, valuesDict, errorsDict)

	def validatePrefsConfigUi(self, valuesDict):
		# this is where we will detect a change in polling settings so we can update the polling threads
		# self.logger.info(u"validatePrefsConfigUi called with %s" % valuesDict)
		return (True, valuesDict)

	########################################
	# Starting and stopping devices
	######################
	def deviceStartComm(self, dev):
		func = inspect.stack()[0][3]
		self.logger.debug(u"%s: called for: %s@%s.", func, dev.name, dev.address)
		# Called for each device on startup
		# get some data for local use from the device
		name      = dev.name
		address   = dev.address
		multiPlug = dev.pluginProps['multiPlug']
		if multiPlug:
			devPoll = self.pluginPrefs['devPoll']
		else:
			devPoll = dev.pluginProps['devPoll']

		# Update the model display column
		dev.model = dev.pluginProps['model']
		dev.description = "plug " + str(int(dev.pluginProps['outletNum'])+1)
		dev.replaceOnServer()

		# self.logger.debug("deviceStartComn starting %s" % (name), type="TP-Link", isError=False)
		if name in self.tpThreads:
			self.logger.debug("deviceStartComm error: Thread exists for %s , %s- %s" % (name, address, self.tpThreads[dev.name]))
			# self.tpThreads[address].interupt(None)
		elif not devPoll:
			self.logger.info("Polling thread not started for device  %s, %s. It has polling disabled", name, address)
		elif devPoll:
			# We start one thread per device ip address
			if address not in self.tpThreads:
				# Create a thread
				self.process = myThread(self.logger, dev, self.pluginPrefs)
				self.tpThreads[address] = self.process
				self.logger.debug("Polling thread started for device %s, %s", name, address)
				# ... and save a copy of the device that created this thread
				self.tpDevices[address] = dev
			elif address in self.tpThreads:
				self.logger.debug(u"deviceStartComm IN thread update %s, %s", name, address)
				myDeviceId  = dev.pluginProps['deviceId']
				if not myDeviceId:
					self.logger.error("%s: Oops.No deviceId for %s", name, address)
				else:
					self.logger.debug("%s: Already had deviceId  %s", name, myDeviceId)

				# self.logger.info(u"deviceStartComm related to device %s, %s", deviceId, "foio")
				# Since a thread already exists, this is probably a multiPlug
				self.tpThreads[address].interupt(dev=dev, action='dev')
			else:
				# something is horribly wrong
				self.logger.error(u"deviceStartComm error in thread creation %s, %s", name, address)

	def deviceStopComm(self, dev):
		# Called when communication with the hardware should be shutdown.
		# get some data for local use from the device
		name      = dev.name
		address   = dev.address

		self.logger.debug(u"deviceStopComn entered %s, %s" % (name, address))
		if address in self.tpThreads:  # We don't want to waste time if a polling thread was never started
			self.logger.debug("deviceStopComn ending %s, %s" % (name, address))
			self.tpThreads[address].stop()
			del self.tpThreads[address]

	########################################
	########################################
	def initializeDev(self, valuesDict):
		func = inspect.stack()[0][3]
		self.logger.debug(u"%s: called for: %s." % (func, valuesDict))
		# if valuesDict['address'] == "":
		# 	valuesDict['address'] = valuesDict['addressManual']
		self.logger.debug(u"%s: 2 called for: %s." % (func, valuesDict))
		devAddr = valuesDict['address']
		devName = "new device at " + devAddr
		devPort = 9999
		deviceId = None
		childId = None
		tplink_dev = tplink_smartplug (devAddr, devPort, deviceId, childId)
		result = tplink_dev.send('info')
		self.deviceSearchResults[devAddr] = result

		self.logger.debug(u"%s: InitializeDev 3 got %s" % (devName, result))
		data = json.loads(result)
		self.deviceSearchResults[devAddr] = data
		self.logger.debug(u"%s: InitializeDev 4 got %s" % (devName, data))
		valuesDict['deviceId'] = data['system']['get_sysinfo']['deviceId']
		valuesDict['childId'] = str(deviceId) + valuesDict['outletNum']
		valuesDict['mac'] = data['system']['get_sysinfo']['mac']
		valuesDict['model'] = data['system']['get_sysinfo']['model']

		if 'child_num' in data['system']['get_sysinfo']:
			self.logger.debug(u"%s: %s has child_id", func, devName)
			valuesDict['multiPlug'] = True
			valuesDict['outletsAvailable'] = data['system']['get_sysinfo']['child_num']
		else:
			self.logger.debug(u"%s: %s does not have child_id", func, devName)
			valuesDict['multiPlug'] = False
			valuesDict['outletsAvailable'] = 1

		if 'ENE' in data['system']['get_sysinfo']['feature']:
			valuesDict['energyCapable'] = True
		else:
			valuesDict['energyCapable'] = False

		valuesDict['initialize'] = False

		return valuesDict

	########################################
	# Relay Action callback
	######################
	def actionControlDimmerRelay(self, action, dev):
		func = inspect.stack()[0][3]
		self.logger.debug(u"%s: called with: %s for %s." % (func, action, dev.name))
		addr = dev.address
		port = 9999
		if dev.pluginProps['multiPlug']:
			deviceId = dev.pluginProps['deviceId']
			childId = dev.pluginProps['outletNum']
		else:
			deviceId = None
			childId = None

		tplink_dev = tplink_smartplug (addr, port, deviceId, childId)
		self.logger.debug(u"%s: tplink_dev set with: %s, %s, %s, %s." % (func, addr, port, deviceId, childId))

		###### TURN ON ######
		if action.deviceAction == indigo.kDimmerRelayAction.TurnOn:
			cmd = "on"
			if dev.pluginProps['devPoll']:
				self.tpThreads[dev.address].interupt(state=True, action='state')
		###### TURN OFF ######
		elif action.deviceAction == indigo.kDimmerRelayAction.TurnOff:
			cmd = "off"
			if dev.pluginProps['devPoll']:
				self.tpThreads[dev.address].interupt(state=False, action='state')
		###### TOGGLE ######
		elif action.deviceAction == indigo.kDimmerRelayAction.Toggle:
			if dev.onState:
				cmd = "off"
				if dev.pluginProps['devPoll']:
					self.tpThreads[dev.address].interupt(state=False, action='state')
			else:
				cmd = "on"
				if dev.pluginProps['devPoll']:
					self.tpThreads[dev.address].interupt(state=True, action='state')
		else:
			self.logger.error("Unknown command: {}".format(indigo.kDimmerRelayAction))
			return

		result = tplink_dev.send(cmd)
		sendSuccess = False
		try:
			result_dict = json.loads(result)
			error_code = result_dict["system"]["set_relay_state"]["err_code"]
			if error_code == 0:
				sendSuccess = True
			else:
				self.logger.error("turn {} command failed (error code: {})".format(cmd, error_code))
		except:
			pass
		indigo.debugger()
		if sendSuccess:
			# If success then log that the command was successfully sent.
			self.logger.debug(u'sent "{}" {}'.format(dev.name, cmd))

			# And then tell the Indigo Server to update the state.
			if cmd == "on":
				state = True
			else:
				state = False
			dev.updateStateOnServer(key="onOffState", value=state)
			if self.logOnOff:
				self.logger.info(u"%s set to %s", dev.name, cmd)
			#self.tpThreads[dev.address].interupt(dev=dev, action='status')
			
		else:
			# Else log failure but do NOT update state on Indigo Server.
			self.logger.error(u'send "{}" {} failed with result "{}"'.format(dev.name, cmd, result))

	########################################
	# General Action callback
	######################
	def actionControlGeneral(self, action, dev):
		if action.deviceAction == indigo.kDeviceGeneralAction.RequestStatus:
			self.getInfo(action, dev)
		else:
			self.logger.error(u'unsupported Action callback "{}" {}'.format(dev.name, action))

	########################################
	# Custom Plugin Action callbacks (defined in Actions.xml)
	######################

	# The 'status' callback
	def getInfo(self, pluginAction, dev):
		func = inspect.stack()[0][3]
		self.logger.debug(u"%s: called for: %s." % (func, dev.name))
		address = dev.address

		try:
			self.tpThreads[address].interupt(dev=dev, action='status')
			self.logger.info("%s: Device reachable and states updated.", dev.name)
		except Exception as e:
			self.logger.error("%s: Device not reachable and states could not be updated. %s", dev.name, str(e))

		return

	########################################
	# General Action callback
	######################
	def actionControlUniversal(self, action, dev):
		###### ENERGY UPDATE ######
		if action.deviceAction == indigo.kUniversalAction.EnergyUpdate:
			if dev.pluginProps['energyCapable'] == True :
				self.logger.info("Energy Status Update Requested for " + dev.name)
				self.getInfo("", dev)
			else: self.logger.info("Device " + dev.name + " not energy capable.")

		###### STATUS REQUEST ######
		elif action.deviceAction == indigo.kUniversalAction.RequestStatus:
			self.getInfo("", dev)

	########################################
	# Device ConfigUI Callbacks
	######################
	def getTpDevice(self, filter="", valuesDict=None, typeId="", targetId=0):
		func = inspect.stack()[0][3]
		self.logger.debug(u"%s: called for: %s, %s, %s, %s." % (func, filter, typeId, targetId, valuesDict))

		# if targetId in indigo.devices:
		# 	self.logger.error(u"%s: found %s %s" % (func, targetId, indigo.devices[targetId].configured))
		# else:
		# 	self.logger.error(u"%s: not found %s" % (func, targetId))
		deviceArray = []
		if indigo.devices[targetId].configured:
			return deviceArray
		else:
			tplink_discover = tplink_smartplug(None, None)
			self.deviceSearchResults = tplink_discover.send('discover')
			self.logger.debug(u"%s: received %s" % (func, self.deviceSearchResults))

			for address in self.deviceSearchResults:
				model = self.deviceSearchResults[address]['system']['get_sysinfo']['model']
				menuText = model + " @ " + address
				menuEntry = (address, menuText)
				deviceArray.append(menuEntry)
			menuEntry = ('manual', 'manual entry')
			deviceArray.append(menuEntry)

			return deviceArray

	def selectTpDevice(self, valuesDict, typeId, devId):
		func = inspect.stack()[0][3]
		self.logger.debug(u"%s: called for: %s, %s, %s." % (func, typeId, devId, valuesDict))

		if valuesDict['addressSelect'] != 'manual': 
			self.logger.debug("%s: %s -- %s\n" % (func, valuesDict['addressSelect'], valuesDict['manualAddressResponse']))
			valuesDict['address'] = valuesDict['addressSelect']
			address = valuesDict['address']
			valuesDict['deviceId']  = self.deviceSearchResults[address]['system']['get_sysinfo']['deviceId']
			valuesDict['childId']   = str(valuesDict['deviceId']) + valuesDict['outletNum']
			valuesDict['mac']       = self.deviceSearchResults[address]['system']['get_sysinfo']['mac']
			valuesDict['model']     = self.deviceSearchResults[address]['system']['get_sysinfo']['model']
			valuesDict['displayOk'] = True
			valuesDict['displayManAddress'] = True
			
		elif valuesDict['manualAddressResponse']:
			self.logger.debug("%s: %s -- %s\n" % (func, valuesDict['address'], valuesDict['manualAddressResponse']))
			valuesDict = self.initializeDev(valuesDict)
			valuesDict['displayOk'] = True
			valuesDict['displayManAddressButton'] = False

		elif valuesDict['addressSelect'] == 'manual':
			valuesDict['displayManAddress'] = True
			valuesDict['displayManAddressButton'] = True
			valuesDict['manualAddressResponse'] = True
			return valuesDict

		address = valuesDict['address']
		if 'child_num' in self.deviceSearchResults[address]['system']['get_sysinfo']:
			self.logger.debug(u"%s: %s has child_id", func, address)
			valuesDict['multiPlug'] = True
			valuesDict['outletsAvailable'] = self.deviceSearchResults[address]['system']['get_sysinfo']['child_num']
		else:
			self.logger.debug(u"%s: %s does not have child_id", func, address)
			valuesDict['multiPlug'] = False
			valuesDict['outletsAvailable'] = 1
			valuesDict['outletNum'] = "00"

		if 'ENE' in self.deviceSearchResults[address]['system']['get_sysinfo']['feature']:
			valuesDict['energyCapable'] = True
		else:
			valuesDict['energyCapable'] = False

		self.logger.debug("returning valuesDict: %s" % valuesDict)

		return valuesDict

	def selectTpOutlet(self, filter="", valuesDict=None, typeId="", targetId=0):
		func = inspect.stack()[0][3]
		self.logger.debug(u"%s: called for: %s, %s, %s, %s." % (func, filter, typeId, targetId, valuesDict))

		outletArray = []
		
		if 'newDev' in valuesDict and 'address' in valuesDict:
			address = valuesDict['address']
			if address in self.deviceSearchResults:
				self.logger.debug(u"%s:1 in dictoutlets avail %s" % (func, valuesDict['outletsAvailable']))
				# if valuesDict['addressSelect'] == 'manual':
				self.logger.debug(u"%s:2 in dictoutlets avail %s" % (func, valuesDict['outletsAvailable']))
				if 'child_num' in self.deviceSearchResults[address]['system']['get_sysinfo']:
					self.logger.debug(u"%s:3 in dictoutlets avail %s" % (func, valuesDict['outletsAvailable']))
					maxOutlet = int(self.deviceSearchResults[address]['system']['get_sysinfo']['child_num'])+1
					address = valuesDict['address']
				
					for outlet in range(1, maxOutlet):
						internalOutlet = int(outlet)-1
						menuEntry = (str(internalOutlet).zfill(2), outlet)
						outletArray.append(menuEntry)
				else:	
					self.logger.debug(u"%s: not in dict outlets avail %s" % (func, valuesDict['outletsAvailable']))
					for outlet in range(0, int(valuesDict['outletsAvailable'])):
						self.logger.debug(u"%s: loop %s" % (func, outlet))
						internalOutlet = int(outlet)
						menuEntry = (str(internalOutlet).zfill(2), outlet+1)
						outletArray.append(menuEntry)

			elif valuesDict['outletsAvailable'] > 0:
				self.logger.debug(u"%s: outlets 2 avail %s" % (func, valuesDict['outletsAvailable']))
				for outlet in range(0, int(valuesDict['outletsAvailable'])):
					self.logger.debug(u"%s: loop %s" % (func, outlet))
					internalOutlet = int(outlet)
					menuEntry = (str(internalOutlet).zfill(2), outlet+1)
					outletArray.append(menuEntry)


		self.logger.debug(u"%s: returned: OA=%s" % (func, outletArray))
		return outletArray

	########################################
	# Menu callbacks defined in MenuItems.xml
	########################################
	def toggleDebugging(self):
		if self.debug:
			self.logger.info("Turning off debug logging")
			self.pluginPrefs["showDebugInfo"] = False
		else:
			self.logger.info("Turning on debug logging")
			self.pluginPrefs["showDebugInfo"] = True
		self.debug = not self.debug


	########################################
	# Device reporting
	def dumpDeviceInfo(self, valuesDict, b):
		func = inspect.stack()[0][3]
		self.logger.debug("%s: called with a=%s and b=%s", func, str(valuesDict), b)

		return(True)	
	
	def displayButtonPressed(self, valuesDict, bar):
		func = inspect.stack()[0][3]
		self.logger.debug("%s: called with valuesDict=%s", func, valuesDict)

		devNumber = int(valuesDict['targetDevice'])
		dev = indigo.devices[devNumber]
		props = dev.pluginProps
		self.logger.debug("%s: pluginPropsr=%s", func, props)
	
		valuesDict['address']       = props['address']
		valuesDict['devPoll']       = props['devPoll']
		valuesDict['deviceId']      = props['deviceId']
		valuesDict['energyCapable'] = props['energyCapable']
		valuesDict['mac']           = props['mac']
		valuesDict['model']         = props['model']
		valuesDict['multiPlug']     = props['multiPlug']
		valuesDict['offPoll']       = props['offPoll']
		valuesDict['onPoll']        = props['onPoll']
		valuesDict['outletNum']     = int(props['outletNum'])+1
		valuesDict['alias']         = dev.states['alias']
		valuesDict['displayOk']     = True

		self.logger.debug("Device info = %s", valuesDict)

		return(valuesDict)

	def printToLogPressed(self, valuesDict, bar):
		func = inspect.stack()[0][3]
		self.logger.debug("%s: called with foo=%s bar=%s", func, valuesDict, bar)
		devNumber = int(valuesDict['targetDevice'])
		dev = indigo.devices[devNumber]
		tabs = "\t\t\t\t"
		report = "Tp-Link plugin device report" + \
			tabs + "Indigo Device Name:\t" + dev.name + "\n" + \
			tabs + "IP Address:\t\t\t" + valuesDict['address'] + "\n" + \
			tabs + "Device ID:\t\t\t" + valuesDict['deviceId'] + "\n" + \
			tabs + "Alias:\t\t\t\t" + valuesDict['alias'] + "\n" + \
			tabs + "Outlet Number:\t\t" + valuesDict['outletNum'] + "\n" + \
			tabs + "Model:\t\t\t\t" + valuesDict['model'] + "\n" + \
			tabs + "On state polling freq:\t" + valuesDict['onPoll'] + "\n" + \
			tabs + "Off state polling freq:\t" + valuesDict['offPoll'] + "\n" + \
			tabs + "MAC Address:\t\t\t" + valuesDict['mac'] + "\n" + \
			tabs + "Polling enabled:\t\t" + str(valuesDict['devPoll']) + "\n" + \
			tabs + "Multiple Outlets:\t\t" + str(valuesDict['multiPlug']) + "\n" + \
			tabs + "Energy reporting:\t\t" + str(valuesDict['energyCapable']) + "\n"
			
		self.logger.info("%s", report)

		return

	