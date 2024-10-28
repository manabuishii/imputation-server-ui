import os
import subprocess
import yaml
from typing import List, Tuple


# コマンドを実行する
def exec_command_oneline(
    region: str, target_vcf_filepath: str, singularity_image_path: str
) -> int:
    try:
        # 環境変数を設定、WARNINGを出さないようにする
        env = os.environ.copy()
        env["SINGULARITYENV_LC_ALL"] = "C"
        cmd = f"singularity run {singularity_image_path} bcftools view -H -r {region} {target_vcf_filepath} | head -n 10"
        result = subprocess.run(cmd, shell=True, text=True, capture_output=True, env=env)
        output = result.stdout
        exitstatus = result.returncode
        if exitstatus != 0:
            print(output)
            print(f"exit status: {exitstatus}")
            return exitstatus
        # 行数をチェックちょうど10行かのチェック、10でないときはエラー
        lines = output.splitlines()
        number_of_lines = len(lines)
        if number_of_lines != 10:
            print(output)
            print("lines are not 10.")
            return -1
    except Exception as e:
        print(f"An error occurred: {e}")
        return -1
    return 0


# regionが有効かどうかを判定する関数
# 中でコマンドを実行して、そのコマンドの実行結果が0かどうかで判定する
def is_valid_region(region: str, target_vcf_filepath: str, singularity_image_path: str) -> bool:
    exitstatus = exec_command_oneline(region, target_vcf_filepath, singularity_image_path)
    return exitstatus == 0


# create_vcffile_index関数
def create_vcffile_index(target_vcf_filepath: str, singularity_image_path: str) -> bool:
    try:
        # 環境変数を設定、WARNINGを出さないようにする
        env = os.environ.copy()
        env["SINGULARITYENV_LC_ALL"] = "C"
        with subprocess.Popen(
            [
                "singularity",
                "run",
                singularity_image_path,
                "bcftools",
                "index",
                "-f",
                "-t",
                target_vcf_filepath,
            ],
            stdout=subprocess.PIPE,
            text=True,
        ) as head_process:
            output = head_process.stdout.read()
            # bcftools の終了コードを取得
            bcftools_status = head_process.wait()
            if bcftools_status != 0:
                print(output)
                print(f"bcftools index failed. [exit status: {bcftools_status}]")
                return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False
    return True


def generate_reference_panel(
    target_vcf_filepath: str, config_filepath: str, singularity_image_path: str
) -> Tuple[bool, str]:
    """
    Generate a reference panel for the target VCF file.
    index file is automatically created.
    if there is a index file, it is overwritten.
    Args:
        target_vcf_filepath (str): The target VCF file path.
        config_filepath (str): The reference panel configuration file path.
        singularity_image_path (str): The Singularity image path.
    Returns:
        Tuple[bool, str]: A tuple of a boolean value and a string.
        isValid: valid or not.
        contents: The contents of the reference panel configuration file.
    """
    # ファイルサイズが0の場合はFalseと、メッセージを返す
    if os.path.getsize(target_vcf_filepath) == 0:
        return False, "File size is 0."
    # create index
    isCreated = create_vcffile_index(target_vcf_filepath, singularity_image_path)
    if not isCreated:
        return False, "Failed to create index file."
    # read original config file
    with open(config_filepath, "r") as file:
        regionlist = yaml.safe_load(file)
    ## loop region list. array
    filtered_region_list = {"region_list": []}
    for regionobj in regionlist["region_list"]:
        region = regionobj["region"]
        # result = is_valid_region(region)
        result = is_valid_region(region, target_vcf_filepath, singularity_image_path)
        if result:
            filtered_region_list["region_list"].append(regionobj)
    if len(filtered_region_list["region_list"]) == 0:
        return False, "No valid region"
    contents = yaml.dump(filtered_region_list)
    return True, contents


# if there is "2-digit", remove it.
def filtered_2_digit(data):
    filtered_data = []
    for row in data:
        if "2-digit" in row["Column1"]:
            continue
        if "2-digit" in row["Column2"]:
            continue
        if "2-digit" in row["Column3"]:
            continue
        if "2-digit" in row["Column4"]:
            continue
        filtered_data.append(row)
    return filtered_data


def check_bbj_config_available() -> Tuple[bool, bool, bool, bool]:
    is_check_1 = False
    is_check_2 = False
    is_check_3 = False
    is_check_4 = False
    print(os.path.expanduser("~/jga-panel/BBJ1K_1/default.config.yaml"))
    if os.path.exists(os.path.expanduser("~/jga-panel/BBJ1K_1/default.config.yaml")):
        is_check_1 = True
    if os.path.exists(os.path.expanduser("~/jga-panel/BBJ1K_2/default.config.yaml")):
        is_check_2 = True
    if os.path.exists(os.path.expanduser("~/jga-panel/BBJ1K_3/default.config.yaml")):
        is_check_3 = True
    if os.path.exists(os.path.expanduser("~/jga-panel/BBJ1K_4/default.config.yaml")):
        is_check_4 = True
    return is_check_1, is_check_2, is_check_3, is_check_4
