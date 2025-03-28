#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""This is the imputation server web UI."""
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask import Blueprint

import requests
import jinja2
import csv
import os
import json
import time
from datetime import datetime

import utils.utils as utils

from dotenv import load_dotenv

load_dotenv()

raw_data = []
with open("hibagmodel4flask.csv", "r") as csvfile:
    csvreader = csv.DictReader(csvfile)
    raw_data = list(csvreader)

data = utils.filtered_2_digit(raw_data)


# hibag_genotyping_platform/rdata_filenames.txtを読み込んで、登場順にdataにColumn5として追加する
with open("hibag_genotyping_platforms/rdata_filenames.txt", "r") as rdata_filenames:
    rdata_filenames_list = rdata_filenames.read().splitlines()
    line = 0
    for row in data:
        row["Column5"] = rdata_filenames_list[line]
        line += 1


app = Flask(__name__)
app_blueprint = Blueprint(
    "app", __name__, url_prefix=os.environ.get("URL_PREFIX_IMPUTATION_WORKFLOW_UI", "/")
)

hibag_job_template = """
in_bed:
  class: File
  path: {{ in_bed_path }}
in_chromosome_number: "{{ in_chromosome_number }}"
filter_chrom_out_name: "test_chrom6_filter_newdocker1"
out_name: "{{ runhibag_out_name }}"
in_modelfile:
  class: File
  path: {{ model_file }}
"""

hibag_parameters = {
    "in_bed_path": "",
    "in_chromosome_number": "6",
    "runhibag_out_name": "",
    "model_file": "",
}
hibagdatadirectory = "/usr/local/shared_data/imputation-server/hibagdata/"
# set the secret key.
app.secret_key = os.getenv("IMPUTATION_SERVER_SECRET_KEY")
# bcftools container
app.config["BCFTOOLS_IMAGE_PATH"] = os.getenv("BCFTOOLS_IMAGE_PATH", "")
is_bcftools = os.path.exists(app.config["BCFTOOLS_IMAGE_PATH"])

#
# PGS Catalog API URL
PGS_API_URL = "https://www.pgscatalog.org/rest/score/all"

# キャッシュファイルのパス
CACHE_FILE = "pgs_catalog_cache.json"
# キャッシュの有効期限（秒）- 1日 * 7
CACHE_EXPIRY = 864000 * 1000 * 7


def fetch_all_pgs_scores():
    """
    PGS Catalog APIから全てのスコアデータを取得する
    ページネーションを使用して全件取得
    """
    all_results = []
    next_url = PGS_API_URL

    while next_url:
        print(f"Fetching data from: {next_url}")
        response = requests.get(next_url)
        data = response.json()

        # 結果を追加
        all_results.extend(data.get("results", []))

        # 次のページがあれば取得
        next_url = data.get("next")

    # 全データを含む応答を作成
    complete_response = {
        "count": len(all_results),
        "next": None,
        "previous": None,
        "results": all_results,
    }

    return complete_response


def get_cached_data():
    """
    キャッシュからデータを取得する
    キャッシュが存在しない、または期限切れの場合はNoneを返す
    """
    if not os.path.exists(CACHE_FILE):
        return None

    try:
        with open(CACHE_FILE, "r") as f:
            cache_data = json.load(f)

        # キャッシュの有効期限をチェック
        cache_time = cache_data.get("cache_time", 0)
        print(f"Cache time: {cache_time}")
        print(f"Current time: {time.time()}")
        print(f"Time diff: {time.time() - cache_time}")
        print(f"Cache expiry: {CACHE_EXPIRY}")
        if time.time() - cache_time > CACHE_EXPIRY:
            print("Cache expired")
            return None

        return cache_data.get("data")
    except Exception as e:
        print(f"Error reading cache: {e}")
        return None


