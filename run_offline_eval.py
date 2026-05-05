import json

from evaluation.offline_evaluator import OfflineEvaluator


if __name__ == "__main__":
    print(json.dumps(OfflineEvaluator().run(), ensure_ascii=False, indent=2))
