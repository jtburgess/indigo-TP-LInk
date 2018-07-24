#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2014, Perceptive Automation, LLC. All rights reserved.
# http://www.indigodomo.com

import indigo

import os
import sys

from tplink_smartplug import tplink_smartplug

# Note the "indigo" module is automatically imported and made available inside
# our global name space by the host process.

################################################################################
class Plugin(indigo.PluginBase):
	########################################
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		self.debug = False

	########################################
	def startup(self):
		self.debugLog(u"startup called")

	def shutdown(self):
		self.debugLog(u"shutdown called")

	####################
	def _getDeviceGroupList(self, filter, valuesDict, devIdList):
		menuItems = []
		for devId in devIdList:
			if devId in indigo.devices:
				dev = indigo.devices[devId]
				devName = dev.name
			else:
				devName = u"- device not found -"
			menuItems.append((devId, devName))
		return menuItems

	def _addRelay(self, valuesDict, devIdList):
		newdev = indigo.device.create(indigo.kProtocol.Plugin, deviceTypeId="myRelayType")
		newdev.model = "Example Multi-Device"
		newdev.subModel = "Relay"		# Manually need to set the model and subModel names (for UI only)
		newdev.replaceOnServer()
		return valuesDict

	def _addDimmer(self, valuesDict, devIdList):
		newdev = indigo.device.create(indigo.kProtocol.Plugin, deviceTypeId="myDimmerType")
		newdev.model = "Example Multi-Device"
		newdev.subModel = "Dimmer"		# Manually need to set the model and subModel names (for UI only)
		newdev.replaceOnServer()
		return valuesDict

	def _removeDimmerDevices(self, valuesDict, devIdList):
		for devId in devIdList:
			try:
				dev = indigo.devices[devId]
				if dev.deviceTypeId == "myDimmerType":
					indigo.device.delete(dev)
			except:
				pass	# delete doesn't allow (throws) on root elem
		return valuesDict

	def _removeRelayDevices(self, valuesDict, devIdList):
		for devId in devIdList:
			try:
				dev = indigo.devices[devId]
				if dev.deviceTypeId == "myRelayType":
					indigo.device.delete(dev)
			except:
				pass	# delete doesn't allow (throws) on root elem
		return valuesDict

	def _removeAllDevices(self, valuesDict, devIdList):
		for devId in devIdList:
			try:
				indigo.device.delete(devId)
			except:
				pass	# delete doesn't allow (throws) on root elem
		return valuesDict

	########################################
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		return (True, valuesDict)

	########################################
	# Relay / Dimmer Action callback
	######################
	def actionControlDimmerRelay(self, action, dev):
		addr = dev.address
		port = 9999
		self.debugLog("TPlink name=%s, addr=%s, action=%s" % (dev.name, addr, action) )
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
			newOnState = not dev.onState
		else:
			indigo.server.log("Unknown command: %s" % (indigo.kDimmerRelayAction, ), isError=True )
			return

		result = tplink_dev.send(cmd)
		if "\"err_code\":0" in result:
			sendSuccess = True
		else:
			sendSuccess = False

		if sendSuccess:
			# If success then log that the command was successfully sent.
			indigo.server.log(u"sent \"%s\" %s" % (dev.name, cmd))

			# And then tell the Indigo Server to update the state.
			dev.updateStateOnServer("onOffState", True)
		else:
			# Else log failure but do NOT update state on Indigo Server.
			indigo.server.log(u"send \"%s\" %s failed with result \"%s\"" % (dev.name, cmd, result), isError=True)

	########################################
	# General Action callback
	######################
	def actionControlGeneral(self, action, dev):
		if action.deviceAction == indigo.kDeviceGeneralAction.RequestStatus:
			self.getInfo(action, dev)
		else:
			indigo.server.log(u"unsupported Action callback \"%s\" %s" % (dev.name, action), isError=True)

	########################################
	# Custom Plugin Action callbacks (defined in Actions.xml)
	######################
	def getInfo(self, pluginAction, dev):
		try:
			import json
		except ImportError:
			import simplejson as json

		addr = dev.address
		port = 9999
		self.debugLog("TPlink get Info name=%s, addr=%s" % (dev.name, addr, ) )
		tplink_dev = tplink_smartplug (addr, port)
		result = tplink_dev.send("info")

		try:
			# pretty print the json result
			json_result = json.loads(result)
			indigo.server.log ( json.dumps(json_result, sort_keys=True, indent=2, separators=(',', ': ')), type="TPLink Device Info" )
		except ValueError, e:
			indigo.server.log ("Json value error: %s on %s" % (e, result), isError=True )
