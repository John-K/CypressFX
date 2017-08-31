"""CypressFX is an object-oriented programming and control framework to
interact with Cypress's FX series of 'EZ-USB' chipsets"""

import usb.core
import usb.util
import intelhex
import pkg_resources
from binascii import hexlify, unhexlify
from array import array

class FX2(object):
    """Supports firmware and EEPROM operations on Cypress FX2 devices"""
    REQ_WRITE = (usb.core.util.ENDPOINT_OUT | usb.core.util.CTRL_TYPE_VENDOR |
                 usb.core.util.CTRL_RECIPIENT_DEVICE)
    REQ_READ = (usb.core.util.ENDPOINT_IN | usb.core.util.CTRL_TYPE_VENDOR |
                usb.core.util.CTRL_RECIPIENT_DEVICE)
    CMD_RW_INTERNAL = 0xA0
    CMD_RW_EEPROM = 0xA2
    MAX_CTRL_BUFFER_LENGTH = 4096

    def __init__(self, usbDev):
        if not usbDev:
            raise AttributeError("USB Device passed is not valid")
        self.dev = usbDev
        self.running_vend_ax_fw = False

    @staticmethod
    def with_vid_pid(vid, pid):
        """Opens a device with a given USB VendorID and ProductID"""
        dev = usb.core.find(idVendor=vid, idProduct=pid)
        if dev:
            return FX2(dev)
        return None

    @staticmethod
    def with_bus_address(bus, address):
        """Opens a device at a given USB Bus and Address"""
        dev = usb.core.find(bus=bus, address=address)
        if dev:
            return FX2(dev)
        return None

    def reset(self, enable_cpu):
        """Resets a device and optionally enables the CPU core"""
        cpu_address = 0xE600
        data = 0

        if enable_cpu:
            print("reset CPU")
        else:
            print("stop CPU")
            data = 1

        wrote = self.__send_usbctrldata(cpu_address & 0xFFFF, bytes(data))
        if not wrote > 0:
            return False
        return True

    def __ensure_vend_ax_firmware(self):
        """Makes sure that we're running the default code"""
        if not self.running_vend_ax_fw:
            hexfile = pkg_resources.resource_filename('CypressFX',
                                                      'vend_ax.hex')
            self.load_intelhex_firmware(hexfile)
            self.running_vend_ax_fw = True

    def read_eeprom(self, length=8):
        """Reads bytes from the device's EEPROM"""
        self.__ensure_vend_ax_firmware()
        data = self.dev.ctrl_transfer(self.REQ_READ, self.CMD_RW_EEPROM, 0x00,
                                      0x00, length)
        return data

    def write_eeprom(self, data):
        """Writes data to the device's EEPROM"""
        self.__ensure_vend_ax_firmware()
        wrote = self.dev.ctrl_transfer(self.REQ_WRITE, self.CMD_RW_EEPROM,
                                       0x00, 0x00, data)
        return wrote

    def __send_usbctrldata(self, addr, data):
        wrote = self.dev.ctrl_transfer(self.REQ_WRITE,
                                       self.CMD_RW_INTERNAL,
                                       addr, 0x00, data)
        if not wrote == len(data):
            raise IOError("Failed to write %d bytes to %x" % (len(data),
                          addr))
        return wrote

    def load_intelhex_firmware(self, filename):
        INTEL_HEX_HDR_LEN = 5
        total = 0

        f = open(filename, 'r')
        if not f:
            print("Could not open '{}'".format(filename))
            raise IntelHexError("unable to open file")

        # halt CPU
        if not self.reset(enable_cpu=False):
            raise CypressFXCPUResetError()

        num_segments = 0
        buf = []
        buf_start = 0
        buf_end = 0

        for line in f:
            line = line.rstrip(' \r\n')

            if line[0] == ':':
                bin = array('B', unhexlify(line[1:]))

            rec_len = bin[0]
            if len(bin) != rec_len + INTEL_HEX_HDR_LEN:
                raise IntelHexError("lengths do not match: {} vs {}".format(
                                    len(bin), rec_len + INTEL_HEX_HDR_LEN))

            addr = bin[1] * 256 + bin[2]

            rec_type = bin[3]
            if not (0 <= rec_type <= 5):
                raise IntelHexError("Invalid record type {}".format(rec_type))

            crc = sum(bin)
            crc &= 0xFF
            if crc != 0:
                raise IntelHexError("Invalid checksum value")

            if rec_type == 0:
                # data record
                if (len(buf) > 0 and buf_end != addr) or (len(buf) +
                   rec_len) > 1023:
                    num_segments += 1
                    wrote = self.__send_usbctrldata(buf_start, buf)
                    total += wrote
                    print("0x{0:04x} wrote {1:} bytes".format(buf_start,
                          wrote))
                    buf_start = 0
                    buf_end = 0
                    buf = []

                if buf_start == 0 and len(buf) == 0:
                    buf_start = addr
                    buf_end = addr

                buf += bin[4:4+rec_len]
                buf_end += rec_len
            elif rec_type == 1:
                pass
            else:
                print("unhandled record type {}".format(rec_type))

        if len(buf) > 0:
            num_segments += 1
            wrote = self.__send_usbctrldata(buf_start, buf)
            total += wrote
            print("0x{0:04x} wrote {1:} bytes".format(buf_start, wrote))

        print("WROTE: {} bytes, {} segments".format(total, num_segments))
        if not self.reset(enable_cpu=True):
            raise CypressFXCPUResetError()

        return total

    def old_load_intelhex_firmware(self, filename):
        """Loads firmware from an IntelHex formatted file"""
        total = 0
        fw_hex = intelhex.IntelHex(filename)
        if not self.reset(enable_cpu=False):
            print("Failed to halt CPU")
            raise
        for seg_start, seg_end in fw_hex.segments():
            data = fw_hex.tobinstr(start=seg_start, end=seg_end-1)
            # libusb issue #110 https://github.com/libusb/libusb/issues/110
            offset = 0
            while len(data) > 0:
                end = len(data)
                if end > self.MAX_CTRL_BUFFER_LENGTH:
                    end = self.MAX_CTRL_BUFFER_LENGTH
                print("0x{0:04x} loading {1:4d} bytes".format(
                      seg_start + offset, end))
                wrote = self.dev.ctrl_transfer(self.REQ_WRITE,
                                               self.CMD_RW_INTERNAL,
                                               seg_start+offset, 0x00,
                                               data[:end])
                if not wrote == end:
                    raise IOError("Failed to write %d bytes to %x" % (end,
                                  seg_start))
                total += wrote
                offset += wrote
                data = data[end:]

        if not self.reset(enable_cpu=True):
            print("Failed to start CPU")
            raise
        return total


class CypressFXError(Exception):
    '''Base CypressFX Exception'''
    _fmt = 'CypressFX base error'

    def __init__(self, msg=None):
        '''Init exception with the given message'''
        self.msg = msg

    def __str__(self):
        '''Returns a string representation of the exception'''
        if self.msg:
            return self.msg


class CypressFXCPUResetError(CypressFXError):
    _fmt = 'Cypress FX CPU Reset Error'


class USBCommunicationError(CypressFXError):
    _fmt = 'USB communication error'


class IntelHexError(CypressFXError):
    '''Base Exception class for Intel Hex file parsing'''
    _fmt = 'IntelHex base error'
