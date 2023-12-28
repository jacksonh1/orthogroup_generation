import copy
import json
import os
import pathlib
import re
from pathlib import Path

import pandas as pd
from Bio import Seq, SeqIO
from pyprojroot import here

import local_env_variables.env_variables as env
import local_orthoDB_group_tools.sql_queries as sql_queries
import local_orthoDB_group_tools.uniprotid_search as uniprotid_search


class orthoDB_database:
    def __init__(self, database_files: env.orthoDB_files_object = env.orthoDB_files):
        self.datafiles = database_files
        self.data_all_seqrecords_dict = env.load_data_all_odb_seqs(self.datafiles)
        self.data_levels_df = env.load_data_levels_df(self.datafiles)
        self._load_data_species_dict()

    def _load_data_species_dict(self):
        self.data_species_dict = (
            env.load_data_species_df(self.datafiles)[["species ID", "species name"]]
            .set_index("species ID")
            .to_dict()["species name"]
        )



class orthoDB_query:
    """
    This object's role should be to store the information about the selected ortholog group and the query protein, and to provide methods to query the orthoDB database for information about the ortholog group.
    """

    odb_database = orthoDB_database()

    def __init__(self, output_dir_base=None):
        if output_dir_base is None:
            output_dir_base = "./orthoDB_analysis"
        self.output_dir_base = Path(output_dir_base)
        self.output_dir_base.mkdir(parents=True, exist_ok=True)
        self.output_file_dict = {}
        self.filter_dict = {}

    # ==============================================================================
    # // helper functions for finding the protein in the database using uniprot id
    # ==============================================================================

    def _get_geneid_info(self, query_odb_gene_id=None):
        if query_odb_gene_id is None:
            query_odb_gene_id = self.query_odb_gene_id
        self.query_species_id = sql_queries.odb_gene_id_2_species_id(query_odb_gene_id)
        self.query_species_name = self.odb_database.data_species_dict[
            self.query_species_id
        ]
        self.query_ogid_list = sql_queries.odb_gene_id_2_ogid_list(query_odb_gene_id)
        # if there are no OGs for this gene, raise a ValueError
        if len(self.query_ogid_list) == 0:
            raise ValueError(
                f"no ortholog groups found for gene id {query_odb_gene_id}"
            )
        qseq = self.odb_database.data_all_seqrecords_dict[query_odb_gene_id]
        self.query_sequence = qseq
        # self.query_sequence_id = str(qseq.id)

    def _available_OGs_info(self):
        """get info about the list of OGs available for the selected geneid"""
        query_og_df = sql_queries.ogid_list_2_og_df(self.query_ogid_list)
        query_level_df = self.odb_database.data_levels_df[
            self.odb_database.data_levels_df["level NCBI tax id"].isin(
                query_og_df["level NCBI tax id"].unique()
            )
        ].copy()
        query_available_OGs_info_df = pd.merge(
            query_og_df, query_level_df, on="level NCBI tax id", how="inner"
        )
        query_available_OGs_info_df = query_available_OGs_info_df[
            [
                "OG id",
                "level NCBI tax id",
                "level name",
                "total non-redundant count of species underneath",
                "OG name",
            ]
        ]
        query_available_OGs_info_df[
            "total non-redundant count of species underneath"
        ] = query_available_OGs_info_df[
            "total non-redundant count of species underneath"
        ].astype(
            float
        )
        # query_OG_info_df = query_OG_info_df.infer_objects()
        self.query_available_OGs_info_df = query_available_OGs_info_df.sort_values(
            by="total non-redundant count of species underneath"
        )

    # ==============================================================================
    # // DRIVER - finding and setting the geneid in the database
    # ==============================================================================
    def driver_set_geneid_by_uniprotid_search(
        self, uniprotid, duplicate_action="longest"
    ):
        self.query_odb_gene_id = uniprotid_search.uniprotid_2_odb_gene_id(
            uniprotid, duplicate_action=duplicate_action
        )
        self.query_uniprot_id = uniprotid
        _ = self._get_geneid_info()
        self._available_OGs_info()

    def driver_set_geneid_directly(self, geneid):
        """
        TODO: get UniprotID from gene or xref table. Should probably use SQL query for this
        """
        self.query_odb_gene_id = geneid
        _ = self._get_geneid_info()
        self._available_OGs_info()

    # ==============================================================================
    # // writing output to files
    # ==============================================================================
    def set_query_output_directory(self, output_folder_name=None):
        if output_folder_name is None:
            if hasattr(self, "query_uniprot_id"):
                output_dir_path = (
                    self.output_dir_base
                    / f"{self.query_uniprot_id}-{self.query_odb_gene_id}"
                    / f"{self.selected_query_og_level_name}"
                )
            else:
                output_dir_path = (
                    self.output_dir_base
                    / f"{self.query_odb_gene_id}"
                    / f"{self.selected_query_og_level_name}"
                )
        else:
            output_dir_path = self.output_dir_base / output_folder_name
        self.query_output_dir_path = output_dir_path
        self.query_output_dir_path.mkdir(parents=True, exist_ok=True)

    def write_all_sequences(self, file_prefix=None):
        """
        TODO: put the filenames into in the set_query_output_directory function
        """
        if file_prefix is None:
            file_prefix = self.file_prefix
        output_filename1 = self.query_output_dir_path / f"{file_prefix}_full_OG.fasta"
        self._write_sequence_list_2_fasta(
            list(self.sequences_full_OG_dict.values()), output_filename1
        )
        self.output_file_dict["fasta sequences - full OG"] = output_filename1

        output_filename2 = self.query_output_dir_path / f"{file_prefix}_OG_LDOs.fasta"
        self._write_sequence_list_2_fasta(self.sequences_LDO_list, output_filename2)
        self.output_file_dict["fasta sequences - OG LDOs"] = output_filename2

        output_filename3 = (
            self.query_output_dir_path / f"{file_prefix}_OG_LDOs_cdhit.fasta"
        )
        self._write_sequence_list_2_fasta(
            self.sequences_OG_LDO_cdhit_list, output_filename3
        )
        self.output_file_dict["fasta sequences - OG LDOs cdhit"] = output_filename3

        if hasattr(self, "alignment_OG_LDO_cdhit"):
            output_filename4 = (
                self.query_output_dir_path
                / f"{file_prefix}_OG_LDOs_cdhit_mafftaln.fasta"
            )
            self._write_sequence_list_2_fasta(
                self.alignment_OG_LDO_cdhit, output_filename4
            )
            self.output_file_dict["fasta alignment - OG LDO cdhit"] = output_filename4

    def write_out_params(self):
        if hasattr(self, "query_uniprot_id"):
            info_json_filename = (
                self.query_output_dir_path
                / f"{self.query_uniprot_id}_{self.selected_query_og_level_name}_info__dict__.json"
            )
        else:
            info_json_filename = (
                self.query_output_dir_path
                / f"{self.query_odb_gene_id}_{self.selected_query_og_level_name}_info__dict__.json"
            )
        self.output_file_dict["json - query and ortho group info"] = info_json_filename
        self.output_file_dict_absolute = {
            k: str(v.absolute()) for k, v in self.output_file_dict.items()
        }
        self.output_file_dict = {k: str(v) for k, v in self.output_file_dict.items()}
        self.output_file_dict_absolute = {
            k: str(v) for k, v in self.output_file_dict_absolute.items()
        }
        output_dict = {}
        output_dict["json_info_file"] = str(info_json_filename)
        for k, v in self.__dict__.items():
            if k.startswith("sequence") or k.startswith("alignment"):
                continue
            if k == "query_sequence":
                continue
            if type(v) in [pd.DataFrame, pd.Series]:
                continue
            if type(v) == pathlib.PosixPath:
                output_dict[k] = str(v)
                continue
            output_dict[k] = v

        output_dict["num_sequences_full_OG"] = len(self.sequences_full_OG_dict)
        output_dict["num_sequences_LDO"] = len(self.sequences_LDO_list)
        output_dict["num_sequences_LDO_cdhit"] = len(self.sequences_OG_LDO_cdhit_list)
        self.output_dict = output_dict
        with open(info_json_filename, "w") as f:
            json.dump(output_dict, f, indent=4)
        # with open(self.query_output_dir_path / 'filter_results.json', 'w') as f:
        # json.dump(self.filter_dict, f, indent=4)

    # ==============================================================================
    # // DRIVER - write files
    # ==============================================================================
    def write_files(self, output_folder_name=None):
        self.set_query_output_directory(output_folder_name=output_folder_name)
        self.file_prefix = self.query_output_dir_path.stem
        self.write_all_sequences()
        self.write_out_params()

    # ==============================================================================
    # // functions to print info to screen
    # ==============================================================================
    def print_database_filepaths(self):
        for k, v in self.odb_database.datafiles.items():
            print(f"- {k}\n    {v}")

    def print_orthoDB_readme(self):
        with open(self.odb_database.datafiles["readme"], "r") as f:
            print(f.read())

    # ==============================================================================
    # // general utilities (static methods)
    # ==============================================================================
    @staticmethod
    def _search_df(df, column, query):
        matches = df[df[column] == query].copy()
        if len(matches) == 0:
            print(f"`{query}` not found in {column} column")
            return None
        return matches

    @staticmethod
    def _convert_sequence_dict_to_list(seq_dict):
        return [seq for seq in seq_dict.values()]

    @staticmethod
    def _write_sequence_list_2_fasta(seqrecord_list, filename):
        with open(filename, "w") as f:
            SeqIO.write(seqrecord_list, f, "fasta")

    # for i in ldo_seqrecord_list:
    #     score = ldo_df.loc[ldo_df["id"] == i.id, "PID"].values[0]
    #     i.id = f"{i.id}-{score:.2f}"
