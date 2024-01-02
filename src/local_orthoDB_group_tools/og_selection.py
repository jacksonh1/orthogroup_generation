
import pandas as pd

import local_env_variables.env_variables as env
import local_orthoDB_group_tools.sql_queries as sql_queries


def _ogid_list_2_og_info_df(ogid_list: list[str]) -> pd.DataFrame:
    og_query_results = []
    for og_id in ogid_list:
        og_query_results.append(sql_queries.get_ogid_info(og_id))
    og_df = pd.DataFrame.from_records(
        og_query_results, columns=["OG id", "level NCBI tax id", "OG name"]
    )
    og_df["level NCBI tax id"] = og_df["level NCBI tax id"].astype(int)
    return og_df


def ogid_list_2_og_level_info_df(ogid_list: list[str]) -> pd.DataFrame:
    """get info about the list of OGs available for the selected geneid"""
    query_og_df = _ogid_list_2_og_info_df(ogid_list)
    query_available_OGs_info_df = pd.merge(
        query_og_df, env.odb_database.data_levels_df, on="level NCBI tax id", how="left"
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
        int
    )
    # query_OG_info_df = query_OG_info_df.infer_objects()
    query_available_OGs_info_df = query_available_OGs_info_df.sort_values(
        by="total non-redundant count of species underneath"
    )
    return query_available_OGs_info_df


def get_available_ogs(odb_gene_id: str) -> pd.DataFrame:
    """get info about the list of OGs available for an input odb gene id

    returns a dataframe with the following columns:
    OG id | level NCBI tax id | level name | total non-redundant count of species underneath | OG name
    """
    ogid_list = sql_queries.odb_gene_id_2_ogid_list(odb_gene_id)
    return ogid_list_2_og_level_info_df(ogid_list)


def select_OG_by_level_name(odb_gene_id: str, level_name: str) -> tuple[str, str]:
    """select an OG from the list of available OGs for the selected gene id

    Returns
    -------
    str
        the selected OG id
    str
        the selected OG level name

    Raises
    ------
    ValueError
        raised if no OGs are found for the `odb_gene_id` with level name `level_name`
    ValueError
        raised if multiple OGs are found for the `odb_gene_id` with level name `level_name`
    """
    ogs_info_df = get_available_ogs(odb_gene_id)
    selected_OG_info_df = ogs_info_df[ogs_info_df["level name"] == level_name]
    if len(selected_OG_info_df) == 0:
        raise ValueError(
            f"No OGs found for {odb_gene_id} with level name `{level_name}`. available levels are: {list(ogs_info_df['level name'].unique())}"
        )
    if len(selected_OG_info_df) > 1:
        raise ValueError(
            f"Multiple OGs found for {odb_gene_id} with level name `{level_name}`. duplicate OGs: {selected_OG_info_df}"
        )
    return selected_OG_info_df["OG id"].values[0], selected_OG_info_df["level name"].values[0]


# ==============================================================================
# //
# ==============================================================================



# def select_OG_by_level_with_most_species(odbquery: database.orthoDB_query):
#     temp = odbquery.query_available_OGs_info_df.sort_values(
#         by="total non-redundant count of species underneath", ascending=False
#     ).reset_index(drop=True)
#     odbquery.selected_query_ogid = temp.loc[0, "OG id"]
#     wrap_up_OG_selection(odbquery)



# def select_OG_by_target_number_of_species(odbquery: database.orthoDB_query, target_number_of_species):
#     temp = odbquery.query_available_OGs_info_df.copy()
#     temp["diff"] = abs(
#         target_number_of_species
#         - temp["total non-redundant count of species underneath"]
#     )
#     odbquery.selected_query_ogid = temp.loc[temp["diff"].idxmin(), "OG id"]
#     wrap_up_OG_selection(odbquery)




# class orthoDB_query:
#     """
#     This object's role should be to store the information about the selected ortholog group and the query protein, and to provide methods to query the orthoDB database for information about the ortholog group.
#     """

#     odb_database = env.odb_database

#     def __init__(self):
#         self.ogid = None

#     @staticmethod
#     def _search_df(df, column, query):
#         matches = df[df[column] == query].copy()
#         if len(matches) == 0:
#             print(f"`{query}` not found in {column} column")
#             return None
#         return matches

#     @staticmethod
#     def _convert_sequence_dict_to_list(seq_dict):
#         return [seq for seq in seq_dict.values()]

#     @staticmethod
#     def _write_sequence_list_2_fasta(seqrecord_list, filename):
#         with open(filename, "w") as f:
#             SeqIO.write(seqrecord_list, f, "fasta")


# class odb_orthogroup:


#     def __init__(self, ogid):
#         self.ogid = ogid
#         _, self.ncbi_tax_id, self.og_name = sql_queries.get_ogid_info(ogid)
#         self.level = env.odb_database.data_levels_taxid_name_dict[int(self.ncbi_tax_id)]

#     def __repr__(self):
#         return f"odb_orthogroup - ({self.ogid})"

#     def __str__(self):
#         return f"odb_orthogroup - ({self.ogid})"

#     def get_og_sequence_ids(self):
#         return sql_queries.ogid_2_odb_gene_id_list(self.ogid)
