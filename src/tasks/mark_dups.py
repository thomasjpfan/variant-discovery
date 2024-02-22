from typing import List

from flytekit import TaskMetadata, dynamic, kwtypes
from flytekit.extras.tasks.shell import OutputLocation, ShellTask
from flytekit.types.file import FlyteFile

from tasks.sample_types import SamFile
from config import base_image

# """
# Perform quality control using FastQC.

# This function takes a FlyteDirectory object containing raw sequencing data,
# gathers QC metrics using FastQC, and returns a FlyteDirectory object that
# can be crawled with MultiQC to generate a report.

# Args:
#     seq_dir (FlyteDirectory): An S3 prefix containing raw sequencing data to be processed.

# Returns:
#     qc (FlyteDirectory): A directory containing fastqc report output.
# """
mark_dups = ShellTask(
    name="mark_dups",
    debug=True,
    metadata=TaskMetadata(retries=3, cache=True, cache_version="1"),
    script="""
    "java" \
    "-jar" \
    "/usr/local/bin/gatk" \
    "MarkDuplicates" \
    -I {inputs.sam} \
    -O {outputs.o} \
    -M {outputs.m} \
    """,
    inputs=kwtypes(sample=str, sam=FlyteFile),
    output_locs=[
        OutputLocation(
            var="o", var_type=FlyteFile, location="/tmp/mark_dups/{inputs.sample}_dedup.sam"
        ),
        OutputLocation(
            var="m", var_type=FlyteFile, location="/tmp/mark_dups/{inputs.sample}_dedup_metrics.sam"
        )
    ],
    container_image=base_image,
)


@dynamic
def mark_dups_samples(sams: List[SamFile]) -> List[SamFile]:
    deduped = []
    for i in sams:
        deduped.append(mark_dups(sample=i.sample, sam=i.sam))
