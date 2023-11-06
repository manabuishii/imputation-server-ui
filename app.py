#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""This is the imputation server web UI."""
from flask import Flask, render_template, request
import pandas as pd

app = Flask(__name__)

# set the secret key.  keep this really secret:
app.secret_key = "k9SZr98j/3yX R~XHH!jmN]0d2,?RT"

data = pd.read_csv('hibagmodel4flask.csv')

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
    # items = ["model1", "model2", "model3"]
    # selected_item = None

    # if request.method == "GET":
    #     return render_template("hibag.html")
    # elif request.method == "POST":
    #     selected_item = request.form.get('select_item')
    # return render_template("hibag.html", items=items, selected_item=selected_item)

    selections = [request.form.get('dropdown1'), request.form.get('dropdown2'), request.form.get('dropdown3'), request.form.get('dropdown4')]
    selections = [s for s in selections if s]  # Remove None values

    filtered_data = data
    #for i, column in enumerate(['option1', 'option2', 'option3', 'option4']):
    for i, column in enumerate(['USE_YOUR_MODEL_OR_NOT', 'GENOTYPING_PLATFORMS', 'RESOLUTION', 'ANCESTRY']):
        if i < len(selections):
            filtered_data = filtered_data[filtered_data[column] == selections[i]]

    options1 = data['USE_YOUR_MODEL_OR_NOT'].unique().tolist()
    options2 = filtered_data['GENOTYPING_PLATFORMS'].unique().tolist() if len(selections) >= 1 else []
    options3 = filtered_data['RESOLUTION'].unique().tolist() if len(selections) >= 2 else []
    options4 = filtered_data['ANCESTRY'].unique().tolist() if len(selections) >= 3 else []
    answer = filtered_data['HIBAG_MODEL_URL'].tolist() if len(selections) >= 4 else []

    return render_template('hibag.html', options1=options1, options2=options2, options3=options3, options4=options4, answer=answer, selections=selections)


if __name__ == "__main__":
    # run host 0.0.0.0
    # Base.metadata.create_all(bind=ENGINE)

    app.run(
        debug=True,
        host="0.0.0.0",
    )
