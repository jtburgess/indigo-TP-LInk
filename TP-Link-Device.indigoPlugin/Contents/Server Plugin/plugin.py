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
from tpl_polling import pollingThread

# Note the "indigo" module is automatically imported and made available inside
# our global name space by the host process.				

################################################################################
class Plugin(indigo.PluginBase):
	########################################
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		# self.indigo_log_handler.setFormatter(logging.Formatter('%(levelname)-10s\t%(name)s.%(funcName)-28s %(msg)s'))
		self.debug = pluginPrefs.get("showDebugInfo", False)
		self.logOnOff = pluginPrefs.get('logOnOff', False)
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
		# Commit any state changes
		dev.stateListOrDisplayStateIdChanged()

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
				self.process = pollingThread(self.logger, dev, self.logOnOff, self.pluginPrefs)
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
		# Since we got this far, we might as well tell someone
		self.logger.info(u"Polling started for %s@%s.", dev.name, dev.address)

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

	# Energy and Status callback
	def actionControlUniversal(self, action, dev):
		func = inspect.stack()[0][3]
		self.logger.debug(u"%s: action: %s for device: %s." % (func, action, dev.name))
		###### ENERGY UPDATE ######
		if action.deviceAction == indigo.kUniversalAction.EnergyUpdate:
			if dev.pluginProps['energyCapable'] == True :
				self.logger.info("Energy Status Update Requested for " + dev.name)
				self.getInfo("", dev)
			else: self.logger.info("Device " + dev.name + " not energy capable.")

		###### STATUS REQUEST ######
		elif action.deviceAction == indigo.kUniversalAction.RequestStatus:
			self.getInfo("", dev)

		###### ENERGY RESET ######
		elif action.deviceAction == indigo.kUniversalAction.EnergyReset:
			self.logger.info("%s: energy reset for Device: %s", func, dev.name)

			# Get the plugionProps, modify them, and save them back
			pluginProps = dev.pluginProps
			accuUsage = float(pluginProps['totAccuUsage'])
			curTotEnergy = float(dev.states['totWattHrs'])
			accuUsage += curTotEnergy
			pluginProps['totAccuUsage'] = accuUsage
			dev.replacePluginPropsOnServer(pluginProps)

			# and now reset the Indigo Device Detail display
			dev.updateStateOnServer("accumEnergyTotal", 0.0)


	########################################
	# Device ConfigUI Callbacks
	######################

	# Dynamically create/update the states list for each device
	def getDeviceStateList(self, dev):
		func = inspect.stack()[0][3]
		self.logger.debug(u"%s: called for: %s." % (func, dev))

		statesDict = indigo.PluginBase.getDeviceStateList(self, dev)
		rssi  = self.getDeviceStateDictForNumberType(u"rssi", u"rssi", u"rssi")
		alias = self.getDeviceStateDictForNumberType(u"alias", u"alias", u"alias")
		statesDict.append(rssi)
		statesDict.append(alias)
	
		if len(dev.pluginProps) >0: # We actually have a device here...
			if dev.pluginProps['energyCapable']: # abd the device does energy reporting
				# Add the energy reporting states

				#accuWattHrs = self.getDeviceStateDictForNumberType(u"accuWattHrs", u"accuWattHrs", u"accuWattHrs")
				curWatts = self.getDeviceStateDictForNumberType(u"curWatts", u"curWatts", u"curWatts")
				totWattHrs = self.getDeviceStateDictForNumberType(u"totWattHrs", u"totWattHrs", u"totWattHrs")
				curVolts = self.getDeviceStateDictForNumberType(u"curVolts", u"curVolts", u"curVolts")
				curAmps = self.getDeviceStateDictForNumberType(u"curAmps", u"curAmps", u"curAmps")
				
				#statesDict.append(accuWattHrs)
				statesDict.append(curWatts)
				statesDict.append(totWattHrs)
				statesDict.append(curVolts)
				statesDict.append(curAmps)

		return statesDict

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
			try:
				self.deviceSearchResults = tplink_discover.discover()
			except Exception as e:
				self.logger.error("Discovery connection failed with (%s)" % (str(e)))

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

	