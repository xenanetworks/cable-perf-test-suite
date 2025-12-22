# *************************************
# author: leonard.yu@teledyne.com
# *************************************

import time
import csv
import os
from typing import List, Dict, Any
import logging

# *************************************************************************************
# func: create_report_dir
# description: Create report directory
# *************************************************************************************
async def create_report_dir() -> str:
    datetime = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    path = "xena_cpom_" + datetime
    if not os.path.exists(path):
        os.makedirs(path)
    return path

class TcvrRxOutputEqTestReportGenerator:
    def __init__(self, logger_name: str, name: str = "Tcvr Rx Output EQ Test", chassis: str = "10.10.10.10"):
        self.logger = logging.getLogger(logger_name)
        self.name = name
        self.chassis = chassis
        self.__fieldnames = ["Time", "Lane", "Amplitude", "PreCursor", "PostCursor", "PRBS BER"]
        self.__create_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.__database = {}

    def record_data(self, port_name: str, lane: int, amplitude: int, precursor: int, postcursor:int, prbs_ber: float) -> None:
        self.logger.info(f"Lane ({lane}) Amplitude: {amplitude}, PreCursor: {precursor}, PostCursor: {postcursor}, PRBS BER: {prbs_ber}")
        time_str = time.strftime("%H:%M:%S", time.localtime())
        if port_name not in self.__database:
            self.__database[port_name] = []
        self.__database[port_name].append({
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
            ["Datetime:", self.__create_time],
            []
        ]
        with open(filename, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            for line in headers:
                writer.writerow(line)
            for key, value in self.__database.items():
                writer.writerow([key])
                dict_writer = csv.DictWriter(csvfile, fieldnames=self.__fieldnames)
                dict_writer.writeheader()
                for data in value:
                    dict_writer.writerow(data)
                writer.writerow([])


class TcvrTxInputEqTestReportGenerator:
    def __init__(self, logger_name: str, name: str = "Tcvr Rx Output EQ Test", chassis: str = "10.10.10.10"):
        self.logger = logging.getLogger(logger_name)
        self.name = name
        self.chassis =chassis
        self.__fieldnames = ["Time", "Lane", "Tx EQ", "PRBS BER"]
        self.__create_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.__database = {}

    def record_data(self, port_name: str, lane: int, eq_value: int, prbs_ber: float) -> None:
        self.logger.info(f"Lane ({lane}) Equalizer: {eq_value}, PRBS BER: {prbs_ber}")
        time_str = time.strftime("%H:%M:%S", time.localtime())
        if port_name not in self.__database:
            self.__database[port_name] = []
        self.__database[port_name].append({
                "Time": time_str,
                "Lane": lane,
                "Tx EQ": eq_value,
                "PRBS BER": '{:.2e}'.format(abs(prbs_ber))
            })
            
    
    def generate_report(self, filename: str) -> None:
        headers = [
            ["*******************************************"],
            ["Test:", self.name],
            ["Chassis:", self.chassis],
            ["Datetime:", self.__create_time],
            []
        ]
        with open(filename, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            for line in headers:
                writer.writerow(line)
            for key, value in self.__database.items():
                writer.writerow([key])
                dict_writer = csv.DictWriter(csvfile, fieldnames=self.__fieldnames)
                dict_writer.writeheader()
                for data in value:
                    dict_writer.writerow(data)
                writer.writerow([])


class HostTxEqTestReportGenerator:
    def __init__(self, logger_name: str, name: str = "Host Tx EQ Test", chassis: str = "10.10.10.10"):
        self.logger = logging.getLogger(logger_name)
        self.name = name
        self.chassis = chassis
        self.__fieldnames = ["Time", "Lane", "Equalizers", "PRBS BER"]
        self.__created_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.__database = {}

    def setup(self, num_tx_taps: int, num_txtaps_pre: int, num_txtaps_post: int) -> None:
        self.num_tx_taps = num_tx_taps
        self.num_txtaps_pre = num_txtaps_pre
        self.num_txtaps_post = num_txtaps_post

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

        self.__fieldnames = ["Time", "Lane"] + [f"Pre{self.num_txtaps_pre-i}" for i in range(self.num_txtaps_pre)] + ["Main"] + [f"Post{i+1}" for i in range(self.num_txtaps_post)] + ["PRBS BER"]
        
    def record_data(self, port_name: str, lane_ber_dicts: List[Dict[str, Any]], lane_txeqs_dicts: List[Dict[str, Any]]) -> None:
        
        sorted_lane_txeqs_dicts = sorted(lane_txeqs_dicts, key=lambda x: x["lane"])
        sorted_lane_ber_dicts = sorted(lane_ber_dicts, key=lambda x: x["lane"])

        for lane_ber_dict, lane_txeqs_dict in zip(sorted_lane_ber_dicts, sorted_lane_txeqs_dicts):
            lane = lane_ber_dict["lane"]
            txeqs = lane_txeqs_dict["txeq_values"]
            prbs_ber = lane_ber_dict["prbs_ber"]
            self.logger.info(f"Lane ({lane}): Tx Eqs: {txeqs}, PRBS BER: {prbs_ber}")
            
            time_str = time.strftime("%H:%M:%S", time.localtime())
            
            if port_name not in self.__database:
                self.__database[port_name] = []
            self.rec["Time"] = time_str
            self.rec["Lane"] = lane
            for i in range(self.num_txtaps_pre):
                self.rec[f"Pre{self.num_txtaps_pre - i}"] = txeqs[i]
            self.rec["Main"] = txeqs[self.num_txtaps_pre]
            for i in range(self.num_txtaps_post):
                self.rec[f"Post{i+1}"] = txeqs[self.num_txtaps_pre + 1 + i]
            self.rec["PRBS BER"] = '{:.2e}'.format(abs(prbs_ber))

            self.__database[port_name].append(self.rec)
            
    
    def generate_report(self, filename: str) -> None:
        headers = [
            ["*******************************************"],
            ["Test:", self.name],
            ["Chassis:", self.chassis],
            ["Datetime:", self.__created_time],
            []
        ]
        with open(filename, 'w+') as csvfile:
            writer = csv.writer(csvfile)
            for line in headers:
                writer.writerow(line)
            for key, value in self.__database.items():
                writer.writerow([key])
                dict_writer = csv.DictWriter(csvfile, fieldnames=self.__fieldnames)
                dict_writer.writeheader()
                for data in value:
                    dict_writer.writerow(data)
                writer.writerow([])