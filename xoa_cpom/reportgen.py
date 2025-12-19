# *************************************
# author: leonard.yu@teledyne.com
# *************************************

import time
import csv
from typing import List

class TcvrRxOutputEqTestReportGenerator:
    def __init__(self):
        self.name = "Tcvr Rx Output EQ Test"
        self.chassis = "10.10.10.10"
        self.fieldnames = ["Time", "Lane", "Amplitude", "PreCursor", "PostCursor", "PRBS BER"]
        self.datetime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.database = {}

    def record_data(self, port_name: str, lane: int, amplitude: int, precursor: int, postcursor:int, prbs_ber: float) -> None:
        time_str = time.strftime("%H:%M:%S", time.localtime())
        if port_name not in self.database:
            self.database[port_name] = []
        self.database[port_name].append({
                "Time": time_str,
                "Lane": lane,
                "Amplitude": amplitude,
                "PreCursor": precursor,
                "PostCursor": postcursor,
                "PRBS BER": '{:.2e}'.format(abs(prbs_ber))
            })
            
    
    def generate_report(self, filename: str) -> None:
        headers = [
            ["*******************************************"],
            ["Test:", self.name],
            ["Chassis:", self.chassis],
            ["Datetime:", self.datetime],
            []
        ]
        with open(filename, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            for line in headers:
                writer.writerow(line)
            for key, value in self.database.items():
                writer.writerow([key])
                dict_writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
                dict_writer.writeheader()
                for data in value:
                    dict_writer.writerow(data)
                writer.writerow([])


class TcvrTxInputEqTestReportGenerator:
    def __init__(self):
        self.name = "Tcvr Tx Input EQ Test"
        self.chassis = "10.10.10.10"
        self.fieldnames = ["Time", "Lane", "Tx EQ", "PRBS BER"]
        self.datetime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.database = {}

    def record_data(self, port_name: str, lane: int, eq: int, prbs_ber: float) -> None:
        time_str = time.strftime("%H:%M:%S", time.localtime())
        if port_name not in self.database:
            self.database[port_name] = []
        self.database[port_name].append({
                "Time": time_str,
                "Lane": lane,
                "Tx EQ": eq,
                "PRBS BER": '{:.2e}'.format(abs(prbs_ber))
            })
            
    
    def generate_report(self, filename: str) -> None:
        headers = [
            ["*******************************************"],
            ["Test:", self.name],
            ["Chassis:", self.chassis],
            ["Datetime:", self.datetime],
            []
        ]
        with open(filename, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            for line in headers:
                writer.writerow(line)
            for key, value in self.database.items():
                writer.writerow([key])
                dict_writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
                dict_writer.writeheader()
                for data in value:
                    dict_writer.writerow(data)
                writer.writerow([])


class HostTxEqTestReportGenerator:
    def __init__(self):
        self.name = "Host Tx EQ Test"
        self.chassis = "10.10.10.10"
        self.fieldnames = ["Time", "Lane", "Equalizers", "PRBS BER"]
        self.datetime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.database = {}
        self.num_tx_taps = 0
        self.num_txtaps_pre = 0
        self.num_txtaps_post = 0

    def setup_record_structure(self) -> None:
        # Generate dict with "pre", "post" keys for tx taps depending on the num_txtaps_pre and num_txtaps_post
        self.rec = dict()
        self.rec["Time"] = ""
        self.rec["Lane"] = 0
        for i in range(self.num_txtaps_pre):
            self.rec[f"Pre{self.num_txtaps_pre-i}"] = 0
        self.rec["Main"] = 0
        for i in range(self.num_txtaps_post):
            self.rec[f"Post{i+1}"] = 0
        self.rec["PRBS BER"] = 0.0
        self.fieldnames = ["Time", "Lane"] + [f"Pre{self.num_txtaps_pre-i}" for i in range(self.num_txtaps_pre)] + ["Main"] + [f"Post{i+1}" for i in range(self.num_txtaps_post)] + ["PRBS BER"]
        
    def record_data(self, port_name: str, lane: int, eqs: List[int], prbs_ber: float) -> None:
        if len(eqs) != self.num_tx_taps:
            raise ValueError(f"Length of eqs {len(eqs)} does not match num_tx_taps {self.num_tx_taps}")
        
        time_str = time.strftime("%H:%M:%S", time.localtime())
        if port_name not in self.database:
            self.database[port_name] = []
        self.rec = dict()
        self.rec["Time"] = time_str
        self.rec["Lane"] = lane
        for i in range(self.num_txtaps_pre):
            self.rec[f"Pre{self.num_txtaps_pre - i}"] = eqs[i]
        self.rec["Main"] = eqs[self.num_txtaps_pre]
        for i in range(self.num_txtaps_post):
            self.rec[f"Post{i+1}"] = eqs[self.num_txtaps_pre + 1 + i]
        self.rec["PRBS BER"] = '{:.2e}'.format(abs(prbs_ber))

        self.database[port_name].append(self.rec)
            
    
    def generate_report(self, filename: str) -> None:
        headers = [
            ["*******************************************"],
            ["Test:", self.name],
            ["Chassis:", self.chassis],
            ["Datetime:", self.datetime],
            []
        ]
        with open(filename, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            for line in headers:
                writer.writerow(line)
            for key, value in self.database.items():
                writer.writerow([key])
                dict_writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
                dict_writer.writeheader()
                for data in value:
                    dict_writer.writerow(data)
                writer.writerow([])