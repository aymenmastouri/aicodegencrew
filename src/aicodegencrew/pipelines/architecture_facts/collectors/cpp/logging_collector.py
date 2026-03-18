"""C++ Logging Specialist — spdlog, glog, boost.log patterns."""

from __future__ import annotations

import re
from pathlib import Path

from ..base import CollectorOutput, DimensionCollector, RawLoggingFact


class CppLoggingCollector(DimensionCollector):
    DIMENSION = "logging_observability"

    SPDLOG_PATTERN = re.compile(r'#include\s*[<"]spdlog/')
    GLOG_PATTERN = re.compile(r'#include\s*[<"]glog/')
    BOOST_LOG_PATTERN = re.compile(r'#include\s*[<"]boost/log/')

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        self._log_start()
        self._collect_logging_frameworks()
        self._log_end()
        return self.output

    def _collect_logging_frameworks(self):
        spdlog_count = 0
        glog_count = 0
        boost_log_count = 0

        for path in self._find_files("*.cpp"):
            content = self._read_file_content(path)
            if self.SPDLOG_PATTERN.search(content):
                spdlog_count += 1
            if self.GLOG_PATTERN.search(content):
                glog_count += 1
            if self.BOOST_LOG_PATTERN.search(content):
                boost_log_count += 1

        for path in self._find_files("*.h"):
            content = self._read_file_content(path)
            if self.SPDLOG_PATTERN.search(content):
                spdlog_count += 1
            if self.GLOG_PATTERN.search(content):
                glog_count += 1
            if self.BOOST_LOG_PATTERN.search(content):
                boost_log_count += 1

        if spdlog_count:
            fact = RawLoggingFact(
                name="spdlog-usage",
                observability_type="log_usage",
                framework="spdlog",
                container_hint=self.container_id,
            )
            fact.metadata["file_count"] = spdlog_count
            fact.add_evidence("(aggregated)", 0, 0, f"spdlog in {spdlog_count} C++ files")
            self.output.add_fact(fact)

        if glog_count:
            fact = RawLoggingFact(
                name="glog-usage",
                observability_type="log_usage",
                framework="glog",
                container_hint=self.container_id,
            )
            fact.metadata["file_count"] = glog_count
            fact.add_evidence("(aggregated)", 0, 0, f"glog in {glog_count} C++ files")
            self.output.add_fact(fact)

        if boost_log_count:
            fact = RawLoggingFact(
                name="boost-log-usage",
                observability_type="log_usage",
                framework="boost_log",
                container_hint=self.container_id,
            )
            fact.metadata["file_count"] = boost_log_count
            fact.add_evidence("(aggregated)", 0, 0, f"boost.log in {boost_log_count} C++ files")
            self.output.add_fact(fact)
