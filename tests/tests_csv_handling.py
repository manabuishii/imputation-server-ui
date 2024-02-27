import unittest
import csv


with open("hibagmodel4flask.csv", "r") as csvfile:
    # CSVファイルを読み込む
    csvreader = csv.DictReader(csvfile)

    # データをリストに格納
    data = list(csvreader)

import pandas as pd

hibagmodel_df = pd.read_csv("hibagmodel4flask.csv")


def test_lists_intersection(list1, list2):
    set1 = set(list1)
    set2 = set(list2)
    intersection = set1.intersection(set2)
    return len(intersection) > 0


class TestListIntersection(unittest.TestCase):
    def test_column1(self):
        dropdown_list1_hdf = hibagmodel_df["Column1"].unique().tolist()
        dl1 = set(row["Column1"] for row in data)
        self.assertTrue(test_lists_intersection(dl1, dropdown_list1_hdf))

    def test_column2(self):
        for selected_val1 in hibagmodel_df["Column1"].unique().tolist():
            unique_values_column2_df = (
                hibagmodel_df[hibagmodel_df["Column1"] == selected_val1]["Column2"]
                .unique()
                .tolist()
            )
            unique_values_column2 = list(
                set(row["Column2"] for row in data if row["Column1"] == selected_val1)
            )
            self.assertTrue(
                test_lists_intersection(unique_values_column2, unique_values_column2_df)
            )

    def test_column3(self):
        for selected_val1 in hibagmodel_df["Column1"].unique().tolist():
            unique_values_column2_df = (
                hibagmodel_df[hibagmodel_df["Column1"] == selected_val1]["Column2"]
                .unique()
                .tolist()
            )
            for selected_val2 in unique_values_column2_df:
                # unique_values_column3_df = hibagmodel_df[(hibagmodel_df['Column1'] == selected_val1) & (hibagmodel_df['Column2'] == selected_val2)]['Column3'].unique().tolist()
                # unique_values_column3 = list(set(row['Column3'] for row in data if row['Column1'] == selected_val1 and row['Column2'] == selected_val2))
                val1_index = hibagmodel_df["Column1"] == selected_val1
                val2_index = hibagmodel_df["Column2"] == selected_val2
                foo = val1_index & val2_index
                dropdown_list3_df = hibagmodel_df[foo]["Column3"].unique().tolist()
                #
                filtered_data = [
                    row
                    for row in data
                    if row["Column1"] == selected_val1 and row["Column2"] == selected_val2
                ]
                unique_values_column3 = list(set(row["Column3"] for row in filtered_data))
                self.assertTrue(test_lists_intersection(unique_values_column3, dropdown_list3_df))


if __name__ == "__main__":
    unittest.main()
