"""
Code to run a simple API for getting results from RCET-RTEQcorrscan.

:author: Calum Chamberlain
:date: 18 Aug 2025

Adapted from code provided by Florent Aden-Antoniow


Goals:
1. provide a list of earthquakes responding to
2. retrieve results from selected earthquake (catalog.csv)
3. (possibly) - get static plots for that earthquake and statistics
"""
import uvicorn
import json
import pandas as pd
import logging
import os
import glob

from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse


Logger = logging.getLogger(__name__)

logging.basicConfig(
    level="INFO", 
    format="%(asctime)s\t[%(processName)s:%(threadName)s]: %(name)s\t%(levelname)s\t%(message)s")


BASEPATH = "/tmp/outputs/detections"
CATALOG_FILENAME = "{basepath}/{triggerID}/{triggerID}/output_out/catalog.csv"
SOURCE_FILENAME = "{basepath}/{triggerID}/{triggerID}/plotter_out/output_metrics_summary_file.csv"
PLOT_FILENAME = "{basepath}/{triggerID}/{triggerID}/plotter_out/{plot_type}_latest.png"


HOST = "0.0.0.0"
PORT = "8000"
CATS = "http://{host}:{port}/catalog/?triggerID={triggerID}"
TRIGGERS = "http://{host}:{port}/triggers"
PLOTS = "http://{host}:{port}/plots/?triggerID={triggerID}&plot_type={plot_type}"
SOURCES = "http://{host}:{port}/sources/?triggerID={triggerID}"

KNOWN_PLOT_TYPES = [
    "Scaled_Magnitude_Comparison",
    "Aftershock_extent_depth_map",
    "catalog_RT",
    "catalog_templates",
    "confidence_ellipsoid",
    "confidence_ellipsoid_vertical",
    "focal_sphere",
    "Geometry_with_time"
]


def get_catalog(triggerID: str) -> pd.DataFrame:
    filename = CATALOG_FILENAME.format(basepath=BASEPATH, triggerID=triggerID)
    Logger.info(f"Reading from {filename}")

    if not os.path.isfile(filename):
        Logger.error(f"{filename} does not exist")

    df = pd.read_csv(filepath_or_buffer=filename, parse_dates=[1])
    Logger.info(f"Read in file of {len(df)} rows")

    return df


def get_sources(triggerID: str) -> pd.DataFrame:
    filename = SOURCE_FILENAME.format(basepath=BASEPATH, triggerID=triggerID)
    Logger.info(f"Reading from {filename}")

    if not os.path.isfile(filename):
        Logger.error(f"{filename} does not exist")

    df = pd.read_csv(filepath_or_buffer=filename, parse_dates=[1])
    return df


def get_triggers() -> List[str]:
    possible_trigger_dirs = glob.glob(f"{BASEPATH}/*")
    triggers = []
    for possible_trigger_dir in possible_trigger_dirs:
        triggerID = os.path.basename(possible_trigger_dir)
        Logger.info(f"Scanning {triggerID} for output")
        cat_file = CATALOG_FILENAME.format(
            basepath=BASEPATH, triggerID=triggerID)
        if os.path.isfile(cat_file):
            triggers.append(triggerID)
    return triggers


########################### APP ########################################


app = FastAPI()


# -- allow any origin to query API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"]
)

