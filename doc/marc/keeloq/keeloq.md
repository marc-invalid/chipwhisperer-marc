<meta charset="UTF-8">

Keeloq for ChipWhisperer
========================

This is a set of tools to perform power analysis of the Keeloq cipher.  It
is based on and integrated with the [ChipWhisperer](https://wiki.newae.com/)
software.  Tutorials and example traces are provided for a quick learning
experience.

Implementation and documentation copyright 2016 by Marc.
_________________________________________________________________________


Toolset overview
----------------

### Keeloq data capture

Loose collection of utilities to capture Keeloq data transmissions and
annotate them to the power traces.

  - GNURadio flow to receive and demodulate RF messages
  - Keeloq OOK decoder to convert baseband to HEX values
  - Script to annotate HEX values to traces captured with ChipWhisperer


### Preprocessing filter: Resync Slice-to-Slot

Powerful plugin to prepare traces for analysis.

  - Compensate for internal RC oscillator drift (HCSxxx)
  - Extract arbitrary point ranges from each round
  - Compress ranges to one peak per round


### Trace Explorer partition modes: Keeloq (various)

Several partition modes relevant to the Keeloq algorithm.  Useful for visual
exploration, understanding the attacks, and even executing them manually.

  - **Bit (various)**: Partition by ciphertext output or intermediate
                       LSB/MSB value
  - **HD (various)**:  Partition by Hamming distance of status register
                       during shift operations


### Attack module: Keeloq DPA

Container for several automatted attacks:

  - **Encoder Bit model**: Attacks the intermediate MSB bit value.
  - **Encoder HD model**:  Attacks the status register Hamming distance
                           during shift operations.

_________________________________________________________________________


Tutorial overview
-----------------

### [The Keeloq algorithm](keeloq_algorithm/keeloq_algorithm.html)

Rehash of public information about Keeloq.

  - Algorithm description
  - Implementations
  - Crypto analysis
  - Source code


### Capture power consumption of HCS301

> **### TODO ###**: Not finished yet

  - Prepare victim (GND shunt)
  - Connect CW1002 and differential probe
  - Configure CW Capture software
  - Find suitable triggers


### Capture ciphertext of HCS301 with GNU Radio

> **### TODO ###**: Not finished yet

  - Configure GNU Radio live-boot environment
  - Prepare reception of RF messages
  - Perform capture of power and RF data simultaneously
  - Annotate ciphertext data to power traces


### Preparation of traces

> **### TODO ###**: Not finished yet

  - Compensate for clock drift and eliminate freaks
  - Recover Keeloq round timing
  - Identify and extract interesting point ranges
  - Compress to peaks
  - Export polished results


### Bit model attack on Keeloq

> **### TODO ###**: Not finished yet


### Hamming distance model attack on Keeloq

> **### TODO ###**: Not finished yet


_______________________________________________________________________


Example traces
--------------

To complement the tutorials, the following example projects are provided.


### HCS301 raw

Useful to study trace preparation.  Contains synchronization issues
(RC oscillator clock drift).

> **### TODO ###**

  - \> 500 semi-consecutive¹ messages
  - 48.2 MHz sample rate (approx 200 samples per cipher round)
  - Covers last 100 rounds (approx)
  - Captured with ChipWhisperer CW1002 hardware kit
  - Ciphertext annotated


### [HCS301 sync](examples/HCS301_sync.zip)

Derived from **HCS301 raw**, with clock drift compensated and freaks
removed.  Useful to study any aspect of the power behavior.

  - 501 semi-consecutive¹ messages
  - 200 samples per cipher round
  - **### FIXME ###** rounds covered


### HCS301 bits ([full](examples/HCS301_bits_full.zip) / [peak](examples/HCS301_bits_peak.zip))

Derived from **HCS301 sync**, trimmed to just the point range where
MSB/LSB bit values leak.  Useful to study bit model attacks.

  - Samples per cipher round: 40 (full) or 3 (peak)
  - Each round is zero-padded for visual guidance


### HCS301 shift (full / peak)

> **### TODO ###**

Derived from **HCS301 sync**, trimmed to just the point range where the
status register leaks.  Useful to study Hamming distance attacks.

  - **### FIXME ###** samples per cipher round


### Notes:

¹ semi-consecutive:

  > Only every other generated message was captured, and some of them
    were discarded afterwards.  All messages are from the same device,
    the internal counter is increasing, the step size is small, but it
    is not 1.
______________________________________________________________________

_Document version: 25-Sep-2016_
