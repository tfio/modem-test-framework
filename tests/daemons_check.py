# -*- coding: utf-8 -*-

import compat
import unittest
import sys

from plmn.results import *
from plmn.runner import *



class DaemonChecks(unittest.TestCase):
    def required_services(self):
        ps_ef = Runner.run_cmd('ps -ef')
        if 'ModemManager' not in ps_ef:
            Results.add_error('ps -ef', 'Modem Manager is not running. Start using: sudo start modemmanager')

        if 'NetworkManager' not in ps_ef:
            Results.add_error('ps -ef', 'Network Manager is not running. Start using: sudo start network-manager')

    def wwan_interfaces(self):
        ifcfg = Runner.run_cmd('ifconfig -a')
        if 'wwan' not in ifcfg:
            Results.add_error('ifconfig -a', 'wwan interface is not enumerated. Please restart network-manager using: sudo stop network-manager && sudo start network-manager')

    def test_daemons(self):
        self.required_services()
        self.wwan_interfaces()

if __name__ == '__main__':
    nargs = process_args()
    unittest.main(argv=sys.argv[nargs:], exit=False)
    Results.print_results()
