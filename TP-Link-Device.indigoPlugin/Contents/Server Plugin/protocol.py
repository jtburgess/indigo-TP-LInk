#!/usr/bin/env python
#
# based on work by by Lubomir Stroetmann and others
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

import json
import socket
import struct
import sys



# Encryption and Decryption of TP-Link Smart Home Protocol
# XOR Autokey Cipher with starting key = 171
def encrypt(string):
  key = 171
  result = struct.pack('>I', len(string))
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

################################################################################
class tplink_protocol(object):
####################################################################
  def __init__(self, address, port, deviceID = None, childID = None, logger = None):
    """ ToDo child ID should be restricted to _relay_ devces, but this works, for now
    """
    self.address  = address
    self.port     = port
    self.deviceID = deviceID
    self.childID  = childID
    self.logger   = logger

    # We don't want to print if this class has been called from Indigo
    # but we do want to print if called from command line tool
    try:
      if sys.stdin.isatty():
        # running interactively
        self.isatty = True
      else:
        self.isatty = False
    except ValueError: # I/O operation on closed file (?)
      self.isatty = False

    # both or neither deviceID and childID should be set
    if (deviceID is not None and childID is not None) or (deviceID is None and childID is None):
      pass # both combinations are ok
    else:
      quit("ERROR: both deviceID and childID must be set together")

  # Send command and receive reply
  # some commands require a parameter. These are encoded as XXX and YYY in the command definition
  def send(self, request, arg1=None, arg2=None):
    if request in self.commands():
      cmd = self.commands()[request]
    else:
      cmd = request

    if "XXX" in cmd:
      if arg1 is not None:
        cmd=cmd.replace("XXX", arg1)
        # self.debugLog (u"send: XXX replaced with {}, cmd='{}'".format(arg1, cmd))
      else:
        return json.dumps({ 'error':  "TP-Link  command '{}' requires XXX value".format(request) })
    if "YYY" in cmd:
      if arg2 is not None:
        cmd=cmd.replace("YYY", arg2)
        # self.debugLog(u"send: YYY replaced with {}, cmd='{}'".format(arg2, cmd))
      else:
        return json.dumps({ 'error':  "TP-Link  command '{}' requires YYY value".format(request) })

    # if both deviceID and childID are set, { context... } is prepended to the command
    if self.deviceID is not None and self.childID is not None:
      context = '{"context":{"child_ids":["' + self.deviceID + "{:02d}".format(int(self.childID)) +'"]},'
      # now replace the initial '{' of the command with that string
      cmd = context + cmd[1:]

    self.debugLog ("Sent:  " + cmd + " == " + request)
    try:
      sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      sock.settimeout(3.0)
      sock.connect((self.address, 9999))
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
    except socket.timeout:
      return json.dumps({'error': 'TP-Link connection timeout'})
    except Exception as e:
      return json.dumps({'error': {"python error" : str(e), "cmd" : cmd}})

    finally:
      try:
        if sock:
          sock.close()
          #sock.shutdown(socket.SHUT_RDWR)
      #except Exception:
      except OSError:
        # OSX raises OSError when shutdown() gets called on a closed
        # socket. We ignore it here as the data has already been read
        # into the buffer at this point.
        pass

#      finally:
#        if sock:
#          sock.close()

    return decrypt(buffer[4:])

  def discover(self):
    cmd = self.commands()['discover']
    address = '255.255.255.255'
    port = 9999
    timeout = 5.0
    discovery_packets = 3
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(float(timeout))

    self.debugLog ("Sending discovery to %s:%s   %s" % (address, port, cmd))

    encrypted_cmd = encrypt(cmd)
    for _ in range(discovery_packets):
      sock.sendto(encrypted_cmd[4:], (address, port))

    # if running from command line tester...
    self.debugLog("Waiting %s seconds for responses..." % timeout)

    foundDevs = {}
    try:
      while True:
        data, addr = sock.recvfrom(4096)
        ip, port = addr
        info = json.loads(decrypt(data))
        # print("%s\n%s\n" % (ip, info))
        if not ip in foundDevs:
          foundDevs[ip] = info
    except:
      pass

    return foundDevs

  # These are the same across all types.
  # There are also have device-type specific commands, which are merged in the subclass
  def commands(self):
    BaseCommands = {
      'info'     : '{"system":{"get_sysinfo":{}}}',
      'discover' : '{"system":{"get_sysinfo":{}}}',
      'reboot'   : '{"system":{"reboot":{"delay":1}}}',
      'reset'    : '{"system":{"reset":{"delay":1}}}',
      'schedule' : '{"schedule":{"get_rules":{}}}',
    }

    return BaseCommands

  # logging -- to terminal if called from command line, or use self.logger() if initialized with a logger
  def debugLog(self, stringToPrint):
    if self.isatty:
      print stringToPrint
    elif self.logger is not None:
      self.logger.debug(stringToPrint)
