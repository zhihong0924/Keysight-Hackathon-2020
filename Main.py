#Hackath2020-Intelligent Agent-Based System for Multi-Connections Management
from IO import *
import threading
import queue
import json

maxsize = 1000

class Manager:
	def __init__(self):
		self.Elogs_Queue = dict()
		self.Is_Running = dict()
		self.IO = dict()
		self.IO_Thread_Lock = threading.Lock()
		self.Data_Thread_Lock = threading.Lock()
		self.Elogs_Queue = {
			1: queue.Queue(maxsize),
			2: queue.Queue(maxsize),
			3: queue.Queue(maxsize),
			4: queue.Queue(maxsize),
			}
		self.Is_Running = {
			1: False,
			2: False,
			3: False,
			4: False,
			}
		self.IO = {
			1: IO(),
			2: IO(),
			3: IO(),
			4: IO()
			}

class Response:
    def __init__(self, isSuccess, result):
        self.isSuccess = isSuccess
        self.result = result

class Handler:
	def handle_request(self, manager, request):
		self.manager = manager
		self.channel = request.instrumentChannel
		if request.scpi['Action'] == "start":
			self.current = 0
			self.list_current = request.scpi['ListCurrent']
			self.list_duration = request.scpi['ListTime']
			self.voltage_limit = request.scpi['voltageLimit']
			self.cut_off_current = request.scpi['CutoffCurrent']
		switcher = { 
			"start": self.start,
			"fetch_elog": self.fetch_elog,
			"stop": self.stop			} 
		func = switcher.get(request.scpi['Action'], "nothing") 
		if func != "nothing":
			return func()
		
	#Used to start datalog
	def start(self):
		if self.manager.Is_Running[self.channel] == True:
			response = Response(False, "Sorry, channel {0} is currently busy. QwQ".format(self.channel))
			json_response = json.dumps(response.__dict__)
		else:
			self.manager.Is_Running[self.channel] = True
			thread = threading.Thread(target=self.manager.IO[self.channel].start_datalog, args=(self.manager, self.channel, self.current, self.voltage_limit, self.list_current, self.list_duration, self.cut_off_current))
			thread.start()
			response = Response(True, "")
			json_response = json.dumps(response.__dict__)
		return json_response

	#Used to get elog data(s)
	def fetch_elog(self):
		self.manager.Data_Thread_Lock.acquire()
		if self.manager.Elogs_Queue[self.channel].empty() and self.manager.Is_Running[self.channel] == False:
			response = Response(False, "Operation stopped.")
			json_response = json.dumps(response.__dict__)
		else:
			elogs = list()
			while not self.manager.Elogs_Queue[self.channel].empty(): 
				elogs.append(self.manager.Elogs_Queue[self.channel].get())
			response = Response(True, elogs)
			json_response = json.dumps(response.__dict__)

		self.manager.Data_Thread_Lock.release()
		return json_response

	def stop(self):
		self.manager.Is_Running[self.channel] = False
		response = Response(True, "")
		json_response = json.dumps(response.__dict__)
		return json_response