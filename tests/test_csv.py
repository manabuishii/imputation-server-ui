import csv
from tests.tests_csv_handling_2 import filtered_2_digit


def test_filtered_2_digit(tmp_path):
    # Create a temporary CSV file
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        "Column1,Column2,Column3,Column4\n"
        "value1,value2,value3,value4\n"
        "2-digit,value2,value3,value4\n"
        "value1,2-digit,value3,value4\n"
        "value1,value2,2-digit,value4\n"
        "value1,value2,value3,2-digit\n"
    )

    # Read the CSV file and filter out rows containing "2-digit"
    data = []
    with open(csv_file, "r") as csvfile:
        csvreader = csv.DictReader(csvfile)
        data = list(csvreader)

    filtered_data = filtered_2_digit(data)

    # Check the filtered data
    assert len(filtered_data) == 1
    assert filtered_data[0] == {
        "Column1": "value1",
        "Column2": "value2",
        "Column3": "value3",
        "Column4": "value4",
    }
