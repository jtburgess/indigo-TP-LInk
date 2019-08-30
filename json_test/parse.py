#! /usr/bin/env python
# -*- coding: utf-8 -*-

import json
import sys

filename = sys.argv[1]

jsonFile = open(filename, "r")
if jsonFile.mode == 'r':
    result = jsonFile.read()

data = json.loads(result)


for i in data:
    # print (i)
    for ii in data[i]:
         # print (ii,':',data[i][ii])
         for iii in data[i][ii]:
             print (i, "----", ii, "----", iii,'----', data[i][ii][iii])
             print "\n"
             # for iiii in data[i][ii][iii]:
             #     print (iiii,':',data[i][ii][iii][iiii])

# print "Done with result dump\n\n\n"
# print data['system']['get_sysinfo']['children'], "\n\n"

for child in data['system']['get_sysinfo']['children']:
    print ("%13s  %s" % (child['alias'], child['state']))

# print
# print data['emeter']['get_realtime'], "\n\n"
# for element in data['emeter']['get_realtime']:
#     print element
