#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""This is the imputation server web UI."""
from flask import Flask, render_template, request, jsonify
import pandas as pd
import jinja2

app = Flask(__name__)

hibag_job_template = '''
in_bed:
  class: File
  path: {{ in_bed_path }}
in_chromosome_number: "{{ in_chromosome_number }}"
filter_chrom_out_name: "test_chrom6_filter_newdocker1"
runhibag_out_name: "{{ runhibag_out_name }}"
in_modelfile:
  class: File
  path: {{ model_file }}
'''

hibag_parameters = {
    'in_bed_path': '',
    'in_chromosome_number': '6',
    'runhibag_out_name': '',
    'model_file': '' 
}

# set the secret key.  keep this really secret:
app.secret_key = "k9SZr98j/3yX R~XHH!jmN]0d2,?RT"

hibagmodel_df = pd.read_csv('hibagmodel4flask.csv')

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
        configcontent += "gp: " + "\"" + request.form["output_genotype_prob"] + "\"" + "\n"
        configcontent += "nthreads: " + request.form["num_threads"] + "\n"

        # read the reference panel config file
        refpanel = request.form["reference_panel"]
        referencepanelconfigfile =""
        if refpanel == "GRCh37.1KGP":
            referencepanelconfigfile = "/home/ddbjshare-pg/imputation-server/reference/GRCh37.1KGP/default.config.yaml"
        elif refpanel == "GRCh37.1KGP-EAS":
            referencepanelconfigfile = "/home/ddbjshare-pg/imputation-server/reference/GRCh37.1KGP-EAS/default.config.yaml"
        elif refpanel == "GRCh38.1KGP":
            referencepanelconfigfile = "/home/ddbjshare-pg/imputation-server/reference/GRCh38.1KGP/default.config.yaml"
        elif refpanel == "GRCh38.1KGP-EAS":
            referencepanelconfigfile = "/home/ddbjshare-pg/imputation-server/reference/GRCh38.1KGP-EAS/default.config.yaml"
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
    dropdown_list1 = hibagmodel_df['Column1'].unique().tolist()
    if request.method == "GET":
        return render_template('hibag.html', dropdown_list1=dropdown_list1)
    elif request.method == "POST":
        env = jinja2.Environment(loader=jinja2.BaseLoader())
        template = env.from_string(hibag_job_template)
        hibag_parameters['in_bed_path'] = request.form["in_bed"]
        hibag_parameters['runhibag_out_name'] = request.form["out_name"]
        print(request.form["hibagmodel_filepath"])
        hibag_parameters['model_file'] = request.form["hibagmodel_filepath"]
        rendered_yaml = template.render(hibag_parameters)
        return render_template('hibag.html', dropdown_list1=dropdown_list1, rendered_yaml=rendered_yaml)

@app.route('/hibag/get_dropdown2')
def get_dropdown2():
    selected_val1 = request.args.get('selected_val1', type=str)
    dropdown_list2 = hibagmodel_df[hibagmodel_df['Column1'] == selected_val1]['Column2'].unique().tolist()
    print(dropdown_list2)
    return jsonify(dropdown_list2)

@app.route('/hibag/get_dropdown3')
def get_dropdown3():
    selected_val2 = request.args.get('selected_val2', type=str)
    selected_val1 = request.args.get('selected_val1', type=str)
    # print(selected_val1)
    val1_index = hibagmodel_df['Column1'] == selected_val1
    val2_index = hibagmodel_df['Column2'] == selected_val2
    foo = val1_index & val2_index
    # print(foo.value_counts())
    dropdown_list3 = hibagmodel_df[foo]['Column3'].unique().tolist()
    return jsonify(dropdown_list3)

@app.route('/hibag/get_hibagmodel_filepath')
def get_hibagmodel_filepath():
    selected_val3 = request.args.get('selected_val3', type=str)
    selected_val2 = request.args.get('selected_val2', type=str)
    selected_val1 = request.args.get('selected_val1', type=str)
    val1_index = hibagmodel_df['Column1'] == selected_val1
    val2_index = hibagmodel_df['Column2'] == selected_val2
    val3_index = hibagmodel_df['Column3'] == selected_val3
    foo = val1_index & val2_index & val3_index
    hibagmodel_filepath = hibagmodel_df[foo]['Column4'].unique().tolist()
    return jsonify(hibagmodel_filepath)

if __name__ == "__main__":
    # run host 0.0.0.0
    # Base.metadata.create_all(bind=ENGINE)

    app.run(
        debug=True,
        host="0.0.0.0",
    )