def save_to_cache(data, cache_file=CACHE_FILE):
    """
    データをキャッシュに保存する
    """
    cache_data = {
        "cache_time": time.time(),
        "timestamp": datetime.now().isoformat(),
        "data": data,
    }

    try:
        with open(cache_file, "w") as f:
            json.dump(cache_data, f)
        print(f"Data cached successfully to {cache_file}. Total records: {data.get('count', 0)}")
    except Exception as e:
        print(f"Error saving cache: {e}")


@app_blueprint.route("/pgs")
def pgs():
    return render_template("pgs.html")


@app_blueprint.route("/pgs/generate-config", methods=["POST"])
def generate_pgs_config():
    """Generate PGS configuration based on submitted parameters."""
    # Get the form data from the request
    pgs_ids = request.form.getlist("pgs_ids")
    pgp_ids = request.form.getlist("pgp_ids")
    efo_ids = request.form.getlist("efo_ids")
    run_id = request.form.get("run_id", "")

    # pgs_ids, pgp_ids, efo_ids are at least 1 required
    if not (pgs_ids or pgp_ids or efo_ids):
        # redirect to the pgs page with an error message
        return redirect(url_for("app.pgs"))
    # run_id is required
    if not run_id:
        # redirect to the pgs page with an error message
        return redirect(url_for("app.pgs"))

    # Create a formatted string representation of the parameters
    config_content = "params {\n"

    if pgs_ids:
        config_content += "  pgs_id='" + ",".join(pgs_ids) + "'\n"

    if pgp_ids:
        config_content += "  pgp_id='" + ",".join(pgp_ids) + "'\n"

    if efo_ids:
        config_content += "  efo_id='" + ",".join(efo_ids) + "'\n"
    # open ../sapporo-service/run/
    sapporo_path = f"../sapporo-service/run/{run_id[:2]}/{run_id}"
    try:
        with open(sapporo_path + "/run_request.json", "r") as f:
            run_request = json.load(f)
            workflow_params = run_request["workflow_params"]
            # check workflow_params has GRCh37 or GRCh38
            if "GRCh37" in workflow_params:
                config_content += "\n  target_build='GRCh37'\n"
            elif "GRCh38" in workflow_params:
                config_content += "\n  target_build='GRCh38'\n"
            else:
                # error: target_build is not found
                return redirect(url_for("app.pgs"))
    except FileNotFoundError:
        # If the file cannot be opened, redirect to app.pgs
        return redirect(url_for("app.pgs"))
    # file list sapporo_path/outputs/*.vcf.gz
    vcf_files = []
    # samplesheetにパスを書くために、カレントディレクトリの絶対パスを取得
    current_dir = os.getcwd()
    # samplesheetの中身
    samplesheet_content = "sampleset,path_prefix,chrom,format,vcf_genotype_field\n"

    for root, dirs, files in os.walk(sapporo_path + "/outputs"):
        for file in files:
            if file.endswith(".beagle.vcf.gz"):
                # if file start with "chrX", pass
                if file.startswith("chrX"):
                    continue
                # samplesheetの中身を追加
                # sampleset
                sampleset = "1kgp-jpt"
                # path_prefix /path/to/outputs/chr1.beagle.vcf.gzのうち 最後の.vcf.gzまたはvcf を削除
                full_path = os.path.normpath(os.path.join(current_dir, root, file))
                path_prefix = ""
                if full_path.endswith(".vcf.gz"):
                    path_prefix = full_path[:-7]
                elif full_path.endswith(".vcf"):
                    path_prefix = full_path[:-4]
                # chrom
                chrom = file.split(".")[0].replace("chr", "")
                # format
                format = "vcf"
                # vcf_genotype_field
                vcf_genotype_field = "DS"
                samplesheet_content += (
                    f"{sampleset},{path_prefix},{chrom},{format},{vcf_genotype_field}\n"
                )
                vcf_files.append(full_path)
    # save sapporo_path > outputs/samplesheet-run_id.csv
    samplesheet_path = os.path.normpath(
        os.path.join(current_dir, sapporo_path, "outputs", "samplesheet-" + run_id + ".csv")
    )
    with open(samplesheet_path, "w") as f:
        f.write(samplesheet_content)
    # add samplesheet to config_content
    config_content += "\n"
    config_content += f"  input='{samplesheet_path}'\n"
    # add min_overlap
    config_content += f"\n  min_overlap=0\n\n"
    config_content += "}\n"

    # if not vcf_files, error
    if not vcf_files:
        return render_template("pgs_config.html", config_content="No VCF files found.")
    # add vcf_files to config_content
    # config_content += "\nvcf_files:\n"
    # for vcf_file in vcf_files:
    #     config_content += f"  - {vcf_file}\n"

    # Render the template with the config content
    return render_template("pgs_config.html", config_content=config_content)


