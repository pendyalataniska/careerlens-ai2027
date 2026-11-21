import json

from app.services.matching_evaluation import evaluate_labeled_dataset


def main() -> None:
    print(json.dumps(evaluate_labeled_dataset(), indent=2))


if __name__ == "__main__":
    main()
