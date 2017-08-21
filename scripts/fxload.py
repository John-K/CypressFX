#!/usr/bin/env python
"""fxload python tool"""

from CypressFX import FX2
import argparse
import binascii
import sys

def main():
    parser = argparse.ArgumentParser(description='')

    parser.add_argument('-i', '--input', metavar='<firmware.hex>', help="Input file for flashing")

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-d', '--device', metavar='<vid>:<pid>', help='USB VID:PID of target device')
    group.add_argument('-a', '--address', '-p', metavar='<bus>,<addr>', help="USB bus and address of target device")

    group2 = parser.add_argument_group(title="EEPROM functions")
    parser.add_argument('-r', '--read-eeprom', help='Read data from EEPROM', action="store_true")
    parser.add_argument('-w', '--write-eeprom', metavar='<hexdata>', help="Write data to EEPROM")

    args = parser.parse_args()
    
    dev = None

    if args.device:
        info = args.device.split(':')
        if not len(info) == 2:
            print "Error: invalid device '%s'" % args.device
            sys.exit(1)
        vid = int(info[0],0)
        pid = int(info[1],0)
        dev = FX2.with_vid_pid(vid, pid)
    elif args.address:
        info = args.address.split(',')
        if not len(info) == 2:
            print "Error: invalid device address '%s'" % args.address
            sys.exit(1)
        bus = int(info[0])
        addr = int(info[1])
        dev = FX2.with_bus_address(bus, addr)
    else:
        print "Error: no device was specified"
        sys.exit(1)

    if not dev:
        print "Error: could not find a suitable USB device"
        sys.exit(1)

    if args.read_eeprom:
        print "Reading EEPROM..."
        data = dev.read_eeprom()
        print "Data[%d]" % len(data),
        for d in data:
            print "%02x" % d,
        print

    if args.write_eeprom:
        to_write = len(args.write_eeprom)
        if to_write % 2 != 0:
            print "Error: an odd number of characters was supplied"
            sys.exit(1)
        to_write /= 2
        print "Writing %d bytes to EEPROM..." % to_write
        data = binascii.unhexlify(args.write_eeprom)
        assert to_write == len(data)
        wrote = dev.write_eeprom(data)
        assert wrote == to_write
        print

    if args.input:
        print "Programming '%s'..." % args.input,
        wrote = dev.load_intelhex_firmware(args.input)
        if wrote > 0:
            print "complete!"
        else:
            print "failed!"
            
if __name__ == '__main__':
    main()