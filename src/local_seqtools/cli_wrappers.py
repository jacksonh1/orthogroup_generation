import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from Bio import Align, AlignIO, Seq, SeqIO

import local_seqtools.cdhit_tools as cdhit_tools
import local_seqtools.general_utils as tools

"""
functions that end with `_command` return a string that can be used as a command line argument
functions that end with wrapper: 
- run the command line argument
- generate temporary files
- return the output
- then delete the temporary files
"""

def mafft_align_wrapper(
    input_seqrecord_list, output_type="list", fast=False, n_align_threads=8
):
    assert output_type in [
        "list",
        "dict",
        "alignment",
    ], f'`output_type` must be one of ["list", "alignment"]'
    # create temporary file
    temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
    # write seqrecords to temporary file
    SeqIO.write(input_seqrecord_list, temp_file, "fasta")
    temp_file.close()
    # run mafft
    alignment_filename = f"{temp_file.name}-mafft.fa"
    # raise an error if the alignment file already exists. (it won't but just in case)
    if os.path.exists(alignment_filename):
        raise FileExistsError(f"{alignment_filename} already exists")
    if fast:
        mafft_command = f'mafft --thread {n_align_threads} --quiet --retree 1 "{temp_file.name}" > "{alignment_filename}"'
    else:
        mafft_command = (
            f'mafft --thread {n_align_threads} --quiet --anysymbol "{temp_file.name}" > "{alignment_filename}"'
        )
    # print(mafft_command)
    subprocess.run(mafft_command, shell=True, check=True)
    # read in mafft output
    if output_type == "list":
        mafft_output = tools.import_fasta(alignment_filename, output_format="list")
    elif output_type == "dict":
        mafft_output = tools.import_fasta(alignment_filename, output_format="dict")
    elif output_type == "alignment":
        mafft_output = AlignIO.read(alignment_filename, "fasta")
    # delete temporary file
    os.remove(alignment_filename)
    os.remove(temp_file.name)
    return mafft_output


def clustal_align_wrapper(
    input_seqrecord_list, alignment_type="basic", output_type="list"
):
    assert output_type in [
        "list",
        "dict",
        "alignment",
    ], f'`output_type` must be one of ["list", "dict", "alignment"]'
    assert alignment_type in [
        "basic",
        "full",
    ], f'`output_type` must be one of ["basic", "full"]'
    # create temporary file
    temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
    # write seqrecords to temporary file
    SeqIO.write(input_seqrecord_list, temp_file, "fasta")
    temp_file.close()
    alignment_filename = f"{temp_file.name}-clustal.fa"
    # raise an error if the alignment file already exists. (it won't but just in case)
    if os.path.exists(alignment_filename):
        raise FileExistsError(f"{alignment_filename} already exists")

    if alignment_type == "basic":
        clustal_command = f'clustalo -i "{temp_file.name}" -o "{alignment_filename}" -v --outfmt=fa --threads=6'
    elif alignment_type == "full":
        clustal_command = f'clustalo -i "{temp_file.name}" -o "{alignment_filename}" -v --outfmt=fa --full --threads=6'
    subprocess.run(clustal_command, shell=True, check=True)

    # read in clustal output
    if output_type == "list":
        clustal_output = tools.import_fasta(alignment_filename, output_format="list")
    elif output_type == "dict":
        clustal_output = tools.import_fasta(alignment_filename, output_format="dict")
    elif output_type == "alignment":
        clustal_output = AlignIO.read(alignment_filename, "fasta")
    # delete temporary file
    os.remove(alignment_filename)
    os.remove(temp_file.name)
    return clustal_output


def cd_hit_wrapper(input_seqrecord_list, output_type="list", linux=False, extra_args=""):
    assert output_type in [
        "list",
        "dict",
    ], f'`output_type` must be one of ["list", "dict"]'

    # create temporary file
    temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
    # write seqrecords to temporary file
    SeqIO.write(input_seqrecord_list, temp_file, "fasta")
    temp_file.close()
    clustered_seqs_filename = f"{temp_file.name}-cdhit.fa"
    # raise an error if the alignment file already exists. (it won't but just in case)
    if os.path.exists(clustered_seqs_filename):
        raise FileExistsError(f"{clustered_seqs_filename} already exists")

    clustered_seqs_clusters_filename = clustered_seqs_filename + ".clstr"
    if linux:
        command = (
            f"cd-hit -i {temp_file.name} -o {clustered_seqs_filename} -M 0 -d 0 {extra_args}"
        )
    else:
        command = f"/Users/jackson/mambaforge/envs/cd_hit_x86/bin/cd-hit -i {temp_file.name} -o {clustered_seqs_filename} -M 0 -d 0 {extra_args}"
    subprocess.run(command, shell=True, check=True)

    output_clstrs_dict = cdhit_tools.cd_hit_clstr_parser(clustered_seqs_clusters_filename)

    # read in clustal output
    if output_type == "list":
        output = tools.import_fasta(clustered_seqs_filename, output_format="list")
    elif output_type == "dict":
        output = tools.import_fasta(clustered_seqs_filename, output_format="dict")
    # delete temporary file
    os.remove(clustered_seqs_filename)
    os.remove(clustered_seqs_clusters_filename)
    os.remove(temp_file.name)
    return output, output_clstrs_dict


