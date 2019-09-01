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
import threading
from tplink_smartplug import tplink_smartplug
import time
import inspect

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
		else:
			self.logger.error(u"%s: called for %s with action=%s, state=%s" % (func, self.dev.id, action, state))
			return

		self.changed = True
		return
			
	def stop(self):
		self.logger.debug(u"from: %s  time to quit" % (self.name))
		self._is_running = False

	def run(self):
		func = inspect.stack()[0][3]
		self.logger.debug(u"%s: called for: %s." % (func, self.dev.name))
		dev = self.dev
		devType = dev.deviceTypeId
		devAddr = dev.address
		devPort = 9999
		self.logger.debug(u"%s multiPlug is %s" % (dev.name, self.multiPlug))
		
		self.logger.debug(u"Starting data refresh for %s :%s:%s: with %s" % (dev.name, devType, devAddr, self.offPoll))

		tplink_dev_states = tplink_smartplug(devAddr, devPort)

		while True:
			self.logger.debug(u"%s: Starting polling loop with interval %s\n", self.name, self.pollFreq)
			try:
				result = tplink_dev_states.send('info')
			except Exception as e:
				self.logger.error("Fatal error attempting to update %s: %s" % (self.name, str(e)))
				return
			data = json.loads(result)
			self.logger.debug(u"%s: finished state data collection with %s" % (self.name, data))
		
			if self.multiPlug:
				self.logger.debug(u"%s: entered multiPlug state block" % (self.name))
				elements = data['system']['get_sysinfo']['children']
				self.logger.debug(u"%s: Elements %s" % (self.name, elements))
				
				for element in elements:
					devState = bool(element['state'])
					self.logger.debug(u"%s: id=%s, alias=%s, element:%s" % (self.name, element['id'], element['alias'], element))
					for outlet in self.outlets:
						self.logger.debug(u"%s: Got Here -1x with %s and %s" % (self.name, outlet, element['id'][-2:]))
						if element['id'][-2:] == outlet:
							# self.logger.debug(u"%s: YES %s" % (self.name, self.outlets[outlet].id))
							self.logger.debug(u"%s: indigo device onOffState is %s, actual is %s", self.name, self.lastState, devState)
							if devState != self.lastState:
								if devState:
									state = "on"
									self.interupt(state=True, action='state')
								else:
									state = "off"
									self.interupt(state=False, action='state')	
								self.lastState = devState								

								alias = element['alias']
								alias = element['alias']
								state_update_list = [
									{'key':'onOffState', 'value':devState},
									{'key':'alias', 'value':alias}
									]
								alias = element['alias']
								self.outlets[outlet].updateStatesOnServer(state_update_list)
								
			else:
				# self.logger.debug(u"%s: Got Here 0 with %s" % (self.name, data))
				devState = data['system']['get_sysinfo']['relay_state']
				self.logger.debug(u"%s: state= %s" % (self.name, devState))
				
				if devState != self.lastState:
					if devState:
						state = "on"
						self.interupt(state=True, action='state')
					else:
						state = "off"
						self.interupt(state=False, action='state')
					self.lastState = devState	

					alias = data['system']['get_sysinfo']['alias']
					state_update_list = [
						{'key':'onOffState', 'value':state},
						{'key':'alias', 'value':alias}
						]
					dev.updateStatesOnServer(state_update_list)
					# dev.updateStateOnServer("onOffState", state)
			
			self.logger.debug(u"%s: finished state update %s" % (self.name, data))

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
								{'key':'curAmps', 'value':curAmps}
								]
							indigoDevice.updateStatesOnServer(state_update_list)

						else:
							# self.logger.error(u"GOT HERE")
							self.logger.debug("Outlet %s:%s was off. No data collected", self.name, childId)
							state_update_list = [
								{'key':'curWatts', 'value':0},
								{'key':'curVolts', 'value':0},
								{'key':'curAmps', 'value':0}
								]
							indigoDevice.updateStatesOnServer(state_update_list)
						
				else:
					self.logger.debug(u"Outlet %s: outlet=%s not configured. No energy usage collected" % (self.name, childId))

				
			else:    # devType == "hs110":
				tplink_dev_energy = tplink_smartplug (devAddr, devPort, None, None)
				result = tplink_dev_energy.send('energy')
				data = json.loads(result)
				self.logger.debug("Received result: |%s|" % (result))
				curWatts = data['emeter']['get_realtime']['power_mw']/1000
				curVolts = data['emeter']['get_realtime']['voltage_mv']/1000
				curAmps  = data['emeter']['get_realtime']['current_ma']/1000

				state_update_list = [
					{'key':'curWatts', 'value':curWatts},
					{'key':'curEnergyLevel', 'value':curWatts},
					# {'key':'energyAccumTotal', 'value':1000},
					# {'key':'energyAccumBaseTime', 'value':curWatts},
					# {'key':'energyAccumTimeDelta', 'value':99},
					{'key':'curVolts', 'value':curVolts},
					{'key':'curAmps', 'value':curAmps}
					]
				dev.updateStatesOnServer(state_update_list)

				self.logger.info("Received results for %s @ %s secs: %s, %s, %s: change = %s" % (dev.name, self.pollFreq, curWatts, curVolts, curAmps, self.changed))
			
			self.logger.debug(u"%s: In the loop - finished data gathering. Will now pause for %s" % (self.name, self.pollFreq))
			pTime = 0.5
			cTime = float(self.pollFreq)
			
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


