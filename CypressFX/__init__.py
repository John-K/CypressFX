"""CypressFX is an object-oriented programming and control framework to
interact with Cypress's FX series of 'EZ-USB' chipsets"""

import usb.core
import usb.util
import intelhex
import pkg_resources


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
        data = bytearray(1)

        if enable_cpu:
            data[0] = 0
            print("reset CPU")
        else:
            print("stop CPU")
            data[0] = 1
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
        """Loads firmware from an IntelHex formatted file"""
        total = 0
        fw_hex = intelhex.IntelHex(filename)
        if not self.reset(enable_cpu=False):
            raise IOError("Failed to halt CPU")
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
            raise IOError("Failed to start CPU")

        return total
