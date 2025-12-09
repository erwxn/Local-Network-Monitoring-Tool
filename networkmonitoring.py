import time
import socket
import threading
import os
import ipaddress
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, Optional, List

from ping3 import ping
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.align import Align
HOSTS_FILE = "hosts.txt"
MAX_THREADS = 50  
PING_INTERVAL = 1.0
HISTORY_SIZE = 10

class HostResult:
    """Stores the monitoring results for a single host."""
    def __init__(self, host: str, history_size: int = 10):
        self.host = host
        self.response = "init..."
        self.history = deque(maxlen=history_size)
        self.avg_latency = 0.0
        self.latency_change = ""
        self.host_name = host 
        self.success_rate = 0.0
        self.test_count = 0
        self.last_update = datetime.now()
        self.jitter = 0.0
        self.is_up = False

    def update(self, latency: Optional[float]):
        self.test_count += 1
        self.last_update = datetime.now()

        if latency is None:
            self.response = "timeout"
            self.history.append(None)
            self.is_up = False
        else:
            latency_ms = latency * 1000
            self.response = f"{latency_ms:.2f} ms"
            self.history.append(latency_ms)
            self.is_up = True

        self.calculate_metrics()

    def calculate_metrics(self):
        non_none_history = [lat for lat in self.history if lat is not None]

        if non_none_history:
            new_avg = sum(non_none_history) / len(non_none_history)
            if self.avg_latency:
                if new_avg > self.avg_latency:
                    self.latency_change = "[red]↑[/]"
                elif new_avg < self.avg_latency:
                    self.latency_change = "[green]↓[/]"
                else:
                    self.latency_change = "-"
            self.avg_latency = new_avg
            self.jitter = max(non_none_history) - min(non_none_history)
            self.success_rate = (len(non_none_history) / len(self.history)) * 100
        else:
            self.avg_latency = 0.0
            self.jitter = 0.0
            self.success_rate = 0.0
            self.latency_change = "-"

class NetworkMonitor:
    def __init__(self):
        self.results: Dict[str, HostResult] = {}
        self.console = Console()
        self.layout = Layout()
        self._ensure_hosts_file()
        self._load_hosts()

    def _ensure_hosts_file(self):
        """Creates a dummy hosts.txt if it doesn't exist."""
        if not os.path.exists(HOSTS_FILE):
            with open(HOSTS_FILE, "w") as f:
                f.write("8.8.8.8\n1.1.1.1\ngoogle.com\n# 192.168.1.1-192.168.1.5")
            self.console.print(f"[yellow]Created default '{HOSTS_FILE}' file.[/]")

    def _load_hosts(self):
        try:
            with open(HOSTS_FILE, "r") as file:
                raw_hosts = [line.strip() for line in file if line.strip() and not line.startswith("#")]
            
            cleaned_hosts = []
            for h in raw_hosts:
                h = h.replace("https://", "").replace("http://", "")
                h = h.split("/")[0]
                cleaned_hosts.append(h)

            expanded_hosts = self._expand_hosts(cleaned_hosts)
            for host in expanded_hosts:
                if host not in self.results:
                    self.results[host] = HostResult(host, HISTORY_SIZE)
            self.console.print(f"[green]Loaded {len(self.results)} hosts.[/]")
        except Exception as e:
            self.console.print(f"[bold red]Error loading hosts:[/] {e}")

    def _expand_hosts(self, hosts: List[str]) -> List[str]:
        expanded = []
        for host in hosts:
            if '/' in host:
                try:
                    network = ipaddress.IPv4Network(host, strict=False)
                    if network.num_addresses > 256:
                         self.console.print(f"[yellow]Skipping {host}: Too many IPs ({network.num_addresses}). Split into smaller chunks.[/]")
                         continue
                    expanded.extend([str(ip) for ip in network.hosts()])
                except ValueError:
                    self.console.print(f"[yellow]Invalid CIDR: {host}[/]")
            elif '-' in host: 
                try:
                    start, end = host.split('-')
                    start_ip = ipaddress.IPv4Address(start.strip())
                    end_ip = ipaddress.IPv4Address(end.strip())
                    if int(end_ip) - int(start_ip) > 256:
                        self.console.print(f"[yellow]Skipping range {host}: Too many IPs.[/]")
                        continue
                    current = start_ip
                    while current <= end_ip:
                        expanded.append(str(current))
                        current += 1
                except ValueError:
                    self.console.print(f"[yellow]Invalid Range: {host}[/]")
            else:
                expanded.append(host)
        return expanded

    def _resolve_hostname(self, host: str) -> str:
        try:
            return socket.gethostbyaddr(host)[0]
        except socket.herror:
            return host

    def _ping_host(self, host: str):
        host_result = self.results[host]
        host_result.host_name = self._resolve_hostname(host)

        while True:
            try:
                latency = ping(host, timeout=2)
            except PermissionError:
                host_result.response = "PERM ERR"
                time.sleep(5)
                continue
            except Exception:
                latency = None
            
            host_result.update(latency)
            time.sleep(PING_INTERVAL)

    def _start_pinging(self):
        hosts = list(self.results.keys())
        workers = min(len(hosts), MAX_THREADS)
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for host in hosts:
                executor.submit(self._ping_host, host)

    def _generate_header(self) -> Panel:
        """Generates the statistics header."""
        total = len(self.results)
        up = sum(1 for h in self.results.values() if h.is_up)
        down = total - up
        status_color = "green" if down == 0 else "red"
        
        grid = Table.grid(expand=True)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="center", ratio=1)
        
        grid.add_row(
            f"[bold]Total Hosts:[/]\n{total}",
            f"[bold green]Online:[/]\n{up}",
            f"[bold red]Offline:[/]\n{down}"
        )
        
        return Panel(grid, style=f"white on {status_color}" if down > 0 else "white on black", title="[bold]Network Status Monitor[/]", border_style=status_color)

    def _generate_table(self) -> Table:
        table = Table(show_header=True, header_style="bold magenta", expand=True)
        table.add_column("Host", style="cyan")
        table.add_column("Hostname", style="dim white")
        table.add_column("Status", justify="center")
        table.add_column("Latency", justify="right")
        table.add_column("Jitter", justify="right")
        table.add_column("Success %", justify="right")
        
        for host, result in self.results.items():
            status_style = "green" if result.is_up else "red"
            status_icon = "●" if result.is_up else "○"
            
            table.add_row(
                host,
                result.host_name,
                f"[{status_style}]{status_icon} {result.response}[/]",
                f"{result.avg_latency:.1f}ms {result.latency_change}",
                f"{result.jitter:.1f}ms",
                f"{result.success_rate:.0f}%"
            )
        return table

    def run(self):
        if not self.results:
            self.console.print("[bold red]No hosts found to monitor.[/]")
            return

        threading.Thread(target=self._start_pinging, daemon=True).start()
        self.layout.split(
            Layout(name="header", size=5),
            Layout(name="body")
        )

        with Live(self.layout, refresh_per_second=4, screen=True) as live:
            while True:
                self.layout["header"].update(self._generate_header())
                self.layout["body"].update(Panel(self._generate_table(), title="Live Metrics", border_style="blue"))
                time.sleep(0.25)

if __name__ == "__main__":
    if os.name != 'nt' and os.geteuid() != 0:
        print("\033[91mError: ICMP pings require root privileges. Run with sudo.\033[0m")
        exit(1)
        
    try:
        monitor = NetworkMonitor()
        monitor.run()
    except KeyboardInterrupt:
        print("\nExiting...")
