#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2016 by Marc
#
# Synopsis:
#
#	Converts a list of HEX codes into ChipWhisperer "native" npy format.
#
#	The input is one HEX key/plaintext/ciphertext per line.  Must be 16 bytes or less
#	(will be padded to 16 bytes with trailing 00).
#
#	Each HEX input will be written into a separate output file.  The filenames are taken
#	from the second input file, a list of filenames.
#
# Example:
#
#	We have captured 10 traces with ChipWhisperer, and logged the 10 ciphertexts with an
#	external device.  Now we want to annotate the ciphertexts so that ChipWhisperer can
#	use them.
#
#	Step 1:	Gather list of trace ciphertext filenames and verify the number of them
#
#			cd traces
#			ls *_textout.npy | sort | tee textout_filenames.txt | grep "npy" -c
#
#	Step 2:	Filter list of ciphertexts and verify the number of them
#
#			cat textout_log.txt | grep "HEX=3" | sed -e "s/.*HEX=//" -e "s/ .*//" | uniq | sed -e "s/.*-//" | tee textout_hexdata.txt | grep ".*" -c
#
#	Step 3:	Backup the original (empty) files
#
#			mkdir textout_empty_DEL
#			mv *_textout.npy textout_empty_DEL/
#
#	Step 4:	Edit this program to reflect the filenames and number of items (near end of file)
#
#			vi ../hex_to_npy.py
#
#	Step 5:	Run this program
#
#			python2.7 ../hex_to_npy.py
#
#
# See also:
#
#	vi ./chipwhisperer/common/traces/TraceContainerNative.py
#

import os
import numpy as np

from binascii import hexlify

class TestClass():
    _name = "Test/TestClass"

    def __init__(self, parentParam=None, configfile=None):
        self.configfile = configfile
        print "Reached: TestClass init"
	self.byteSize = 16
        self.numTrace = 1234



#-- Convert "data.txt" with one hexnumber per line, into a series of individual files ("filenames.txt")

    def import_many(self, data_name, filenames, numfiles):
        self.numTrace = numfiles

        data_file    = open(data_name, 'r')
        data_linenum = 0

        name_file    = open(filenames, 'r')
        name_linenum = 0

        for trace_num in range(0, self.numTrace):

            #--- get output filename

            name_linenum += 1
            name_raw   = name_file.readline()
            name_clean = name_raw.strip('\r\n')

            if (len(name_clean)<2):
                print "FILENAMES line %d: syntax error" % (name_linenum)
                break

            #--- get input data

            data_linenum += 1
            data_raw   = data_file.readline()
            data_clean = data_raw.strip('\r\n \t\xa0')

            if (len(data_clean)<2):
                print "INPUTDATA line %d: syntax error" % (data_linenum)
                break

            #--- verbose messages

            print "Trace=%03d data=0x%s filename=%s" % (trace_num, data_clean.upper(), name_clean)

            #--- convert input to native (zero-padded or truncated to fit)
            #
            # native is a list of bytearrays, with just one single entry

            data_native = np.zeros([1, self.byteSize], dtype=np.uint8)
            for byte in range(0, self.byteSize):
                if (byte*2) >= len(data_clean):
                    break
                data_native[0, byte] = int(data_clean[byte*2+0] + data_clean[byte*2+1], 16)

            #--- write to file

            np.save(name_clean, data_native)

        data_file.close()
        name_file.close()




if __name__ == "__main__":

    print "Reached: main"

    test = TestClass()

    test.import_many("textout_hexdata.txt", "textout_filenames.txt", 540)







