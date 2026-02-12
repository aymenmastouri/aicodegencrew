/**
 * Stop dev servers: kill processes on ports 8001/4200 + orphan uvicorn children.
 * Usage: node scripts/stop-dev.js
 */
const { execSync } = require("child_process");

const PORTS = [8001, 4200];
const killed = new Set();

// 1. Kill by port
for (const port of PORTS) {
  try {
    const output = execSync(
      `netstat -ano | findstr ":${port}" | findstr "LISTENING"`,
      { encoding: "utf8", stdio: ["pipe", "pipe", "ignore"] },
    );
    const pids = output
      .split("\n")
      .map((line) => line.trim().split(/\s+/).pop())
      .filter((pid) => pid && pid !== "0");
    for (const pid of new Set(pids)) {
      try {
        execSync(`taskkill /F /T /PID ${pid}`, { stdio: "ignore" });
        killed.add(pid);
        console.log(`Killed PID ${pid} (port ${port})`);
      } catch {
        // already dead
      }
    }
  } catch {
    console.log(`Port ${port} — nothing running`);
  }
}

// 2. Kill orphan uvicorn child processes (multiprocessing spawn from dead parents)
try {
  const output = execSync(
    'wmic process where "name=\'python.exe\'" get processid,commandline /format:csv',
    { encoding: "utf8", stdio: ["pipe", "pipe", "ignore"] },
  );
  for (const line of output.split("\n")) {
    if (line.includes("uvicorn") || line.includes("multiprocessing.spawn")) {
      const match = line.match(/,(\d+)\s*$/);
      if (match && !killed.has(match[1])) {
        const pid = match[1];
        try {
          execSync(`taskkill /F /PID ${pid}`, { stdio: "ignore" });
          killed.add(pid);
          console.log(`Killed orphan PID ${pid}`);
        } catch {
          // already dead
        }
      }
    }
  }
} catch {
  // wmic not available or no python processes
}

console.log("Dev servers stopped.");
