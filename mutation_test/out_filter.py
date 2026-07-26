import json
import os
import sys

# [脱敏] 根目录说明
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)
from references.work_db import WorkDB
from references.work_item import WorkResult, WorkerOutcome

class OutFilter:
    @staticmethod
    def uncovered_filter(work_db_path: str, coverage_json_path: str):
        '''过滤出未覆盖行的变异体
        '''
        with open(coverage_json_path, 'r') as f:
            coverage_data = json.load(f)

        # 自动获取第一个文件的missing_lines
        files = coverage_data['files']
        first_file_name = list(files.keys())[0]  # 获取第一个文件名
        missing_lines = files[first_file_name]['missing_lines']
        # 读取work_db，以读方式打开，不存在会报错
        work_db = WorkDB(work_db_path, WorkDB.Mode.open)

        for item in work_db.work_items:
            for mutation in item.mutations:
                try:
                    # 获取变异体所在行号
                    line_number = mutation.end_pos[0]
                    if mutation.end_pos[1] == 0:
                        # 变异体结尾所在列号为0，则考虑上一行
                        line_number -= 1
                    if line_number in missing_lines:
                        work_db.set_result(
                            item.job_id,
                            WorkResult(output=None, test_outcome=None, diff=None, worker_outcome=WorkerOutcome.SKIPPED),
                        )
                except Exception as ex:
                    raise Exception(
                        f"module_path: {mutation.module_path}, start_pos: {mutation.start_pos}, end_pos: {mutation.end_pos}"
                    ) from ex