@app_blueprint.route("/api/pgs-catalog", methods=["GET"])
def proxy_pgs_catalog():
    """
    プロキシエンドポイント - PGS Catalog APIへのリクエストを中継
    CORSの問題を回避するためのバックエンドプロキシ
    キャッシュ機能を実装して、APIへの負荷を軽減
    """
    try:
        # キャッシュからデータを取得
        cached_data = get_cached_data()

        # キャッシュが有効な場合はそれを返す
        if cached_data:
            print("Returning cached data")

            # キャッシュのタイムスタンプ情報を追加
            if os.path.exists(CACHE_FILE):
                try:
                    with open(CACHE_FILE, "r") as f:
                        cache_info = json.load(f)
                        if "timestamp" in cache_info:
                            cached_data["_cache_timestamp"] = cache_info["timestamp"]
                except Exception as e:
                    print(f"Error reading cache timestamp: {e}")

            return jsonify(cached_data)

        # キャッシュがない場合はAPIから全データを取得
        print("Fetching all data from API")
        all_data = fetch_all_pgs_scores()

        # データをキャッシュに保存
        save_to_cache(all_data)

        # タイムスタンプ情報を追加
        all_data["_cache_timestamp"] = datetime.now().isoformat()

        # APIからのレスポンスをJSONとして返す
        return jsonify(all_data)
    except Exception as e:
        # エラーが発生した場合はエラーメッセージを返す
        error_msg = str(e)
        print(f"Error: {error_msg}")
        return jsonify({"error": error_msg}), 500


