
# Keeloq for ChipWhisperer

This is a set of tools to perform power analysis of the Keeloq cipher.
It is based on and integrated with the ChipWhisperer software.  Tutorials
and example traces are provided for a quick learning experience.

Implementation and documentation copyright 2016 by Marc.

___

## Toolset overview

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

___

## Example traces

### HCS301 raw

Useful to study trace preparation.  Contains synchronization issues
(RC oscillator clock drift).

  - 500 semi-consecutive messages
  - 48.2 MHz sample rate (approx 200 samples per cipher round)
  - Covers last 100 rounds (approx)
  - Captured with ChipWhisperer CW1002 hardware kit


### HCS301 sync

Derived from **HCS301 raw**, with clock drift compensated and freaks removed.
Useful to study any aspect of the power behavior.

  - 500 semi-consecutive messages
  - 200 samples per cipher round
  - Covers last 100 rounds (approx)


### HCS301 bits (full / peak)

Derived from **HCS301 sync**, trimmed to just the point range where MSB/LSB
bit values leak.

  - 500 semi-consecutive messages
  - **### FIXME ###** samples per cipher round
  - Cover last 100 rounds (approx)


### HCS301 shift (full / peak)

Derived from **HCS301 sync**, trimmed to just the point range where the
status register leaks.

  - 500 semi-consecutive messages
  - **### FIXME ###** samples per cipher round
  - Cover last 100 rounds (approx)

___

## Tutorial overview

### The Keeloq algorithm

Rehash of available information about the Keeloq algorithm.

  - Algorithm description
  - Source code
  - Existing implementations

### Capture power consumption of HCS301

  - Prepare victim (GND shunt)
  - Connect CW1002 and differential probe
  - Configure CW Capture software
  - Find suitable triggers

### Capture ciphertext of HCS301 with GNU Radio

  - Configure GNU Radio live-boot environment
  - Prepare reception of RF messages
  - Perform capture of power and RF data simultaneously
  - Annotate ciphertext data to power traces

### Preparation of traces

  - Compensate for clock drift and eliminate freaks
  - Recover Keeloq round timing
  - Identify and extract interesting point ranges
  - Compress to peaks
  - Export polished results

### Bit model attack on Keeloq

  **### TODO ###**

### Hamming distance model attack on Keeloq

  **### TODO ###**

___

# Thanks

Thanks to *Colin O'Flynn* for making ChipWhisperer open-source.  This
extension would not exist otherwise.  Also, because of it, I learned
python, git, and markdown.  Thanks for that!

___

_Document version: 08-Sep-2016_
