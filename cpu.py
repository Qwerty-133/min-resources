import subprocess
import time
from loguru import logger
import multiprocessing
import pathlib
import sys


MAX_RETRIES = 10
SHORT_WAIT_SECS = 1
LONG_WAIT_SECS = 60 * 5
GENERATED_CPU_LOAD = 10
CPU_LOAD_THRESHOLD = 20


PROJECT_PATH = pathlib.Path(__file__).parent
GET_CPU_USAGE_SCRIPT_PATH = PROJECT_PATH / "cpu.fish"
REDUCE_CPU_CONSUMPTION_COMMAND = r"cpulimit -p {} -l {} -b"
CPU_CORES_COMMAND = "grep -c ^processor /proc/cpuinfo"


def run_entire_command(command, timeout):
    try:
        completed_process = subprocess.run(
            command,
            timeout=timeout,
            check=True,
            encoding="utf-8",
            capture_output=True,
            shell=True,
        )
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as error:
        stdout = (
            error.stdout
            if isinstance(error.stdout, str)
            else error.stdout.decode("utf-8")
        )
        stderr = (
            error.stderr
            if isinstance(error.stderr, str)
            else error.stderr.decode("utf-8")
        )
        logger.exception(
            "Command failed. Return code: {} Stderr: {} Stdout: {}",
            getattr(error, "returncode"),
            stderr,
            stdout,
        )
        raise error from None
    else:
        return completed_process


def get_current_cpu_usage():
    for _ in range(1, MAX_RETRIES + 1):
        try:
            completed_process = run_entire_command(
                f"fish {GET_CPU_USAGE_SCRIPT_PATH}", timeout=2
            )
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            pass
        else:
            cpu_usage = float(completed_process.stdout.strip())
            return cpu_usage

    logger.error("Failed to get CPU usage after {} retries.", MAX_RETRIES)
    sys.exit(1)


def infinity():
    while True:
        pass


def start_infinity_with_reduced_cpu_load():
    logger.info("Starting infinity process with reduced CPU load.")
    for core in range(1, CPU_CORES + 1):
        process = multiprocessing.Process(
            target=infinity, name=f"Infinite Loop - Core {core}", daemon=True
        )
        process.start()
        infinity_processes.append(process)

        reduce_command = REDUCE_CPU_CONSUMPTION_COMMAND.format(
            process.pid, GENERATED_CPU_LOAD / CPU_CORES
        )
        reduce_process = subprocess.Popen(
            reduce_command,
            encoding="utf-8",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        reduce_processes.append(reduce_process)


def end_infinity_processes():
    for infinity_process, reduce_process in zip(infinity_processes, reduce_processes):
        infinity_process.terminate()

        try:
            reduce_process.wait(timeout=1)
        except subprocess.TimeoutExpired as e:
            logger.exception("Reduce process for {} did not terminate in time.", infinity_process.name)
            raise e from None

    infinity_processes.clear()
    reduce_processes.clear()


infinity_processes = []
reduce_processes = []
CPU_CORES = int(run_entire_command(CPU_CORES_COMMAND, timeout=1).stdout.strip())


def main():
    while True:
        cpu_usage = get_current_cpu_usage()
        logger.info("CPU usage: {}", cpu_usage)

        if cpu_usage < CPU_LOAD_THRESHOLD:
            if not infinity_processes:
                logger.info("CPU usage is below threshold. Spawning new process.")
                start_infinity_with_reduced_cpu_load()
            time.sleep(SHORT_WAIT_SECS)
        elif cpu_usage > CPU_LOAD_THRESHOLD:
            if infinity_processes:
                logger.info("CPU usage is above threshold. Terminating infinity process.")
                end_infinity_processes()
            time.sleep(LONG_WAIT_SECS)


try:
    main()
except KeyboardInterrupt:
    logger.info("Exiting...")
