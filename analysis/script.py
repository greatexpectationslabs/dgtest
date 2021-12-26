# type: ignore
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Set

import requests
import tqdm
from dateutil import parser


@dataclass
class AzureRun:
    id: str
    name: str
    timestamp: str
    pipeline: str
    result: str
    state: str
    tests: Dict[str, int]

    def __str__(self) -> str:
        string = f"{self.id}, {self.name}, {self.timestamp}, {self.pipeline}, {self.result}, {self.state}"
        for k, v in self.tests.items():
            string += f", {k} | {v}"
        return string


def get_seen_entries() -> Set[str]:
    with open("azure_runs.csv") as f:
        entries = f.readlines()

    seen = set(e.split(",")[0] for e in entries)
    print(f"Retrieved {len(seen)} existing entries")
    return seen


def collect_azure_runs(pipeline_id: int, seen: Set[str]) -> List[AzureRun]:
    runs = []
    response = requests.get(
        fr"https://dev.azure.com/great-expectations/great_expectations/_apis/pipelines/{pipeline_id}/runs\?api-version\=6.0-preview.1"
    )

    parsed = json.loads(response.text)
    for entry in parsed["value"]:

        id_ = str(entry["id"])
        result = entry.get("result", "TBD")
        if id_ in seen or result == "TBD":
            continue

        timestamp = parser.parse(entry["createdDate"])
        if timestamp.year == 2021 and timestamp.month == 12 and timestamp.day >= 13:
            run = AzureRun(
                id=str(entry["id"]),
                name=entry["name"],
                timestamp=entry["createdDate"],
                pipeline=entry["pipeline"]["name"],
                result=result,
                state=entry["state"],
                tests={},
            )
            runs.append(run)

    print(f"Parsing {len(runs)} runs from pipeline {pipeline_id}")
    return runs


def retrieve_logs(runs: List[AzureRun]) -> None:
    for run in tqdm.tqdm(runs):
        _retrieve_logs(run)


def _retrieve_logs(run: AzureRun) -> None:
    build_id = run.id
    response = requests.get(
        f"https://dev.azure.com/great-expectations/bedaf2c2-4c4a-4b37-87b0-3877190e71f5/_apis/build/builds/{build_id}/logs"
    )
    if response.status_code != 200:
        return

    parsed = json.loads(response.text)
    count = parsed["count"]
    regex = re.compile(r"collected (\d+) items")

    stages = [
        "compatibility_matrix Python38-PandasLatest",
        "comprehensive Python38",
        "mysql",
        # "mssql",  # Duplicated by mysql
        "test_cli",
    ]

    test_counts = {stage: 0 for stage in stages}

    for n in range(1, count + 1):
        if all(val > 0 for val in test_counts.values()):
            break

        response = requests.get(
            f"https://dev.azure.com/great-expectations/bedaf2c2-4c4a-4b37-87b0-3877190e71f5/_apis/build/builds/{build_id}/logs/{n}"
        )
        if response.status_code != 200:
            return

        contents = response.text
        for stage in stages:
            if stage in contents.split("\n")[0] and "test session starts" in contents:
                match = regex.search(contents)
                if match:
                    test_counts[stage] = int(match.group(1))
                    break

    run.tests = test_counts
    print(f"  {run}")

    with open("azure_runs.csv", "a") as f:
        f.write(f"{run}\n")


def get_deviations_between_pipelines():
    seen = set()
    dependency_graph_runs = collect_azure_runs(8, seen)
    great_expectations_runs = collect_azure_runs(1, seen)

    all_runs = dependency_graph_runs + great_expectations_runs
    run_results = defaultdict(list)
    deviations = []

    for run in all_runs:
        run_results[run.name].append(run.result)

        results = run_results[run.name]
        if len(results) == 2 and results[0] != results[1]:
            deviations.append(run)

    print("Deviations:")
    for run in deviations:
        print(run.id, run.name, run.timestamp)


def main():
    seen = get_seen_entries()
    dependency_graph_runs = collect_azure_runs(8, seen)
    retrieve_logs(dependency_graph_runs)

    get_deviations_between_pipelines()


if __name__ == "__main__":
    main()