################################################################################
class Plugin(indigo.PluginBase):
	########################################
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		self.debug = pluginPrefs.get("showDebugInfo", False)

		self.offUpFreq = 30   # interval in secs between updates when the plug is off should be <= 30
		self.onUpFreq  =  2   # interval in secs between updates when the plug is on
		self.updateFreq = self.offUpFreq
		self.tpThreads = {}
		self.tpDevices = {}
		self.tpQueue = Queue()

	########################################
	def startup(self):
		self.logger.debug(u"startup called")

	def shutdown(self):
		self.logger.debug(u"shutdown called")

	########################################
	# Validation handlers
	######################
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		errorsDict = indigo.Dict()

		self.logger.info(u"received \"%s\"" % (valuesDict))
		cmd = "/sbin/ping -c1 -t5 -q " + valuesDict['address'] + " >/dev/null 2>&1" 
		response = os.system(cmd)
		# self.logger.debug("Response: %s " % (response))
		
		#and then check the response...
		if int(response) != 0:
			self.logger.info(u"%s is not reachable" % valuesDict['address'])
			errorsDict["address"] = "Host unreachable"
			return (False, valuesDict, errorsDict)
			
		# If this is a new device, or we have been asked to re-initialize it...
		if ('initialize' in valuesDict and valuesDict['initialize']) or valuesDict['newDev']:
			self.initializeDev(valuesDict)

		valuesDict['newDev'] = False
		valuesDict['initialize'] = False
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
				myDeviceId  = dev.states['deviceId']
				if not myDeviceId:
					self.logger.error("%s: Oops.No deviceId for %s", name, address)
					id = self.tpDevices[address].id
					self.logger.info("%s: found Id for %s", name, str(id))
					myDeviceId = indigo.devices[id].states['deviceId']
					dev.updateStateOnServer("deviceId", myDeviceId)
					self.logger.info("%s: Got deviceId  %s", name, myDeviceId)
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
	# Relay / Dimmer Action callback
	######################
	def actionControlDimmerRelay(self, action, dev):
		addr = dev.address
		port = 9999
		deviceId = dev.pluginProps['deviceId']
		childId = dev.pluginProps['outletNum']
		# childId = deviceId + outletNum
		# self.logger.debug("TPlink name={}, addr={}, action={}".format(dev.name, addr, action))

		tplink_dev = tplink_smartplug (addr, port, deviceId, childId)

		###### TURN ON ######
		if action.deviceAction == indigo.kDimmerRelayAction.TurnOn:
			# Command hardware module (dev) to turn ON here:
			cmd = "on"
			# TODO: make conditional if polling is enabled
			self.tpThreads[dev.address].interupt(state=True, action='state')
		###### TURN OFF ######
		elif action.deviceAction == indigo.kDimmerRelayAction.TurnOff:
			# Command hardware module (dev) to turn OFF here:
			cmd = "off"
			self.tpThreads[dev.address].interupt(state=False, action='state')
		###### TOGGLE ######
		elif action.deviceAction == indigo.kDimmerRelayAction.Toggle:
			# Command hardware module (dev) to toggle here:
			if dev.onState:
				cmd = "off"
				self.tpThreads[dev.address].interupt(state=False, action='state')
			else:
				cmd = "on"
				self.tpThreads[dev.address].interupt(state=True, action='state')
			# newOnState = not dev.onState
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

		if sendSuccess:
			# If success then log that the command was successfully sent.
			self.logger.debug(u'sent "{}" {}'.format(dev.name, cmd))

			# And then tell the Indigo Server to update the state.
			dev.updateStateOnServer("onOffState", cmd)
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
	def getInfo(self, pluginAction, dev):
		self.logger.info("sent '{}' status request".format(dev.name))
		addr = dev.address
		port = 9999
		self.logger.debug("getInfo name={}, addr={}".format(dev.name, addr, ) )
		tplink_dev = tplink_smartplug (addr, port)
		result = tplink_dev.send("info")

		try:
			# pretty print the json result
			json_result = json.loads(result)
			# Get the device state from the JSON
			if json_result["system"]["get_sysinfo"]["relay_state"] == 1:
				state = "on"
			else:
				state = "off"
			# Update Indigo's device state
			dev.updateStateOnServer("onOffState", state)
			self.logger.info("getInfo result JSON:\n{}".format(json.dumps(json_result, sort_keys=True, indent=2, separators=(',', ': '))))
		except ValueError as e:
			self.logger.error("JSON value error: {} on {}".format(e, result))


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

	def dumpDeviceInfo(self, valuesDict, b):
		func = inspect.stack()[0][3]
		self.logger.debug("%s: called with a=%s and b=%s", func, str(valuesDict), b)

		return(True)	
	
	def displayButtonPressed(self, valuesDict, bar):
		func = inspect.stack()[0][3]
		self.logger.debug("%s: called with foo=%s bar=%s", func, valuesDict, bar)

		devNumber = int(valuesDict['targetDevice'])
		dev = indigo.devices[devNumber]
		props = dev.pluginProps
	
		valuesDict['address']       = props['address']
		valuesDict['devPoll']       = props['devPoll']
		valuesDict['deviceId']      = props['deviceId']
		valuesDict['energyCapable'] = props['energyCapable']
		valuesDict['mac']           = props['mac']
		valuesDict['model']         = props['model']
		valuesDict['multiPlug']     = props['multiPlug']
		valuesDict['offPoll']       = props['offPoll']
		valuesDict['onPoll']        = props['onPoll']
		valuesDict['outletNum']     = props['outletNum']
		valuesDict['alias']         = dev.states['alias']
		valuesDict['displayOk']     = True

		self.logger.debug("Device info = %s", valuesDict)

		return(valuesDict)

	def printToLogPressed(self, valuesDict, bar):
		func = inspect.stack()[0][3]
		self.logger.debug("%s: called with foo=%s bar=%s", func, valuesDict, bar)

		self.logger.info("Device data for %s:\n%s", "device", valuesDict)

		return

	########################################
	########################################
	def initializeDev(self, valuesDict):
		func = inspect.stack()[0][3]
		self.logger.debug(u"%s: called for: %s." % (func, valuesDict))
		devAddr = valuesDict['address']
		devName = "new device at " + devAddr
		devPort = 9999
		deviceId = None
		childId = None
		tplink_dev = tplink_smartplug (devAddr, devPort, deviceId, childId)
		result = tplink_dev.send('info')

		self.logger.debug(u"%s: InitializeDev 3 got %s" % (devName, result))
		data = json.loads(result)
		self.logger.debug(u"%s: InitializeDev 4 got %s" % (devName, data))
		# dev_name = data['system']['get_sysinfo']['alias']
		valuesDict['deviceId'] = data['system']['get_sysinfo']['deviceId']
		# self.logger.debug(u"%s: In initializeDev 4.1" % (dev.address))
		valuesDict['childId'] = str(deviceId) + valuesDict['outletNum']
		# alias = data['system']['get_sysinfo']['alias']
		valuesDict['mac'] = data['system']['get_sysinfo']['mac']
		valuesDict['model'] = data['system']['get_sysinfo']['model']

		if 'ENE' in data['system']['get_sysinfo']['feature']:
			valuesDict['energyCapable'] = True
		else:
			valuesDict['energyCapable'] = True

		valuesDict['initialize'] = False

		return valuesDict