def muscle_align_wrapper(input_seqrecord_list, output_type="list"):
    assert output_type in [
        "list",
        "dict",
        "alignment",
    ], f'`output_type` must be one of ["list", "dict", "alignment"]'

    muscle_binary = "/Users/jackson/tools/muscle/muscle-5.1.0/src/Darwin/muscle"

    temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
    SeqIO.write(input_seqrecord_list, temp_file, "fasta")
    temp_file.close()
    alignment_filename = f"{temp_file.name}-muscle.fa"
    # raise an error if the alignment file already exists. (it won't but just in case)
    if os.path.exists(alignment_filename):
        raise FileExistsError(f"{alignment_filename} already exists")

    muscle_command = (
        f'{muscle_binary} -super5 "{temp_file.name}" -output "{alignment_filename}"'
    )
    subprocess.run(muscle_command, shell=True, check=True)

    if output_type == "list":
        muscle_output = tools.import_fasta(alignment_filename, output_format="list")
    elif output_type == "dict":
        muscle_output = tools.import_fasta(alignment_filename, output_format="dict")
    elif output_type == "alignment":
        muscle_output = AlignIO.read(alignment_filename, "fasta")

    # delete temporary file
    os.remove(alignment_filename)
    os.remove(temp_file.name)
    return muscle_output


def run_aacons(input_alignment_file, aacons_executable='java -jar /Users/jackson/tools/aacons/compbio-conservation-1.1.jar'):
    """executes aacons on an alignment file and returns the path to the output file

    Parameters
    ----------
    input_alignment_file : str
        input alignment file
    aacons_executable : str, optional
        command to execute aacons, by default 'java -jar /Users/jackson/tools/aacons/compbio-conservation-1.1.jar'

    Returns
    -------
    Pathlib.Path
        output file path
    """    
    input_alignment_file = Path(input_alignment_file)
    output_file_name = input_alignment_file.stem + "-aacons.txt"
    output_file = input_alignment_file.parent / output_file_name
    
    # run aacons
    aacons_command = f'{aacons_executable} -i={input_alignment_file} -m -o={output_file}'
    subprocess.run(aacons_command, shell=True, check=True)
    return output_file


def run_aacons_normed(input_alignment_file, aacons_executable='java -jar /Users/jackson/tools/aacons/compbio-conservation-1.1.jar'):
    """executes aacons on an alignment file and returns the path to the output file

    Parameters
    ----------
    input_alignment_file : str
        input alignment file
    aacons_executable : str, optional
        command to execute aacons, by default 'java -jar /Users/jackson/tools/aacons/compbio-conservation-1.1.jar'

    Returns
    -------
    Pathlib.Path
        output file path
    """    
    input_alignment_file = Path(input_alignment_file)
    output_file_name = input_alignment_file.stem + "-aacons_normed.txt"
    output_file = input_alignment_file.parent / output_file_name
    
    # run aacons
    aacons_command = f'{aacons_executable} -i={input_alignment_file} -m -n -o={output_file}'
    subprocess.run(aacons_command, shell=True, check=True)
    return output_file






# %%
# ==============================================================================
# // deprecated functions
# ==============================================================================

# # function that generates a mafft alignment command
# def mafft_align_command(fasta_file, output_dir, outfmt="fa", overwrite=True):
#     allowed_outfmts = ["fa", "clustal"]
#     if outfmt == "fa":
#         new_name = f"{os.path.splitext(os.path.basename(fasta_file))[0]}-MAFFTalgn.fa"
#         new_file = os.path.join(output_dir, new_name)
#         command = f'mafft --thread 8 --quiet "{fasta_file}" > "{new_file}"'
#     elif outfmt == "clustal":
#         new_name = (
#             f"{os.path.splitext(os.path.basename(fasta_file))[0]}-MAFFTalgn.clustal"
#         )
#         new_file = os.path.join(output_dir, new_name)
#         command = f'mafft --thread 8 --quiet --clustalout "{fasta_file}" > "{new_file}"'
#     # if `outfmt` is not recognized, raise an error
#     if outfmt not in allowed_outfmts:
#         raise ValueError(f"`outfmt` must be one of {allowed_outfmts}")
#     if not overwrite:
#         if os.path.exists(new_file):
#             print(f"{new_file} file already exists")
#             return None
#     return command


# # function to generate clustal alignment command
# def clustal_align_command(fasta_file, output_dir, outfmt="fa", overwrite=True):
#     new_name = (
#         f"{os.path.splitext(os.path.basename(fasta_file))[0]}-clustalalgn.{outfmt}"
#     )
#     new_file = os.path.join(output_dir, new_name)
#     if not overwrite:
#         if os.path.exists(new_file):
#             print(f"{new_file} file already exists")
#             return None
#     command = f'clustalo -i "{fasta_file}" -o "{new_file}" -v --outfmt={outfmt}'
#     return command


# def cp_command_filenames_run(source_filepath, destination_filepath):
#     command = f'cp "{source_filepath}" "{destination_filepath}"'
#     subprocess.run(command, shell=True, check=True)

# def __cp_command(
#     source_directory, source_filename, destination_directory, destination_filename=None
# ):
#     source = os.path.join(source_directory, source_filename)
#     if destination_filename is None:
#         destination = os.path.join(destination_directory, source_filename)
#     else:
#         destination = os.path.join(destination_directory, destination_filename)
#     command = f'cp "{source}" "{destination}"'
#     return command
