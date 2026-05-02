import asyncio
from typing import Dict, Optional, List
from dataclasses import dataclass
import datetime

@dataclass
class BackgroundProcess:
    id: str
    command: str
    process: asyncio.subprocess.Process
    start_time: datetime.datetime
    logs: List[str]

class ProcessManager:
    def __init__(self):
        self.processes: Dict[str, BackgroundProcess] = {}
        self._log_callback = None

    def set_log_callback(self, callback):
        self._log_callback = callback

    async def start_process(self, process_id: str, command: str, cwd: str) -> bool:
        if process_id in self.processes:
            # Kill existing process with same ID
            await self.stop_process(process_id)

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT, # Merge stderr into stdout
                cwd=cwd
            )
            
            bg_proc = BackgroundProcess(
                id=process_id,
                command=command,
                process=process,
                start_time=datetime.datetime.now(),
                logs=[]
            )
            self.processes[process_id] = bg_proc
            
            # Start a background task to read logs
            asyncio.create_task(self._read_logs(bg_proc))
            return True
        except Exception as e:
            if self._log_callback:
                self._log_callback(f"Failed to start {process_id}: {e}")
            return False

    async def _read_logs(self, bg_proc: BackgroundProcess):
        while True:
            line = await bg_proc.process.stdout.readline()
            if not line:
                break
            
            log_line = line.decode('utf-8', errors='replace').strip()
            bg_proc.logs.append(log_line)
            
            # Keep only last 500 lines in memory per process
            if len(bg_proc.logs) > 500:
                bg_proc.logs.pop(0)
                
            if self._log_callback:
                # Format: [process_id] log content
                self._log_callback(f"[{bg_proc.id}] {log_line}")
        
        exit_code = await bg_proc.process.wait()
        if self._log_callback:
            self._log_callback(f"Process {bg_proc.id} exited with code {exit_code}")

    async def stop_process(self, process_id: str):
        if process_id in self.processes:
            proc = self.processes[process_id]
            try:
                proc.process.terminate()
                await proc.process.wait()
            except:
                pass
            del self.processes[process_id]

    def get_logs(self, process_id: str) -> str:
        if process_id in self.processes:
            return "\n".join(self.processes[process_id].logs)
        return "No such process running."

    async def stop_all(self):
        for pid in list(self.processes.keys()):
            await self.stop_process(pid)
