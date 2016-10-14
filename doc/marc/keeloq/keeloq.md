<meta charset="UTF-8">

Keeloq for ChipWhisperer
========================

This is a set of tools to study power analysis of the Keeloq cipher.  It
is based on and integrated with the [ChipWhisperer](https://wiki.newae.com/)
software.

The Keeloq algorithm is very simple, yet omni-present in our current
world, making it an easy target to learn power analysis with.

Tutorials and example traces are provided for quick entry, even without
having to buy any specialized hardware.

Implementation and documentation copyright 2016 by Marc.
_________________________________________________________________________


Toolset overview
----------------

### Keeloq data capture

Loose collection of utilities to capture Keeloq data transmissions and
annotate them to power traces.

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

### [The Keeloq algorithm](keeloq_algorithm/keeloq_algorithm.md)

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

The traces are provided to complement the tutorials, and to serve as
starting point for further studies.

  - [HCS301 encoder chip](keeloq_examples_hcs301/keeloq_examples_hcs301.md)

______________________________________________________________________

_Document author: marc_ - _Document version: 25-Sep-2016_ - [Fork README](../../../README.md)
