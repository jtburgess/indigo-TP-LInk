#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2014, Perceptive Automation, LLC. All rights reserved.
# http://www.indigodomo.com

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

# Note the "indigo" module is automatically imported and made available inside
# our global name space by the host process.

class myThread(Thread):
	def __init__(self, dev):
		Thread.__init__(self)
		self.dev = dev
		self.name = dev.name
		# self.offPoll = int(offPoll)
		self.offPoll = int(dev.pluginProps['offPoll'])
		self.onPoll = int(dev.pluginProps['onPoll'])
		self.configured = self.dev.pluginProps['configured']
		self.multiPlug = self.dev.pluginProps['multiPlug']
		if self.multiPlug:
			self.childId = dev.states['outletNum']
		self.onOffState = dev.states['onOffState']
		if self.onOffState:
			self.pollFreq = self.onPoll
		else:
			self.pollFreq = self.offPoll
		self.deviceId = dev.states['deviceId']
		self.changed = False
		# indigo.server.log(u"Initializing: %s:%s" % (dev.name, self.offPoll))
		self._is_running = True
		self.start()

	def interupt(self, state):
		#####  All of this code is unecessary since any device changes stop and restart the queue anyeway
		# self.dev = indigo.devices[self.dev.id]
		# indigo.server.log(u"from: %s You interupted with %s" % (self.name, state))
		# self.configured = self.dev.pluginProps['configured']
		# indigo.server.log(u"from: %s configured = %s" % (self.name, self.configured))
		# self.offPoll = int(self.dev.pluginProps['offPoll'])
		# self.onPoll = int(self.dev.pluginProps['onPoll'])
		# self.onOffState = self.dev.states['onOffState']
		# indigo.server.log(u"Current state %s %s" % (self.onOffState, bool(self.onOffState)))
		# indigo.server.log(u"Was: onPoll=%s & offPOll=%s" % (self.onPoll, self.offPoll))
		# if self.offPoll != self.lastOffPoll or self.onPoll != self.lastOnPoll or self.onOffState != self.lastOnOffState or self.configured:

		# indigo.server.log(u"Just before the test state %s %s" % (self.onOffState, bool(self.onOffState)))
		if state:
			self.pollFreq = self.onPoll
		else:
			self.pollFreq = self.offPoll
		self.changed = True
			# indigo.server.log(u"Now: is %s, onPoll=%s & offPOll=%s" % (self.pollFreq, self.onPoll, self.offPoll))

		# indigo.server.log(u"Property or state change for %s" % (self.name))
			
	def stop(self):
		indigo.server.log(u"from: %s  time to quit" % (self.name))
		self._is_running = False

	def run(self):
		dev = self.dev
		devType = dev.deviceTypeId
		# indigo.server.log(u"Running: %s" % (devType))
		devAddr = dev.address
		devPort = 9999
		lastState = 0
		if self.multiPlug:
			deviceId = self.deviceId
			childId = self.childId
		else:
			deviceId = None
			childId = None
		
		# indigo.server.log(u"Starting data refresh for %s :%s:%s: with %s" % (dev.name, devType, devAddr, self.offPoll))

		tplink_dev = tplink_smartplug (devAddr, devPort, deviceId, childId)
		while True:
			# indigo.server.log(u"%s: Starting polling loop with interval %s" % (self.name, self.offPoll))
			result = tplink_dev.send('info')
			data = json.loads(result)
			state = data['system']['get_sysinfo']['relay_state']
			# indigo.server.log(u"%s: state= %s" % (self.name, state))
			if state == 1:
				state = "on"
				if state != lastState:
					self.interupt(True)
			else:
				state = "off"
				if state != lastState:
					self.interupt(False)
			lastState = state

			dev.updateStateOnServer("onOffState", state)

			# Check % (self.name) to see if we should grab device parameters from the plug
			if dev.pluginProps['newDev'] or self.configured:
				# indigo.server.log(u"%s: In the loop - re-reading device info" % (self.name))
				dev_name = data['system']['get_sysinfo']['dev_name']
				deviceId = data['system']['get_sysinfo']['deviceId']
				alias = data['system']['get_sysinfo']['alias']
				mac = data['system']['get_sysinfo']['mac']
				model = data['system']['get_sysinfo']['model']

				result = tplink_dev.send('cloudinfo')
				data = json.loads(result)
				user = data['cnCloud']['get_info']['username']
				bind = data['cnCloud']['get_info']['binded']

				state_update_list = [
					{'key':'dev_name', 'value':dev_name},
					{'key':'deviceId', 'value':deviceId},
					{'key':'alias', 'value':alias},
					{'key':'mac', 'value':mac},
					{'key':'model', 'value':model},
					{'key':'user', 'value':user},
					{'key':'bind', 'value':bind}
					]
				dev.updateStatesOnServer(state_update_list)
				
				# Reset the properties that control gathering informational states
				indigo.server.log(u"Ressetting config properties")
				localPropsCopy = self.dev.pluginProps
				localPropsCopy['newDev'] = False
				localPropsCopy['configured'] = False
				self.dev.replacePluginPropsOnServer(localPropsCopy)

			if devType == "hs110":
				result = tplink_dev.send('energy')
				data = json.loads(result)
				# indigo.server.log("Received result: |%s|" % (result), type="TP-Link", isError=True)
				curWatts = data['emeter']['get_realtime']['power_mw']/1000
				curVolts = data['emeter']['get_realtime']['voltage_mv']/1000
				curAmps  = data['emeter']['get_realtime']['current_ma']/1000

				state_update_list = [
					{'key':'curWatts', 'value':curWatts},
					{'key':'curVolts', 'value':curVolts},
					{'key':'curAmps', 'value':curAmps}
					]
				dev.updateStatesOnServer(state_update_list)

				indigo.server.log("Received results for %s @ %s secs: %s, %s, %s: chenge = %s" % (dev.name, self.pollFreq, curWatts, curVolts, curAmps, self.changed), type="TP-Link", isError=False)
			# indigo.server.log(u"%s: In the loop - finished data gathering" % (self.name))
			pTime = 0.5
			cTime = self.pollFreq
			while cTime > 0:
				# indigo.server.log(u"Timer = %6.4f" % (cTime))
				if self.changed or not self._is_running:
					# indigo.server.log(u"Device change for %s" % (self.name))
					self.changed = False
					break
				else:
					# indigo.server.log(u"starting mini sleep for %6.4f" % (pTime))
					time.sleep(pTime)
					cTime = cTime - pTime
					# indigo.server.log(u"Timer = %6.4f" % (cTime))

			if not self._is_running:
				break
			
			# indigo.server.log(u"%s: In the loop - timer ended" % (self.name))


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
		self.tpQueue = Queue()

	########################################
	def startup(self):
		self.logger.debug(u"startup called")

	def shutdown(self):
		self.logger.debug(u"shutdown called")

	########################################
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		errorsDict = indigo.Dict()

		# self.logger.info(u"received \"%s\"" % (valuesDict))
		cmd = "/sbin/ping -c1 -t5 -q " + valuesDict['address'] + " >/dev/null 2>&1" 
		response = os.system(cmd)
		# indigo.server.log("Response: %s " % (response), type="TP-Link", isError=True)
		
		#and then check the response...
		if int(response) != 0:
			self.logger.info(u"%s is not reachable" % valuesDict['address'], isError=True)
			errorsDict["address"] = "Host unreachable"
			return (False, valuesDict, errorsDict)
			
		# valuesDict['newDev'] = False
		return (True, valuesDict, errorsDict)

	########################################
	def deviceStartComm(self, dev):
		# indigo.server.log("deviceStartComn starting %s" % (dev.name), type="TP-Link", isError=False)
		# myThread(dev)
		if dev.name in self.tpThreads:
			indigo.server.log("deviceStartComm error: Thread exists for %s - %s" % (dev.name, self.tpThreads[dev.name]))
			# self.tpThreads[dev.name].interupt(None)
		elif dev.pluginProps['devPoll']:
			# We start one thread per device.
			self.process = myThread(dev)
			self.tpThreads[dev.name] = self.process
			indigo.server.log("Started thread for device  %s" % (self.tpThreads), type="TP-Link", isError=False)

	def deviceStopComm(self, dev):
		# Called when communication with the hardware should be shutdown.
		if dev.name in self.tpThreads:  # We don't want to waste time if a polling thread was never started
			indigo.server.log("deviceStopComn ending %s" % (dev.name), type="TP-Link", isError=False)
			self.tpThreads[dev.name].stop()
			del self.tpThreads[dev.name]

	########################################
	# Relay / Dimmer Action callback
	######################
	def actionControlDimmerRelay(self, action, dev):
		addr = dev.address
		port = 9999
		self.logger.debug("TPlink name={}, addr={}, action={}".format(dev.name, addr, action))
		tplink_dev = tplink_smartplug (addr, port)

		###### TURN ON ######
		if action.deviceAction == indigo.kDimmerRelayAction.TurnOn:
			# Command hardware module (dev) to turn ON here:
			cmd = "on"
			self.tpThreads[dev.name].interupt(True)
		###### TURN OFF ######
		elif action.deviceAction == indigo.kDimmerRelayAction.TurnOff:
			# Command hardware module (dev) to turn OFF here:
			cmd = "off"
			self.tpThreads[dev.name].interupt(False)
		###### TOGGLE ######
		elif action.deviceAction == indigo.kDimmerRelayAction.Toggle:
			# Command hardware module (dev) to toggle here:
			if dev.onState:
				cmd = "off"
				self.tpThreads[dev.name].interupt(False)
			else:
				cmd = "on"
				self.tpThreads[dev.name].interupt(True)
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
			self.logger.info(u'sent "{}" {}'.format(dev.name, cmd))

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

