import os
import pandas as pd
import rich
from rich.console import Console
from rich.prompt import Prompt
from canalyse import Canalyse
import pyfiglet as pf
import json
import time
import sys


class Interface:
    def __init__(self, filename: str = "nav.json") -> None:
        with open(filename) as file:
            self.menu = json.load(file)
        self.path: list[str] = []
        self.console = Console()
        self.channel = self.menu["Settings"]["Communication channel"]
        self.bustype = self.menu["Settings"]["Communication Interface"]


    def header(self) -> None:
        print("")
        result = pf.figlet_format("CANalyse", font="slant")
        print(result)
        print("")

    def footer(self) -> None:
        print("")

    def goto(self, path):
        path = path.copy()
        curr_page = self.menu
        while len(path) > 0:
            curr_page = curr_page[path[0]]
            del path[0]
        return curr_page

    def control_panel(self) -> str:
        option: int = int(input("---> "))
        options = self.goto(self.path)
        if option == len(options) + 1:
            return "back"
        return list(options.keys())[option - 1]

    def page(self) -> None:
        options = list(self.goto(self.path).keys())
        for i in range(len(options)):
            print(f"{i+1}) {options[i]}")
        back = "Back"
        if len(self.path) == 0:
            back = "Exit"
        self.console.print(f"{len(options)+1}) {back}", style="bold red")

    def display(self) -> None:
        while True:
            os.system("clear")
            self.header()
            self.page()
            self.footer()
            try:
                option = self.control_panel()
                if option == "back":
                    if len(self.path) > 0:
                        self.path.pop()
                    else:
                        print("Exiting...")
                        break
                elif type(self.goto(self.path + [option])) == str:
                    self.execute(option)
                else:
                    self.path.append(option)
            except KeyboardInterrupt:
                break
            except Exception as e:
                raise e

    def execute(self, option: str) -> None:
        func = self.goto(self.path + [option])
        print(f"executes {func}")
        if func == "ide":
            self.ide()
        elif func == "telegram":
            self.telegram()
        elif func == "smartscan":
            self.smartscan()

    def ide(self):
        os.system("clear")
        self.header()
        with Canalyse(self.channel, self.bustype) as cn:
            history = []
            while True:
                code = input("###--> ")
                code = code.lower().strip()
                if code in ["close", "quit", "exit"]:
                    break
                else:
                    try:
                        output = cn.repl(code)
                        if output is not None:
                            print(output)
                        history.append(code)
                    except KeyboardInterrupt:
                        break
                    except Exception as e:
                        print(e)

    def smartscan(self):
        os.system("clear")
        with Canalyse(self.channel, self.bustype) as cn:
            cn.smartscan()
        pass

    def telegram(self):
        print("under construction")


if __name__ == "__main__":
    interface = Interface()
    interface.display()
