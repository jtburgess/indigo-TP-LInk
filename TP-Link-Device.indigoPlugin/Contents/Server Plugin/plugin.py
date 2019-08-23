#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2014, Perceptive Automation, LLC. All rights reserved.
# http://www.indigodomo.com

import indigo
import os
import sys
import json
from tplink_smartplug import tplink_smartplug

# Note the "indigo" module is automatically imported and made available inside
# our global name space by the host process.

################################################################################
class Plugin(indigo.PluginBase):
	########################################
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		self.debug = pluginPrefs.get("showDebugInfo", False)

	########################################
	def startup(self):
		self.logger.debug(u"startup called")

	def shutdown(self):
		self.logger.debug(u"shutdown called")

	########################################
	# Poll all of the states from the smart plug and pass values to
	# Indigo Server.
	def _refreshStatesFromHardware(self, dev, logRefresh):
		devType = dev.deviceTypeId
		devAddr = dev.address
		devPort = 9999

		self.logger.info(u"Got Here 1 with :%s:%s:" % (devType, devAddr))
	
		tplink_dev = tplink_smartplug (devAddr, devPort)

		self.logger.info(u"Dev props \"%s\"" % (dev.pluginProps))
		self.logger.info("TPlink name={}, addr={}".format(dev.name, devAddr))
		
		result = tplink_dev.send('info')
		# indigo.server.log("Received sRcvd: |%s|" % (binascii.hexlify(bytearray(sRcvd))), type="TP-Link", isError=True)
		data = json.loads(result)
		state = data['system']['get_sysinfo']['relay_state']
		dev.updateStateOnServer("onOffState", state)
		
		if not dev.pluginProps['configured']:
			dev_name = data['system']['get_sysinfo']['dev_name']
			alias = data['system']['get_sysinfo']['alias']
			mac = data['system']['get_sysinfo']['mac']
			model = data['system']['get_sysinfo']['model']

			result = tplink_dev.send('cloudinfo')
			data = json.loads(result)
			user = data['cnCloud']['get_info']['username']
			bind = data['cnCloud']['get_info']['binded']

			state_update_list = [
				{'key':'dev_name', 'value':dev_name},
				{'key':'alias', 'value':alias},
				{'key':'mac', 'value':mac},
				{'key':'model', 'value':model},
				{'key':'user', 'value':user},
				{'key':'bind', 'value':bind}
				]
			dev.updateStatesOnServer(state_update_list)
			
			self.logger.info(u"not conf")
			localPropsCopy = dev.pluginProps
			localPropsCopy['configured'] = True
			dev.replacePluginPropsOnServer(localPropsCopy)

		else:
			self.logger.info(u"conf")

		if devType == "hs110":
			result = tplink_dev.send('energy')
			data = json.loads(result)
			indigo.server.log("Received result: |%s|" % (result), type="TP-Link", isError=True)
			curWatts = data['emeter']['get_realtime']['power_mw']/1000
			curVolts = data['emeter']['get_realtime']['voltage_mv']/1000
			curAmps  = data['emeter']['get_realtime']['current_ma']/1000

			state_update_list = [
				{'key':'curWatts', 'value':curWatts},
				{'key':'curVolts', 'value':curVolts},
				{'key':'curAmps', 'value':curAmps}
				]
			dev.updateStatesOnServer(state_update_list)

			indigo.server.log("Received results: %s, %s, %s" % (curWatts, curVolts, curAmps), type="TP-Link", isError=True)

		#indigo.server.log(u"Update received for %s: state %s, watts %s" % (dev.name, state, curWatts), type="TP-Link", isError=False)

	########################################
	def runConcurrentThread(self):
		try:
			while True:
				for dev in indigo.devices.iter("self"):
					if not dev.enabled or not dev.configured:
						continue

					# Plugins that need to poll out the status from the meter
					# could do so here, then broadcast back the new values to the
					# Indigo Server.
					self._refreshStatesFromHardware(dev, False)

				self.sleep(10)
		except self.StopThread:
			pass	# Optionally catch the StopThread exception and do any needed cleanup.
			
	########################################
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		errorsDict = indigo.Dict()

		self.logger.info(u"received \"%s\"" % (valuesDict))
		cmd = "/sbin/ping -c1 -t5 -q " + valuesDict['address'] + " >/dev/null 2>&1" 
		response = os.system(cmd)
		# indigo.server.log("Response: %s " % (response), type="TP-Link", isError=True)
		
		#and then check the response...
		if int(response) != 0:
			self.logger.info(u"%s is not reachable" % valuesDict['address'], isError=True)
			errorsDict["address"] = "Host unreachable"
			return (False, valuesDict, errorsDict)
			
		valuesDict['newDev'] = False
		return (True, valuesDict, errorsDict)

	########################################
	def deviceStartComm(self, dev):
		# Called when communication with the hardware should be established.
		# Here would be a good place to poll out the current states from the
		# meter. If periodic polling of the meter is needed (that is, it
		# doesn't broadcast changes back to the plugin somehow), then consider
		# adding that to runConcurrentThread() above.
		self._refreshStatesFromHardware(dev, True)
		pass

	def deviceStopComm(self, dev):
		# Called when communication with the hardware should be shutdown.
		pass

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
		###### TURN OFF ######
		elif action.deviceAction == indigo.kDimmerRelayAction.TurnOff:
			# Command hardware module (dev) to turn OFF here:
			cmd = "off"
		###### TOGGLE ######
		elif action.deviceAction == indigo.kDimmerRelayAction.Toggle:
			# Command hardware module (dev) to toggle here:
			if dev.onState:
				cmd = "off"
			else:
				cmd = "on"
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

