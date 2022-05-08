#Hackath2020-Intelligent Agent-Based System for Multi-Connections Management
import vxi11
import time

VISA_Address = "TCPIP0::169.254.84.22::inst0::INSTR"
#priority = ":SOURce:FUNCtion CURRent,(@{0});"
range = ":SOURce:CURRent:RANGe {0},(@{1});"
current_level = ":SOURce:CURRent:LEVel:IMMediate:AMPLitude {0},(@{1});"
slew = ":SOURce:CURRent:SLEW:MAXimum 1,(@{0});"
voltage_limit = ":SOURce:VOLTage:LIMit:POSitive:IMMediate:AMPLitude {0},(@{1});"
voltage_protect = ":SOURce:VOLTage:PROTection:REMote:POSitive:LEVel 5,(@{0});"
voltage_protect_delay = ":SOURce:VOLTage:PROTection:DELay:TIME 6e-05,(@{0});"
output_on = ":OUTPut:STATe 1,(@{0});"
resolution = ":SENSe:SWEep:TINTerval:RESolution RES40;"
elog_volt = ":SENSe:ELOG:FUNCtion:VOLTage 0,(@{0});"
elog_curr = ":SENSe:ELOG:FUNCtion:CURRent 1,(@{0});:SENSe:ELOG:FUNCtion:CURRent:MINMax 0,(@{0});:SENSe:ELOG:CURRent:DC:RANGe:AUTO 1,(@{0});"
integration_period = ":SENSe:ELOG:PERiod 0.1024,(@{0});"
trigger = ":TRIGger:ELOG:SOURce BUS,(@{0});"
operation = ":STATus:OPERation:PTRansition 127,(@{0});:STATus:OPERation:NTRansition 0,(@{0});"
init_datalog = "init:elog (@{0})"
shut_down = ":ABORt:ELOG (@{0});:OUTPut:STATe 0,(@{0});"
fetch_elog = "fetc:elog? 100000,(@{0})"
trigger_elog =":trig:elog (@{0});"
abort_trans = ":ABOR:TRAN (@{0});"
init_trans = ":INITiate:IMMediate:TRANsient (@{0});"
no_error = "No error"
	
class IO:

	def __init__(self):
		self.instr = vxi11.Instrument(VISA_Address)

	#Main method to start datalog, set Iscontinue flag to false to stop the operation
	def start_datalog(self, manager, channel, current, vl, list_current, list_duration, cut_off_current):
		try:
			manager.IO_Thread_Lock.acquire()
			#region Lock to setup instrument
			#self.instr = vxi11.Instrument(VISA_Address)
			#Set Priority Mode
			#self.instr.write(priority.format(channel))
			self.get_error()
		
			#Set Common Settings
			self.instr.write(range.format(max(list_current), channel) + current_level.format(current, channel) + slew.format(channel) + voltage_limit.format(vl, channel) + voltage_protect.format(channel) + voltage_protect_delay.format(channel))
			self.get_error()

			#Turn On Output
			self.instr.write(output_on.format(channel) + resolution + elog_volt.format(channel) + elog_curr.format(channel) + integration_period.format(channel) + trigger.format(channel) + operation.format(channel))
			self.get_error()

			#Init Datalog
			self.instr.write(init_datalog.format(channel))
			self.get_error()
			time.sleep(1)

			#Trig Datalog
			self.instr.write(trigger_elog.format(channel))
			time.sleep(1)

			#Trigger output list
			self.trigg_output_list(channel, list_current, list_duration)

			#endregion
			manager.IO_Thread_Lock.release()

			time.sleep(1)
			curr = max(list_current)

			while manager.Is_Running[channel] == True and curr > cut_off_current:
				time.sleep(0.1)
				response = self.fetch_elog(manager, channel)
				elog = response.split(',')
				for e in elog:
					curr = float(e)
					print("channel {0} : {1}".format(channel, str(e)))
					self.enqueue_data_to_manager(manager, channel, e)
		except Exception as e:
			print(e)
		finally:
			manager.Is_Running[channel] = False
			manager.IO_Thread_Lock.acquire()
			self.instr.write(abort_trans.format(channel))
			self.instr.write(shut_down.format(channel))
			manager.IO_Thread_Lock.release()
	
	#Trigger output list. No need to lock as it inside setup region
	def trigg_output_list(self, channel, list_current, list_duration):
		current = ','.join(map(str, list_current))
		duration = ','.join(map(str,list_duration))
		BEOST = ""
		for c in list_current:
			if BEOST == "":
				BEOST = "OFF"
			else:
				BEOST = "OFF" + "," + BEOST

		output_list = abort_trans.format(channel) + ":CURR:MODE LIST, (@{0});".format(channel) + ":LIST:CURR {0}, (@{1});".format(current, channel) + ":LIST:DWEL {0}, (@{1});".format(duration, channel)
		output_list = output_list + ":LIST:TOUT:BOST {0}, (@{1});".format(BEOST, channel)+ ":LIST:TOUT:EOST {0}, (@{1});".format(BEOST, channel) + ":LIST:COUN 3, (@{0});".format(channel)
		output_list = output_list + ":LIST:TERM:LAST 0, (@{0});".format(channel) + ":TRIG:TRAN:SOUR IMM,(@{0});".format(channel)
		self.instr.write(output_list)
		self.instr.write(init_trans.format(channel))
		self.get_error()

	#Query all SCPI error. No need to lock as it inside setup region
	def get_error(self):
		error = self.instr.ask("syst:err?")
		print(error)
		while no_error not in error:
			print(error)
			error = self.instr.ask("syst:err?")

	#Enqueue data to manager. Need to lock data_thread as user might query it while we wrtting it
	def enqueue_data_to_manager(self, manager, channel, elog):
		manager.Data_Thread_Lock.acquire()
		if(manager.Elogs_Queue[channel].full()):
			manager.Elogs_Queue[channel].get()
		manager.Elogs_Queue[channel].put(elog)
		manager.Data_Thread_Lock.release()

	#Fetch elog. Need to lock io_thread as user might start send elog on another channel
	def fetch_elog(self, manager, channel):
		manager.IO_Thread_Lock.acquire()
		self.instr.write("FORMat:DATA ASCII")
		self.instr.write("FORMat:BORDer NORMal")
		response = self.instr.ask(fetch_elog.format(channel))
		manager.IO_Thread_Lock.release()
		return response



