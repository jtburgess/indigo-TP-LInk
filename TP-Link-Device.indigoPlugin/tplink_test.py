#!/usr/bin/env python
#
# based on work by by Lubomir Stroetmann
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
import sys
import argparse
import json

# this only works if the direcgtory structure is unchanged and  local
sys.path.insert(0, './Contents/Server Plugin')
from protocol import tplink_protocol
from tplink_dimmer_protocol import tplink_dimmer_protocol
from tplink_relay_protocol import tplink_relay_protocol
from tplink_relayswitch_protocol import tplink_relayswitch_protocol

version = 0.9

####################################################################
def check_server(address):
  # Create a TCP socket
  s = socket.socket()
  s.settimeout(2.0)
  port = 9999
  # print "Checking availability of %s on port %s" % (address, port)
  try:
    s.connect((address, port))
    # print "Connected to %s on port %s" % (address, port)
    return address
  except socket.error as e:
    print ("Connection to %s on port %s failed: %s" % (address, port, e))
    # parser.error("Invalid hostname.")
  finally:
    s.close()

class logger():
  def debug(s):
    print ("DEBUG:" + s)
  def info(s):
    print ("INFO :" + s)

################################################################################
def main():

  # Parse commandline arguments
  # this is needed so help can provide a list of generic commands
  my_target = tplink_protocol(None, None)
  choices=my_target.commands()
  choices.update ( {"on": "on", "off": "off"}) # the implementaion is different but these are common commands

  parser = argparse.ArgumentParser(description="TP-Link Wi-Fi command line Client v" + str(version))
  parser.add_argument("-t", "--target", required=True, help="Target hostname or IP address", type=check_server)

  group = parser.add_mutually_exclusive_group(required=True)
  group.add_argument("-c", "--command", help="Preset command to send. Generic choices are: "+", ".join(choices), choices=choices )
  group.add_argument("-C", "--CMD", help="unvalidated Command")
  group.add_argument("-j", "--json", metavar="<JSON string>", help="Full JSON string of command to send")

  TPtype = parser.add_mutually_exclusive_group(required=False)
  TPtype.add_argument("-r", "--relay", action='store_true', help="tplinkSmartPlug type")
  TPtype.add_argument("-b", "--bulb", action='store_true', help="tplinkSmartBulb type")
  TPtype.add_argument("-s", "--switch", action='store_true', help="tplinkRelaySwitch type")

  # options for plug strips (untested)
  parser.add_argument("-d", "--deviceID", required=False, help="device ID for testing powerstrip")
  parser.add_argument("-p", "--childID", required=False, help="port on device", type=int)

  # options for dimmers
  parser.add_argument("-R", "--rampTime", required=False, help="ramp time (msec) for dimmers", type=int)
  parser.add_argument("-B", "--brightness", required=False, help="Brightness for dimmers", type=int)


  args = parser.parse_args()

  # for sending options to send()
  arg1 = None
  arg2 = None

  # this allows you to use device-type specific commands
  if args.relay is True:
      my_target = tplink_relay_protocol(args.target, 9999, args.deviceID, args.childID, logger=logger)
      print ("using Relay protocol")
      choices = my_target.commands()
  elif args.bulb is True:
      my_target = tplink_dimmer_protocol(args.target, 9999, logger=logger)
      #print "using Dimmer protocol"
      choices = my_target.commands()
      if args.brightness is not None:
        arg1 = args.brightness
      else:
        arg1 = 50 # default to half-way
      if args.rampTime is not None:
        arg2 = args.rampTime
      else:
        arg2 = 1000 # default to 1 second
      print ("Dimmer: brightness={}, rampTime={}".format(arg1, arg2))
  elif args.switch is True:
      my_target = tplink_relayswitch_protocol(args.target, 9999, logger=logger)
      print ("using RelaySwitch protocol")
      choices = my_target.commands()
  elif args.command != 'discover':
      print ("unknown device type: {}".format(args.switch))
      sys.exit(1)

  if args.command == 'discover':
      # discover and info are generic
      # my_target = tplink_protocol(args.target, 9999)
      response =  my_target.discover()
  elif args.target is None : # or (args.relay is None and args.bulb is None):
      print ("Error: valid target host IP (%s) is required" % (args.target))
      sys.exit(1)
  else:
      received = None
      # allow validated or unvalidated commands
      if args.command:
        received = my_target.send(args.command, arg1=arg1, arg2=arg2)
      elif args.CMD:
        received = my_target.send(args.CMD, arg1=arg1, arg2=arg2)
      elif args.json:
        received = my_target.send(args.json)
      else:
        print ("Error: -c, -C or -j is required")
        sys.exit(1)

      try:
        response = json.loads( received )
      except ValueError as e:
          print ("Value error: %s on %s" % (e, received) )
#       except TypeError, e:
#           print ("Type error: %s on %s" % (e, received) )

      print ("Received: ")
      print (json.dumps(response, sort_keys=True, indent=2, separators=(',', ': ')))
      sys.exit(0)

###### main for testing #####
if __name__ == '__main__' :
  main()
