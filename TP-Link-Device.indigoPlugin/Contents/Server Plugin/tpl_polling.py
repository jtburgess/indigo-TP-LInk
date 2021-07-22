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
from protocol import tplink_protocol

################################################################################
class pollingThread(Thread):
	####################################################################
	def __init__(self, logger, dev, logOnOff, pluginPrefs):
		Thread.__init__(self)
		self.logger = logger
		self.logger.debug(u"called for: %s." % (dev.name))
		self.dev = dev
		self.name = dev.name
		self.lastState = 1
		self.localOnOff = False
		self.pollErrors = 0
		self.exceptCount = 0
		self.pluginPrefs = pluginPrefs
		self.logOnOff = logOnOff

	def interupt(self, state=None, dev=None, action=None):
		self.logger.debug(u"called for %s with action=%s, state=%s" % (self.dev.name, action, state))

		# self.logger.threaddebug(u"%s: Before, poll freq is %s" % (dev.name, self.pollFreq))
		if action == 'status':
			if self.pollErrors > 0:
				self.logger.error ("{}: Device has {} poll Errors.".format(dev.name, self.pollErrors))
				return False
			if self.exceptCount > 0:
				self.logger.error ("{}: Device has {} poll Exceptions.".format(dev.name, self.exceptCount))
				return False
			return True

		if self.dev.deviceTypeId =='tplinkSmartPlug':
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
				self.logger.error(u"called for %s with action=%s, state=%s" % (self.dev.id, action, state))
				return
		else: # if self.dev.deviceTypeId =='tplinkSmartSwitch' or self.dev.deviceTypeId =='tplinkSmartBulb'
			if action == 'state' and state:
				self.pollFreq = self.dev.pluginProps['onPoll']
			elif action == 'state' and not state:
				self.pollFreq = self.dev.pluginProps['offPoll']
			elif action == 'dev':
				self.dev = dev
			else:
				self.logger.error(u"called for %s with action=%s, state=%s" % (self.dev.id, action, state))
				return

		if action == 'state':
			self.localOnOff = True

		sleep(0.5)
		self.changed = True
		return(True)

	def stop(self):
		# We should probably tell someone
		self.logger.info(u"Polling stopped for %s@%s." % (self.name, self.dev.address) )

		self._is_running = False

#	def run(self):
# main thread loop replicated in each subclass
# need tofigure out how to put common logic here with call backs...

