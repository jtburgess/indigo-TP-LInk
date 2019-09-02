#!/usr/bin/env python
#
# TP-Link Wi-Fi Smart Plug Protocol Client
# For use with TP-Link HS-100 or HS-110
#
# by Lubomir Stroetmann
# Copyright 2016 softScheck GmbH
#  from: https://github.com/softScheck/tplink-smartplug/blob/master/tplink_smartplug.py
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import socket
import argparse
import struct
from struct import pack
import json

version = 0.2

debug = False

# Predefined Smart Plug Commands
# For a full list of commands, consult tplink_commands.txt
commands = {'info'     : '{"system":{"get_sysinfo":{}}}',
			'on'       : '{"system":{"set_relay_state":{"state":1}}}',
			'off'      : '{"system":{"set_relay_state":{"state":0}}}',
			'cloudinfo': '{"cnCloud":{"get_info":{}}}',
			'wlanscan' : '{"netif":{"get_scaninfo":{"refresh":0}}}',
			'time'     : '{"time":{"get_time":{}}}',
			'schedule' : '{"schedule":{"get_rules":{}}}',
			'countdown': '{"count_down":{"get_rules":{}}}',
			'antitheft': '{"anti_theft":{"get_rules":{}}}',
			'reboot'   : '{"system":{"reboot":{"delay":1}}}',
			'reset'    : '{"system":{"reset":{"delay":1}}}',
			'e+i'      : '{ "emeter": { "get_realtime": {} }, "system": { "get_sysinfo": {} } }',
			'energy'   : '{"emeter":{"get_realtime":{}}}'
}

# Encryption and Decryption of TP-Link Smart Home Protocol
# XOR Autokey Cipher with starting key = 171
def encrypt(string):
	key = 171
	result = pack('>I', len(string))
	for i in string:
		a = key ^ ord(i)
		key = a
		result += chr(a)
	return result

def decrypt(string):
	key = 171
	result = ""
	for i in string:
		a = key ^ ord(i)
		key = ord(i)
		result += chr(a)
	return result

########################
# the class has an optional deviceID string, used by power Strip devices (and others???)
# and the send command has an optional childID representing the socket on the power Strip
class tplink_smartplug():
	def __init__(self, ip, port, deviceID = None, childID = None):
		self.ip = ip
		self.port = port

		# both or neither deviceID and childID should be set
		if (deviceID is not None and childID is not None) or (deviceID is None and childID is None):
			pass # both combinations are ok
		else:
			quit("ERROR: both deviceID and childID must be set together")

		self.deviceID = deviceID
		self.childID = childID
		if debug:
			print("init with host=%s, port=%s" % ( ip, port) )
		return

	# Send command and receive reply
	def send(self, cmd):
		if cmd in commands:
			cmd = commands[cmd]
		# else:
		# 	quit("ERROR: unknown command: %s" % (cmd, ))

		print ("Got %s" % cmd)

		# if both deviceID and childID are set, { context... } is prepended to the command
		if self.deviceID is not None and self.childID is not None:
			context = '{"context":{"child_ids":["' + self.deviceID + "{:02d}".format(int(self.childID)) +'"]},'
			# now replace the initial '{' of the command with that string
			cmd = context + cmd[1:]
		# note error checking on deviceID and childID is done in __init__

		if debug:
			print ("send cmd=%s" % (cmd, ))
		
		### Insert pyHS100 code here
		timeout = 10
		try:
			# sock = socket.create_connection((self.ip, self.port), timeout)

			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			sock.settimeout(5)
			sock.connect((self.ip, 9999))

			# _LOGGER.debug("> (%i) %s", len(cmd), cmd)
			sock.send(encrypt(cmd))

			buffer = bytes()
            # Some devices send responses with a length header of 0 and
            # terminate with a zero size chunk. Others send the length and
            # will hang if we attempt to read more data.
			length = -1
			while True:
				chunk = sock.recv(4096)
				if length == -1:
					length = struct.unpack(">I", chunk[0:4])[0]
				buffer += chunk
				if (length > 0 and len(buffer) >= length + 4) or not chunk:
					break
		except Exception as e:
			return ("Fatal error in tplink_smartplug: %s" % (str(e)))
	
		finally:
			try:
				if sock:
					sock.shutdown(socket.SHUT_RDWR)
			except OSError:
				# OSX raises OSError when shutdown() gets called on a closed
				# socket. We ignore it here as the data has already been read
				# into the buffer at this point.
				pass

			finally:
				if sock:
					sock.close()
		response = decrypt(buffer[4:])

		return response

# Check if hostname is valid
def validHostname(hostname):
	try:
		socket.gethostbyname(hostname)
	except socket.error:
		parser.error("Invalid hostname.")
	return hostname

########################
# for debugging
def main():
	try:
		import json
	except ImportError:
		print ("using simplejson")
		import simplejson as json

	global debug
	# Parse commandline arguments
	parser = argparse.ArgumentParser(description="TP-Link Wi-Fi Smart Plug Client v" + str(version))
	parser.add_argument("-t", "--target", metavar="<hostname>", required=True, help="Target hostname or IP address", type=validHostname)
	group = parser.add_mutually_exclusive_group(required=True)
	group.add_argument("-c", "--command", metavar="<command>", help="Preset command to send. Choices are: "+", ".join(commands), choices=commands)
	group.add_argument("-C", "--CMD", metavar="<command>", help="unvalidated Command")
	group.add_argument("-j", "--json", metavar="<JSON string>", help="Full JSON string of command to send")
	parser.add_argument("-d", "--deviceID", metavar="<deviceID>", required=False, help="device ID for testing powerstrip")
	parser.add_argument("-p", "--childID", metavar="<childID>", required=False, help="port on device", type=int)

	args = parser.parse_args()

#	if (args.deviceID is None) ^ (args.childID is None):
#		# this is true if one is set and the other isn't
#		# we need BOTH to be set or both NOT set
#		print "both device and port must be set or not set"
#		exit(1)
	print ("args2 = %s" % args)
	debug = True
	if args.deviceID:
		my_target = tplink_smartplug(args.target, 9999, deviceID=args.deviceID, childID=args.childID)
	else:
		my_target = tplink_smartplug(args.target, 9999)

	if args.command is None:
		cmd = args.json
	else:
		cmd = commands[args.command]
	print ("args2 = %s" % args)
	print ("args.command = %s" % args.command)

	if args.childID:
		data = my_target.send(args.command)
	else:
		data = my_target.send(cmd)

	print "Sent:     ", args.command

	# data[0] = "{"
	response = json.loads(data)
	try:
		# pretty print the json result
		# json_result = json.loads(data)
		print "Received: ", json.dumps(response, sort_keys=True, indent=2, separators=(',', ': '))
	except ValueError, e:
		print ("Json value error: %s on %s" % (e, data) )


###### main for testing #####
if __name__ == '__main__' :
	main()
