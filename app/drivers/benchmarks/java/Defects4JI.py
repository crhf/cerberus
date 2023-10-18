import os
import os.path
from datetime import datetime

from app.core import container, definitions, emitter, values
from app.drivers.benchmarks.java.Defects4J import Defects4J


class Defects4JI(Defects4J):
    log_instrument_path = None
    log_refactor_path = None

    def __init__(self):
        self.name = os.path.basename(__file__)[:-3].lower()
        super(Defects4JI, self).__init__()

    def deploy(self, bug_index, container_id):
        if not super().deploy(bug_index, container_id):
            return False
        return self.refactor(bug_index, container_id)

    def refactor(self, bug_index: int, container_id: str):
        emitter.normal("\t\t\trefactoring")
        experiment_item = self.experiment_subjects[bug_index - 1]
        bug_id = str(experiment_item[definitions.KEY_BUG_ID])
        self.log_refactor_path = (
            f"{self.dir_logs}/{self.name}-{bug_id}-refactor.log"
        )

        refactored_diff_dir = os.path.join(
            values.dir_benchmark,
            self.name,
            "instrumentation",
            "refactored-diffs",
        )

        def copy_diff_file(diff_dir, diff_file_name, target_name):
            if os.path.isdir(diff_dir) and diff_file_name in os.listdir(
                diff_dir
            ):
                target_path = os.path.join(self.dir_setup, target_name)
                source_path = os.path.join(diff_dir, diff_file_name)
                if container_id:
                    container.copy_file_to_container(
                        container_id, source_path, target_path
                    )

        copy_diff_file(
            refactored_diff_dir,
            f"{bug_id.replace('-', '_').lower()}.diff",
            "refactor.diff",
        )

        return self.apply_diff_file(
            bug_index, container_id, "refactor.diff", self.log_refactor_path
        )

    def apply_diff_file(
        self,
        bug_index: int,
        container_id: str,
        diff_file_name: str,
        log_file_path: str,
    ):
        diff_file_path = os.path.join(self.dir_setup, diff_file_name)
        status = 0
        if container.is_file(container_id, diff_file_path):
            time = datetime.now()
            patch_command = f'bash -c "patch -f -p 1 < {diff_file_path}"'
            status = self.run_command(
                container_id,
                patch_command,
                log_file_path,
                os.path.join(self.dir_expr, "src"),
            )
            elapsed = (datetime.now() - time).total_seconds()
            emitter.debug(f"\t\t\t Applying diff file took {elapsed} second(s)")

            # if status == 0:
            # if not self.build(bug_index, container_id):
            # status = 1
        return status == 0
