# Victron packages

import sc_utils
from delegates.base import SystemCalcDelegate

class BL(object):
    Disabled = 0
    Restart = 1
    Default = 2
    Absorption = 3
    Float = 4
    Discharged = 5
    ForceCharge = 6
    Sustain = 7
    LowSocCharge = 8

class SOCG(object):
    KeepCharged = 9
    Default = 10
    Discharged = 11
    LowSocCharge = 12

class SystemState(SystemCalcDelegate):
	""" Calculates the system state. If ESS is installed, show that state,
		otherwise return the VEBus state. """

	# vebus states are passed right through, and range from 0x00 (Off) to 0x0b (psu). Let's start ESS
	# states at 0x20.
	UNKNOWN = 0x00
	DISCHARGING = 0x100
	SUSTAIN = 0x101

	def __init__(self):
		super(SystemState, self).__init__()

	def get_input(self):
		return [
			('com.victronenergy.battery', [
				'/Info/MaxDischargeCurrent',
				'/Info/MaxChargeCurrent']),
			('com.victronenergy.settings', [
				'/Settings/CGwacs/BatteryLife/State',
				'/Settings/SystemSetup/MaxChargeCurrent',
				'/Settings/CGwacs/MaxDischargePower']),
			('com.victronenergy.vebus', [
				'/Hub4/AssistantId',
				'/Hub4/Sustain',
				'/State',
				'/VebusMainState',
				'/Bms/AllowToDischarge',
				'/Bms/AllowToCharge'])]

	def get_output(self):
		return [
			('/SystemState/State', {'gettext': '%s'}),
			('/SystemState/LowSoc', {'gettext': '%s'}),
			('/SystemState/BatteryLife', {'gettext': '%s'}),
			('/SystemState/DischargeDisabled', {'gettext': '%s'}),
			('/SystemState/ChargeDisabled', {'gettext': '%s'}),
			('/SystemState/SlowCharge', {'gettext': '%s'}),
			('/SystemState/UserChargeLimited', {'gettext': '%s'}),
			('/SystemState/UserDischargeLimited', {'gettext': '%s'}),
		]

	def bms_state(self, vebus):
		# Will return None if no vebus BMS
		may_discharge = self._dbusmonitor.get_value(vebus,
			'/Bms/AllowToDischarge')
		may_charge = self._dbusmonitor.get_value(vebus,
			'/Bms/AllowToCharge')

		if may_discharge is None or may_charge is None:
			# There is no vebus BMS in the system. Check if there
			# are operational limits set by another BMS. If these values
			# don't exist we will get None, which we interpret as
			# a signal that discharge is allowed. This is handled adequately
			# because None != 0.
			may_discharge = self._dbusmonitor.get_value(vebus,
				'/BatteryOperationalLimits/MaxDischargeCurrent') != 0
			may_charge = self._dbusmonitor.get_value(vebus,
				'/BatteryOperationalLimits/MaxChargeCurrent') != 0
		return (bool(may_charge), bool(may_discharge))

	def state(self, newvalues):
		vebus = newvalues.get('/VebusService')
		flags = sc_utils.SmartDict(dict.fromkeys(['LowSoc', 'BatteryLife',
		'DischargeDisabled', 'ChargeDisabled', 'SlowCharge', 'UserChargeLimited', 'UserDischargeLimited'], 0))

		if vebus is None:
			# This could be because a VEBUS BMS turned the inverter off.
			# Unfortunately we will never know. Just admit we don't know.
			return (SystemState.UNKNOWN, flags)

		# VEBUS is available
		ss = self._dbusmonitor.get_value(vebus, '/State')
		assistant_id  = self._dbusmonitor.get_value(vebus, '/Hub4/AssistantId')
		if assistant_id is None:
			# ESS not installed. Return vebus state
			return (ss, flags)

		# VEBUS is available and ESS is installed
		mainstate = self._dbusmonitor.get_value(vebus, '/VebusMainState')

		# Charge or bypass mode.
		if mainstate in (8, 9):
			# BMS state
			flags.ChargeDisabled, flags.DischargeDisabled = map(
				lambda x: int(not x), self.bms_state(vebus))

			# User limit
			user_discharge_limit = self._dbusmonitor.get_value(
				'com.victronenergy.settings',
				'/Settings/CGwacs/MaxDischargePower')
			user_charge_limit = self._dbusmonitor.get_value(
				'com.victronenergy.settings',
				'/Settings/SystemSetup/MaxChargeCurrent')
			flags.UserDischargeLimited = int(user_discharge_limit == 0)
			flags.UserChargeLimited = int(user_charge_limit == 0)

			# ESS state
			hubstate = self._dbusmonitor.get_value('com.victronenergy.settings',
				'/Settings/CGwacs/BatteryLife/State')
			if hubstate in (BL.Default, BL.Absorption, BL.Float, SOCG.Default):
				if newvalues.get('/Dc/Battery/Power') < -30:
					ss = SystemState.DISCHARGING
			elif hubstate in (BL.Discharged, SOCG.Discharged):
				flags.LowSoc = 1
				flags.BatteryLife = int(hubstate == BL.Discharged)
			elif hubstate in (BL.ForceCharge, BL.LowSocCharge,
					SOCG.LowSocCharge):
				flags.SlowCharge = 1

			# Sustain flag
			if self._dbusmonitor.get_value(vebus, '/Hub4/Sustain'):
				ss = SystemState.SUSTAIN

		return (ss, flags)

	def update_values(self, newvalues):
		newvalues['/SystemState/State'], flags = self.state(newvalues)
		newvalues.update({'/SystemState/' + k: v for k, v in flags.items()})