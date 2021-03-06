# -*- coding: utf-8 -*-

import re
from utils import *
from results import *
from runner import Runner
from mmcli_parser import MMCLIParser

import time

class ModemCmds:
    @classmethod
    def mmcli_cmd_present(cls):
        mmcli_exec = Results.get_state('MMCLI Exec')
        if mmcli_exec is None:
            mmcli_exec = Runner.run_cmd('which mmcli')
            if mmcli_exec is not None and len(mmcli_exec.strip()) is 0:
                Results.add_state('MMCLI Exec', mmcli_exec.strip())

        assert mmcli_exec is not None

    @classmethod
    def list_modems(cls):
        logging.debug('Listing modems.')
        cls.mmcli_cmd_present()

        modem_loc = Results.get_state('Modem Location')
        if modem_loc is None:
            mmcli = Runner.run_cmd('mmcli -L')
            if '/org/freedesktop/ModemManager' not in mmcli:
                Results.add_error('mmcli -L', 'Modem not found. Please enable the modem through instrument UI.')
            else:
                modem_loc = re.search(r'(/org/freedesktop/ModemManager\d/Modem/\d)', mmcli.strip()).group(1)
                Results.add_state('Modem Location', modem_loc)
                Results.add_state('Modem Index', re.search(r'/org/freedesktop/ModemManager\d/Modem/(\d)', modem_loc).group(1))

        logging.debug('Modem Location: ' + str(modem_loc))
        logging.debug('Modem Index: ' + str(Results.get_state('Modem Index')))
        assert modem_loc is not None

    @classmethod
    def list_modem_wait(cls):
        cls.mmcli_cmd_present()

        modem_loc = Results.get_state('Modem Location')
        if modem_loc is None:
            for idx in range(0,60):
                mmcli = Runner.run_cmd('mmcli -L')
                if '/org/freedesktop/ModemManager1/Modem/' not in mmcli:
                    logging.debug('Modem not listed yet. Waiting..')
                    time.sleep(1)
                else:
                    modem_loc = re.search(r'(/org/freedesktop/ModemManager\d/Modem/\d)', mmcli.strip()).group(1)
                    Results.add_state('Modem Location', modem_loc)
                    Results.add_state('Modem Index',
                                      re.search(r'/org/freedesktop/ModemManager\d/Modem/(\d)', modem_loc).group(1))
                    break


    @classmethod
    def modem_enabled(cls):
        cls.list_modems()

        modem_en = Results.get_state('Modem Enabled')
        if modem_en is None:
            modem_idx = Results.get_state('Modem Index')

            mmcli = Runner.run_cmd('mmcli -m {} --simple-status'.format(modem_idx))
            res = MMCLIParser.parse(mmcli)

            logging.debug('mmcli -m {} --simple-status output'.format(modem_idx))
            logging.debug(res)

            if res is not None and 'Status' in res.keys() and 'state' in res['Status'].keys():
                if res['Status']['state'] == 'disabled':
                    Results.add_error('mmcli -m {} --simple-status'.format(modem_idx), 'Modem not enabled. Please enable using mmcli -m {} --enable'.format(modem_idx))

                elif res['Status']['state'] != 'registered' and res['Status']['state'] != 'connected' and res['Status']['state'] != 'searching' and res['Status']['state'] != 'enabled':
                    Results.add_error('mmcli -m {} --simple-status'.format(modem_idx),
                                      'Modem not enabled/registered. Contact support with log files')
                else:
                    modem_en = True
                    Results.add_state('Modem Enabled', modem_en)

        assert modem_en is True

    @classmethod
    def modem_info(cls):
        # This is a re-entrant method, so anytime this function is called:
        # - We re-run all commands and get complete modem info.
        Results.reset()

        cls.mmcli_cmd_present()
        cls.list_modems()
        cls.modem_enabled()
        cls.sim_present()
        cls.sim_unlocked()
        cls.sim_registered()

        modem_info = Results.get_state('Modem Info')
        if modem_info is None:
            modem_idx = Results.get_state('Modem Index')
            assert modem_idx is not None

            mmcli = Runner.run_cmd('mmcli -m {}'.format(modem_idx)).strip()
            modem_info = MMCLIParser.parse(mmcli)
            if len(modem_info.keys()) > 0:
                Results.add_state('Modem Info', modem_info)
            else:
                Results.add_error('mmcli -m {}'.format(modem_idx),
                                  'Error getting/parsing modem info. Contact support with test output.')

        assert modem_info is not None

    @classmethod
    def sim_present(cls):
        cls.list_modems()

        sim_present = Results.get_state('SIM Present')
        if sim_present is None:
            modem_idx = Results.get_state('Modem Index')
            mmcli = Runner.run_cmd('mmcli -m {}'.format(modem_idx))
            res = MMCLIParser.parse(mmcli)
            if 'SIM' in res.keys() and 'Status' in res.keys() and 'state' in res['Status'].keys():
                if res['Status']['state'] == 'failed':
                    Results.add_error('mmcli -m {}'.format(modem_idx) + ' | gerp state',
                                      'SIM card not found. Insert SIM card and restart modem')
                else:
                    sim_present = True
                    Results.add_state('SIM Present', sim_present)

        assert sim_present is True

    @classmethod
    def sim_unlocked(cls):
        cls.sim_present()

        sim_unlocked = Results.get_state('SIM Unlocked')
        if sim_unlocked is None:
            modem_idx = Results.get_state('Modem Index')
            assert modem_idx is not None

            mmcli = Runner.run_cmd('mmcli -m {}'.format(modem_idx))
            res = MMCLIParser.parse(mmcli)
            if '3GPP' in res.keys() and 'enabled locks' in res['3GPP'].keys():
                if res['3GPP']['enabled locks'] == 'none':
                    sim_unlocked = True
                    Results.add_state('SIM Unlocked', sim_unlocked)
                else:
                    Results.add_state('SIM Unlocked', False)
                    Results.add_error('mmcli -m {}'.format(modem_idx) + ' | grep \'enabled lock\'', 'SIM card is locked with a PIN.')
        assert sim_unlocked is True

    @classmethod
    def is_sim_registered(cls):
        cls.sim_present()
        cls.sim_unlocked()

        sim_registered = Results.get_state('SIM Registered')
        logging.debug('SIM Registered: ' + str(sim_registered))

        if sim_registered is not True:
            modem_idx = Results.get_state('Modem Index')
            assert modem_idx is not None

            mmcli = Runner.run_cmd('mmcli -m {}'.format(modem_idx))
            res = MMCLIParser.parse(mmcli)
            if 'SIM' in res.keys() and 'Status' in res.keys() and 'state' in res['Status'].keys():
                if res['Status']['state'] == 'registered' or res['Status']['state'] == 'connected':
                    sim_registered = True
                    Results.add_state('SIM Registered', sim_registered)
                else:
                    Results.add_state('SIM Registered', False)

        if sim_registered is True:
            return True
        else:
            return False

    @classmethod
    def sim_registered(cls):
        sim_reg = cls.is_sim_registered()
        if sim_reg is False:
            Results.add_error('mmcli -m 0 | grep state',
                              'SIM card not registered. Please restart modem manager using: sudo stop modemmanager && sudo start modemmanager')

        assert sim_reg is True, 'SIM is not yet Registered'

    @classmethod
    def modem_manager_is_running(cls):
        ps_ef = Runner.run_cmd('ps -ef')
        if 'ModemManager' in ps_ef:
            return True
        else:
            return False

    @classmethod
    def modem_manager_in_debug_mode(cls):
        ps_ef = Runner.run_cmd('ps -ef')
        if 'ModemManager --debug' in ps_ef:
            Results.add_state('Modem Manager Debug', True)
            return True
        else:
            Results.add_state('Modem Manager Debug', False)
            return False


    @classmethod
    def modem_manager_start_in_debug_mode(cls):
        dbg_mode = cls.modem_manager_in_debug_mode()
        if not dbg_mode:
            Runner.run_cmd('sudo stop modemmanager')
            time.sleep(2)
            Runner.run_cmd('/usr/sbin/ModemManager --debug')
            time.sleep(5)

            # Get all modem info again.
            cls.modem_info()

            # Ensure debug omde is True
            dbg_mode = cls.modem_manager_in_debug_mode()
            if not dbg_mode:
                Results.add_error('/usr/sbin/ModemManager --debug', 'Modem manager cannot be started in debug mode.')

            assert dbg_mode is True
        return dbg_mode

    @classmethod
    def modem_sanity(cls):
        cls.mmcli_cmd_present()
        cls.modem_enabled()
        cls.sim_present()
        cls.sim_unlocked()


    # Uses MMCLI commands to put modem into Low power mode (LPM) and back online.
    @classmethod
    def mode_lpm_online(cls):
        cls.list_modems()

        modem_idx = Results.get_state('Modem Index')
        assert modem_idx is not None

        res = Runner.run_cmd('mmcli -m {} --disable'.format(modem_idx))
        assert res is not None
        time.sleep(3)

        res = Runner.run_cmd('mmcli -m {} --enable'.format(modem_idx))
        assert res is not None
        time.sleep(10)

    @classmethod
    def restart_modem_sometimes_does_not_work(cls):
        # works in most scenarios.
        # But sometimes this does not work if /dev/ttyACM device is busy.
        # Use the other method using AT commands (AT!GRESET) it works always.

        # Find the highest index /dev/ttyACM* device.
        res = Runner.run_cmd('ls /dev/ttyACM*').strip()
        devs = re.findall(r'/dev/ttyACM\d', res)
        largest_dev_idx = 0
        for dev in devs:
            dev_idx = re.search('/dev/ttyACM(\d)', dev).group(1)
            if int(dev_idx) > largest_dev_idx:
                largest_dev_idx = int(dev_idx)

        # Command to reset device:
        modem_off_cmd = "echo gprs 0 > /dev/ttyACM{}".format(largest_dev_idx)
        logging.debug("Turning OFF Modem using ACM Device command: " + modem_off_cmd)

        res = Runner.run_cmd(modem_off_cmd)
        time.sleep(5)

        # Command to turn-on Modem.
        modem_on_cmd = "echo gprs 1 > /dev/ttyACM{}".format(largest_dev_idx)
        logging.debug("Turning ON Modem using ACM Device command: " + modem_on_cmd)
        time.sleep(10)

        # Perform basics initialization.
        Results.reset()
        cls.mmcli_cmd_present()
        cls.list_modem_wait()

if __name__ == '__main__':
    process_args()
    ModemCmds.modem_enabled()
