#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""This is the imputation server web UI."""
from flask import Flask, render_template, request, jsonify

import jinja2
import csv
import os

from dotenv import load_dotenv

load_dotenv()

data = []
with open("hibagmodel4flask.csv", "r") as csvfile:
    csvreader = csv.DictReader(csvfile)
    data = list(csvreader)

# hibag_genotyping_platform/rdata_filenames.txtを読み込んで、登場順にdataにColumn5として追加する
with open("hibag_genotyping_platforms/rdata_filenames.txt", "r") as rdata_filenames:
    rdata_filenames_list = rdata_filenames.read().splitlines()
    line = 0
    for row in data:
        row["Column5"] = rdata_filenames_list[line]
        line += 1


app = Flask(__name__)

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


@app.route("/", methods=["GET", "POST"])
def index():
    """Show the main page."""
    # GET
    if request.method == "GET":
        return render_template("index.html")
    # POST
    elif request.method == "POST":
        configcontent = ""
        configcontent += "gt:\n  class: File\n"
        configcontent += "  path: " + request.form["target_vcf"] + "\n"
        configcontent += "gp: " + '"' + request.form["output_genotype_prob"] + '"' + "\n"
        configcontent += "nthreads: " + request.form["num_threads"] + "\n"

        # read the reference panel config file
        refpanel = request.form["reference_panel"]
        referencepanelconfigfile = ""
        if refpanel == "GRCh37.1KGP":
            referencepanelconfigfile = "/usr/local/shared_data/imputation-server/reference/GRCh37.1KGP/default.config.yaml"
        elif refpanel == "GRCh37.1KGP-EAS":
            referencepanelconfigfile = "/usr/local/shared_data/imputation-server/reference/GRCh37.1KGP-EAS/default.config.yaml"
        elif refpanel == "GRCh38.1KGP":
            referencepanelconfigfile = "/usr/local/shared_data/imputation-server/reference/GRCh38.1KGP/default.config.yaml"
        elif refpanel == "GRCh38.1KGP-EAS":
            referencepanelconfigfile = "/usr/local/shared_data/imputation-server/reference/GRCh38.1KGP-EAS/default.config.yaml"
        elif refpanel == "others":
            referencepanelconfigfile = request.form["ref_panel_config"]
        with open(referencepanelconfigfile, "r") as f:
            configcontent += f.read()
        return render_template("index.html", configcontent=configcontent)


@app.route("/plink", methods=["GET", "POST"])
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


@app.route("/bplink", methods=["GET", "POST"])
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


@app.route("/hibag", methods=["GET", "POST"])
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


@app.route("/hibag/get_dropdown2")
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


@app.route("/hibag/get_dropdown3")
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


@app.route("/hibag/get_hibagmodel_filepath")
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


if __name__ == "__main__":
    # run host 0.0.0.0
    # Base.metadata.create_all(bind=ENGINE)

    app.run(
        debug=True,
        host="0.0.0.0",
        port=int(os.environ.get("FLASK_PORT", 5000)),
    )