@app_blueprint.route("/api/refresh-cache", methods=["POST"])
def refresh_cache():
    """
    キャッシュを強制的に更新するエンドポイント
    """
    try:
        # APIから全データを取得
        all_data = fetch_all_pgs_scores()

        # データをキャッシュに保存
        save_to_cache(all_data)

        return jsonify(
            {
                "success": True,
                "message": f"Cache refreshed successfully. Total records: {all_data.get('count', 0)}",
                "timestamp": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app_blueprint.route("/", methods=["GET", "POST"])
def index():
    """Show the main page."""
    # check tool
    is_message = False
    message_contents = ""
    if not is_bcftools:
        is_message = True
        message_contents = f"bcftools image[{app.config['BCFTOOLS_IMAGE_PATH']}] is not found.please set the PATH to bcftools singularity image , in .env file with BCFTOOLS_IMAGE_PATH=bcftools.sif"
    # check BBJ config
    is_check_1, is_check_2, is_check_3, is_check_4 = utils.check_bbj_config_available()
    print(is_check_1)
    # GET
    if request.method == "GET":

        return render_template(
            "index.html",
            is_message=is_message,
            message_contents=message_contents,
            is_check_1=is_check_1,
            is_check_2=is_check_2,
            is_check_3=is_check_3,
            is_check_4=is_check_4,
        )
    # POST
    elif request.method == "POST":
        target_vcf = request.form["target_vcf"]
        if not os.path.exists(target_vcf):
            if message_contents != "":
                message_contents += "<br>"
            message_contents += f"The target VCF file[{target_vcf}] is not found."
            return render_template(
                "index.html",
                is_message=True,
                message_contents=message_contents,
                is_check_1=is_check_1,
                is_check_2=is_check_2,
                is_check_3=is_check_3,
                is_check_4=is_check_4,
            )

        configcontent = ""
        configcontent += "gt:\n  class: File\n"
        configcontent += "  path: " + target_vcf + "\n"
        configcontent += "gp: " + '"' + request.form["output_genotype_prob"] + '"' + "\n"
        configcontent += "nthreads: " + request.form["num_threads"] + "\n"

        # read the reference panel config file
        refpanel = request.form["reference_panel"]
        referencepanelconfigfile = ""
        if refpanel == "GRCh37.1KGP":
            referencepanelconfigfile = "/usr/local/shared_data/imputation-server/reference/GRCh37.1KGP/default.config.yaml"
        elif refpanel == "GRCh37.1KGP-test":
            referencepanelconfigfile = (
                "/usr/local/shared_data/imputation-server/reference/GRCh37.1KGP/test.config.yaml"
            )
        elif refpanel == "GRCh37.1KGP-EAS":
            referencepanelconfigfile = "/usr/local/shared_data/imputation-server/reference/GRCh37.1KGP-EAS/default.config.yaml"
        elif refpanel == "GRCh38.1KGP":
            referencepanelconfigfile = "/usr/local/shared_data/imputation-server/reference/GRCh38.1KGP/default.config.yaml"
        elif refpanel == "GRCh38.1KGP-test":
            referencepanelconfigfile = (
                "/usr/local/shared_data/imputation-server/reference/GRCh38.1KGP/test.config.yaml"
            )
        elif refpanel == "GRCh38.1KGP-EAS":
            referencepanelconfigfile = "/usr/local/shared_data/imputation-server/reference/GRCh38.1KGP-EAS/default.config.yaml"
        elif refpanel == "others":
            referencepanelconfigfile = request.form["ref_panel_config"]
        #
        # with open(referencepanelconfigfile, "r") as f:
        #     configcontent += f.read()
        is_valid, reference_panel_contents = utils.generate_reference_panel(
            target_vcf, referencepanelconfigfile, app.config["BCFTOOLS_IMAGE_PATH"]
        )
        if is_valid:
            configcontent += reference_panel_contents
            return render_template(
                "index.html",
                configcontent=configcontent,
                is_check_1=is_check_1,
                is_check_2=is_check_2,
                is_check_3=is_check_3,
                is_check_4=is_check_4,
            )
        else:
            if message_contents != "":
                message_contents += "<br>"
            message_contents += "Failed to create the reference panel.<br>No valid region or chromosome is different.(ex.first column 'chr1' or '1')"
            return render_template(
                "index.html",
                is_message=True,
                message_contents=message_contents,
                is_check_1=is_check_1,
                is_check_2=is_check_2,
                is_check_3=is_check_3,
                is_check_4=is_check_4,
            )
    #
    return render_template(
        "index.html",
        is_check_1=is_check_1,
        is_check_2=is_check_2,
        is_check_3=is_check_3,
        is_check_4=is_check_4,
    )


@app_blueprint.route("/plink", methods=["GET", "POST"])
def plink():
    """Show the plink2vcf conversion configuration page."""
    # GET
    if request.method == "GET":
        return render_template("plink.html")
    elif request.method == "POST":
        configcontent = ""
        configcontent += "in_ped:\n    class: File\n    path: " + request.form["in_ped"] + "\n"
        configcontent += "out_name: " + request.form["out_name"] + "\n"
    return render_template("plink.html", configcontent=configcontent)


@app_blueprint.route("/bplink", methods=["GET", "POST"])
def bplink():
    """Show the bplink2vcf conversion configuration page."""
    # GET
    if request.method == "GET":
        return render_template("bplink.html")
    elif request.method == "POST":
        configcontent = ""
        configcontent += "in_bed:\n    class: File\n    path: " + request.form["in_bed"] + "\n"
        configcontent += "out_name: " + request.form["out_name"] + "\n"
    return render_template("bplink.html", configcontent=configcontent)


@app_blueprint.route("/hibag", methods=["GET", "POST"])
def hibag():
    dl1 = list(row["Column1"] for row in data)
    dropdown_list1 = []
    for i in dl1:
        if i not in dropdown_list1:
            dropdown_list1.append(i)

    if request.method == "GET":
        return render_template("hibag.html", dropdown_list1=dropdown_list1)
    elif request.method == "POST":
        if "reset_hibagmodel" not in request.form:
            env = jinja2.Environment(loader=jinja2.BaseLoader())
            template = env.from_string(hibag_job_template)
            hibag_parameters["in_bed_path"] = request.form["in_bed"]
            hibag_parameters["runhibag_out_name"] = request.form["out_name"]
            # print(request.form["hibagmodel_filepath"])
            hibag_parameters["model_file"] = request.form["hibagmodel_filepath"]
            rendered_yaml = template.render(hibag_parameters)
            in_bed_text = request.form["in_bed"]
            out_name_text = request.form["out_name"]
            return render_template(
                "hibag.html",
                in_bed=in_bed_text,
                out_name=out_name_text,
                rendered_yaml=rendered_yaml,
            )
        elif "reset_hibagmodel" in request.form:
            in_bed_text = request.form["in_bed"]
            out_name_text = request.form["out_name"]
            return render_template(
                "hibag.html",
                dropdown_list1=dropdown_list1,
                in_bed=in_bed_text,
                out_name=out_name_text,
            )


@app_blueprint.route("/hibag/get_dropdown2", methods=["GET", "POST"])
def get_dropdown2():
    selected_val1 = request.args.get("selected_val1", type=str)
    # dropdown_list2 = list(set(row["Column2"] for row in data if row["Column1"] == selected_val1))
    dl2 = list(row["Column2"] for row in data if row["Column1"] == selected_val1)
    dropdown_list2 = []
    for i in dl2:
        if i not in dropdown_list2:
            dropdown_list2.append(i)

    # print(dropdown_list2)
    return jsonify(dropdown_list2)


@app_blueprint.route("/hibag/get_dropdown3", methods=["GET", "POST"])
def get_dropdown3():
    selected_val2 = request.args.get("selected_val2", type=str)
    selected_val1 = request.args.get("selected_val1", type=str)

    filtered_data = [
        row for row in data if row["Column1"] == selected_val1 and row["Column2"] == selected_val2
    ]

    # 'Column3' 列の一意の値を取得し、リストに変換
    dl3 = list(row["Column3"] for row in filtered_data)
    dropdown_list3 = []
    for i in dl3:
        if i not in dropdown_list3:
            dropdown_list3.append(i)

    return jsonify(dropdown_list3)


@app_blueprint.route("/hibag/get_hibagmodel_filepath", methods=["GET", "POST"])
def get_hibagmodel_filepath():
    selected_val3 = request.args.get("selected_val3", type=str)
    selected_val2 = request.args.get("selected_val2", type=str)
    selected_val1 = request.args.get("selected_val1", type=str)
    filtered_data = [
        row
        for row in data
        if row["Column1"] == selected_val1
        and row["Column2"] == selected_val2
        and row["Column3"] == selected_val3
    ]

    # 'Column4' 列の一意の値を取得し、リストに変換
    hibagmodel_filepath = list(
        set(os.path.normpath(hibagdatadirectory + row["Column5"]) for row in filtered_data)
    )

    return jsonify(hibagmodel_filepath)


app.register_blueprint(app_blueprint)
if __name__ == "__main__":
    # run host 0.0.0.0
    # Base.metadata.create_all(bind=ENGINE)

    app.run(
        debug=True,
        host="0.0.0.0",
        port=int(os.environ.get("FLASK_PORT", 5000)),
    )
