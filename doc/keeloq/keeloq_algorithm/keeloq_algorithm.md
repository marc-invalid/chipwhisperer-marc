
The Keeloq algorithm
====================


Algorithm description
---------------------

Keeloq works on 32-bit blocks and uses a 64-bit key.

It's a shift-register with non-linear feedback (NLFSR).  There are 528 rounds,
each producing one new bit from one key bit and several feedback bits.

Encryption is used in _Encoders_ or _Transmitters_ to generate rolling code
messages.  The plaintext, including a sequentially incrementing counter, is
encrypted using the *device key* (which is also known to the receiver).  This
ciphertext is sent along with the device serial number.

Decryption is used in _Decoders_ or _Receivers_.  The *device key* is looked
up by serial number and used to decrypt the message.  The counter
value is then verified against the allowed range.

Other uses for the algorithm include key derivation schemes, where two
32-bit ciphertexts (generated using a *manufacturer key*) are concatenated
to form the 64-bit device key.


### Encryption

The 32-bit plaintext is placed into the STATUS register (NLFSR, shown above
in the diagram).  After executing the algorithm for 528 rounds, the STATUS
register contains the ciphertext.

<center>![Diagram of Keeloq Encryption][image encrypt]_(Ruptor)_</center>


### Decryption

To revert the algorithm, only the tap positions and data directions are
changed.

<center>![Diagram of Keeloq Decryption][image decrypt]_(Ruptor)_</center>


[image encrypt]: ./encrypt.png
[image decrypt]: ./decrypt.png
_____________________________________________________________________________


Known implementations
---------------------

### Encoders (Transmitters)

  * Microchip ``HCSxxx`` (hardware implementation at 1.25 MHz)

> **### TODO ###**


### Decoders (Receivers)

> **### TODO ###**


_____________________________________________________________________________


Known crypto analysis
---------------------

> **### TODO ###**


_____________________________________________________________________________


Source code
-----------

### C (_Ruptor_)

        #define KeeLoq_NLF		0x3A5C742E
        #define bit(x,n)		(((x)>>(n))&1)
        #define g5(x,a,b,c,d,e)	(bit(x,a)+bit(x,b)*2+bit(x,c)*4+bit(x,d)*8+bit(x,e)*16)
        
        u32	KeeLoq_Encrypt (const u32 data, const u64 key) {
        	u32 x = data, r;
        	for (r = 0; r < 528; r++) {
        		x = (x>>1)^((bit(x,0)^bit(x,16)^(u32)bit(key,r&63)^bit(KeeLoq_NLF,g5(x,1,9,20,26,31)))<<31);
        	}
        	return x;
        }
        
        u32	KeeLoq_Decrypt (const u32 data, const u64 key) {
        	u32 x = data, r;
        	for (r = 0; r < 528; r++) {
        		x = (x<<1)^bit(x,31)^bit(x,15)^(u32)bit(key,(15-r)&63)^bit(KeeLoq_NLF,g5(x,0,8,19,25,30));
        	}
        	return x;
        }


### Python

        #--- KEELOQ: Non-Linear-Function 0x3A5C742E in algebraic normal form

        def keeloqNLF(a, b, c, d, e):
            return (d + e + a*c + a*e + b*c + b*e + c*d + d*e + a*d*e + a*c*e + a*b*d + a*b*c) % 2;
        
        #---- KEELOQ: Decrypt

        def keeloqDecryptCalcLSB(data, keybit):
            nlf = keeloqNLF((data>>30)%2, (data>>25)%2, (data>>19)%2, (data>>8)%2, (data>>0)%2)
            lsb = (keybit ^ (data>>31) ^ (data>>15) ^ nlf) % 2
            return lsb

        def keeloqDecryptKeybit(data, keybit):
            return ((data & 0x7FFFFFFF)<<1) ^ keeloqDecryptCalcLSB(data, keybit)

        def keeloqDecrypt(data, key):
            for round in range(0,528):
                keybit = (key >> ((591-round) % 64)) % 2
                data = keeloqDecryptKeybit(data, keybit)
            return data

        #---- KEELOQ: Encrypt
        
        def keeloqEncryptCalcMSB(data, keybit):
            nlf = keeloqNLF((data>>31)%2, (data>>26)%2, (data>>20)%2, (data>>9)%2, (data>>1)%2)
            msb = (keybit ^ (data>>0) ^ (data>>16) ^ nlf) % 2
            return msb

        def keeloqEncryptKeybit(data, keybit):
            return (keeloqEncryptCalcMSB(data, keybit) << 31) ^ (data >> 1)

> **### TODO ###**: keeloqEncrypt() is missing


______________________________________________________________________

_Document version: 20-Sep-2016_
