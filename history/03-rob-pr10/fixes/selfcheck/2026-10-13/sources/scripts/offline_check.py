"""离线检查启动时撤销旧 PASS，失败时保存本轮状态。"""

import json
from pathlib import Path


def run_check(main, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    result = directory / "RESULT.json"

    def publish(record):
        temporary = result.with_suffix(".tmp")
        temporary.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        temporary.replace(result)

    publish({"result": "RUNNING", "physical_hardware_tested": False})
    try:
        main()
    except (Exception, KeyboardInterrupt) as error:
        publish({"result": "FAILED", "physical_hardware_tested": False,
                 "error_type": type(error).__name__, "error": str(error)})
        raise
