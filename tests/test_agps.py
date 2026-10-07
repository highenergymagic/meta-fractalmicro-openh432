# SPDX-License-Identifier: MIT
import hashlib
import importlib.util
import operator
from functools import reduce
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
SOURCE=HERE/"openh432-agps.py"
if not SOURCE.exists():
    SOURCE=HERE.parent/"recipes-navigation/openh432-agps/files/openh432-agps.py"
spec=importlib.util.spec_from_file_location("agps",SOURCE)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
HOUR=409818
NOW=m.GPS_EPOCH+HOUR*3600-m.OFFSET+600
def sample():
    data=b""
    for sat in range(1,33):
        words=[HOUR|(sat<<24)]+[0]*16
        words.append(reduce(operator.xor,words,0))
        data+=struct.pack("<18I",*words)
    return data
class AgpsTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(len(m.current_records(sample(),NOW)),32)
    def test_invalid_size(self):
        for data in (b"",sample()[:-1],bytes(m.MAX_BYTES+1)):
            with self.assertRaises(ValueError): m.inspect(data)
    def test_corrupt_record(self):
        b=bytearray(sample());b[8]^=1
        with self.assertRaises(ValueError): m.inspect(b)
    def test_zero_record_omitted(self):
        b=bytearray(sample()); words=list(struct.unpack("<18I",b[:72]))
        words[0]&=0xffffff;words[-1]=reduce(operator.xor,words[:-1],0)
        b[:72]=struct.pack("<18I",*words)
        self.assertEqual(len(m.current_records(b,NOW)),31)
    def test_expiry(self):
        for now in (NOW-21600,NOW+21600,m.OFFSET_VALID_UNTIL):
            with self.assertRaises(ValueError): m.current_records(sample(),now)
    def test_md5(self):
        data=sample()
        m.verify_md5(data,hashlib.md5(data).hexdigest().encode()+b" \x00\n")
        with self.assertRaises(ValueError): m.verify_md5(data,b"0"*32)
    def test_nmea(self):
        self.assertEqual(m.frame(b"PMTK607"),b"$PMTK607*33\r\n")
        self.assertEqual(m.decode(b"$PMTK001,721,3*34"),[b"PMTK001",b"721",b"3"])
        self.assertIsNone(m.decode(b"$PMTK001,721,3*00"))
    def test_redirect_refused(self):
        with self.assertRaises(ValueError):
            m.NoRedirect().redirect_request(None,None,302,None,None,"http://example.invalid/")
    def test_no_arbitrary_source(self):
        with self.assertRaises(ValueError): m.retrieve("https://example.invalid",10)
        self.assertEqual(m.BASE,"https://gpsdata-proxy-openh432.highenergymagic.net/")
    def test_clock_missing(self):
        with patch.object(m.Path,"stat",side_effect=FileNotFoundError):
            self.assertFalse(m.clock_ready(NOW))
    def test_rejected_ack(self):
        obj=object.__new__(m.Receiver)
        with patch.object(obj,"send"),patch.object(obj,"wait",return_value=[b"PMTK001",b"721",b"2"]):
            with self.assertRaises(ValueError):obj.command(b"PMTK721",b"721")
    def test_success_ack(self):
        obj=object.__new__(m.Receiver)
        with patch.object(obj,"send"),patch.object(obj,"wait",return_value=[b"PMTK001",b"721",b"3"]):
            obj.command(b"PMTK721",b"721")

if __name__=="__main__":
    unittest.main()
