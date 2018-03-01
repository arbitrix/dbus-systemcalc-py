#!/usr/bin/env python

# This adapts sys.path to include all relevant packages
import context

# our own packages
from base import TestSystemCalcBase

# Monkey patching for unit tests
import patches


class VoltageSenseTest(TestSystemCalcBase):
	def __init__(self, methodName='runTest'):
		TestSystemCalcBase.__init__(self, methodName)

	def setUp(self):
		TestSystemCalcBase.setUp(self)
		self._add_device('com.victronenergy.vebus.ttyO1',
			product_name='Multi',
			values={
				'/Ac/ActiveIn/L1/P': 123,
				'/Ac/ActiveIn/ActiveInput': 0,
				'/Ac/ActiveIn/Connected': 1,
				'/Ac/Out/L1/P': 100,
				'/Dc/0/Voltage': 12.25,
				'/Dc/0/Current': -8,
				'/DeviceInstance': 0,
				'/Devices/0/Assistants': [0x55, 0x1] + (26 * [0]),  # Hub-4 assistant
				'/Dc/0/MaxChargeCurrent': None,
				'/Soc': 53.2,
				'/State': 3,
				'/BatteryOperationalLimits/MaxChargeVoltage': None,
				'/BatteryOperationalLimits/MaxChargeCurrent': None,
				'/BatteryOperationalLimits/MaxDischargeCurrent': None,
				'/BatteryOperationalLimits/BatteryLowVoltage': None,
				'/BatterySense/Voltage': None,
				'/FirmwareFeatures/BolFrame': 1,
				'/FirmwareFeatures/BolUBatAndTBatSense': 1
			})
		self._add_device('com.victronenergy.settings',
			values={
				'/Settings/SystemSetup/AcInput1': 1,
				'/Settings/SystemSetup/AcInput2': 2,
			})

	def test_voltage_sense_no_battery_monitor_old_vebus_firmware(self):
		self._monitor.set_value('com.victronenergy.vebus.ttyO1', '/FirmwareFeatures/BolUBatAndTBatSense', 0)
		self._add_device('com.victronenergy.solarcharger.ttyO1', {
			'/State': 0,
			'/Link/NetworkMode': 0,
			'/Link/VoltageSense': None,
			'/Dc/0/Voltage': 12.32,
			'/Dc/0/Current': 9.7},
			connection='VE.Direct')
		self._update_values(5000)
		self._check_values({
			'/Dc/Battery/Voltage': 12.32,
			'/Dc/Battery/VoltageService': 'com.victronenergy.solarcharger.ttyO1'
		})
		self._check_external_values({
			'com.victronenergy.vebus.ttyO1': {
				'/BatterySense/Voltage': None},
			'com.victronenergy.solarcharger.ttyO1': {
				'/Link/VoltageSense': None}})

	def test_voltage_sense_no_battery_monitor_old_mppt_firmware(self):
		self._monitor.add_value('com.victronenergy.settings', '/Settings/Services/Bol', 1)
		self._monitor.add_value('com.victronenergy.vebus.ttyO1', '/BatterySense/Voltage', None)
		self._add_device('com.victronenergy.solarcharger.ttyO1', {
			'/State': 0,
			'/Dc/0/Voltage': 12.32,
			'/Dc/0/Current': 9.7},
			connection='VE.Direct')
		self._update_values(5000)
		self._check_values({
			'/Dc/Battery/Voltage': 12.32,
			'/Dc/Battery/VoltageService': 'com.victronenergy.solarcharger.ttyO1'
		})
		self._check_external_values({
			'com.victronenergy.vebus.ttyO1': {
				'/BatterySense/Voltage': 12.32}})

	def test_voltage_sense_no_battery_monitor(self):
		self._monitor.add_value('com.victronenergy.settings', '/Settings/Services/Bol', 1)
		self._monitor.add_value('com.victronenergy.vebus.ttyO1', '/FirmwareFeatures/BolUBatAndTBatSense', 1)
		self._monitor.add_value('com.victronenergy.vebus.ttyO1', '/BatterySense/Voltage', None)
		self._add_device('com.victronenergy.solarcharger.ttyO1', {
			'/State': 0,
			'/Link/NetworkMode': 0,
			'/Link/VoltageSense': None,
			'/Dc/0/Voltage': 12.2,
			'/Dc/0/Current': 9.7},
			connection='VE.Direct')
		self._update_values(5000)
		self._check_values({
			'/Dc/Battery/Voltage': 12.2,
			'/Dc/Battery/VoltageService': 'com.victronenergy.solarcharger.ttyO1'
		})
		self._check_external_values({
			'com.victronenergy.vebus.ttyO1': {
				'/BatterySense/Voltage': 12.2},
			'com.victronenergy.solarcharger.ttyO1': {
				'/Link/VoltageSense': None}})

	def test_voltage_sense_mppt_and_battery_monitor(self):
		self._monitor.add_value('com.victronenergy.settings', '/Settings/Services/Bol', 1)
		self._monitor.add_value('com.victronenergy.vebus.ttyO1', '/FirmwareFeatures/BolUBatAndTBatSense', 1)
		self._monitor.add_value('com.victronenergy.vebus.ttyO1', '/BatterySense/Voltage', None)
		self._add_device('com.victronenergy.battery.ttyO2',
			product_name='battery',
			values={
				'/Dc/0/Voltage': 12.15,
				'/Dc/0/Current': 5.3,
				'/Dc/0/Power': 65,
				'/Soc': 15.3,
				'/DeviceInstance': 2})
		self._add_device('com.victronenergy.solarcharger.ttyO1', {
			'/State': 0,
			'/Link/NetworkMode': 0,
			'/Link/VoltageSense': None,
			'/Dc/0/Voltage': 12.2,
			'/Dc/0/Current': 9.7},
			connection='VE.Direct')
		self._update_values(5000)
		self._check_values({
			'/Dc/Battery/Voltage': 12.15,
			'/Dc/Battery/VoltageService': 'com.victronenergy.battery.ttyO2'
		})
		self._check_external_values({
			'com.victronenergy.vebus.ttyO1': {
				'/BatterySense/Voltage': 12.15},
			'com.victronenergy.solarcharger.ttyO1': {
				'/Link/VoltageSense': 12.15}})

	def test_voltage_sense_vebus_and_battery_monitor(self):
		self._monitor.add_value('com.victronenergy.settings', '/Settings/Services/Bol', 1)
		self._monitor.add_value('com.victronenergy.vebus.ttyO1', '/FirmwareFeatures/BolUBatAndTBatSense', 1)
		self._monitor.add_value('com.victronenergy.vebus.ttyO1', '/BatterySense/Voltage', None)
		self._add_device('com.victronenergy.battery.ttyO2',
			product_name='battery',
			values={
				'/Dc/0/Voltage': 12.15,
				'/Dc/0/Current': 5.3,
				'/Dc/0/Power': 65,
				'/Soc': 15.3,
				'/DeviceInstance': 2})
		self._update_values(5000)
		self._check_values({
			'/Control/SolarChargerVoltageSense': 1,
			'/Dc/Battery/Voltage': 12.15,
			'/Dc/Battery/VoltageService': 'com.victronenergy.battery.ttyO2'
		})
		self._check_external_values({
			'com.victronenergy.vebus.ttyO1': {
				'/BatterySense/Voltage': 12.15}})

	def test_voltage_sense_disabled(self):
		self._monitor.add_value('com.victronenergy.settings', '/Settings/Services/Bol', 1)
		self._monitor.add_value('com.victronenergy.vebus.ttyO1',
			'/FirmwareFeatures/BolUBatAndTBatSense', 1)
		self._monitor.add_value('com.victronenergy.vebus.ttyO1',
			'/BatterySense/Voltage', None)
		self._set_setting('/Settings/SystemSetup/SharedVoltageSense', 0)

		self._add_device('com.victronenergy.battery.ttyO2',
			product_name='battery',
			values={
				'/Dc/0/Voltage': 12.15,
				'/Dc/0/Current': 5.3,
				'/Dc/0/Power': 65,
				'/Soc': 15.3,
				'/DeviceInstance': 2})
		self._add_device('com.victronenergy.solarcharger.ttyO1', {
			'/State': 0,
			'/Link/NetworkMode': 0,
			'/Link/VoltageSense': None,
			'/Dc/0/Voltage': 12.2,
			'/Dc/0/Current': 9.7},
			connection='VE.Direct')
		self._update_values(5000)
		# Check that voltagesense is indicated as inactive
		self._check_values({
			'/Control/SolarChargerVoltageSense': 0,
		})
		# Check that other devices were left alone
		self._check_external_values({
			'com.victronenergy.vebus.ttyO1': {
				'/BatterySense/Voltage': None}})
		self._check_external_values({
			'com.victronenergy.solarcharger.ttyO1': {
				'/Link/SenseVoltage': None}})

	def test_no_dvcc_no_voltage_sense(self):
		self._monitor.add_value('com.victronenergy.settings', '/Settings/Services/Bol', 0)
		self._set_setting('/Settings/SystemSetup/SharedVoltageSense', 1)

		self._monitor.add_value('com.victronenergy.vebus.ttyO1',
			'/FirmwareFeatures/BolUBatAndTBatSense', 1)
		self._monitor.add_value('com.victronenergy.vebus.ttyO1',
			'/BatterySense/Voltage', None)

		self._add_device('com.victronenergy.battery.ttyO2',
			product_name='battery',
			values={
				'/Dc/0/Voltage': 12.15,
				'/Dc/0/Current': 5.3,
				'/Dc/0/Power': 65,
				'/Soc': 15.3,
				'/DeviceInstance': 2})
		self._add_device('com.victronenergy.solarcharger.ttyO1', {
			'/State': 0,
			'/Link/NetworkMode': 0,
			'/Link/VoltageSense': None,
			'/Dc/0/Voltage': 12.2,
			'/Dc/0/Current': 9.7},
			connection='VE.Direct')
		self._update_values(5000)
		# Check that voltagesense is indicated as inactive
		self._check_values({
			'/Control/SolarChargerVoltageSense': 0,
		})
		# Check that other devices were left alone
		self._check_external_values({
			'com.victronenergy.vebus.ttyO1': {
				'/BatterySense/Voltage': None}})
		self._check_external_values({
			'com.victronenergy.solarcharger.ttyO1': {
				'/Link/SenseVoltage': None}})
