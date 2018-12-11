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
from struct import pack

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

class tplink_smartplug():
	def __init__(self, ip, port):
		self.ip = ip
		self.port = port
		if debug:
			print("init with host=%s, port=%s" % ( ip, port) )
		return

	# Send command and receive reply
	def send(self, cmd):
		if cmd in commands:
			cmd = commands[cmd]
		else:
			quit("unknown command: %s" % (cmd, ))

		if debug:
			print ("send cmd=%s" % (cmd, ))
		try:
			sock_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			sock_tcp.connect((self.ip, self.port))
			sock_tcp.send(encrypt(cmd))
			data = sock_tcp.recv(2048)
			sock_tcp.close()

			# don't know what the first 3 decrypted bytes are. skip them
			# Byte 4 is a '?' but for valid json replace it with '{'
			result = decrypt(data)
			return '{' + result[5:]
		except socket.error:
			quit("Cound not connect to host " + self.ip + ":" + str(self.port))

# Check if hostname is valid
def validHostname(hostname):
	try:
		socket.gethostbyname(hostname)
	except socket.error:
		parser.error("Invalid hostname.")
	return hostname

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
	# group.add_argument("-j", "--json", metavar="<JSON string>", help="Full JSON string of command to send")
	args = parser.parse_args()

	debug = True
	my_target = tplink_smartplug(args.target, 9999)

#	if args.command is None:
#		cmd = args.json
#	else:
#		cmd = commands[args.command]

	print "Sent:     ", args.command
	data = my_target.send(args.command)

	# data[0] = "{"
	try:
		# pretty print the json result
		json_result = json.loads(data)
		print "Received: ", json.dumps(json_result, sort_keys=True, indent=2, separators=(',', ': '))
	except ValueError, e:
		print ("Json value error: %s on %s" % (e, data) )


###### main for testing #####
if __name__ == '__main__' :
	main()
