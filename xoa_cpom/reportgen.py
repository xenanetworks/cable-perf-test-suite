# *************************************
# author: leonard.yu@teledyne.com
# *************************************

import time
import csv

class RxOutputEQTestReportGenerator:
    def __init__(self):
        self.name = "Rx Output EQ Test"
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


class TxInputEQTestReportGenerator:
    def __init__(self):
        self.name = "Tx Input EQ Test"
        self.chassis = "10.10.10.10"
        self.fieldnames = ["Time", "Lane", "TX EQ", "PRBS BER"]
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