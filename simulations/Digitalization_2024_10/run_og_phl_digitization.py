# Need to fix references to Calculator, reform json, and substitute new tax
# function call
import multiprocessing
from distributed import Client
import os
import json
import time
import copy
import numpy as np
import importlib.resources
import matplotlib.pyplot as plt
import ogcore
from ogcore.parameters import Specifications
from ogcore import output_tables as ot
from ogcore import output_plots as op
from ogcore.execute import runner
from ogcore.utils import safe_read_pickle
from ogphl.calibrate import Calibration
from ogphl.utils import is_connected

# Use a custom matplotlib style file for plots
# plt.style.use("ogcore.OGcorePlots")


def main():
    # Define parameters to use for multiprocessing
    num_workers = min(multiprocessing.cpu_count(), 7)
    client = Client(n_workers=num_workers, threads_per_worker=1)
    print("Number of workers = ", num_workers)

    # Directories to save data
    CUR_DIR = os.path.dirname(os.path.realpath(__file__))
    save_dir = os.path.join(CUR_DIR, "DIGITIZATION")
    base_dir = os.path.join(save_dir, "OUTPUT_BASELINE")
    reform_dir = os.path.join(save_dir, "OUTPUT_REFORM")

    """
    ---------------------------------------------------------------------------
    Run baseline policy
    ---------------------------------------------------------------------------
    """
    # Set up baseline parameterization
    p = Specifications(
        baseline=True,
        num_workers=num_workers,
        baseline_dir=base_dir,
        output_base=base_dir,
    )
    # Update parameters for baseline from default json file
    with importlib.resources.open_text(
        "ogphl", "ogphl_default_parameters.json"
    ) as file:
        defaults = json.load(file)
    p.update_specifications(defaults)
    p.M = 2  # 7 number of industries equal to 2
    p.I = 2  # 5 number of goods equal to 2
    # Update parameters from calibrate.py Calibration class
    # c = Calibration(p)
    # d = c.get_dict()
    # updated_params = {
    #     "gamma_g": [0.0] * p.M,
    #     "epsilon": [1.0] * p.M,
    #     "gamma": [0.588] * p.M,  #TODO: see if can find diff by industry
    #      "cit_rate": [[0.25], [0.25]], #[[0.25], [0.25], [0.25], [0.25], [0.25], [0.25], [0.25]],  # TODO: see if can find diff by industry
    #     "tau_c": [[0.11], [0.11]], #[[0.11], [0.11], [0.11], [0.11], [0.11]],  # TODO: see if can find diff by cons good
    #     "alpha_c": [0.7, 0.3], #d["alpha_c"],
    #     "io_matrix": np.eye(2) #d["io_matrix"],
    # }
    # p.update_specifications(updated_params)
    telecom_spec = {
        "M": 2,
        "I": 2,
        "gamma_g": [
            0.02,
            0.02,
        ],  # need to set production function params to for two industries
        "epsilon": [1.0, 1.0],
        "gamma": [
            0.20,
            0.28,
        ],  # assumption for capital share to output (first sector is telecom)
        "cit_rate": [[0.12], [0.15]],  # same CIT for telecom and other sectors
        "tau_c": [[0.12], [0.12]],  # same VAT for telecom and other sectors
        "alpha_c": [
            0.023,
            0.977,
        ],
        "io_matrix": np.eye(2),
        "RC_TPI": 0.01,
    }
    p.update_specifications(telecom_spec)

    # Run model
    #start_time = time.time()
    #runner(p, time_path=True, client=client)
    #print("run time = ", time.time() - start_time)
    #client.close()

    """
    ---------------------------------------------------------------------------
    Run reform policy
    ---------------------------------------------------------------------------
    """
    client = Client(n_workers=num_workers, threads_per_worker=1)

    # create new Specifications object for reform simulation
    p2 = copy.deepcopy(p)
    p2.baseline = False
    p2.output_base = reform_dir

    # Parameter change for the reform run: shock TFP for telecom
    e_new = p2.e[0, :, :] * 1.005
    updated_params_ref = {
        "delta_annual": 0.045,
        "e": e_new,
    }
    p2.update_specifications(updated_params_ref)
    #increasing the share of telecom to people's total consumption
    p2.update_specifications(updated_params_ref)

    # Run model
    start_time = time.time()
    runner(p2, time_path=True, client=client)
    print("run time = ", time.time() - start_time)
    client.close()

    """
    ---------------------------------------------------------------------------
    Save some results of simulations
    ---------------------------------------------------------------------------
    """
    base_tpi = safe_read_pickle(os.path.join(base_dir, "TPI", "TPI_vars.pkl"))
    base_params = safe_read_pickle(os.path.join(base_dir, "model_params.pkl"))
    reform_tpi = safe_read_pickle(
        os.path.join(reform_dir, "TPI", "TPI_vars.pkl")
    )
    reform_params = safe_read_pickle(
        os.path.join(reform_dir, "model_params.pkl")
    )
    ans = ot.macro_table(
        base_tpi,
        base_params,
        reform_tpi=reform_tpi,
        reform_params=reform_params,
        var_list=["Y", "C", "K", "L", "r", "w"],
        output_type="pct_change",
        num_years=10,
        start_year=base_params.start_year,
    )

    # create plots of output
    op.plot_all(
        base_dir,
        reform_dir,
        os.path.join(save_dir, "OG-PHL_Digitization_plots"),
    )

    print("Percentage changes in aggregates:", ans)
    # save percentage change output to csv file
    ans.to_csv(os.path.join(save_dir, "OG-PHL_Digitization_output1.csv"))


if __name__ == "__main__":
    # execute only if run as a script
    main()
