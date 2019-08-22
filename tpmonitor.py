#!/usr/bin/env python -u

# Set target IP, port and command to send
ip = "192.168.5.113" # the ip address of your plug
port = 9999          # normally leave at the default 9999

# Set the polling frequency
offUpFreq = 30   # interval in secs between updates when the plug is off should be <= 30
onUpFreq  =  2   # interval in secs between updates when the plug is on

# Specify the variable names for the following data elements
indigoStateVarName =  "planchaState"
indigoWattsVarName =  "planchaWatts"
indigoAmpsVarName  =  "planchaAmps"
indigoVoltsVarName =  "planchaVolts"

######################################
# No changes needed below this point #
######################################
import socket
import json
import sys
from struct import pack
from threading import Event
import binascii
import subprocess
import signal

# Make sure we are not already running
cmd = '/usr/bin/pgrep -f tpmonitor.py'
process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
myPID, err = process.communicate()
# indigo.server.log("Got pid = %s" % (my_pid), type="TP-Link", isError=True)
if len(myPID.splitlines()) >0:
   indigo.server.log("Quiting. tpmonitor.py is already running. pid = %s" % (myPID), type="TP-Link", isError=True)
   return
indigo.server.log("PID of TPLink Monitor is: " + myPID, type="TP-Link")

# Create a way to exit the timed loop...
def reset(signo, _frame):
	indigo.server.log("Polling wait interup received", type="TP-Link")
	exit.set()
# ...and a trigger to invoke the exit
signal.signal(getattr(signal, 'SIGUSR1'), reset)

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

# Get our variable references from Indigo
try:
	indigoState = indigo.variables[indigoStateVarName]
	indigoWatts = indigo.variables[indigoWattsVarName]
	indigoAmps  = indigo.variables[indigoAmpsVarName]
	indigoVolts = indigo.variables[indigoVoltsVarName]
except Exception as e:
	indigo.server.log("Fatal error looking uo Indigo variables: %s" % (str(e)), type="TP-Link", isError=True)
	return

# set variables for the connection the the TPLink plug and the reply processing
cmdEm = '{"emeter":{"get_realtime":{}}}'
enccmdEm = encrypt(cmdEm)
cmdSt = '{"system":{"get_sysinfo":{}}}'
enccmdSt = encrypt(cmdSt)
lastState = 2  # 2 is not a legal state. Thus a state change will be forced on the first run
lastWatts = 0
errCount = 0
failFlag = False
failMsg = "Empty"
updateFreq = offUpFreq

# Open a socket and get ready to send and receive data
try:
	sock_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
	sock_tcp.settimeout(10)
	sock_tcp.connect((ip, port))	
except Exception as e:
	indigo.server.log("Untrapped Exception attempting to open connection to %s:%s. %s|%s" % (ip, str(port), str(sys.exc_info()[0]), str(e)), type="TP-Link", isError=True)
	return

indigo.server.log("Connected to TPLink Wi-Fi Smartplug at %s." % ip, type="TP-Link", isError=False)

while True:
	try:
		# indigo.server.log("Starting TCP Read", type="TP-Link", isError=True)
		sock_tcp.send(enccmdSt)
		sRcvd = sock_tcp.recv(8096)
		
		if not sRcvd:
			indigo.server.log("No sRcvd received", type="TP-Link", isError=True)
		else:
			# indigo.server.log("Received sRcvd: |%s|" % (binascii.hexlify(bytearray(sRcvd))), type="TP-Link", isError=True)
			sData = json.loads(decrypt(sRcvd[4:]))
			state = sData['system']['get_sysinfo']['relay_state']

		sock_tcp.send(enccmdEm)
		eRcvd = sock_tcp.recv(8096)
		if not eRcvd:
			indigo.server.log("No eRcvd received", type="TP-Link", isError=True)
		else:
			# indigo.server.log("Received eRcvd: |%s|" % (binascii.hexlify(bytearray(eRcvd))), type="TP-Link", isError=True)
			eData = json.loads(decrypt(eRcvd[4:]))
			curWatts = eData['emeter']['get_realtime']['power_mw']
			curVolts = eData['emeter']['get_realtime']['voltage_mv']
			curAmps  = eData['emeter']['get_realtime']['current_ma']

		if abs(curWatts - lastWatts) > 5000 or state != lastState:
			startFreq = updateFreq
			if state == 1:
				updateFreq = onUpFreq
			else:
				updateFreq = offUpFreq
			if startFreq != updateFreq:
				indigo.server.log("Polling frequency reset to %s secs." % (str(updateFreq)), type="TP-Link", isError=False)

			lastWatts = curWatts # do this here so we get a delta against the last reported watts
			# indigo.server.log(u"Info log message: %s, %s, %s, %s" % (str(state), str(curWatts/1000), str(float(curAmps)/1000), str(curVolts/1000)))
			indigo.variable.updateValue(indigoState, value=str(state))
			indigo.variable.updateValue(indigoWatts, value=str(curWatts/1000))
			indigo.variable.updateValue(indigoAmps, value=str(float(curAmps)/1000))
			indigo.variable.updateValue(indigoVolts, value=str(curVolts/1000))
		
		lastState = state
		errCount = 0
	
	except socket.timeout:
		errCount += 1
		if errCount < 10:
			indigo.server.log("Timeout (" + str(errCount) + " fails) waiting for host " + ip + ":" + str(port), isError=True)
		else:
			failMsg = "Timeout waiting for host "
			failFlag = True

	except socket.error:
		errCount += 1
		if errCount < 10:
			indigo.server.log("Could not connect to host (" + str(errCount) + " fails)  " + ip + ":" + str(port), isError=True)
		else:
			failMsg = "Could not connect to host"
			failFlag = True

	except (KeyError, ValueError) as e:
		errCount += 1
		if errCount < 10:
			indigo.server.log("No valid response received (" + str(errCount) + " fails)  " + ip + ":" + str(port) + " | " + str(e), isError=True)
		else:
			failMsg = "No valid response received"
			failFlag = True
	
	except Exception as e:
		errCount += 1
		if errCount < 10:
			indigo.server.log("Untrapped exception(" + str(errCount) + " fails)  " + ip + ":" + str(port) + " | " + str(e), isError=True)
		else:
			failMsg = "Untrapped Exception" + str(sys.exc_info()[0]) + " | " + str(e)
			failFlag = True

	if failFlag:
		indigo.server.log("Quitting: %s %s:%s" % (failMsg, ip, str(port)), type="TP-Link", isError=True)
		break

	# Start a short, interuptable, event to create a delay between loop invocations
	exit = Event()
	exit.wait(updateFreq)
	exit.clear()

sock_tcp.close()
indigo.server.log("Received quit signal, shutting down connection to %s:%s" % (ip, port), type="TP-Link", isError=True)
return