# Home page
@app.get('/')
async def root():
    examplelinkcat = CATS.format(host=HOST, port=PORT, triggerID="2014p051675")
    triggerlink = TRIGGERS.format(host=HOST, port=PORT)

    html_content = f"""
    <html>
        <head>
            <title>RCET RTEQcorrscan results</title>
        </head>
        <body>
            <h1>So you want some aftershocks eh!?</h1>
            <p>Herein you will be able to get the most recent results for a specific RT-EQcorrscan run.</p>
            <h2>Example API syntax</h2>
            <p>To get the list of current triggers: <a href="{triggerlink}" target=>{triggerlink}</a></p>
            
            <h3>To download output catalog</h3>
            <p>Requesting catalog for trigger 2014p051675: <a href="{examplelinkcat}" target=_blank>{examplelinkcat}</a></p>
            <p>To load the results into a pandas dataframe:</p>
            <pre class="brush: python">
            import pandas as pd

            df = pd.read_json('{examplelinkcat}', orient='table')
            </pre>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

# Query for triggers
@app.get("/triggers/")
def root():
    try:
        trigger_ids = get_triggers()
    except Exception as e:
        return f"ERROR: {e}"

    return StreamingResponse(
        {"trigger_ids": trigger_ids},
        media_type="application/json",
        headers={"Content-Disposition":
                 f"attachment;filename=trigger_IDs.json"}
    )

# HTML render for events
@app.get("/trigger_table/")
def root():
    trigger_ids = get_triggers()
    
    trigger_table_head = """
    <table>
        <tr>
            <th>TriggerID</th>
            <th>Catalog-URL</th>
            <th>Sources-URL</th>
    """
    for plot_type in KNOWN_PLOT_TYPES:
        trigger_table_head += f"\n<th>{plot_type} URL</th>"
    trigger_table_head += "\n</tr>"
    trigger_table_foot = """
    </table>
    """
    trigger_table_body = []
    for trigger_id in trigger_ids:
        cat_url = CATS.format(host=HOST, port=PORT, triggerID=trigger_id)
        source_url = SOURCES.format(host=HOST, port=PORT, triggerID=trigger_id)
        trigger_row = f"""
        <tr>
            <td>{trigger_id}</td>
            <td><a href="{cat_url}">Catalog</a></td>
            <td><a href="{source_url}">Sources</a></td>
        """
        for plot_type in KNOWN_PLOT_TYPES:
            plot_url = PLOTS.format(host=HOST, port=PORT, triggerID=trigger_id,
                                    plot_type=plot_type)
            trigger_row += f"""\n<td><a href="{plot_url}">{plot_type}_latest</a></td>"""

        trigger_row += "\n</tr>"
        trigger_table_body.append(trigger_row)
    trigger_table_body = "\n".join(trigger_table_body)
    trigger_table = "\n".join(
        [trigger_table_head, trigger_table_body, trigger_table_foot])

    # Form the full html
    html_content = f"""
    <html>
        <head>
            <title>RCET RTEQcorrscan triggers</title>
        </head>
        <body>
            <h3>Available triggers:</h3>
            {trigger_table}
        </body>
    </html>
    """

    return HTMLResponse(content=html_content, status_code=200)



# Query for catalogs
@app.get("/catalog/")
def root(triggerID: str):
    try:
        cat_df = get_catalog(triggerID)
    except Exception as e:
        return f"ERROR: {e}"

    result = cat_df.to_json(index=False, orient='table')
    parsed = json.loads(result)

    return StreamingResponse(
        iter([result]),
        media_type='text/json',
        headers={"Content-Disposition":
                 f"attachment;filename=<{triggerID}_catalog.json"})


# Query for source params
@app.get("/sources/")
def root(triggerID: str):
    try:
        source_df = get_sources(triggerID)
    except Exception as e:
        return f"ERROR: {e}"
    
    result = source_df.to_json(index=False, orient='table')
    parsed = json.loads(result)

    return StreamingResponse(
        iter([result]),
        media_type='text/json',
        headers={"Content-Disposition":
                 f"attachment;filename=<{triggerID}_source.json"})



# Query for plots
@app.get("/plots/")
def root(triggerID: str, plot_type: str):
    if plot_type not in KNOWN_PLOT_TYPES:
        Logger.error(f"{plot_type} not in known types.")
        return HTMLResponse(
                content=f"""
    <html>
        <p>{plot_type} is not a known plot format.</p>
        <p>Known plot types:</p>
        <p>{KNOWN_PLOT_TYPES}</p>
    </html>
    """,
            status_code=400)
    plotfile = PLOT_FILENAME.format(
        triggerID=triggerID, basepath=BASEPATH, plot_type=plot_type)
    if not os.path.isfile(plotfile):
        Logger.error(f"{plotfile} does not exist")
        return HTMLResponse(
                content=f"""
    <html>
        <p>{plot_type} is not a known plot format.</p>
        <p>Known plot types:</p>
        <p>{KNOWN_PLOT_TYPES}</p>
    </html>
    """,
            status_code=400)
    return FileResponse(path=plotfile)



def main():
    uvicorn.run(app, host="0.0.0.0", port=8001)    


if __name__ == "__main__":
    main()
