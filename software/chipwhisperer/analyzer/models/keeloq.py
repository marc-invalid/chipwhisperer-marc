#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016 MARC
#
# FIXME: hamming weight table taken from CW

#--- Hamming weight / Hamming distance (HW/HD)

##Generate this table with:
#HW = []
#for n in range(0, 256):
#    HW = HW + [bin(n).count("1")]
HW8Bit = [0, 1, 1, 2, 1, 2, 2, 3, 1, 2, 2, 3, 2, 3, 3, 4, 1, 2, 2, 3, 2, 3, 3,
          4, 2, 3, 3, 4, 3, 4, 4, 5, 1, 2, 2, 3, 2, 3, 3, 4, 2, 3, 3, 4, 3, 4,
          4, 5, 2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6, 1, 2, 2, 3, 2,
          3, 3, 4, 2, 3, 3, 4, 3, 4, 4, 5, 2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5,
          4, 5, 5, 6, 2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6, 3, 4, 4,
          5, 4, 5, 5, 6, 4, 5, 5, 6, 5, 6, 6, 7, 1, 2, 2, 3, 2, 3, 3, 4, 2, 3,
          3, 4, 3, 4, 4, 5, 2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6, 2,
          3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6, 3, 4, 4, 5, 4, 5, 5, 6,
          4, 5, 5, 6, 5, 6, 6, 7, 2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5,
          6, 3, 4, 4, 5, 4, 5, 5, 6, 4, 5, 5, 6, 5, 6, 6, 7, 3, 4, 4, 5, 4, 5,
          5, 6, 4, 5, 5, 6, 5, 6, 6, 7, 4, 5, 5, 6, 5, 6, 6, 7, 5, 6, 6, 7, 6,
          7, 7, 8]

def keeloqGetHW(var):
    hw = 0
    while var > 0:
        hw = hw + HW8Bit[var % 256]
        var = var >> 8
    return hw

def keeloqGetHD(var1, var2):
    return keeloqGetHW(var1 ^ var2)


#--- KEELOQ: Non-Linear-Function 0x3A5C742E in algebraic normal form

def keeloqNLF(a, b, c, d, e):
    return (d + e + a*c + a*e + b*c + b*e + c*d + d*e + a*d*e + a*c*e + a*b*d + a*b*c) % 2;

#---- KEELOQ: Calc next bit from current state

def keeloqEncryptCalcMSB(data, keybit):
    nlf = keeloqNLF((data>>31)%2, (data>>26)%2, (data>>20)%2, (data>>9)%2, (data>>1)%2)
    msb = (keybit ^ (data>>0) ^ (data>>16) ^ nlf) % 2
    return msb

def keeloqDecryptCalcLSB(data, keybit):
    nlf = keeloqNLF((data>>30)%2, (data>>25)%2, (data>>19)%2, (data>>8)%2, (data>>0)%2)
    lsb = (keybit ^ (data>>31) ^ (data>>15) ^ nlf) % 2
    return lsb

#--- KEELOQ: Encrypts/decrypts one round (without key schedule, caller supplies key bit).  Returns new data.

def keeloqEncryptKeybit(data, keybit):
    return (keeloqEncryptCalcMSB(data, keybit) << 31) ^ (data >> 1)

def keeloqDecryptKeybit(data, keybit):
    return ((data & 0x7FFFFFFF)<<1) ^ keeloqDecryptCalcLSB(data, keybit)

#--- KEELOQ: Encrypts/decrypts one round (without key schedule), returns new data and hamming distance

def keeloqEncryptKeybitHD(data, keybit):
    encrypt = keeloqEncryptKeybit(data, keybit)
    return encrypt, keeloqGetHD(data, encrypt)

def keeloqDecryptKeybitHD(data, keybit):
    decrypt = keeloqDecryptKeybit(data, keybit)
    return decrypt, keeloqGetHD(data, decrypt)

#--- KEELOQ: Full decrypt

def keeloqDecrypt(data, key):
    for round in range(0,528):
        keybit = (key >> ((591-round) % 64)) % 2
        data = keeloqDecryptKeybit(data, keybit)
    return data

#--- KEELOQ: Filter keystream so it only contains valid chars "01"

def keeloqFilterKeystream(keystream=None):
    return filter(lambda ch: ch in "01", keystream) if (keystream is not None) else ""

#--- KEELOQ: Partial decrypt with keystream

def keeloqDecryptKeystream(data, keystream=None, round=528):
    keystream = keeloqFilterKeystream(keystream)
    for i in range(0, len(keystream)):
        data = keeloqDecryptKeybit(data, int(keystream[i]))
    round -= len(keystream)
    return data, round

#--- KEELOQ: Test

def test():
    #Manual tests right now - need to automate this.

    ##### AES-128 Tests
    print "**********KEELOQ  Tests***************"
    print "TODO"


if __name__ == "__main__":
    test()

