# Debug Notes

## Deadlock When Invoking Child Processes Synchronously Against In-Process Test HTTP Server

### Symptom

Tests executing Python scripts via execFileSync or runPython hung for 30+ seconds and timed out when making HTTP requests against an in-process Node.js http.createServer instance created in the same test runner.

### Root cause

Node.js is single-threaded. Calling synchronous child process execution methods (execFileSync / execSync) blocks the main thread and the Node event loop until the child process terminates. Because the event loop is blocked, the in-process HTTP server cannot accept or respond to incoming connections from the spawned child process, causing the child process to hang until its socket timeout expires.

### Verified fix

Use asynchronous execution (execFileAsync via promisify(execFile) or runPythonAsync) with await when calling scripts that make HTTP requests to the test in-process HTTP fixture server. This allows Node event loop to service incoming requests concurrently while the child process runs.

### Prevention / Fast path

Whenever testing client libraries or CLIs against a local http.createServer spun up within the Node test suite, always use await runPythonAsync(...) or await execFileAsync(...) instead of execFileSync.
