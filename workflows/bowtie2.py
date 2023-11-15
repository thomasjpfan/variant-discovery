from pathlib import Path
from flytekit import kwtypes, task, Resources, current_context, TaskMetadata
from flytekit.extras.tasks.shell import OutputLocation, ShellTask
from flytekit.types.file import FlyteFile
from flytekit.types.directory import FlyteDirectory

from .config import ref_hash, base_image, logger
from .sample_types import FiltSample, SamFile
from .utils import subproc_raise


"""
Generate Bowtie2 index files from a reference genome.

Args:
    ref (FlyteFile): A FlyteFile object representing the input reference file.

Returns:
    FlyteDirectory: A FlyteDirectory object containing the index files.
"""
bowtie2_index = ShellTask(
    name="bowtie2-index",
    debug=True,
    requests=Resources(cpu="4", mem="10Gi"),
    metadata=TaskMetadata(retries=3, cache=True, cache_version=ref_hash),
    container_image=base_image,
    script="""
    mkdir {outputs.idx}
    bowtie2-build {inputs.ref} {outputs.idx}/bt2_idx
    """,
    inputs=kwtypes(ref=FlyteFile),
    output_locs=[
        OutputLocation(var="idx", var_type=FlyteDirectory, location="/root/idx")
    ],
)


@task(container_image=base_image, requests=Resources(cpu="4", mem="10Gi"))
def bowtie2_align_paired_reads(idx: FlyteDirectory, fs: FiltSample) -> SamFile:
    """
    Perform paired-end alignment using Bowtie 2 on a filtered sample.

    This function takes a FlyteDirectory object representing the Bowtie 2 index and a
    FiltSample object containing filtered sample data. It performs paired-end alignment
    using Bowtie 2 and returns a SamFile object representing the resulting alignment.

    Args:
        idx (FlyteDirectory): A FlyteDirectory object representing the Bowtie 2 index.
        fs (FiltSample): A FiltSample object containing filtered sample data to be aligned.

    Returns:
        SamFile: A SamFile object representing the alignment result in SAM format.
    """
    idx.download()
    logger.debug(f"Index downloaded to {idx.path}")
    ldir = Path(current_context().working_directory)
    sam = ldir.joinpath(f"{fs.sample}_bowtie2.sam")
    rep = ldir.joinpath(f"{fs.sample}_bowtie2_report.txt")
    logger.debug(f"Writing SAM to {sam} and report to {rep}")

    cmd = [
        "bowtie2",
        "-x",
        f"{idx.path}/bt2_idx",
        "-1",
        fs.filt_r1,
        "-2",
        fs.filt_r2,
        "-S",
        sam,
    ]
    logger.debug(f"Running command: {cmd}")
     
    stdout, stderr = subproc_raise(cmd)

    with open(rep, "w") as f:
        f.write(stderr)

    return SamFile(
        sample=fs.sample, sam=FlyteFile(path=str(sam)), report=FlyteFile(path=str(rep))
    )
