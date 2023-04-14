import os
import re
from datetime import datetime
from os.path import join

from app.core import definitions
from app.core import emitter
from app.core import values
from app.core.utilities import error_exit
from app.drivers.tools.analyze.AbstractAnalyzeTool import AbstractAnalyzeTool


class SAVER(AbstractAnalyzeTool):
    relative_binary_path = None

    def __init__(self):
        self.name = os.path.basename(__file__)[:-3].lower()
        super(SAVER, self).__init__(self.name)

    def prepare(self, bug_info):
        tool_dir = join(self.dir_expr, self.name)
        if not self.is_dir(tool_dir):
            self.run_command(f"mkdir -p {tool_dir}", dir_path=self.dir_expr)
        emitter.normal("\t\t\t preparing subject for repair with " + self.name)
        dir_src = join(self.dir_expr, "src")
        clean_command = "make clean"
        self.run_command(clean_command, dir_path=dir_src)

        time = datetime.now()
        bug_type = bug_info[definitions.KEY_BUG_TYPE]
        if bug_type == "Memory Leak":
            compile_command = (
                "infer -j 20 -g --headers --check-nullable-only -- make -j20"
            )
        else:
            compile_command = (
                "infer -j 20 run -g --headers --check-nullable-only -- make -j20"
            )
        emitter.normal("\t\t\t\t compiling subject with " + self.name)
        self.run_command(compile_command, dir_path=dir_src)
        emitter.normal(
            "\t\t\t\t compilation took {} second(s)".format(
                (datetime.now() - time).total_seconds()
            )
        )

    def run_analysis(self, bug_info, config_info):
        self.prepare(bug_info)
        super(SAVER, self).run_analysis(bug_info, config_info)
        if values.only_instrument:
            return
        timeout_h = str(config_info[definitions.KEY_CONFIG_TIMEOUT])
        additional_tool_param = config_info[definitions.KEY_TOOL_PARAMS]

        if values.use_container:
            emitter.error(
                "[Exception] unimplemented functionality: SAVER docker support not implemented"
            )
            error_exit("Unhandled Exception")

        self.timestamp_log_start()
        bug_type = bug_info[definitions.KEY_BUG_TYPE]
        dir_src = join(self.dir_expr, "src")
        saver_command = "timeout -k 5m {0}h infer saver --pre-analysis-only {1}".format(
            str(timeout_h), additional_tool_param
        )

        status = self.run_command(
            saver_command, dir_path=dir_src, log_file_path=self.log_output_path
        )
        self.process_status(status)

        self.timestamp_log_end()
        emitter.highlight("\t\t\tlog file: {0}".format(self.log_output_path))

    def save_artifacts(self, dir_info):
        emitter.normal("\t\t\t saving artifacts of " + self.name)
        copy_command = "cp -rf {}/saver {}".format(self.dir_expr, self.dir_output)
        self.run_command(copy_command)
        infer_output = join(self.dir_expr, "src", "infer-out")
        copy_command = "cp -rf {} {}".format(infer_output, self.dir_output)
        self.run_command(copy_command)
        super(SAVER, self).save_artifacts(dir_info)
        return

    def analyse_output(self, dir_info, bug_id, fail_list):
        emitter.normal("\t\t\t analysing output of " + self.name)
        dir_results = join(self.dir_expr, "result")
        conf_id = str(values.current_profile_id.get("NA"))
        self.log_stats_path = join(
            self.dir_logs,
            "{}-{}-{}-stats.log".format(conf_id, self.name.lower(), bug_id),
        )

        regex = re.compile("(.*-output.log$)")
        for _, _, files in os.walk(dir_results):
            for file in files:
                if regex.match(file) and self.name in file:
                    self.log_output_path = dir_results + "/" + file
                    break

        if not self.log_output_path or not self.is_file(self.log_output_path):
            emitter.warning("\t\t\t[warning] no output log file found")
            return self._space, self._time, self._error

        emitter.highlight("\t\t\t Log File: " + self.log_output_path)
        is_error = False

        log_lines = self.read_file(self.log_output_path, encoding="iso-8859-1")
        self._time.timestamp_start = log_lines[0].replace("\n", "")
        self._time.timestamp_end = log_lines[-1].replace("\n", "")
        for line in log_lines:
            if "ERROR:" in line:
                self._error.is_error = True
        if is_error:
            emitter.error("\t\t\t\t[error] error detected in logs")

        return self._space, self._time, self._error