from distutils import extension
import os
import pandas as pd
import can
from can import Bus, BusState, Logger, LogReader, MessageSync
import time
import re
import pandasql as ps


class Canalyse:
    def __init__(self, channel, bustype) -> None:
        self.variables = {}
        self.channel = channel
        self.bustype = bustype
        self.builtin = {
            "scan": ["channel", "time"],
            "read": ["filename"],
            "save": ["dataframe", "filename"],
            "play": ["channel", "dataframe"],
        }

    def scan(self, channel, timeline):
        try:
            bus = can.Bus(bustype=self.bustype, channel=channel)
            data = pd.DataFrame(columns=["timestamp", "channel", "id", "data"])
            if int(timeline) != 0:
                t_end = time.time() + int(timeline)
            else:
                t_end = time.time() + 600  # max time limit.

            while time.time() < t_end:
                msg = bus.recv(1)
                if msg is not None:
                    mdata = "".join([str(hex(d))[2:] for d in msg.data])
                    data.at[data.shape[0]] = [
                        msg.timestamp,
                        msg.channel,
                        msg.arbitration_id,
                        mdata,
                    ]
            return data
        except Exception as e:
            print(e)

    def read(self, filename):
        if filename.split(".")[-1] == "csv":
            return pd.read_csv(filename)
        with open(filename, "r+") as file:
            log = file.readlines()
            data = pd.DataFrame(columns=["timestamp", "channel", "id", "data"])
            ids = []

            for line in log:
                try:
                    res = re.split("#| ", line)
                    res[3] = res[3].strip("\n")
                    data.at[data.shape[0]] = res
                except Exception as e:
                    print(e)
        return data

    def save(self, df, filename):
        extension = filename.split(".")[-1]
        if extension == "csv":
            df.to_csv(filename, index=False)
        elif extension == "log":
            col = df.columns()
            for c in ["timestamp", "channel", "id", "data"]:
                if c not in col:
                    pass  # c not available to store in log file
                    print(f"{c} column is needed to store as log")

            with open(filename, "w+") as file:
                for i in range(df.shape[0]):
                    m = [
                        df.loc[i, "timestamp"],
                        df.loc[i, "channel"],
                        df.loc[i, "id"] + "#" + df.loc[i, "data"] + "\n",
                    ]
                    t = " ".join(m)
                    file.write(t)

            pass
        else:
            pass  # file format not supported
            print(f"{extension} not supported")

    def play(self, channel, df):
        try:
            bus = can.Bus(bustype=self.bustype, channel=channel)
            self.save(df, "play_cache.log")
            reader = LogReader("play_cache.log")
            in_sync = MessageSync(reader)
            for m in in_sync:
                if m.is_error_frame:
                    continue
                bus.send(m)
        except Exception as e:
            print(e)

    def playmsg(self, channel, canmsg):
        bus = can.Bus(bustype=self.bustype, channel=channel)
        t = canmsg.split("#")
        m = can.Message(arbitration_id="0x" + t[0], data="0x" + t[1])
        bus.send(m)

    def sql(self, query):
        try:
            df = ps.sqldf(query, self.variables)
            return df
        except Exception as e:
            print(e)

    def isfloat(self, string: str):
        try:
            a = float(string)
            return True
        except:
            return False

    def check_func_args(self, func, args):
        if len(self.builtin[func]) != len(args):
            print(f"function {func} requires 2 arguments {len(args)} given")
            print(f"function {func} requires {len(self.builtin[func])} arguments")
            return False
        return True

    def execute_func(self,func,args):
        if func == "scan" and self.check_func_args(func, args):
            return self.scan(self.evaluate(args[0]), self.evaluate(args[1]))
        elif func == "read" and self.check_func_args(func, args):
            return self.read(self.evaluate(args[0]))
        elif func == "sql" and self.check_func_args(func, args):
            return self.sql(self.evaluate(args[0]))
        elif func == "save" and self.check_func_args(func, args):
            return self.save(self.evaluate(args[0]), self.evaluate(args[1]))
        elif func == "play" and self.check_func_args(func, args):
            return self.play(self.evaluate(args[0]), self.evaluate(args[1]))
        elif func == "playmsg" and self.check_func_args(func, args):
            return self.playmsg(self.evaluate(args[0]), self.evaluate(args[1]))

    def evaluate_var(self,token):
        if token in self.builtin:
            print(f"function {token} requires arguments")
        elif token in self.variables:
            return self.variables[token]
        elif token.isdigit():
            return int(token)
        elif self.isfloat(token):
            return float(token)
        elif token[0] == '"' and token[-1] == '"':
            return str(token[1:-1])
        elif token[0] == "'" and token[-1] == "'":
            return str(token[1:-1])
        elif (
                "+" in token
                or "-" in token
                or "*" in token
                or "/" in token
                or "%" in token
            ):
            return eval(token, self.variables)
    
    def parse_func(self,code):
        cstk = 0
        qstk = 0
        dqstk = 0
        tokens = code.split(",")
        args = []
        start = 0
        for i in range(len(tokens)):
            qstk = tokens[i].count('"') % 2
            dqstk = tokens[i].count("'") % 2
            cstk += tokens[i].count("(")
            cstk -= tokens[i].count(")")
            if cstk == 0 and qstk == 0 and dqstk == 0:
                args.append(",".join(tokens[start: i + 1]))
                start = i + 1
        return args
    def evaluate(self, code):
        tokens = code.strip().split("(")
        if len(tokens) == 0:
            pass
        elif len(tokens) == 1:
            return self.evaluate_var(tokens[0])
        else:
            code = "(".join(tokens[1:]).rstrip(")")
            func = tokens[0]
            args = self.parse_func(code)
            
            return self.execute_func(func,args)
            

    def repl(self, code):
        code = code.strip()
        tokens = re.split("=", code)
        if len(tokens) > 1:
            tokens[0] = tokens[0].strip()
            if len(tokens[0].split(" ")) > 1 or not tokens[0].isalnum():
                pass  # variable assignment error
                print(f"{' '.join(tokens)} not defined")
            elif not tokens[0][0].isalpha():
                print(f"variable should not start with special characters")
            else:
                self.variables[tokens[0]] = self.evaluate("=".join(tokens[1:]))
        else:
            return self.evaluate(code)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.variables = {}
